import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union, AsyncGenerator

from bson import ObjectId
from fastapi import Request

from core.config import (
    get_logger, WEB_SEARCH_SERVICE_NAME, MYSQL_DB_SERVICE_NAME, HUBSPOT_SERVICE_NAME, YOUTUBE_SERVICE_NAME,
    PYTHON_SERVICE_NAME, MAX_DB_RESULT_CHARS, MAX_TABLES_FOR_SCHEMA_CONTEXT, DEFAULT_REPEAT_PENALTY
)
from core.models import ChatPayload, ChatMessage, ChatResponse
from db.mongodb import get_conversations_collection
from services.mcp_service import app_state, submit_mcp_request, wait_mcp_response
from services.llm_service import get_default_ollama_model
from services.provider_service import chat_with_provider, stream_chat_with_provider
from services.profile_service import get_system_prompt_for_user
from auth_hubspot import get_valid_token, SESSION_COOKIE_NAME

logger = get_logger("chat_service")

# --- Result Formatting Helpers ---

def extract_json_from_response(response_content: Any) -> Dict:
    logger.debug(f"extract_json: Input type: {type(response_content)}, content preview: {str(response_content)[:200]}")
    # Already a dict
    if isinstance(response_content, dict):
        return response_content

    # Common case: JSON string
    if isinstance(response_content, str):
        try:
            return json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(f"extract_json: Failed to decode JSON string: {response_content[:200]}")
            return {"status": "error", "message": "Result was a string but not valid JSON."}

    # Newer MCP tool responses often come back as a list of content blocks
    # e.g., [{"type": "text", "content": "{...json...}"}]
    if isinstance(response_content, list):
        # Try to find a text block and parse its content as JSON
        for item in response_content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("content"), str):
                try:
                    return json.loads(item["content"])
                except json.JSONDecodeError:
                    logger.error(f"extract_json: List item text not valid JSON: {item.get('content', '')[:200]}")
                    return {"status": "error", "message": "List contained text content but it was not valid JSON."}
        # Fallback: if first element is a plain JSON string
        if response_content and isinstance(response_content[0], str):
            try:
                return json.loads(response_content[0])
            except json.JSONDecodeError:
                logger.error(f"extract_json: First list element is a string but not valid JSON: {response_content[0][:200]}")
                return {"status": "error", "message": "First list element was a string but not valid JSON."}
        logger.error(f"extract_json: List response did not contain parsable JSON text. Preview: {str(response_content)[:200]}")
        return {"status": "error", "message": "List response did not contain a recognizable JSON text block."}

    # Some HTTP client objects expose .text
    if hasattr(response_content, 'text') and isinstance(getattr(response_content, 'text', None), str):
        try:
            return json.loads(response_content.text)
        except json.JSONDecodeError:
            logger.error(f"extract_json: Failed to decode JSON from .text attribute: {response_content.text[:200]}")
            return {"status": "error", "message": "Result had .text attribute but it was not valid JSON."}

    logger.error(f"extract_json: Unhandled type or content: {type(response_content)}. Preview: {str(response_content)[:200]}")
    return {"status": "error", "message": f"Result was not a recognized JSON format. Type: {type(response_content)}"}

def format_search_results_for_prompt(results_data, query, max_results=3):
    if not isinstance(results_data, dict) or results_data.get("status") == "error":
        return f"Search for '{query}': {results_data.get('message', 'Error or no valid results structure.')}"
    organic = results_data.get('organic_results', [])
    if organic and isinstance(organic, list):
        formatted = [f"{i+1}. {item.get('title', 'N/A')}\n   {item.get('snippet', 'N/A')}\n   Source: {item.get('link', 'N/A')}" for i, item in enumerate(organic[:max_results]) if isinstance(item, dict)]
        if not formatted: return f"Search for '{query}' returned no usable organic result items."
        return f"Web search results for '{query}':\n" + "\n".join(formatted)
    answer = results_data.get('answer_box', {}).get('answer')
    if answer: return f"Web search results for '{query}':\n{answer}"
    return f"Search for '{query}' returned no specific organic results or answer box."

