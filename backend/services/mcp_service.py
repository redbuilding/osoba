import asyncio
import re
import logging
import os
import time
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field

from fastapi import HTTPException
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from core.config import BASE_DIR, WEB_SEARCH_SERVICE_NAME, MYSQL_DB_SERVICE_NAME, HUBSPOT_SERVICE_NAME, YOUTUBE_SERVICE_NAME, PYTHON_SERVICE_NAME, CODEX_SERVICE_NAME, CANVA_SERVICE_NAME, DISABLED_MCP_SERVICES, get_logger

logger = get_logger("mcp_service")

@dataclass
class MCPServiceConfig:
    name: str
    script_name: str
    executable: str = "fastmcp"
    command_verb: str = "run"
    required_tools: List[str] = field(default_factory=list)
    enabled: bool = True

    @property
    def full_command(self) -> List[str]:
        if self.executable == "python":
            return ["python", os.path.join(BASE_DIR, self.script_name)]
        return [self.executable, self.command_verb, os.path.join(BASE_DIR, self.script_name)]

class AppState:
    def __init__(self):
        self.mcp_tasks: Dict[str, asyncio.Task] = {}
        self.mcp_service_queues: Dict[str, asyncio.Queue] = {}  # request queues only
        self.mcp_pending_futures: Dict[str, Dict[str, asyncio.Future]] = {}  # service -> {req_id -> Future}
        self.mcp_service_ready: Dict[str, bool] = {}
        self.mcp_configs: Dict[str, MCPServiceConfig] = {
            WEB_SEARCH_SERVICE_NAME: MCPServiceConfig(
                name=WEB_SEARCH_SERVICE_NAME,
                script_name="server_search.py",
                required_tools=["web_search", "smart_search_extract", "image_search", "news_search"]
            ),
            MYSQL_DB_SERVICE_NAME: MCPServiceConfig(
                name=MYSQL_DB_SERVICE_NAME,
                script_name="server_mysql.py",
                required_tools=["execute_sql_query_tool"],
            ),
            HUBSPOT_SERVICE_NAME: MCPServiceConfig(
                name=HUBSPOT_SERVICE_NAME,
                script_name="server_hubspot.py",
                required_tools=["create_hubspot_marketing_email", "update_hubspot_marketing_email"]
            ),
            YOUTUBE_SERVICE_NAME: MCPServiceConfig(
                name=YOUTUBE_SERVICE_NAME,
                script_name="server_youtube.py",
                required_tools=["get_youtube_transcript"]
            ),
            PYTHON_SERVICE_NAME: MCPServiceConfig(
                name=PYTHON_SERVICE_NAME,
                script_name="server_python.py",
                executable="fastmcp",
                command_verb="run",
                required_tools=["load_csv", "get_head", "create_plot", "get_descriptive_statistics", 
                              "get_data_info", "filter_dataframe", "group_and_aggregate", 
                              "detect_outliers", "convert_data_types", "perform_hypothesis_test"]
            ),
            CODEX_SERVICE_NAME: MCPServiceConfig(
                name=CODEX_SERVICE_NAME,
                script_name="server_codex.py",
                executable="fastmcp",
                command_verb="run",
                required_tools=["create_workspace", "start_codex_run", "get_codex_run", "read_file", "get_manifest", "cleanup_workspace"]
            ),
            CANVA_SERVICE_NAME: MCPServiceConfig(
                name=CANVA_SERVICE_NAME,
                script_name="server_canva.py",
                required_tools=["create_design", "list_designs", "get_design", "export_design"],
            ),
        }

app_state = AppState()

def _resolve_future(service_name: str, request_id: str, result: Dict):
    """Resolve a pending future for a completed request."""
    futures = app_state.mcp_pending_futures.get(service_name, {})
    fut = futures.pop(request_id, None)
    if fut and not fut.done():
        fut.set_result(result)

