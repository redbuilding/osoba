import asyncio
import re
import logging
import os
import time
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field

from fastapi import HTTPException
from fastmcp.client.transports import StdioServerParameters, stdio_client
from mcp import ClientSession

from core.config import BASE_DIR, WEB_SEARCH_SERVICE_NAME, MYSQL_DB_SERVICE_NAME, HUBSPOT_SERVICE_NAME, YOUTUBE_SERVICE_NAME, PYTHON_SERVICE_NAME, get_logger

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
        self.mcp_service_queues: Dict[str, Tuple[asyncio.Queue, asyncio.Queue]] = {}
        self.mcp_service_ready: Dict[str, bool] = {}
        self.mcp_configs: Dict[str, MCPServiceConfig] = {
            WEB_SEARCH_SERVICE_NAME: MCPServiceConfig(
                name=WEB_SEARCH_SERVICE_NAME,
                script_name="server_search.py",
                required_tools=["web_search"]
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
        }

app_state = AppState()

async def run_mcp_service_instance(config: MCPServiceConfig):
    service_name = config.name
    logger.info(f"MCP_SERVICE ({service_name}): Starting STDIO client loop...")
    app_state.mcp_service_ready[service_name] = False

    request_q = asyncio.Queue()
    response_q = asyncio.Queue()
    app_state.mcp_service_queues[service_name] = (request_q, response_q)

    server_params = StdioServerParameters(
        command=config.full_command[0],
        args=config.full_command[1:],
        cwd=BASE_DIR
    )

    while True:
        try:
            logger.info(f"MCP_SERVICE ({service_name}): Launching subprocess with params: {server_params}")
            async with stdio_client(server_params) as streams:
                read_stream, write_stream = streams
                logger.info(f"MCP_SERVICE ({service_name}): Connected to subprocess. Initializing ClientSession...")

                async with ClientSession(read_stream, write_stream) as session:
                    logger.info(f"MCP_SERVICE ({service_name}): ClientSession created. Initializing session...")
                    await session.initialize()
                    logger.info(f"MCP_SERVICE ({service_name}): Session initialized. Listing tools...")

                    tools_response = await session.list_tools()
                    logger.debug(f"MCP_SERVICE ({service_name}): Raw tools_response: {tools_response!r}")

                    if tools_response and tools_response.tools is not None:
                        available_tool_names = [tool.name for tool in tools_response.tools]
                        logger.info(f"MCP_SERVICE ({service_name}): Available tools: {available_tool_names}")

                        all_required_found = all(req_tool in available_tool_names for req_tool in config.required_tools) if config.required_tools else True

                        if all_required_found:
                            app_state.mcp_service_ready[service_name] = True
                            logger.info(f"MCP_SERVICE ({service_name}): Service fully initialized and all required tools are available.")
                        else:
                            app_state.mcp_service_ready[service_name] = False
                            missing_tools = [t for t in config.required_tools if t not in available_tool_names]
                            logger.error(f"MCP_SERVICE ({service_name}): CRITICAL: Required tools NOT FOUND: {missing_tools}")
                    else:
                        logger.error(f"MCP_SERVICE ({service_name}): CRITICAL: No tools found or invalid response from list_tools().")
                        app_state.mcp_service_ready[service_name] = False

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
                                        result = await session.call_tool(tool_to_call, params)
                                        duration = time.time() - start_time
                                        logger.info(f"MCP_SERVICE ({service_name}): TOOL '{tool_to_call}' completed in {duration:.2f}s (req_id: {request_id})")

                                        # Handle complex content (text and images)
                                        response_data = []
                                        content = result.content

                                        # Handle new-style list of dicts from refactored python server
                                        if isinstance(content, list) and content and all(isinstance(item, dict) and 'type' in item for item in content):
                                            response_data = content
                                        # Handle old-style list of mcp.types objects for compatibility
                                        elif content and isinstance(content, list):
                                            for part in content:
                                                if hasattr(part, 'type') and part.type == 'text' and hasattr(part, 'text'):
                                                    response_data.append({"type": "text", "content": part.text})
                                                elif hasattr(part, 'type') and part.type == 'image' and hasattr(part, 'data'):
                                                    response_data.append({"type": "image", "mimeType": part.mimeType, "data": part.data})
                                                else:
                                                    response_data.append({"type": "unknown", "content": str(part)})
                                        # Handle simple string/dict returns from other fastmcp tools
                                        else:
                                            response_data.append({"type": "text", "content": str(content)})

                                        await response_q.put({"id": request_id, "status": "success", "data": response_data})

                                    elif request_type == "resource":
                                        uri_to_get = request_data["uri"]
                                        logger.debug(f"MCP_SERVICE ({service_name}): Getting RESOURCE '{uri_to_get}' (req_id: {request_id})")
                                        resource_result = await session.read_resource(uri_to_get)
                                        duration = time.time() - start_time
                                        logger.info(f"MCP_SERVICE ({service_name}): RESOURCE '{uri_to_get}' completed in {duration:.2f}s (req_id: {request_id})")

                                        resource_content = str(resource_result)
                                        if hasattr(resource_result, 'contents') and resource_result.contents:
                                            resource_content = resource_result.contents[0].text if resource_result.contents[0].text else str(resource_result.contents[0])
                                        elif hasattr(resource_result, 'content'):
                                            resource_content = resource_result.content

                                        await response_q.put({"id": request_id, "status": "success", "data": resource_content})
                                    else:
                                        await response_q.put({"id": request_id, "status": "error", "error": f"Unknown request type: {request_type}"})

                                except Exception as e_mcp_call:
                                    call_target = request_data.get("tool", request_data.get("uri", "N/A"))
                                    logger.error(f"MCP_SERVICE ({service_name}): Error in '{request_type}' call to '{call_target}': {e_mcp_call}", exc_info=True)
                                    await response_q.put({"id": request_id, "status": "error", "error": str(e_mcp_call)})
                                request_q.task_done()
                            except asyncio.QueueEmpty:
                                await asyncio.sleep(0.01)
        except Exception as e_generic:
            logger.error(f"MCP_SERVICE ({service_name}): Generic Exception (subprocess might have failed): {e_generic}", exc_info=True)
        finally:
            app_state.mcp_service_ready[service_name] = False
            logger.info(f"MCP_SERVICE ({service_name}): Connection lost or subprocess ended. Will attempt to reconnect after 10s.")
            await asyncio.sleep(10)

async def submit_mcp_request(service_name: str, request_type: str, payload: Dict[str, Any]) -> str:
    if service_name not in app_state.mcp_service_queues:
        raise HTTPException(status_code=503, detail=f"MCP service '{service_name}' is not available.")

    request_q, _ = app_state.mcp_service_queues[service_name]

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

    return request_id

async def wait_mcp_response(service_name: str, request_id: str, timeout: int = 45) -> Dict:
    if service_name not in app_state.mcp_service_queues:
        return {"id": request_id, "status": "error", "error": f"MCP service '{service_name}' queues not found."}

    _, response_q = app_state.mcp_service_queues[service_name]
    start_time = time.time()
    try:
        while time.time() - start_time < timeout:
            try:
                item = await asyncio.wait_for(response_q.get(), timeout=0.1)
                if item.get("id") == request_id:
                    response_q.task_done()
                    return item
                else:
                    logger.warning(f"MCP_RESPONSE_WAIT ({service_name}): Received item for unexpected ID {item.get('id')}, expected {request_id}. Re-queuing.")
                    await response_q.put(item)
            except asyncio.TimeoutError:
                pass
    except Exception as e:
        logger.error(f"MCP_RESPONSE_WAIT ({service_name}): Error waiting for response for {request_id}: {e}", exc_info=True)
        return {"id": request_id, "status": "error", "error": f"Exception while waiting for MCP response: {str(e)}"}

    return {"id": request_id, "status": "error", "error": "Request timed out"}

def start_mcp_services():
    logger.info("FastAPI Lifespan: Startup sequence initiated.")
    for service_name, config in app_state.mcp_configs.items():
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