def format_db_results_for_prompt(query: str, db_results: Union[Dict, List], max_chars: int) -> str:
    if not db_results: return f"Database query '{query}' yielded no results."
    try:
        data = json.loads(db_results) if isinstance(db_results, str) else db_results
        if isinstance(data, dict) and "error" in data: return f"Database query '{query}' failed: {data['error']}"
        if isinstance(data, dict) and "rows" in data:
            rows, cols = data["rows"], data.get("columns", [])
            if not rows: return f"Database query '{query}' returned no rows."
            header = f"| {' | '.join(map(str, cols))} |" if cols else ""
            lines = [header, f"|{'---|' * len(cols)}"] if header else []
            for row in rows:
                values = [str(row.get(c, "")) for c in cols] if isinstance(row, dict) and cols else [str(v) for v in (row.values() if isinstance(row, dict) else row)]
                lines.append(f"| {' | '.join(values)} |")
                if len("\n".join(lines)) > max_chars:
                    lines.append(f"... (results truncated at {max_chars} chars)")
                    break
            return f"Database query results for '{query}':\n" + "\n".join(lines)
        else:
            formatted_str = f"Database query results for '{query}':\n{json.dumps(data, indent=2)}"
            return formatted_str[:max_chars-25] + "... (results truncated)" if len(formatted_str) > max_chars else formatted_str
    except Exception as e:
        logger.error(f"Error formatting DB results: {e}", exc_info=True)
        return f"Error formatting database results for query '{query}': {str(e)}"

# --- Main Chat Logic ---