async def run_mcp_service_instance(config: MCPServiceConfig):
    service_name = config.name
    logger.info(f"MCP_SERVICE ({service_name}): Starting STDIO client loop...")
    app_state.mcp_service_ready[service_name] = False

    request_q = asyncio.Queue()
    app_state.mcp_service_queues[service_name] = request_q
    app_state.mcp_pending_futures[service_name] = {}

    transport = StdioTransport(
        command=config.full_command[0],
        args=config.full_command[1:],
        cwd=BASE_DIR
    )

    while True:
        try:
            logger.info(f"MCP_SERVICE ({service_name}): Launching subprocess...")
            async with Client(transport) as client:
                logger.info(f"MCP_SERVICE ({service_name}): Connected. Listing tools...")

                tools = await client.list_tools()
                available_tool_names = [tool.name for tool in tools]
                logger.info(f"MCP_SERVICE ({service_name}): Available tools: {available_tool_names}")

                all_required_found = all(req_tool in available_tool_names for req_tool in config.required_tools) if config.required_tools else True

                if all_required_found:
                    app_state.mcp_service_ready[service_name] = True
                    logger.info(f"MCP_SERVICE ({service_name}): Service fully initialized and all required tools are available.")
                else:
                    app_state.mcp_service_ready[service_name] = False
                    missing_tools = [t for t in config.required_tools if t not in available_tool_names]
                    logger.error(f"MCP_SERVICE ({service_name}): CRITICAL: Required tools NOT FOUND: {missing_tools}")

                if app_state.mcp_service_ready.get(service_name, False):
                    while True:
                        try:
                            request_data = request_q.get_nowait()
                            request_id = request_data["id"]
                            request_type = request_data.get("type", "tool")

                            try:
                                start_time = time.time()
                                if request_type == "tool":
                                    tool_to_call = request_data["tool"]
                                    params = request_data["params"]
                                    logger.debug(f"MCP_SERVICE ({service_name}): Calling TOOL '{tool_to_call}' (req_id: {request_id})")
                                    result = await client.call_tool(tool_to_call, arguments=params)
                                    duration = time.time() - start_time
                                    logger.info(f"MCP_SERVICE ({service_name}): TOOL '{tool_to_call}' completed in {duration:.2f}s (req_id: {request_id})")

                                    response_data = []
                                    for part in result.content:
                                        if hasattr(part, 'type') and part.type == 'text' and hasattr(part, 'text'):
                                            response_data.append({"type": "text", "content": part.text})
                                        elif hasattr(part, 'type') and part.type == 'image' and hasattr(part, 'data'):
                                            response_data.append({"type": "image", "mimeType": part.mimeType, "data": part.data})
                                        else:
                                            response_data.append({"type": "unknown", "content": str(part)})

                                    _resolve_future(service_name, request_id, {"id": request_id, "status": "success", "data": response_data})

                                elif request_type == "resource":
                                    uri_to_get = request_data["uri"]
                                    logger.debug(f"MCP_SERVICE ({service_name}): Getting RESOURCE '{uri_to_get}' (req_id: {request_id})")
                                    resource_result = await client.read_resource(uri_to_get)
                                    duration = time.time() - start_time
                                    logger.info(f"MCP_SERVICE ({service_name}): RESOURCE '{uri_to_get}' completed in {duration:.2f}s (req_id: {request_id})")

                                    resource_content = str(resource_result)
                                    if hasattr(resource_result, 'contents') and resource_result.contents:
                                        resource_content = resource_result.contents[0].text if resource_result.contents[0].text else str(resource_result.contents[0])
                                    elif hasattr(resource_result, 'content'):
                                        resource_content = resource_result.content

                                    _resolve_future(service_name, request_id, {"id": request_id, "status": "success", "data": resource_content})
                                else:
                                    _resolve_future(service_name, request_id, {"id": request_id, "status": "error", "error": f"Unknown request type: {request_type}"})

                            except Exception as e_mcp_call:
                                call_target = request_data.get("tool", request_data.get("uri", "N/A"))
                                logger.error(f"MCP_SERVICE ({service_name}): Error in '{request_type}' call to '{call_target}': {e_mcp_call}", exc_info=True)
                                _resolve_future(service_name, request_id, {"id": request_id, "status": "error", "error": str(e_mcp_call)})
                            request_q.task_done()
                        except asyncio.QueueEmpty:
                            await asyncio.sleep(0.01)
        except Exception as e_generic:
            logger.error(f"MCP_SERVICE ({service_name}): Generic Exception (subprocess might have failed): {e_generic}", exc_info=True)
        finally:
            app_state.mcp_service_ready[service_name] = False
            # Fail all pending futures so callers don't hang
            for req_id, fut in list(app_state.mcp_pending_futures.get(service_name, {}).items()):
                if not fut.done():
                    fut.set_result({"id": req_id, "status": "error", "error": "MCP service connection lost"})
            app_state.mcp_pending_futures[service_name] = {}
            logger.info(f"MCP_SERVICE ({service_name}): Connection lost or subprocess ended. Will attempt to reconnect after 10s.")
            await asyncio.sleep(10)

