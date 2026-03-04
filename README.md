# 🔍 🤖 🌐 Osoba

A powerful, modern UI that integrates local and hosted LLMs with intelligent web search and content extraction, SQL, YouTube transcript analysis, HubSpot actions, Python data analysis — and a Codex MCP server for safe code scaffolding — all via the Model Context Protocol (MCP). Features include personalized AI assistance through user profiles and conversation context, a Document Knowledge Base for persistent reference material, provider settings, multi‑provider model picking, streaming chat, persistent conversations, a robust Tasks system, and Scheduled tasks with timezone‑aware timing.

## Overview

Osoba showcases how to extend both local and hosted models through MCP tool use. It combines locally running LLMs via Ollama with intelligent web search and content extraction, SQL querying, YouTube transcript ingestion, HubSpot business actions, Python-based CSV analysis/visualization — and a Codex Workspace server for code generation inside an isolated workspace. A multi‑provider layer adds OpenAI, Anthropic, Google, OpenRouter, Groq, and SambaNova. Conversations and tasks persist in MongoDB.

The project consists of several key components:

- **Backend (FastAPI)**: Manages chat logic, model provider routing, MCP service communication (including starting and managing MCP services like web search, SQL, YouTube, HubSpot, Python, Codex), tasks/scheduler, and persistence.

- **Frontend (React)**: A modern, responsive web interface for users to interact with the chat application.

- **MCP Smart Web Search Server Module**: Provides intelligent web search via the Serper.dev API with automatic content extraction from top results. Uses multi-method content extraction (trafilatura, BeautifulSoup) with URL prioritization, robots.txt compliance, and polite crawling practices.

- **MCP SQL Server Module**: Read-only querying against a MySQL database (with schema resources and query safety).

- **MCP YouTube Transcript Server**: Robustly fetches transcripts using multiple strategies (youtube-transcript-api, Pytube, yt-dlp) with optional proxy support, then persists transcript context to the conversation for follow-ups.

- **MCP HubSpot Business Tools**: Create/update marketing emails via HubSpot APIs using OAuth, with a JSON-first prompting flow.

- **MCP Python Data Analysis Server**: Comprehensive data analysis toolkit including CSV loading, data profiling, filtering, grouping/aggregation, outlier detection, data type conversion, statistical hypothesis testing, and visualization (base64 images) for complete analytical workflows.

- **MCP Codex Workspace Server**: Creates per‑run workspaces and launches the Codex CLI within an isolated directory, persists artifacts (JSONL events, manifest), enforces a configurable output policy, and exposes async run APIs for a streaming‑friendly UX. Gated on a valid OpenAI API key.

- **MongoDB**: Stores conversation history and user data.

This architecture demonstrates how MCP enables local models to access external tools and data sources, significantly enhancing their capabilities. The backend starts and supervises all MCP services for a scalable, feature-rich setup.

## Demo

- Watch the demo on X: https://x.com/redbuilding/status/2010124029936427450

## Features

- 🧠 **Smart Web Search**: Intelligent web search with automatic content extraction from top results. Goes beyond search snippets to fetch and analyze full webpage content using advanced extraction techniques.
- 🔎 **URL Prioritization**: Smart ranking of search results based on relevance scoring, including title/snippet matching, domain authority, and search position weighting.
- 🤖 **Polite Web Crawling**: Respects robots.txt, implements rate limiting, and uses proper User-Agent identification for ethical content extraction.
- 👤 **User Profile & Context**: Configure personal information (role, expertise, projects) and pin conversations for contextual AI assistance. The AI understands your background and can reference previous work for personalized responses.
- 🎯 **Goals & Priorities**: Define your short-term, medium-term, and long-term goals in a structured document (up to 2000 characters) to help the AI understand your objectives and provide relevant assistance.
- 🔔 **Proactive Agent Heartbeat**: Enhanced background service with context gathering (semantic memory, git, project files, system health), automated task creation, and file-based configuration (HEARTBEAT.md). Configurable intervals, context sources, and two-way sync between file and UI.
- 📌 **Conversation Pinning**: Select specific conversations to include as context for future chats, enabling the AI to build upon previous discussions and maintain continuity across sessions.
- 🧠 **Semantic Memory**: Unlimited conversation storage with intelligent semantic search powered by ChromaDB and nomic-embed-text embeddings. Automatically indexes conversations with 5+ messages, searches by meaning (not keywords), and injects relevant past conversations into new chats. Includes Memory Browser (Ctrl+Shift+M) for searching and managing your conversation history.
- 📚 **Document Knowledge Base**: Upload PDFs, Word documents, Markdown files, plain text, or web URLs as persistent reference material. Documents are chunked, embedded, and stored in a dedicated ChromaDB collection. Relevant document snippets are automatically injected into every chat alongside Semantic Memory. Open with Ctrl+Shift+K or the "KB" header button.
- 🧾 **AI Chat Summaries (On‑Demand)**: Generate concise, LLM‑authored summaries for conversations and use them as the context payload for pinned chats (no heuristics). Summaries are user‑triggered, model‑selectable in Settings, and pinning enforces a cap of 5 chats.
- 🎯 **Personalized AI Responses**: AI adapts its communication style and suggestions based on your profile information and pinned conversation history for more relevant assistance.
- 💾 **Persistent Conversations**: Chat history is saved in MongoDB, allowing users to resume conversations.
- 🧠 **Multi‑Provider LLMs**: Ollama (local), plus OpenAI, Anthropic, Google, OpenRouter, Groq, SambaNova — with a Settings screen for API keys and a unified model picker.
- 🔌 **MCP integration**: Backend manages multiple MCP tools (web, SQL, YouTube, HubSpot, Python) as background services.
- 💻 **Modern Web Interface**: Built with React for a responsive and interactive user experience.
- 📊 **Structured search results**: Clean formatting of web search data for optimal context.
- 🌐 **Enhanced Content Extraction**: Multi-method content extraction using trafilatura and BeautifulSoup with graceful fallbacks for maximum reliability.
- ⚙️ **Backend API**: FastAPI backend providing robust API endpoints for chat and conversation management.
- 🗃️ **SQL Querying Tool**: Read-only MySQL querying with schema introspection and retry logic.
- 🔄 **Conversation Management**: List, rename, and delete conversations.
- 📺 **YouTube Transcript Tool**: Paste a YouTube URL; transcripts are fetched and stored for multi-turn follow-ups.
- 🧰 **HubSpot Tools**: OAuth-connect, then create/update marketing emails via guided JSON prompts.
- 🐍 **Python Analysis Tool**: Upload a CSV and run comprehensive analysis including data profiling, filtering, grouping, outlier detection, statistical testing, type conversion, and visualization — results stream back with images and detailed insights.
- ⚡ **Streaming Responses**: Frontend renders model output token-by-token and indicators for tool usage.
- 🗓️ **Long‑Running Tasks (Plan & Execute)**: Create autonomous tasks that plan and execute multi‑step workflows, with budgets, retries, and verification.
- 📈 **Live Task Progress**: Tasks stream progress via SSE; per‑step outputs (tables/images/text) render in the UI.
- 🧩 **LLM‑only Steps (No MCP)**: Tasks can include steps that run directly on Ollama (e.g., summaries/reasoning) without using any MCP tool.
- 🚦 **Priority Task Queue**: Memory-safe task execution with priority scheduling - scheduled tasks run first, user tasks queue behind them, only one task executes at a time to prevent system overload, especially important for local, memory-constrained systems.
- ✨ **Codex Workspace (MCP)**: Launch Codex to generate/edit files in an isolated workspace; inline run status in chat; artifacts persisted for review; gated on OpenAI key.
- 🗓️ **Scheduled Tasks (Timezone‑Aware)**: Recurring cron or one‑time schedules computed in local timezone with DST safety; auto‑disable after first run for one‑time schedules; “Run now” with model override.