class ChatProcessor:
    def __init__(self, request: Request, payload: ChatPayload):
        self.request = request
        self.payload = payload
        self.collection = get_conversations_collection()
        self.user_msg_content = payload.user_message
        self.conv_id = payload.conversation_id
        self.obj_id: Optional[ObjectId] = None
        self.llm_history: List[Dict[str, str]] = []
        self.ui_history: List[ChatMessage] = []
        self.model_name: Optional[str] = None
        self.prompt_for_llm = self.user_msg_content
        self.html_indicator = ""
        self.is_html_response = False
        self.error_message_obj: Optional[ChatMessage] = None
        self.youtube_transcript: Optional[str] = None
        self.python_df_id: Optional[str] = None

    async def _initialize_conversation(self):
        if self.conv_id:
            if not ObjectId.is_valid(self.conv_id): raise ValueError("Invalid conv_id.")
            self.obj_id = ObjectId(self.conv_id)
            conv = self.collection.find_one({"_id": self.obj_id})
            if not conv: raise ValueError(f"Conv ID '{self.conv_id}' not found.")
            self.model_name = conv.get("model_name") or conv.get("ollama_model_name")  # Support both old and new field names
            self.youtube_transcript = conv.get("youtube_transcript")
            self.python_df_id = conv.get("python_df_id")
            for msg in conv.get("messages", []):
                if 'role' in msg and 'content' in msg:
                    llm_content = msg.get("raw_content_for_llm", msg["content"])
                    self.llm_history.append({"role": msg["role"], "content": llm_content})
                self.ui_history.append(ChatMessage(**msg))

        if not self.model_name:
            self.model_name = self.payload.model_name or await get_default_ollama_model()

        if not self.conv_id:
            new_title = f"Chat: {self.user_msg_content[:30]}{'...' if len(self.user_msg_content) > 30 else ''}"
            new_doc = {"title": new_title, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "messages": [], "model_name": self.model_name}
            res = self.collection.insert_one(new_doc)
            self.conv_id = str(res.inserted_id)
            self.obj_id = res.inserted_id

        user_chat_msg = ChatMessage(role="user", content=self.user_msg_content)
        self.ui_history.append(user_chat_msg)
        user_msg_to_save = user_chat_msg.model_dump(exclude_none=True)
        user_msg_to_save["raw_content_for_llm"] = self.user_msg_content
        self.collection.update_one({"_id": self.obj_id}, {"$push": {"messages": user_msg_to_save}, "$set": {"updated_at": datetime.now(timezone.utc)}})

    def _add_indicator(self, html: str):
        self.html_indicator += html
        self.is_html_response = True

    def _set_error(self, content: str):
        self.error_message_obj = ChatMessage(role="assistant", content=content)

    async def _handle_search(self):
        if not app_state.mcp_service_ready.get(WEB_SEARCH_SERVICE_NAME):
            return self._set_error("⚠️ Web search is currently unavailable.")
        logger.info(f"[CHAT_SVC] Smart web search for: '{self.user_msg_content}'")
        try:
            # Use smart_search_extract for enhanced content extraction
            req_id = await submit_mcp_request(WEB_SEARCH_SERVICE_NAME, "tool", {
                "tool": "smart_search_extract", 
                "params": {
                    "query": self.user_msg_content,
                    "max_urls": 3,
                    "max_chars_per_url": 2000,
                    "max_total_chars": 5000
                }
            })
            resp = await wait_mcp_response(WEB_SEARCH_SERVICE_NAME, req_id, timeout=120)  # Longer timeout for extraction
            if resp.get("status") == "error": raise Exception(resp.get("error", "MCP tool error"))

            results = extract_json_from_response(resp.get("data")[0].get("content") if resp.get("data") else {})
            if results.get("status") == "error": raise Exception(results.get("message", "Parse error"))

            # Format smart extraction results for LLM context
            summary = self._format_smart_search_results(results, self.user_msg_content)
            self._add_indicator(f"<div class='search-indicator-custom'><b>🧠 Smart Search:</b> Extracted content from {len(results.get('extracted_content', []))} webpages for \"{self.user_msg_content}\".</div>")
            self.prompt_for_llm = f"Based on smart web search and content extraction for '{self.user_msg_content}':\n{summary}\n\nPlease answer the user's original question: '{self.user_msg_content}'"
        except Exception as e:
            logger.error(f"[CHAT_SVC] Smart web search failed: {e}", exc_info=True)
            self._set_error(f"⚠️ Smart web search failed: {str(e)}")

    def _format_smart_search_results(self, results_data: dict, query: str) -> str:
        """Format smart search extraction results for LLM context"""
        if not isinstance(results_data, dict) or results_data.get("status") == "error":
            return f"Smart search for '{query}': {results_data.get('message', 'Error or no valid results structure.')}"
        
        formatted_parts = []
        
        # Add search summary
        search_summary = results_data.get('search_summary', {})
        if search_summary:
            total_results = search_summary.get('total_results', 0)
            formatted_parts.append(f"Found {total_results} search results for '{query}'")
        
        # Add extracted content from webpages
        extracted_content = results_data.get('extracted_content', [])
        if extracted_content:
            formatted_parts.append("\n--- EXTRACTED WEBPAGE CONTENT ---")
            for i, content in enumerate(extracted_content, 1):
                if content.get('status') == 'success' and content.get('content'):
                    title = content.get('title', 'Untitled')
                    url = content.get('url', 'Unknown URL')
                    webpage_content = content.get('content', '')
                    method = content.get('extraction_method', 'unknown')
                    
                    formatted_parts.append(f"\n{i}. {title}")
                    formatted_parts.append(f"   Source: {url}")
                    formatted_parts.append(f"   Extraction: {method}")
                    formatted_parts.append(f"   Content:\n{webpage_content}")
                elif content.get('status') == 'error':
                    title = content.get('title', 'Untitled')
                    url = content.get('url', 'Unknown URL')
                    error = content.get('error', 'Unknown error')
                    formatted_parts.append(f"\n{i}. {title} (EXTRACTION FAILED)")
                    formatted_parts.append(f"   Source: {url}")
                    formatted_parts.append(f"   Error: {error}")
        
        # Add extraction statistics
        extraction_stats = results_data.get('extraction_stats', {})
        if extraction_stats:
            urls_processed = extraction_stats.get('urls_processed', 0)
            successful = extraction_stats.get('successful_extractions', 0)
            total_chars = extraction_stats.get('total_chars_extracted', 0)
            formatted_parts.append(f"\n--- EXTRACTION SUMMARY ---")
            formatted_parts.append(f"URLs processed: {urls_processed}, Successful: {successful}, Total content: {total_chars} characters")
        
        # Fallback to basic search results if no extracted content
        if not extracted_content:
            organic_results = results_data.get('organic_results', [])
            if organic_results:
                formatted_parts.append("\n--- SEARCH RESULTS (NO CONTENT EXTRACTED) ---")
                for i, result in enumerate(organic_results[:3], 1):
                    title = result.get('title', 'N/A')
                    snippet = result.get('snippet', 'N/A')
                    link = result.get('link', 'N/A')
                    formatted_parts.append(f"{i}. {title}\n   {snippet}\n   Source: {link}")
        
        return "\n".join(formatted_parts) if formatted_parts else f"Smart search for '{query}' returned no usable results."

    async def _handle_database(self):
        if not app_state.mcp_service_ready.get(MYSQL_DB_SERVICE_NAME):
            return self._set_error("⚠️ Database interaction is currently unavailable.")
        logger.info(f"[CHAT_SVC] DB interaction for: '{self.user_msg_content}'")
        try:
            # Get schema
            tables_req_id = await submit_mcp_request(MYSQL_DB_SERVICE_NAME, "resource", {"uri": "resource://tables"})
            tables_resp = await wait_mcp_response(MYSQL_DB_SERVICE_NAME, tables_req_id)
            tables_data = extract_json_from_response(tables_resp.get("data"))

            schema_parts = []
            if isinstance(tables_data, list) and tables_data:
                schema_parts.append(f"Available tables: {', '.join(tables_data)}.")
                for table_name in tables_data[:MAX_TABLES_FOR_SCHEMA_CONTEXT]:
                    schema_req_id = await submit_mcp_request(MYSQL_DB_SERVICE_NAME, "resource", {"uri": f"resource://tables/{table_name}/schema"})
                    schema_resp = await wait_mcp_response(MYSQL_DB_SERVICE_NAME, schema_req_id)
                    schema_data = extract_json_from_response(schema_resp.get("data"))
                    schema_str = f"\nTable: {table_name}\n" + ('\n'.join([f"- {c.get('Field', 'N/A')}: {c.get('Type', 'N/A')}" for c in schema_data]) if isinstance(schema_data, list) else f"  Could not parse schema: {str(schema_data)[:100]}")
                    schema_parts.append(schema_str)
                if len(tables_data) > MAX_TABLES_FOR_SCHEMA_CONTEXT:
                    schema_parts.append(f"\n...and {len(tables_data) - MAX_TABLES_FOR_SCHEMA_CONTEXT} more tables.")
            else:
                raise Exception(f"Could not retrieve table list. Response: {tables_data}")

            full_schema_context = "\n".join(schema_parts)

            # Generate and execute SQL with retry
            extracted_sql, db_results_data = None, None
            for attempt in range(2):
                system_prompt = self._get_sql_gen_prompt(attempt, full_schema_context, locals().get("previous_faulty_sql"), locals().get("previous_db_error"))
                raw_sql_resp = await chat_with_provider([{"role": "system", "content": system_prompt}, {"role": "user", "content": self.user_msg_content}], self.model_name)

                sql_match = re.search(r"```(?:sql)?\s*([\s\S]+?)\s*```", raw_sql_resp or "", re.I)
                temp_sql = (sql_match.group(1) if sql_match else (raw_sql_resp or "")).strip()

                if not temp_sql or temp_sql.upper() == "NO_QUERY_POSSIBLE":
                    raise Exception("Could not form a valid SQL query based on the schema.")
                if not temp_sql.lower().startswith("select"):
                    raise Exception("Generated query was not a SELECT statement.")

                extracted_sql = temp_sql
                query_req_id = await submit_mcp_request(MYSQL_DB_SERVICE_NAME, "tool", {"tool": "execute_sql_query_tool", "params": {"query": extracted_sql}})
                query_resp = await wait_mcp_response(MYSQL_DB_SERVICE_NAME, query_req_id)
                db_results_data = extract_json_from_response(query_resp.get("data"))

                if query_resp.get("status") == "error": raise Exception(f"MCP tool failed: {query_resp.get('error')}")

                db_error = db_results_data.get("error")
                if db_error:
                    is_recoverable = any(k in str(db_error).lower() for k in ["unknown column", "no such table", "syntax error"])
                    if attempt == 0 and is_recoverable:
                        locals()["previous_faulty_sql"], locals()["previous_db_error"] = extracted_sql, db_error
                        logger.warning(f"Recoverable DB error on attempt 1, retrying. Error: {db_error}")
                        continue
                    else:
                        raise Exception(f"SQL execution failed: {db_error}")
                break # Success

            if db_results_data is None: raise Exception("Failed to get DB results after all attempts.")

            formatted_db_results = format_db_results_for_prompt(extracted_sql, db_results_data, MAX_DB_RESULT_CHARS)
            self._add_indicator(f"<div class='db-indicator-custom'><b>💾 Database:</b> Info from query \"{extracted_sql[:50].replace('<', '&lt;')}...\" was used.</div>")
            self.prompt_for_llm = f"Using database info for '{self.user_msg_content}':\n{formatted_db_results}\n\n{self.prompt_for_llm}"
        except Exception as e:
            logger.error(f"[CHAT_SVC] DB interaction failed: {e}", exc_info=True)
            self._set_error(f"⚠️ Database interaction failed: {str(e)}")

    def _get_sql_gen_prompt(self, attempt, schema, faulty_sql=None, db_error=None):
        if attempt == 0:
            return f"""== HARD RULES – FOLLOW STRICTLY ==
① Use only the tables and columns that appear verbatim in the **Database Schema Context** block below.
② Never invent, rename or infer table/column names.
③ Before writing SQL, silently verify every identifier exists in the schema; if any do not, output NO_QUERY_POSSIBLE.
④ Use aggregate functions (SUM, AVG, COUNT, MAX, MIN) **only if the user explicitly requests a total/average/count/etc.**
⑤ If any single part of the request cannot be mapped unambiguously to the schema, output exactly: NO_QUERY_POSSIBLE
⑥ Output only a single, read‑only SQL SELECT statement. Do not include comments, explanations, or markdown.
== DATABASE SCHEMA CONTEXT ==
###
{schema}
###"""
        else:
            return f"""Your previous SQL query attempt failed.
Original User Question: {self.user_msg_content}
Your Faulty SQL Query: {faulty_sql}
Database Error Message: {db_error}

Please re-evaluate the provided database schema and the user's question carefully.
Generate a corrected, safe, read-only SQL SELECT query.
If it's not possible, you MUST output the exact string: NO_QUERY_POSSIBLE
Otherwise, output ONLY the SQL SELECT query.

Database Schema Context:
{schema}"""

    async def _handle_hubspot(self):
        session_id = self.request.cookies.get(SESSION_COOKIE_NAME)
        access_token = await get_valid_token(session_id) if session_id else None
        if not access_token: return self._set_error("⚠️ Not connected to HubSpot. Please connect first.")
        if not app_state.mcp_service_ready.get(HUBSPOT_SERVICE_NAME): return self._set_error("⚠️ The HubSpot service is currently unavailable.")

        logger.info(f"[CHAT_SVC] HubSpot interaction for: '{self.user_msg_content}'")
        try:
            system_prompt = self._get_hubspot_json_gen_prompt()
            raw_json_resp = await chat_with_provider([{"role": "system", "content": system_prompt}, {"role": "user", "content": self.user_msg_content}], self.model_name)

            json_match = re.search(r"```json\s*([\s\S]+?)```", raw_json_resp or "", re.I)
            candidate = (json_match.group(1) if json_match else (raw_json_resp or "")).strip()

            try:
                email_payload = json.loads(candidate)
                if not isinstance(email_payload, dict): raise json.JSONDecodeError
            except json.JSONDecodeError:
                raise Exception("Could not format your request into valid JSON. Please clarify.")

            tool_params = {**email_payload, "access_token": access_token}
            missing = [k for k in ["name","subject","from_sender","to_recipients","content"] if not tool_params.get(k)]
            if missing: raise Exception(f"Missing required fields for email: {', '.join(missing)}")

            req_id = await submit_mcp_request(HUBSPOT_SERVICE_NAME, "tool", {"tool": "create_hubspot_marketing_email", "params": tool_params})
            resp = await wait_mcp_response(HUBSPOT_SERVICE_NAME, req_id, timeout=60)
            if resp.get("status") == "error": raise Exception(f"HubSpot tool failed: {resp.get('error')}")

            hubspot_api_resp = extract_json_from_response(resp.get("data")[0].get("content") if resp.get("data") else {})
            if "error" in hubspot_api_resp: raise Exception(f"HubSpot API Error: {hubspot_api_resp.get('body', 'Details unavailable.')}")

            email_name, email_id = hubspot_api_resp.get("name"), hubspot_api_resp.get("id")
            self._add_indicator("<div class='hubspot-indicator-custom'><b>🤖 HubSpot:</b> An email was created based on your request.</div>")
            self.prompt_for_llm = f"You just created a HubSpot email named '{email_name}' (ID: {email_id}). Confirm to the user that their request '{self.user_msg_content}' is complete."
        except Exception as e:
            logger.error(f"[CHAT_SVC] HubSpot interaction failed: {e}", exc_info=True)
            self._set_error(f"⚠️ HubSpot action failed: {str(e)}")

    def _get_hubspot_json_gen_prompt(self):
        return """You are a JSON‐only generator for the `create_hubspot_marketing_email` tool. Based on the user’s instruction, **output exactly one** JSON object—no prose, no markdown fences—that matches this full schema:
```json
{
"content": {"templatePath": "string", "plainTextVersion": "string"},
"from_sender": {"fromName": "string", "replyTo": "string"},
"name": "string",
"subject": "string",
"to_recipients": {"contactLists": {"include": [integer], "exclude": [integer]}},
"sendOnPublish": boolean
}
```
**Rules:**
1. Fill in *all* required fields.
2. Infer values from the user’s request.
3. If *any* required piece is missing (e.g. list IDs, templatePath), *do not* output JSON; instead respond with a natural‐language clarification question.
4. Do *not* wrap JSON in markdown or add any extra text—output *only* the JSON object."""

    async def _handle_youtube(self):
        if not app_state.mcp_service_ready.get(YOUTUBE_SERVICE_NAME):
            return self._set_error("⚠️ YouTube transcript service is currently unavailable.")
        logger.info(f"[CHAT_SVC] YouTube transcript for: '{self.user_msg_content}'")
        try:
            req_id = await submit_mcp_request(YOUTUBE_SERVICE_NAME, "tool", {"tool": "get_youtube_transcript", "params": {"youtube_url": self.user_msg_content}})
            # Transcripts can take a while
            resp = await wait_mcp_response(YOUTUBE_SERVICE_NAME, req_id, timeout=120)
            if resp.get("status") == "error":
                raise Exception(resp.get("error", "MCP tool error"))

            transcript = resp.get("data")[0].get("content") if resp.get("data") else ""
            if transcript.startswith("Error:"):
                # Pass tool-specific errors directly to the user
                self._set_error(f"⚠️ {transcript}")
                return

            # Save transcript to DB for future use in this conversation
            logger.info(f"Saving YouTube transcript to conv_id {self.conv_id}")
            self.collection.update_one(
                {"_id": self.obj_id},
                {"$set": {"youtube_transcript": transcript, "updated_at": datetime.now(timezone.utc)}}
            )
            self.youtube_transcript = transcript # Also set it on the current instance

            self._add_indicator(f"<div class='youtube-indicator-custom'><b>📺 YouTube:</b> Transcript from \"{self.user_msg_content}\" was used.</div>")
            self.prompt_for_llm = f"Based on the transcript from the YouTube video '{self.user_msg_content}', please answer the user's follow-up question. The user's question is implicitly 'summarize this' or whatever they asked. If they just provided a URL, summarize the content. Transcript:\n\n{transcript}\n\nUser's original request: '{self.user_msg_content}'"

        except Exception as e:
            logger.error(f"[CHAT_SVC] YouTube transcript failed: {e}", exc_info=True)
            self._set_error(f"⚠️ YouTube transcript failed: {str(e)}")

    async def _handle_python(self):
        if not app_state.mcp_service_ready.get(PYTHON_SERVICE_NAME):
            return self._set_error("⚠️ Python analysis service is currently unavailable.")
        logger.info(f"[CHAT_SVC] Python analysis for: '{self.user_msg_content}'")

        try:
            # Step 1: Load CSV if provided, and get a df_id
            if self.payload.csv_data_b64:
                logger.info(f"[CHAT_SVC] Loading new CSV for conv {self.conv_id}")
                req_id = await submit_mcp_request(PYTHON_SERVICE_NAME, "tool", {"tool": "load_csv", "params": {"csv_b64": self.payload.csv_data_b64}})
                resp = await wait_mcp_response(PYTHON_SERVICE_NAME, req_id)
                if resp.get("status") == "error": raise Exception(f"Failed to load CSV: {resp.get('error')}")

                # Expected response: "Successfully loaded dataframe with ID: <uuid>. ..."
                load_resp_text = resp.get("data")[0].get("content", "")
                match = re.search(r"ID: ([\w-]+)", load_resp_text)
                if not match: raise Exception(f"Could not extract dataframe ID from response: {load_resp_text}")
                self.python_df_id = match.group(1)
                self.collection.update_one({"_id": self.obj_id}, {"$set": {"python_df_id": self.python_df_id}})
                self._add_indicator(f"<div class='python-indicator-custom'><b>🐍 Python:</b> CSV loaded. Columns: {load_resp_text.split('Columns: ')[-1]}</div>")

            if not self.python_df_id:
                return self._set_error("⚠️ Please upload a CSV file to use the Python analysis tool.")

            # Step 2: Use LLM to select a tool and parameters
            tool_selection_prompt = self._get_python_tool_selection_prompt(self.python_df_id)
            raw_tool_resp = await chat_with_provider([{"role": "system", "content": tool_selection_prompt}, {"role": "user", "content": self.user_msg_content}], self.model_name)
            logger.debug(f"LLM tool selection response: {raw_tool_resp}")

            tool_json_match = re.search(r"```json\s*([\s\S]+?)\s*```", raw_tool_resp or "", re.I)
            tool_candidate = (tool_json_match.group(1) if tool_json_match else (raw_tool_resp or "")).strip()
            try:
                tool_call = json.loads(tool_candidate)
                tool_name = tool_call.get("tool_name")
                tool_params = tool_call.get("parameters", {})
                if not tool_name: raise ValueError("Missing 'tool_name'")
            except (json.JSONDecodeError, ValueError) as e:
                raise Exception(f"Could not decide which tool to use. Please clarify your request. (LLM response: {tool_candidate})")

            # Step 3: Execute the selected tool
            logger.info(f"[CHAT_SVC] Calling Python tool '{tool_name}' with params: {tool_params}")
            tool_req_id = await submit_mcp_request(PYTHON_SERVICE_NAME, "tool", {"tool": tool_name, "params": tool_params})
            tool_resp = await wait_mcp_response(PYTHON_SERVICE_NAME, tool_req_id, timeout=120) # Plotting can be slow
            if tool_resp.get("status") == "error": raise Exception(f"Python tool '{tool_name}' failed: {tool_resp.get('error')}")

            # Step 4: Format tool output for the final prompt
            tool_results_data = tool_resp.get("data", [])
            tool_output_for_prompt = ""
            for part in tool_results_data:
                if part.get("type") == "text":
                    tool_output_for_prompt += part.get("content", "") + "\n"
                elif part.get("type") == "image":
                    img_b64 = part.get("data")
                    mime_type = part.get("mimeType", "image/png")
                    self._add_indicator(f"<img src='data:{mime_type};base64,{img_b64}' alt='Generated plot' class='my-2 rounded-md border border-gray-600' />")

            self._add_indicator(f"<div class='python-indicator-custom'><b>🐍 Python:</b> Used tool <code>{tool_name}</code>.</div>")
            self.prompt_for_llm = f"Based on the result from the Python tool '{tool_name}', answer the user's original question.\n\nTool Output:\n---\n{tool_output_for_prompt.strip()}\n---\n\nUser's question: '{self.user_msg_content}'"

        except Exception as e:
            logger.error(f"[CHAT_SVC] Python analysis failed: {e}", exc_info=True)
            self._set_error(f"⚠️ Python analysis failed: {str(e)}")

    def _get_python_tool_selection_prompt(self, df_id: str) -> str:
        # In a real app, this could be dynamically generated from the tool server's list_tools response
        return f"""You are an expert data analyst agent. Your task is to select the correct Python tool and parameters to answer the user's request.
The data is already loaded in a dataframe with ID: "{df_id}". You MUST include this `df_id` in your tool parameters.

Respond with a single JSON object containing "tool_name" and "parameters". Do not add explanations.

Available Tools:
- `get_head`: Returns the first n rows of the dataframe. Params: `df_id` (str), `n` (int, optional, default 5).
- `get_descriptive_statistics`: Returns summary statistics for numerical columns. Params: `df_id` (str).
- `check_missing_values`: Counts missing values in each column. Params: `df_id` (str).
- `get_value_counts`: Gets frequency of unique values in a categorical column. Params: `df_id` (str), `column_name` (str).
- `get_correlation_matrix`: Computes correlation between numerical columns. Params: `df_id` (str).
- `query_dataframe`: Filters the dataframe with a query string. Returns a *new* dataframe ID. Use this for filtering questions. Params: `df_id` (str), `query_string` (str).
- `create_plot`: Generates a plot. Params: `df_id` (str), `plot_type` (enum: 'histogram', 'scatterplot', 'barplot', 'boxplot', 'heatmap'), `x_col` (str), `y_col` (str, optional).

Example user request: "show me the first 3 rows"
Your JSON response:
```json
{{
  "tool_name": "get_head",
  "parameters": {{
    "df_id": "{df_id}",
    "n": 3
  }}
}}
```

Example user request: "what's the average salary?"
Your JSON response:
```json
{{
  "tool_name": "get_descriptive_statistics",
  "parameters": {{
    "df_id": "{df_id}"
  }}
}}
```

Example user request: "make a scatterplot of age vs salary"
Your JSON response:
```json
{{
  "tool_name": "create_plot",
  "parameters": {{
    "df_id": "{df_id}",
    "plot_type": "scatterplot",
    "x_col": "age",
    "y_col": "salary"
  }}
}}
```
"""

    async def _inject_profile_system_prompt(self):
        """
        Inject system prompt from active AI profile and conversation context as the first message in conversation history.
        Only applies to main chat conversations, not tasks.
        """
        try:
            # Skip profile injection for task conversations or if already has system message
            if self.llm_history and self.llm_history[0].get("role") == "system":
                return
            
            # Get system prompt for user's active profile
            system_prompt = await get_system_prompt_for_user("default")  # TODO: Use actual user_id when auth is implemented
            
            # Get additional context from pinned conversations
            from services.context_service import get_user_context, format_context_for_system_prompt
            user_context = await get_user_context("default")
            context_prompt = format_context_for_system_prompt(user_context)
            
            # Combine profile and context prompts
            combined_prompt = ""
            if system_prompt:
                combined_prompt = system_prompt
            if context_prompt:
                if combined_prompt:
                    combined_prompt += "\n\n" + context_prompt
                else:
                    combined_prompt = context_prompt
            
            if combined_prompt:
                logger.debug(f"Injecting enhanced system prompt for conv {self.conv_id}")
                # Insert system message at the beginning of conversation history
                self.llm_history.insert(0, {"role": "system", "content": combined_prompt})
        except Exception as e:
            logger.error(f"Error injecting profile system prompt: {e}")
            # Don't fail the conversation if profile injection fails

    def _inject_persistent_context(self):
        """
        If a transcript or dataframe is attached to the convo, and we are NOT in the process
        of fetching a new one, inject the context for the LLM.
        """
        # YouTube Transcript Context
        if self.youtube_transcript and not self.payload.use_youtube:
            logger.debug(f"Injecting persistent YouTube transcript context for conv {self.conv_id}.")
            indicator_html = "<div class='youtube-indicator-custom'><b>📺 YouTube:</b> Using transcript for context.</div>"
            if indicator_html not in self.html_indicator: self._add_indicator(indicator_html)

            MAX_TRANSCRIPT_CHARS_FOR_CONTEXT = 12000
            truncated_transcript = self.youtube_transcript[:MAX_TRANSCRIPT_CHARS_FOR_CONTEXT]
            transcript_context = (
                "You are having a conversation about a YouTube video. "
                "Use the following transcript as the primary source to answer the user's question.\n\n"
                "--- BEGIN YOUTUBE TRANSCRIPT ---\n"
                f"{truncated_transcript}"
                "\n--- END YOUTUBE TRANSCRIPT ---\n"
            )
            if len(self.youtube_transcript) > MAX_TRANSCRIPT_CHARS_FOR_CONTEXT:
                transcript_context += "\n(The transcript was truncated to fit the context window)\n"
            self.prompt_for_llm = f"{transcript_context}\nBased on the transcript, please answer the user's request: '{self.prompt_for_llm}'"

        # Python Dataframe Context
        if self.python_df_id and not self.payload.use_python:
            logger.debug(f"Injecting persistent Python df_id context for conv {self.conv_id}.")
            indicator_html = f"<div class='python-indicator-custom'><b>🐍 Python:</b> Using loaded CSV data (ID: <code>{self.python_df_id[:8]}...</code>) for context.</div>"
            if indicator_html not in self.html_indicator: self._add_indicator(indicator_html)
            # This is a lighter touch, we re-run the tool selection if the user asks a follow-up
            # So we just prepend a note to the prompt.
            self.prompt_for_llm = f"The user is asking a follow-up question about a previously loaded CSV file. You will need to call a Python tool to answer it. The user's question is: '{self.prompt_for_llm}'"
            # Re-enable python handling for follow-up questions
            self.payload.use_python = True


    async def _run_pipeline(self):
        await self._initialize_conversation()
        # Inject profile system prompt FIRST, before any other context
        await self._inject_profile_system_prompt()
        # Persistent context must be injected BEFORE tool handling,
        # as it might re-enable a tool flag (e.g. for Python follow-ups)
        self._inject_persistent_context()

        if self.payload.use_search: await self._handle_search()
        if not self.error_message_obj and self.payload.use_database: await self._handle_database()
        if not self.error_message_obj and self.payload.use_hubspot: await self._handle_hubspot()
        if not self.error_message_obj and self.payload.use_youtube: await self._handle_youtube()
        if not self.error_message_obj and self.payload.use_python: await self._handle_python()


    def _save_assistant_message(self, content: str, raw_content: str):
        assistant_msg = ChatMessage(role="assistant", content=content, is_html=self.is_html_response)
        self.ui_history.append(assistant_msg)
        msg_to_save = assistant_msg.model_dump(exclude_none=True)
        msg_to_save["raw_content_for_llm"] = raw_content
        self.collection.update_one({"_id": self.obj_id}, {"$push": {"messages": msg_to_save}, "$set": {"updated_at": datetime.now(timezone.utc)}})

    async def process_non_streaming(self) -> ChatResponse:
        await self._run_pipeline()
        if self.error_message_obj:
            self._save_assistant_message(self.error_message_obj.content, self.error_message_obj.content)
        else:
            self.llm_history.append({"role": "user", "content": self.prompt_for_llm})
            repeat_penalty = self.payload.repeat_penalty or DEFAULT_REPEAT_PENALTY
            model_response = await chat_with_provider(self.llm_history, self.model_name, repeat_penalty)

            if model_response:
                final_content = f"{self.html_indicator}\n\n{model_response}" if self.is_html_response else model_response
                self._save_assistant_message(final_content, model_response)
            else:
                self._save_assistant_message(f"Sorry, I could not get a response from the model ({self.model_name}).", "")

        return ChatResponse(conversation_id=self.conv_id, chat_history=self.ui_history, model_name=self.model_name)

    async def process_streaming(self) -> AsyncGenerator[str, None]:
        await self._run_pipeline()

        if self.error_message_obj:
            self._save_assistant_message(self.error_message_obj.content, self.error_message_obj.content)
            payload = json.dumps({"type": "error", "content": self.error_message_obj.content})
            yield f"data: {payload}\n\n"
            done_payload = json.dumps({"type": "done", "conversation_id": self.conv_id})
            yield f"data: {done_payload}\n\n"
            return

        # Send indicator separately, don't mix with content
        if self.html_indicator:
            ind_payload = json.dumps({"type": "indicator", "is_html": True, "content": self.html_indicator})
            yield f"data: {ind_payload}\n\n"

        self.llm_history.append({"role": "user", "content": self.prompt_for_llm})
        accumulated_response = ""
        repeat_penalty = self.payload.repeat_penalty or DEFAULT_REPEAT_PENALTY

        async for chunk in stream_chat_with_provider(self.llm_history, self.model_name, repeat_penalty):
            yield chunk
            try:
                data = json.loads(chunk.strip().split("data: ")[1])
                if data.get("type") == "token":
                    accumulated_response += data.get("content", "")
            except (IndexError, json.JSONDecodeError): pass

        # Save clean content without indicator duplication
        if accumulated_response:
            final_content = f"{self.html_indicator}\n\n{accumulated_response}" if self.is_html_response else accumulated_response
            self._save_assistant_message(final_content, accumulated_response)

        # Send clean content in done payload
        done_payload = json.dumps({
            "type": "done", 
            "conversation_id": self.conv_id,
            "content": accumulated_response,  # Clean content only
            "is_html": self.is_html_response
        })
        yield f"data: {done_payload}\n\n"