async def submit_mcp_request(service_name: str, request_type: str, payload: Dict[str, Any]) -> str:
    if service_name not in app_state.mcp_service_queues:
        raise HTTPException(status_code=503, detail=f"MCP service '{service_name}' is not available.")

    request_q = app_state.mcp_service_queues[service_name]

    if request_type == "tool":
        tool_name = payload.get("tool")
        request_id = f"tool_req_{service_name}_{tool_name}_{time.time()}"
        await request_q.put({"id": request_id, "type": "tool", "tool": tool_name, "params": payload.get("params")})
    elif request_type == "resource":
        uri = payload.get("uri")
        safe_uri_part = re.sub(r'[^a-zA-Z0-9_-]', '', uri.split("://")[-1])
        request_id = f"res_req_{service_name}_{safe_uri_part}_{time.time()}"
        await request_q.put({"id": request_id, "type": "resource", "uri": uri})
    else:
        raise ValueError("Invalid MCP request type")

    # Create a Future for this request
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    app_state.mcp_pending_futures.setdefault(service_name, {})[request_id] = fut

    return request_id

async def wait_mcp_response(service_name: str, request_id: str, timeout: int = 45) -> Dict:
    futures = app_state.mcp_pending_futures.get(service_name, {})
    fut = futures.get(request_id)
    if not fut:
        return {"id": request_id, "status": "error", "error": f"No pending request found for {request_id}"}

    try:
        result = await asyncio.wait_for(fut, timeout=timeout)
        return result
    except asyncio.TimeoutError:
        futures.pop(request_id, None)
        return {"id": request_id, "status": "error", "error": "Request timed out"}
    except Exception as e:
        logger.error(f"MCP_RESPONSE_WAIT ({service_name}): Error waiting for {request_id}: {e}", exc_info=True)
        futures.pop(request_id, None)
        return {"id": request_id, "status": "error", "error": f"Exception while waiting: {str(e)}"}

def start_mcp_services():
    logger.info("FastAPI Lifespan: Startup sequence initiated.")
    if DISABLED_MCP_SERVICES:
        logger.info(f"FastAPI Lifespan: Disabled MCP services from env: {DISABLED_MCP_SERVICES}")
    for service_name, config in app_state.mcp_configs.items():
        if service_name in DISABLED_MCP_SERVICES:
            config.enabled = False
        if config.enabled:
            task = asyncio.create_task(run_mcp_service_instance(config))
            app_state.mcp_tasks[service_name] = task
            logger.info(f"FastAPI Lifespan: MCP service task created for '{service_name}'.")
        else:
            logger.info(f"FastAPI Lifespan: MCP service '{service_name}' is disabled.")
            app_state.mcp_service_ready[service_name] = False

async def stop_mcp_services():
    logger.info("FastAPI Lifespan: Shutdown sequence initiated.")
    for service_name, task in app_state.mcp_tasks.items():
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"FastAPI Lifespan: MCP service task for '{service_name}' successfully cancelled.")
            except Exception as e:
                logger.error(f"FastAPI Lifespan: Error during MCP service task '{service_name}' shutdown: {e}", exc_info=True)