## Task Execution & Memory Management

### Task System MCP Tool Access

The task system has **full access to all MCP tools** available in the chat interface, enabling autonomous execution of complex workflows:

**Available Tools (33 total)**:
- **Web Search** (4 tools): Basic search, smart content extraction, image search, news search
- **Python Data Analysis** (17 tools): Data loading, inspection, cleaning, transformation, statistical analysis, visualization
- **HubSpot Business** (2 tools): Create/update marketing emails (requires OAuth)
- **Codex Workspace** (7 tools): Code generation and workspace management (requires OpenAI API key)
- **Database** (1 tool): Read-only SQL queries
- **YouTube** (1 tool): Transcript extraction
- **LLM-only** (1 tool): Direct LLM generation for reasoning steps

**Advanced Task Capabilities**:
- Research with smart content extraction (full webpage content, not just snippets)
- Advanced data analysis with outlier detection and statistical hypothesis testing
- Marketing automation with HubSpot integration
- Code generation with fine-grained Codex workspace management
- Multi-step workflows combining search, analysis, and generation
- **KB context attachment**: Attach 1–2 indexed Knowledge Base documents at task creation to inject reference material into the planner and every LLM step

### Priority Queue System
The application uses a **priority-based task queue** to ensure system stability and prevent memory overload from multiple LLM instances:

- **Priority 1 (Highest)**: Scheduled tasks always run first
- **Priority 2 (Standard)**: User-created tasks queue behind scheduled tasks
- **One Task at a Time**: Only one task executes simultaneously to prevent memory crashes
- **Queue Position**: Users receive feedback about their position in the queue

### Memory Safety
- **Prevents Overload**: Multiple concurrent LLM instances (e.g., 3x Llama3.1 8B = 24GB) could crash systems with limited RAM
- **Safe Execution**: Single task execution ensures memory usage stays within system limits
- **Automatic Queuing**: Tasks automatically queue when another task is running

### Task Scheduling
- **Cron-based Scheduling**: Uses standard cron expressions for flexible scheduling
- **System Requirements**: Scheduled tasks only run when the system is awake and the application is running
- **Catch-up Execution**: Overdue tasks execute immediately when the system resumes

### Scheduled Task Reliability

**Catch-up Logic (Default)**:
When the backend starts after being stopped or the computer wakes from sleep, overdue scheduled tasks execute immediately. Tasks delayed by more than 5 minutes are marked with a warning indicator in the UI showing how late they ran (e.g., "⚠️ Last run: 45m late"). Recurring tasks calculate their next run from the current time to prevent cascading delays.

**Delay Breakdown**:
The system distinguishes between two types of delays:
- **System Delay** (sleep): Time the computer was asleep or backend was stopped
- **Queue Delay** (queued): Time spent waiting for other tasks to complete

The UI shows the breakdown: "⚠️ Last run: 15m late (sleep: 10m, queued: 5m)". This helps you understand whether delays are due to system sleep or task queue congestion. Since only one task executes at a time (for memory safety), tasks may queue behind catch-up tasks after system wake.

**Running as a Service (Optional)**:
For guaranteed execution and automatic startup, you can run Osoba backend as a system service. This ensures the backend is always running and ready to execute scheduled tasks on time. Setup scripts are provided for macOS (Launch Agent), Linux (systemd), and Windows (NSSM). See `scripts/README.md` for detailed setup instructions.

**Wake Scheduling (Advanced)**:
On supported systems, you can configure the computer to wake from sleep specifically to run scheduled tasks. This requires administrator/root access and is recommended primarily for desktop machines or when plugged in due to battery impact. Platform-specific instructions:
- **macOS**: Uses `pmset` to schedule wake events
- **Linux**: Uses RTC wake (hardware support required)
- **Windows**: Uses Task Scheduler with wake timers

See `scripts/README.md` for complete wake scheduling setup and troubleshooting.

