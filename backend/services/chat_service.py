import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union, AsyncGenerator

from bson import ObjectId
from fastapi import Request

from core.config import (
    get_logger, WEB_SEARCH_SERVICE_NAME, MYSQL_DB_SERVICE_NAME, HUBSPOT_SERVICE_NAME, YOUTUBE_SERVICE_NAME,
    MAX_DB_RESULT_CHARS, MAX_TABLES_FOR_SCHEMA_CONTEXT, DEFAULT_REPEAT_PENALTY
)
from core.models import ChatPayload, ChatMessage, ChatResponse
from db.mongodb import get_conversations_collection
from services.mcp_service import app_state, submit_mcp_request, wait_mcp_response
from services.ollama_service import get_default_ollama_model, chat_with_ollama, stream_chat_with_ollama
from auth_hubspot import get_valid_token, SESSION_COOKIE_NAME

logger = get_logger("chat_service")

# --- Result Formatting Helpers ---

def extract_json_from_response(response_content: Any) -> Dict:
    logger.debug(f"extract_json: Input type: {type(response_content)}, content preview: {str(response_content)[:200]}")
    if isinstance(response_content, dict): return response_content
    if isinstance(response_content, str):
        try: return json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(f"extract_json: Failed to decode JSON string: {response_content[:200]}")
            return {"status": "error", "message": "Result was a string but not valid JSON."}
    if hasattr(response_content, 'text') and isinstance(response_content.text, str):
        try: return json.loads(response_content.text)
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

    async def _initialize_conversation(self):
        if self.conv_id:
            if not ObjectId.is_valid(self.conv_id): raise ValueError("Invalid conv_id.")
            self.obj_id = ObjectId(self.conv_id)
            conv = self.collection.find_one({"_id": self.obj_id})
            if not conv: raise ValueError(f"Conv ID '{self.conv_id}' not found.")
            self.model_name = conv.get("ollama_model_name")
            self.youtube_transcript = conv.get("youtube_transcript")
            for msg in conv.get("messages", []):
                if 'role' in msg and 'content' in msg:
                    llm_content = msg.get("raw_content_for_llm", msg["content"])
                    self.llm_history.append({"role": msg["role"], "content": llm_content})
                self.ui_history.append(ChatMessage(**msg))

        if not self.model_name:
            self.model_name = self.payload.ollama_model_name or await get_default_ollama_model()

        if not self.conv_id:
            new_title = f"Chat: {self.user_msg_content[:30]}{'...' if len(self.user_msg_content) > 30 else ''}"
            new_doc = {"title": new_title, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "messages": [], "ollama_model_name": self.model_name}
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
        logger.info(f"[CHAT_SVC] Web search for: '{self.user_msg_content}'")
        try:
            req_id = await submit_mcp_request(WEB_SEARCH_SERVICE_NAME, "tool", {"tool": "web_search", "params": {"query": self.user_msg_content}})
            resp = await wait_mcp_response(WEB_SEARCH_SERVICE_NAME, req_id, timeout=90)
            if resp.get("status") == "error": raise Exception(resp.get("error", "MCP tool error"))

            results = extract_json_from_response(resp.get("data"))
            if results.get("status") == "error": raise Exception(results.get("message", "Parse error"))

            summary = format_search_results_for_prompt(results, self.user_msg_content)
            self._add_indicator(f"<div class='search-indicator-custom'><b>🔍 Web Search:</b> Results for \"{self.user_msg_content}\" were used.</div>")
            self.prompt_for_llm = f"Based on web search results for '{self.user_msg_content}':\n{summary}\n\nPlease answer the user's original question: '{self.user_msg_content}'"
        except Exception as e:
            logger.error(f"[CHAT_SVC] Web search failed: {e}", exc_info=True)
            self._set_error(f"⚠️ Web search failed: {str(e)}")

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
                raw_sql_resp = await chat_with_ollama([{"role": "system", "content": system_prompt}, {"role": "user", "content": self.user_msg_content}], self.model_name)

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
            raw_json_resp = await chat_with_ollama([{"role": "system", "content": system_prompt}, {"role": "user", "content": self.user_msg_content}], self.model_name)

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

            hubspot_api_resp = extract_json_from_response(resp.get("data"))
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

            transcript = resp.get("data", "")
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

    def _inject_persistent_context(self):
        """
        If a transcript is attached to the convo, and we are NOT in the process
        of fetching a new one, inject the transcript as context for the LLM.
        """
        if self.youtube_transcript and not self.payload.use_youtube:
            logger.debug(f"Injecting persistent YouTube transcript context for conv {self.conv_id}.")

            indicator_html = "<div class='youtube-indicator-custom'><b>📺 YouTube:</b> Using transcript for context.</div>"
            if indicator_html not in self.html_indicator:
                self._add_indicator(indicator_html)

            # Use a rough character limit to prevent oversized prompts.
            # ~12k chars is roughly 3k tokens.
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

            # self.prompt_for_llm contains the user's message, or a modified prompt from another tool.
            # We wrap it with our transcript context.
            self.prompt_for_llm = f"{transcript_context}\nBased on the transcript, please answer the user's request: '{self.prompt_for_llm}'"

    async def _run_pipeline(self):
        await self._initialize_conversation()
        if self.payload.use_search: await self._handle_search()
        if not self.error_message_obj and self.payload.use_database: await self._handle_database()
        if not self.error_message_obj and self.payload.use_hubspot: await self._handle_hubspot()
        if not self.error_message_obj and self.payload.use_youtube: await self._handle_youtube()

    def _save_assistant_message(self, content: str, raw_content: str):
        assistant_msg = ChatMessage(role="assistant", content=content, is_html=self.is_html_response)
        self.ui_history.append(assistant_msg)
        msg_to_save = assistant_msg.model_dump(exclude_none=True)
        msg_to_save["raw_content_for_llm"] = raw_content
        self.collection.update_one({"_id": self.obj_id}, {"$push": {"messages": msg_to_save}, "$set": {"updated_at": datetime.now(timezone.utc)}})

    async def process_non_streaming(self) -> ChatResponse:
        await self._run_pipeline()
        self._inject_persistent_context()
        if self.error_message_obj:
            self._save_assistant_message(self.error_message_obj.content, self.error_message_obj.content)
        else:
            self.llm_history.append({"role": "user", "content": self.prompt_for_llm})
            repeat_penalty = self.payload.repeat_penalty or DEFAULT_REPEAT_PENALTY
            model_response = await chat_with_ollama(self.llm_history, self.model_name, repeat_penalty)

            if model_response:
                final_content = f"{self.html_indicator}\n\n{model_response}" if self.is_html_response else model_response
                self._save_assistant_message(final_content, model_response)
            else:
                self._save_assistant_message(f"Sorry, I could not get a response from the model ({self.model_name}).", "")

        return ChatResponse(conversation_id=self.conv_id, chat_history=self.ui_history, ollama_model_name=self.model_name)

    async def process_streaming(self) -> AsyncGenerator[str, None]:
        await self._run_pipeline()
        self._inject_persistent_context()

        if self.error_message_obj:
            self._save_assistant_message(self.error_message_obj.content, self.error_message_obj.content)
            payload = json.dumps({"type": "error", "content": self.error_message_obj.content})
            yield f"data: {payload}\n\n"
            done_payload = json.dumps({"type": "done", "conversation_id": self.conv_id})
            yield f"data: {done_payload}\n\n"
            return

        if self.html_indicator:
            ind_payload = json.dumps({"type": "indicator", "is_html": True, "content": self.html_indicator})
            yield f"data: {ind_payload}\n\n"

        self.llm_history.append({"role": "user", "content": self.prompt_for_llm})
        accumulated_response = ""
        repeat_penalty = self.payload.repeat_penalty or DEFAULT_REPEAT_PENALTY

        async for chunk in stream_chat_with_ollama(self.llm_history, self.model_name, repeat_penalty):
            yield chunk
            try:
                data = json.loads(chunk.strip().split("data: ")[1])
                if data.get("type") == "token":
                    accumulated_response += data.get("content", "")
            except (IndexError, json.JSONDecodeError): pass

        if accumulated_response:
            final_content = f"{self.html_indicator}\n\n{accumulated_response}" if self.is_html_response else accumulated_response
            self._save_assistant_message(final_content, accumulated_response)

        done_payload = json.dumps({
            "type": "done", "conversation_id": self.conv_id,
            "content": f"{self.html_indicator}\n\n{accumulated_response}" if self.is_html_response else accumulated_response,
            "is_html": self.is_html_response
        })
        yield f"data: {done_payload}\n\n"