## Requirements
- Python 3.11+
- Node.js (v18+) and npm/yarn for the frontend
- [Ollama](https://ollama.com/) installed and running locally
- A [Serper.dev](https://serper.dev/) API key (free tier available)
- MongoDB instance (local or cloud)
- MySQL server (optional, for the SQL querying tool)
- Internet connection for web searches and package downloads

**For Semantic Memory & Document Knowledge Base:**
- Ollama with `nomic-embed-text` model: `ollama pull nomic-embed-text`
- ChromaDB, tiktoken, and pdfplumber (automatically installed via requirements.txt)

Optional (enable additional tools):
- Smart web search: `trafilatura`, `beautifulsoup4`, `lxml` (automatically installed)
- Python data analysis: `pandas`, `numpy`, `matplotlib`, `seaborn`
- YouTube transcripts: `youtube-transcript-api`, `pytube`, `yt-dlp`, `requests`
- HubSpot OAuth: valid OAuth app (client ID/secret) and redirect URL
- Codex Workspace: Codex CLI available on PATH (or set `CODEX_BIN`), OpenAI API key configured

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/redbuilding/osoba.git
    cd osoba
    ```

2.  **Set up Backend:**
    *   Navigate to the backend directory:
        ```bash
        cd backend
        ```
    *   Create and activate a virtual environment:
        ```bash
        python3 -m venv mcp
        source mcp/bin/activate  # On Windows: mcp\Scripts\activate
        ```
    *   Install Python dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   Create a `.env` file in the `backend` directory. This is where the backend and its managed MCP services will look for environment variables. To securely store provider API keys, you must generate a stable encryption key (Fernet) and set `SETTINGS_ENCRYPTION_KEY`:
        - Install: `pip install cryptography`
        - Generate (pick one):
          - `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
          - In Python REPL: `from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())`
        - Paste the key into `.env` as `SETTINGS_ENCRYPTION_KEY=...`
        ```dotenv
    
        # For encrypting API keys entered into model provider Settings modal
        SETTINGS_ENCRYPTION_KEY=<paste_generated_fernet_key_here>
        
        # For Smart Web Search (server_search.py)
        SERPER_API_KEY=your_serper_api_key_here

        # Smart extraction configuration (optional)
        SMART_EXTRACT_MAX_URLS=3
        SMART_EXTRACT_MAX_CHARS_PER_URL=2000
        SMART_EXTRACT_MAX_TOTAL_CHARS=5000
        SMART_EXTRACT_REQUEST_DELAY=1.0

        # For MongoDB (main.py)
        MONGODB_URI=mongodb://localhost:27017/
        MONGODB_DATABASE_NAME=mcp_chat_db

        # For MySQL Database Querying (server_mysql.py)
        DB_HOST=localhost
        DB_USER=your_db_user
        DB_PASSWORD=your_db_password
        DB_NAME=your_db_name

        # Optional: HubSpot OAuth (backend/auth_hubspot.py)
        HUBSPOT_CLIENT_ID=your_hubspot_client_id
        HUBSPOT_CLIENT_SECRET=your_hubspot_client_secret
        HUBSPOT_REDIRECT_URI=http://localhost:8000/auth/hubspot/oauth-callback
        FRONTEND_URL=http://localhost:5173

        # Optional: YouTube transcript server (backend/server_youtube.py)
        # YTA_PROXY=https://user:pass@host:port
        # YTA_LOG_LEVEL=INFO

        # Optional: Backend defaults
        DEFAULT_OLLAMA_MODEL=llama3.1
        OLLAMA_REPEAT_PENALTY=1.15
        
        # Codex MCP debugging state
        CODEX_DEBUG=false
        ```

    *   Install optional dependencies for additional tools (if you plan to use them):
        ```bash
        # Smart web search content extraction (recommended)
        pip install trafilatura beautifulsoup4 lxml

        # YouTube transcript tool
        pip install youtube-transcript-api pytube yt-dlp requests

        # Python analysis tool
        pip install pandas numpy matplotlib seaborn scipy
        ```

3.  **Set up Frontend:**
    *   Navigate to the frontend directory:
        ```bash
        cd ../frontend
        ```
        (If you were in `backend/`, otherwise navigate from project root: `cd frontend`)
    *   Install Node.js dependencies:
        ```bash
        npm install
        # or
        # yarn install
        ```
    *   Optional: create `frontend/.env` with a custom API URL (default is `http://localhost:8000/api`):
        ```bash
        echo 'VITE_API_URL=http://localhost:8000/api' > .env
        ```

4.  **Ensure Ollama is installed and a model is available:**
    The application might default to a specific model (e.g., `llama3.1`). Pull your desired model:
    ```bash
    ollama pull llama3.1
    # or your preferred model like llama3, mistral, etc.
    ```
    You can select the model in the UI, or configure a default via `DEFAULT_OLLAMA_MODEL` in the backend `.env` file.

## Security Considerations

> ⚠️ **Osoba is designed for local, single-user use.** The API has no authentication layer. Never expose port 8000 to untrusted networks (e.g., via ngrok, port forwarding, or binding to `0.0.0.0`).

- **Network Exposure**: The backend binds to `127.0.0.1` by default. Do not change this to `0.0.0.0` unless you understand the risks.
- **Encryption Key**: Set `SETTINGS_ENCRYPTION_KEY` in `backend/.env` to a stable Fernet key. Without it, provider API keys are lost on every restart.
- **MongoDB**: The default connection uses no authentication. For sensitive data, enable MongoDB authentication and use a connection string with credentials.
- **Provider API Keys**: Keys are encrypted at rest with Fernet and never returned by the API. Keep your `.env` file secure and out of version control.
- **MySQL Queries**: Queries are validated as read-only SELECT statements and automatically limited to 1000 rows. Connection and read timeouts prevent runaway queries.
- **CSV Uploads**: Uploads are capped at 50 MB decoded size, and the in-memory DataFrame store is limited to 10 datasets (oldest evicted first).

## Usage

1.  **Ensure Prerequisites are Running:**
    *   **Ollama**: Must be running.
    *   **MongoDB**: Your MongoDB instance must be accessible.
    *   **MySQL Server** (if using the SQL tool): Your MySQL server must be running and accessible with the credentials provided in `.env`.

2.  **Start the Backend Server:**
    Navigate to the `backend` directory and run the FastAPI application:
    ```bash
    # From the backend directory
    uvicorn main:app --reload --port 8000
    ```
    The backend API will typically be available at `http://localhost:8000`.
    The FastAPI application automatically starts and manages all MCP services (Web, SQL, YouTube, HubSpot, Python, Codex) as background processes using its lifespan manager. You do **not** need to run the MCP servers separately.

3.  **Start the Frontend Development Server:**
    Navigate to the `frontend` directory and run:
    ```bash
    npm run dev
    # or
    # yarn dev
    ```
    The web interface will typically be accessible at `http://localhost:5173` (or another port specified by Vite).

### Interacting with the Application

-   Open your browser to the frontend URL (e.g., `http://localhost:5173`).
-   Use the chat interface to send messages; responses stream live with indicators when tools run.
-   Click the ✨ Tool Selector to enable one of: Smart Web Search, Database, YouTube, HubSpot, Python, Codex (requires OpenAI configured).
-   Use Settings (header) to configure provider API keys and unlock non‑Ollama models and Codex.
-   **Configure User Profile**: In Settings → User Profile, add your role, expertise areas, current projects, and communication preferences for personalized AI assistance.
-   **Set Your Goals**: In Settings → Goals & Priorities, define your short-term, medium-term, and long-term goals (up to 2000 characters). The AI will use these goals to provide contextual assistance and proactive insights.
-   **Enable Proactive Insights**: Configure the heartbeat service in Settings → Goals & Priorities → Heartbeat Settings to receive periodic AI-generated insights about your progress, blockers, and suggestions. Click the bell icon (🔔) in the header to view insights.
-   **Pin Conversations**: Hover over conversations in the sidebar and click the pin button to include them as context for future chats.
    - If a conversation lacks a summary, you’ll be prompted to generate one before pinning. The UI blocks while the summary is created, then completes the pin.
    - Up to 5 conversations can be pinned. Attempts beyond the cap are blocked and the sidebar shows “X/5 pinned”.
    - Summaries are generated on‑demand by your chosen model (see Settings → Summaries) and are stored for reuse; only stored summaries are used for context.
-   For YouTube: paste a video URL. The transcript is fetched and saved to the conversation for follow-ups.
-   For HubSpot: click “Connect HubSpot” to complete OAuth, then describe the email to create/update.
-   For Python: upload a CSV file when prompted; follow-up questions reuse the loaded DataFrame for advanced analysis including filtering, grouping, outlier detection, statistical testing, and visualization.
-   Manage conversations using the sidebar (create new, select, rename, delete, pin for context).

### Long‑Running Tasks (Plan & Execute)

-   Open the Tasks panel (Tasks button in the header) to:
    -   Create a new task by entering a high‑level goal.
    -   Monitor progress (live SSE stream), view step outputs (tables, images, text), and Pause/Resume/Cancel.
    -   “Promote to Task” from any user chat message to pre‑fill the goal and link the task to the conversation.
    -   Copy entire task results or individual step outputs using dedicated copy buttons.
    -   Delete completed, failed, or canceled tasks to clean up the task list.
    -   The backend plans each task as structured JSON (steps, tool, parameters, success criteria), then executes steps sequentially with:
    -   Budgets: max wall‑time and max tool calls.
    -   Per‑step timeouts and capped retries with backoff.
    -   Output verification against success criteria.
-   Completion: When the final step finishes, the task status becomes COMPLETED. On failure/timeouts/budgets exceeded, status is FAILED. A concise summary is posted back into the linked conversation.
    -   When an OpenAI key is configured, the planner may propose a `codex.run` step for scaffolding/creation goals; otherwise such steps are automatically gated off.

APIs:
-   Create task: `POST /api/tasks { goal, conversation_id?, dry_run? }`
-   List tasks: `GET /api/tasks`
-   Task detail: `GET /api/tasks/{id}`
-   Task stream (SSE): `GET /api/tasks/{id}/stream`
-   Pause/Resume/Cancel: `POST /api/tasks/{id}/pause|resume|cancel`
-   Delete task: `DELETE /api/tasks/{id}`
-   Status: `GET /api/status` includes `tasks.active` count

LLM‑only steps (no MCP):
-   The planner supports `llm.generate` steps that run directly via Ollama, without any MCP server. If a `prompt` is omitted, the step’s `instruction` is used. These steps still respect budgets, timeouts, and verification.

### Legacy Clients (Removed)

The original `chat_client.py` (terminal) and `chat_frontend.py` (Gradio) have been removed from the repository as they are no longer compatible with the current FastAPI backend architecture. All functionality is now provided through the modern React frontend.

## Python Data Analysis Tools

The Python MCP server provides comprehensive data analysis capabilities through the following tools:

### Core Data Operations
- **`load_csv`** - Load CSV data from base64 encoded strings
- **`get_head`** - Display first N rows of DataFrame
- **`get_data_info`** - Comprehensive DataFrame information (dtypes, memory usage, non-null counts)
- **`get_descriptive_statistics`** - Statistical summary for numerical columns

### Data Quality & Cleaning
- **`check_missing_values`** - Identify missing values across columns
- **`handle_missing_values`** - Handle missing data (drop, fill, interpolate)
- **`convert_data_types`** - Safe data type conversion (datetime, category, numeric)
- **`detect_outliers`** - Outlier detection using IQR or Z-score methods

### Data Manipulation & Analysis
- **`filter_dataframe`** - Filter data using pandas query syntax with security validation
- **`group_and_aggregate`** - Group by columns and apply aggregation functions
- **`query_dataframe`** - Advanced DataFrame querying with new DataFrame creation
- **`rename_columns`** - Rename DataFrame columns
- **`drop_columns`** - Remove specified columns

### Statistical Analysis
- **`get_correlation_matrix`** - Compute correlation matrix for numerical columns
- **`get_value_counts`** - Frequency analysis for categorical columns
- **`perform_hypothesis_test`** - Statistical hypothesis testing:
  - Two-sample t-tests
  - Pearson correlation tests
  - Chi-square tests of independence

### Data Visualization
- **`create_plot`** - Generate various plot types:
  - Scatter plots
  - Histograms
  - Bar charts
  - Box plots
  - Returns base64-encoded images for web display

All tools maintain session state through an in-memory DataFrame store, enabling complex multi-step analytical workflows within a single conversation.

## User Profile & Contextual AI Assistance

The application provides personalized AI assistance through user profiles and conversation context management:

### User Profile Configuration
- **Personal Information**: Configure your role, expertise areas, current projects, and communication preferences
- **Contextual Understanding**: The AI understands your background and adapts responses accordingly
- **Settings Integration**: Access via Settings → User Profile for easy configuration

### Conversation Context System
- **Selective Pinning**: Choose specific conversations to include as context for future chats
- **Visual Controls**: Pin/unpin conversations directly from the sidebar with intuitive controls
- **Automatic Summaries**: System automatically generates summaries for pinned conversations when needed
- **Hybrid Summary Approach**: Captures both user questions and assistant solutions for complete context
- **Context Continuity**: AI can reference previous problems AND solutions for coherent assistance
- **Smart Limits**: Context is budgeted to ~2700 characters total (200 profile + up to 2500
across pinned summaries)
- **Persistent Storage**: Generated summaries are stored and reused to avoid regeneration

### Personalized AI Responses
The AI combines your profile information with pinned conversation context to provide:
- **Relevant Suggestions**: Recommendations based on your role and current projects
- **Appropriate Complexity**: Technical depth matching your expertise level
- **Consistent Context**: Ability to reference previous work and maintain conversation continuity
- **Solution Awareness**: Knows what approaches were already tried and can build upon them
- **Adaptive Communication**: Response style tailored to your preferences

### Profile vs AI Configuration
- **User Profile**: Information about YOU (role, projects, preferences) - helps AI understand who it's talking to
- **AI Profile**: Configuration of the AI's behavior and personality - defines how the AI should act
- **Combined Effect**: Creates personalized interactions where the AI knows both who you are and how it should respond

### Technical Implementation
- **Automatic Summary Generation**: When conversations are pinned, summaries are generated on-demand from the last 5 messages
- **Hybrid Summary Format**: Includes both user questions and key assistant solutions (e.g., "User question | Solved: pandas, matplotlib")
- **Smart Solution Extraction**: Identifies code examples, tool recommendations, and solution patterns from assistant responses
- **User Isolation**: Conversations are filtered by user to prevent cross-user context leakage
- **Performance Optimization**: Summaries are generated once and stored for reuse across multiple chats

## Semantic Memory System

Osoba features an advanced semantic memory system that provides unlimited conversation storage with intelligent semantic search, going beyond the 5-conversation pinning limit.

### How It Works

**Automatic Indexing:**
- Conversations with 5+ messages are automatically indexed after 10 minutes of inactivity
- Uses nomic-embed-text (via Ollama) for local, privacy-preserving embeddings
- Stores conversation chunks in ChromaDB vector database for semantic search
- Non-blocking background process ensures no impact on chat performance

**Semantic Search:**
- Search by meaning, not just keywords - finds conceptually similar conversations
- Relevance scoring shows how well results match your query (e.g., "87% match")
- Automatically injects relevant past conversations into new chats
- Only includes conversations above 60% similarity threshold to avoid noise

**Memory Browser (Ctrl+Shift+M):**
- Full-text semantic search across all indexed conversations
- Preview snippets with relevance scores
- Remove individual conversations from memory
- Keyboard shortcuts for quick access

### Key Features

**Unlimited Storage:**
- No artificial limits - store thousands of conversations
- Intelligent chunking (512 tokens with 50-token overlap) preserves context
- Automatic cleanup based on retention policies (configurable)

**Smart Context Injection:**
- Relevant past conversations automatically added to chat context
- Only the most relevant conversations included (not all indexed conversations)
- Respects context window limits while maximizing relevance

**Privacy-First:**
- Local embeddings via Ollama (no external API calls)
- All data stored locally in ChromaDB
- No conversation data leaves your machine

### Using Semantic Memory

**Manual Save:**
- Click "💾 Save to Memory" button (appears for conversations with 5+ messages)
- Immediately indexes the conversation for future reference

**Automatic Indexing:**
- Conversations automatically indexed after 5+ messages and 10 minutes idle
- Background service checks every 5 minutes for eligible conversations
- No user action required

**Searching Memory:**
1. Press `Ctrl+Shift+M` to open Memory Browser
2. Enter your search query (e.g., "Python pandas dataframe")
3. View results with relevance scores and preview text
4. Click to view or remove conversations

**Memory Management:**
- Access Settings → Semantic Memory for statistics and controls
- View total indexed conversations and storage usage
- Trigger manual auto-index check
- Clear all memory (with confirmation)

### Technical Details

**Embedding Model:**
- nomic-embed-text (768-dimensional embeddings)
- Runs locally via Ollama
- No API costs or rate limits

**Vector Database:**
- ChromaDB for persistent vector storage
- Efficient similarity search (<100ms for typical queries)
- Automatic persistence to disk

**Context Integration:**
- Semantic memory injected after profile context
- Formatted as "Relevant past conversations" section
- Includes conversation title, relevance score, and preview text

### Benefits Over Pinning

| Feature | Pinning (5 max) | Semantic Memory |
|---------|----------------|-----------------|
| **Capacity** | 5 conversations | Unlimited |
| **Selection** | Manual | Automatic by relevance |
| **Search** | None | Semantic search |
| **Context Efficiency** | All 5 included | Only relevant ones |
| **Management** | Manual pin/unpin | Auto-indexed |

## Document Knowledge Base

The Document Knowledge Base lets you upload persistent reference material — SOPs, research papers, specifications, documentation — and have the AI automatically draw on it in every conversation, just like Semantic Memory does for past chats.

### Supported Formats

| Format | Extension | Parser |
|--------|-----------|--------|
| Plain text | `.txt` | UTF-8 decode |
| Markdown | `.md` | UTF-8 decode |
| Word documents | `.docx` | python-docx |
| PDFs | `.pdf` | pdfplumber |
| Web pages | URL | trafilatura |

Maximum document size: **200,000 characters** per document.

### How It Works

```
Upload (file / URL)
    ↓
document_parser.py  ← extracts plain text
    ↓
documents_crud.py   ← stores metadata + raw text in MongoDB ("documents" collection)
    ↓
document_indexing.py ← chunks text → embeds via nomic-embed-text → stores in ChromaDB ("documents" collection)
    ↓
kb_context.py       ← at chat time: embeds query, searches "documents", formats snippets
    ↓
chat_service.py     ← injects "=== Knowledge Base ===" section into system prompt
```

Documents with more than 50,000 characters are indexed in the background so the upload responds immediately.

### Opening the Knowledge Base Panel

- **Keyboard shortcut**: `Ctrl+Shift+K`
- **Header button**: Click "KB" in the top navigation bar

### Documents Tab

- **Drag-and-drop upload** or click "Choose File" to select `.txt`, `.md`, `.docx`, or `.pdf` files
- **URL ingestion**: Paste any URL and click "Add URL" (or press Enter) to fetch and index a web page
- **Document cards** show: type badge (color-coded), indexed status dot (green = ready, amber = pending), character count, upload date, and a delete button
- Documents are indexed immediately after upload (or in the background for large files)

### Search Tab

- Enter a query to semantically search across all indexed document chunks
- Results show document title, relevance percentage, and a text snippet

### Sidebar Status

The left sidebar footer shows a live count of indexed documents. The indicator dot turns green once at least one document is available.

### Chat Integration

When you send a message, the backend:
1. Embeds your query with `nomic-embed-text`
2. Searches the `documents` ChromaDB collection for the top-5 most relevant chunks (score ≥ 0.4)
3. Formats matches as an `=== Knowledge Base ===` section injected into the system prompt alongside Semantic Memory

The AI will reference document content when it is relevant, without you having to manually include it in each message.

### Using KB Docs in Tasks

You can explicitly attach 1–2 indexed KB documents when creating a task to give the planner and step agents reference material. This is fully opt-in: if no documents are attached the task behaves exactly as before.

**How to attach:**
1. Open the **Tasks** panel (Ctrl+Shift+T or the Tasks header button)
2. Type your goal
3. Click **"Add KB Doc"** — an inline dropdown lists all indexed documents
4. Select up to **2** documents; each appears as a dismissible chip below the input
5. Click the run button — the selected documents are sent as `kb_doc_ids` in the payload

**What happens under the hood:**
```
Task creation request (with kb_doc_ids)
    ↓
api/tasks.py  — fetches each doc from MongoDB, excerpts up to 4,000 chars each
    ↓ stores {kb_docs: [{id, title}], kb_context: "=== Knowledge Base ===\n..."} in task doc
         ↓                              ↓
task_planner.py              task_runner.py
(planning prompt includes     (every LLM step gets kb_context
 "Reference material" block)   as the 2nd message after system)
```

**Limits:**

| Constraint | Value |
|---|---|
| Max docs per task | 2 |
| Max chars excerpted per doc | 4,000 |
| Max total KB context string | ~9,000 chars |
| Only indexed docs selectable | yes |
| Content snapshotted at creation | yes — consistent through all steps |
| Injected in LLM steps only | yes — not in MCP tool steps |

**Task detail view:** Attached documents are shown as small chips in the task header so you can see at a glance what context was provided.

> **Tip:** Attach an SOP or specification document to tasks that involve following a defined process. The planner will incorporate the document's constraints into its step design, and each LLM generation step will have the full excerpt available.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents/upload` | Upload a file (base64-encoded JSON body) |
| `POST` | `/api/documents/url` | Ingest from a URL |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document detail (includes content) |
| `DELETE` | `/api/documents/{id}` | Delete from MongoDB + ChromaDB |
| `GET` | `/api/documents/search?q=...` | Semantic search over document chunks |
| `GET` | `/api/documents/stats` | Count, chars, chunks |

**Upload payload shape:**
```json
{
  "filename": "spec.pdf",
  "data_b64": "<base64 string>",
  "title": "Product Spec",
  "description": "Optional description",
  "user_id": "default"
}
```

### Backend Files

| File | Purpose |
|------|---------|
| `backend/db/document_store.py` | `DocumentVectorStore` — ChromaDB `"documents"` collection |
| `backend/db/documents_crud.py` | MongoDB CRUD for document metadata |
| `backend/services/document_parser.py` | File/URL → plain text extraction |
| `backend/services/document_indexing.py` | Chunking + embedding + storage pipeline |
| `backend/services/kb_context.py` | Query-time context builder |
| `backend/api/documents.py` | FastAPI router (`/api/documents`) |

## Proactive Agent Heartbeat System

The Enhanced Heartbeat System provides proactive AI assistance through automated insights and task creation. It analyzes your goals, conversations, project state, and system health to suggest actionable next steps.

### Key Features

**Context Gathering:**
- **Semantic Memory**: Conversation history, indexed conversations, storage usage
- **Git Repository**: Current branch, uncommitted files, unpushed commits, recent commits
- **Project Files**: TODO/FIXME comments, recently modified files
- **System Health**: Disk usage, service status

**Automated Task Creation:**
- Insights can automatically create tracked tasks
- Manual conversion via "Create Task" button
- Tasks linked to insights for tracking

**File-Based Configuration (Power Users):**
- Define heartbeat tasks in `HEARTBEAT.md`
- Category-based task organization
- Custom schedules (cron or interval format)
- Two-way sync between file and UI

### How It Works

The heartbeat service runs in the background at configurable intervals (default: every 2 hours). During each heartbeat:

1. **Context Gathering**: Collects goals, conversations, tasks, and enhanced context (memory, git, project, system)
2. **AI Analysis**: Sends context to your chosen LLM (default: Haiku for cost-effectiveness at ~$0.01/user/day)
3. **Insight Generation**: AI generates actionable insights, suggestions, or identifies blockers
4. **Smart Filtering**: Uses "HEARTBEAT_OK" pattern to suppress notifications when everything is on track
5. **Task Creation**: Optionally creates tracked tasks from insights
6. **Notification**: Displays insights in the bell icon panel (top-right header)

### Quick Start

**1. Enable Heartbeat:**
- Settings → Proactive Heartbeat
- Toggle "Enable Heartbeat"
- Choose check interval (30m, 1h, 2h, 4h, 6h)

**2. Configure Context Sources:**
- Enable Semantic Memory (recommended)
- Enable Git Repository (recommended)
- Optionally enable Project Files and System Health

**3. Enable Auto-Create Tasks (Optional):**
- Toggle "Auto-Create Tasks"
- Insights will automatically create tracked tasks

**4. Set Up Goals:**
- Settings → Goals & Priorities
- Enter your goals document (up to 2000 characters)

### Using HEARTBEAT.md (Power Users)

Create `HEARTBEAT.md` in your project root:

```markdown
# Heartbeat Tasks

## Memory Management
Schedule: 0 2 * * *
Enabled: true
Prompt: Review semantic memory usage and suggest cleanup if storage exceeds 100MB
Context: memory

## Testing Reminders
Schedule: 0 9 * * 1
Enabled: true
Prompt: Check test coverage and suggest missing tests
Create_Task: true
Context: git,project
```

**Sync Options:**
- **Load from File**: Import tasks from HEARTBEAT.md to database
- **Save to File**: Export configured tasks to HEARTBEAT.md

### Using Insights

**1. Check Notifications**: Click the bell icon (🔔) in the header
   - Badge shows unread insight count
   - Dropdown panel displays recent insights

**2. Review Insights**: Each insight includes:
   - **Title**: Quick summary of the insight
   - **Description**: Detailed suggestion or observation
   - **Timestamp**: When the insight was generated
   - **Create Task Button**: Convert insight to tracked task

**3. Dismiss Insights**: Click "Dismiss" to remove insights you've addressed

**4. Manual Trigger**: Force an immediate heartbeat check:
   ```bash
   curl -X POST "http://localhost:8000/api/heartbeat/trigger?user_id=default"
   ```

### Example Insights

**Progress Check**:
> **Title**: "Authentication Feature Progress"  
> **Description**: "You mentioned completing the auth feature this week. The last conversation shows you're working on password reset. Consider testing edge cases before marking complete."

**Blocker Identification**:
> **Title**: "Design Mockup Blocker"  
> **Description**: "Your goals mention waiting on design mockups. It's been 3 days since you noted this blocker. Consider reaching out to the design team or creating wireframes yourself."

**Task Suggestion**:
> **Title**: "API Documentation Reminder"  
> **Description**: "You have 5 completed tasks related to API endpoints but no documentation tasks. Consider creating a task to document the new endpoints."

**HEARTBEAT_OK (No Notification)**:
When everything is on track, the AI responds with "HEARTBEAT_OK" and no notification is created, reducing noise.

### Cost Considerations

- **Default Model**: Claude Haiku 4.5 (~$0.25 per 1M input tokens)
- **Typical Cost**: ~$0.01 per user per day with 2-hour intervals
- **Context Size**: ~1500 tokens (goals + 3 conversations + 5 tasks)
- **Daily Heartbeats**: 12 checks/day (2-hour intervals) = ~18K tokens = $0.0045

**Cost Optimization**:
- Use longer intervals (3-4 hours) to reduce frequency
- Disable during off-hours with active hours settings
- Use local Ollama models (free) instead of hosted providers
- Keep goals document concise

### Privacy & Data

- **Local Processing**: All context stays within your system
- **No External Storage**: Insights stored only in your MongoDB
- **User Isolation**: Each user's goals and insights are completely separate
- **Opt-Out Anytime**: Disable in settings or delete goals document

### Troubleshooting

**No Insights Appearing**:
1. Check heartbeat is enabled in Settings
2. Verify you're within active hours
3. Ensure goals document is saved
4. Check backend logs for errors

**Too Many Notifications**:
1. Increase interval (e.g., 2h → 4h)
2. Adjust active hours to work hours only
3. Review goals document - be more specific

**Insights Not Relevant**:
1. Update goals document with current priorities
2. Add more context about blockers and progress
3. Pin relevant conversations for better context

### API Reference

**Get Insights**:
```bash
GET /api/heartbeat/insights?user_id=default&dismissed=false
```

**Dismiss Insight**:
```bash
POST /api/heartbeat/insights/{insight_id}/dismiss?user_id=default
```

**Get Configuration**:
```bash
GET /api/heartbeat/config?user_id=default
```

**Update Configuration**:
```bash
PUT /api/heartbeat/config?user_id=default
Content-Type: application/json

{
  "enabled": true,
  "interval": "2h",
  "active_hours": {
    "start": "09:00",
    "end": "18:00",
    "timezone": "America/New_York"
  }
}
```

**Manual Trigger**:
```bash
POST /api/heartbeat/trigger?user_id=default
```

## Smart Web Search & Content Extraction

The Smart Web Search MCP server provides advanced web search capabilities that go far beyond basic search snippets:

### Intelligent Content Extraction
- **Multi-method extraction**: Uses trafilatura (primary) with BeautifulSoup fallback for maximum reliability
- **Full webpage content**: Extracts complete articles, not just search snippets
- **Content cleaning**: Removes HTML tags, normalizes whitespace, handles entities
- **Structure preservation**: Maintains headings, paragraphs, and content hierarchy

### URL Prioritization Algorithm
- **Relevance scoring**: Ranks URLs based on query term matches in titles and snippets
- **Position weighting**: Considers search result position and domain authority
- **Smart filtering**: Prioritizes documentation, tutorials, and authoritative sources

### Polite & Ethical Crawling
- **Robots.txt compliance**: Automatically checks and respects robots.txt files
- **Rate limiting**: Configurable delays between requests (default: 1 second)
- **Proper identification**: Uses descriptive User-Agent headers
- **Timeout handling**: Graceful failure recovery for unreachable sites

### Configuration Options
Configure extraction behavior via environment variables:
```bash
SMART_EXTRACT_MAX_URLS=3              # Maximum URLs to extract (default: 3)
SMART_EXTRACT_MAX_CHARS_PER_URL=2000  # Character limit per webpage (default: 2000)
SMART_EXTRACT_MAX_TOTAL_CHARS=5000    # Total character limit (default: 5000)
SMART_EXTRACT_REQUEST_DELAY=1.0       # Delay between requests (default: 1.0s)
```

### Performance & Quality
- **8x more context**: Provides significantly more content than basic search snippets
- **High success rate**: Multi-method extraction ensures reliable content retrieval
- **Memory efficient**: Character limits prevent context overflow
- **Fast processing**: Typically 3-5 seconds for 3 URLs with polite delays

The smart search feature is **automatically enabled** for all web searches - users get enhanced content extraction without any additional configuration or UI changes.

## Model Providers & Settings

- Supported providers: `ollama` (local), `openai`, `anthropic`, `google` (Gemini), `openrouter`, `groq`, `sambanova`.
- Open the Settings modal (header → Settings) to add/validate API keys per provider. Keys are validated with a lightweight request (OpenAI uses a small `max_tokens=16` check to avoid false negatives).
- The Model Picker shows models by provider. Non‑Ollama models only appear once the provider is configured.
- Provider model naming/prefixes (examples):
  - Ollama: `llama3.1` (no prefix).
  - OpenAI: `openai/gpt-5.2`.
  - Anthropic: `anthropic/claude-haiku-4-5`.
  - Google: `gemini/gemini-flash-latest`.
  - OpenRouter: `openrouter/meta-llama/llama-3.3-70b-instruct`.
  - Groq: `groq/llama-3.1-8b-instant`.
  - SambaNova: `sambanova/Meta-Llama-3.1-8B-Instruct`.

API endpoints:
- List providers: `GET /api/providers`
- Provider models: `GET /api/providers/models`
- Provider status: `GET /api/providers/{provider_id}/status`
- Save API key: `POST /api/providers/settings { provider, api_key }`
- Remove API key: `DELETE /api/providers/{provider_id}/settings`
- Validate (no key returned): `GET /api/providers/{provider_id}/validate`
- All models (flat list w/provider): `GET /api/models`

Notes:
- Codex MCP requires a valid OpenAI API key. The UI gates the Codex tool if OpenAI is not configured.

Encryption of provider API keys (required):
- The backend encrypts provider API keys (at rest) using a Fernet key set via `SETTINGS_ENCRYPTION_KEY` in `backend/.env`.
- Generate once and keep it stable across restarts; changing it invalidates previously saved keys (you’ll need to re‑enter them).
- Generate and set:
  - `pip install cryptography`
  - `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  - Set in `backend/.env`: `SETTINGS_ENCRYPTION_KEY=<output>`

## Codex Workspace (MCP)

Code generation runs in an isolated workspace with a reviewable manifest and artifacts.

- UI: Click the ✨ Tool Selector and choose “Codex (Workspace)”. Enter an instruction (e.g., “Scaffold a Vite + React app”). The assistant inserts an inline `codex_run` message that shows live status and a brief summary when complete.
- Backend: A FastMCP server (`backend/server_codex.py`) exposes tools to create workspaces, start/poll/cancel runs, read files, and fetch a manifest. Runs are async with a small in‑memory job tracker. Artifacts write to `codex_artifacts/` under the workspace.
- Security posture: Dedicated workspace per run, isolated HOME under workspace, symlink refusal, realpath containment checks, optional post‑run output policy (allowed extensions, dotfiles allowlist, max files/bytes, binary heuristics). For strongest isolation, run the service in a container/VM with no network.
- Requirements: Codex CLI available on PATH (or set `CODEX_BIN`) and a valid `OPENAI_API_KEY` (via Settings or env) — the key is injected only to the Codex subprocess.

Endpoints:
- Create workspace: `POST /api/codex/workspaces { name_hint, keep }`
- Start run (auto‑creates workspace if missing): `POST /api/codex/runs { workspace_id, instruction, model?, timeout_seconds? }`
- Get run status: `GET /api/codex/runs/{run_id}`
- Cancel run: `POST /api/codex/runs/{run_id}/cancel`
- Get manifest: `GET /api/codex/workspaces/{workspace_id}/manifest`
- Read file: `GET /api/codex/workspaces/{workspace_id}/file?relative_path=…`

Environment (optional, defaults shown):
- `CODEX_BIN=codex`, `CODEX_WORKSPACES_DIR=./.codex_workspaces`, `CODEX_MAX_CONCURRENCY=1`, `CODEX_RUN_TTL_HOURS=48`
- `CODEX_MAX_PROMPT_CHARS=20000`, `CODEX_MAX_STDOUT_CHARS=200000`, `CODEX_MAX_STDERR_CHARS=50000`
- `CODEX_MAX_OUTPUT_FILES=500`, `CODEX_MAX_OUTPUT_TOTAL_BYTES=20971520`, `CODEX_DEBUG=false`

Frontend UX notes:
- Codex runs now render inline as a chat message (`type='codex_run'`) that persists in the transcript. The old floating run card is removed.
- The sidebar shows Codex MCP status; it appears green only when the service is ready and OpenAI is configured.
- A File Viewer Modal exists for future use via the manifest/file APIs; it is not auto‑triggered to avoid dead links.

## How It Works

1.  The **User** interacts with the **React Frontend**.
2.  The **Frontend** sends requests (chat messages, conversation management) to the **FastAPI Backend** API.
3.  For chat messages, the **Backend** (`main.py`) processes the request:
    *   It may interact with an LLM via the provider layer (Ollama by default; configure others in Settings).
    *   If the user enables a tool (e.g., web search, SQL query) via the UI:
        *   The backend prepares the necessary context (e.g., fetching database schema for SQL).
        *   It may prompt the Ollama model to generate a tool-specific input (e.g., a SQL query or HubSpot JSON payload).
        *   The backend then communicates with the relevant **MCP Service Module** (managed as a subprocess: search, SQL, YouTube, HubSpot, Python, Codex).
        *   The MCP Service Module executes the tool (e.g., calls Serper.dev API, queries MySQL).
        *   Results from the MCP Service Module are returned to the Backend.
        *   The Backend may re-prompt Ollama with the tool's results to generate a final, informed response.
4.  The **Backend** stores/retrieves conversation history from **MongoDB**.
5.  The final response is streamed back to the **Frontend** and displayed to the user.

### AI Summaries for Context

- Purpose: Pinned conversations contribute short, LLM‑generated summaries to the system prompt so future chats can reference prior work without sending full transcripts.
- Generation:
  - On‑demand, user‑initiated (not heuristic). If you pin a chat that has no summary, the app asks to generate one first and gates pinning until done.
  - The backend assembles up to ~1000 words of recent conversation (HTML stripped) and prompts the selected model to produce a single‑paragraph summary capped at ~750 characters.
  - Stored summaries are reused; automatic regeneration is not performed.
- Limits & Enforcement:
  - Hard cap of 5 pinned conversations. The backend enforces the cap and the UI disables pinning at the limit.
  - Pin stats are surfaced in the UI (e.g., “X/5 pinned”).
- Model Selection:
  - Choose the model under Settings → Summaries → Select Model. This uses the same provider model catalogs as chat.
  - If no model is configured for summaries, generation will fail until you select one.
- Context Assembly:
  - Only stored summaries are included in the system prompt for context; heuristic/auto summaries are not used.
  - The context service budgets space for summaries alongside your profile prompt.
- Maintenance:
  - Admin utilities exist to bulk remove summaries and/or unpin all chats for a clean slate. Use with care in production.

APIs (reference):
- Summary settings: `GET /api/summaries/settings`, `POST /api/summaries/settings { model_name }`
- Generate summary: `POST /api/summaries/generate { conversation_id }`
- Pinning: `POST /api/user-context/pin-conversation { conversation_id, pinned }` (cap enforced)
- Pin stats: `GET /api/user-context/pin-stats` → `{ count, max }`

## Scheduled Tasks (Timezone & One‑Time)

- Create schedules from the Tasks panel → Scheduled tab.
- Two modes:
  - Recurring: cron expression + timezone. Next run is computed from local wall‑clock in the chosen timezone (DST‑aware) and stored as UTC.
  - One‑time: set a date/time and timezone; auto‑disables after the first run.
- You can “Run now” and optionally override the model per run.

See `TASKS_USER_GUIDE.md` for full details.

## Customization

-   **Model Providers**: Use the header Model Picker to select a provider/model. Configure provider API keys in Settings; non‑Ollama models only appear once configured.
-   **Ollama Model**: Select from available local models (or set `DEFAULT_OLLAMA_MODEL`). Models well-suited to coding may work better with SQL (e.g., codestral).
-   **Search Results**: Adjust the number of search results processed in `backend/main.py`.
-   **Database Schema Context**: Modify `MAX_TABLES_FOR_SCHEMA_CONTEXT` in `backend/main.py` to control how many tables' schemas are sent to the LLM.
-   **Prompt Engineering**: Modify the system prompts sent to Ollama in `backend/main.py` to tailor responses and SQL generation.
-   **Styling**: Customize the frontend appearance by modifying CSS files or styles within the React components in `frontend/src/`.

## Setup & Usage (Quick Start)

1. Backend: `cd backend && uvicorn main:app --reload --port 8000`
2. Frontend: `cd frontend && npm install && npm run dev`
3. In the app:
   - Choose a model (header → Model Picker).
   - Optional: open Settings to add OpenAI/other provider keys.
   - Use the ✨ Tool Selector to run Smart Web Search, Database, YouTube, Python, HubSpot, or Codex.
   - Tasks panel supports ad‑hoc and Scheduled tasks.

Prereqs:
- Ollama running for local models (pull a model, e.g., `ollama pull llama3.1`).
- MongoDB reachable (for history/tasks).
- For Codex: install Codex CLI and configure an OpenAI API key (via Settings or env) before starting runs.

## Updating

To update to the latest version without affecting your existing data (MongoDB, ChromaDB, `.env`):

```bash
# 1. Pull latest code
git pull origin main

# 2. Update backend dependencies
cd backend
pip install -r requirements.txt

# 3. Rebuild frontend
cd ../frontend
npm install
npm run build

# 4. Restart the backend
# Manually:
cd ../backend
uvicorn main:app --host 127.0.0.1 --port 8000

# macOS Launch Agent:
launchctl stop com.osoba.backend && launchctl start com.osoba.backend

# Linux systemd:
sudo systemctl restart osoba-backend
```

**Your data is safe**: MongoDB (conversations, tasks, documents, settings) and ChromaDB (semantic memory, KB embeddings) are external services not touched by a code update. Your `.env` file is gitignored and will never be overwritten.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
