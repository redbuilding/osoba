# 🔍 🤖 🌐 OhSee (Ollama Chat with MCP)

A powerful demonstration of integrating local LLMs with real-time web search, SQL, YouTube transcript analysis, HubSpot actions, and Python data analysis via the Model Context Protocol (MCP) — featuring a modern web interface, streaming responses, and persistent conversations.

## Overview

OhSee showcases how to extend a local language model's capabilities through tool use. This application combines the power of locally running LLMs via Ollama with up-to-date web search, SQL querying, YouTube transcript ingestion, HubSpot business actions, and Python-based CSV analysis/visualization — all managed through a robust backend and a user-friendly React frontend. Conversations are persisted using MongoDB.

The project consists of several key components:

- **Backend (FastAPI)**: Manages chat logic, Ollama interactions, MCP service communication (including starting and managing MCP services like web search and SQL querying), and conversation persistence.

- **Frontend (React)**: A modern, responsive web interface for users to interact with the chat application.

- **MCP Web Search Server Module**: Provides web search via the Serper.dev API.

- **MCP SQL Server Module**: Read-only querying against a MySQL database (with schema resources and query safety).

- **MCP YouTube Transcript Server**: Robustly fetches transcripts using multiple strategies (youtube-transcript-api, Pytube, yt-dlp) with optional proxy support, then persists transcript context to the conversation for follow-ups.

- **MCP HubSpot Business Tools**: Create/update marketing emails via HubSpot APIs using OAuth, with a JSON-first prompting flow.

- **MCP Python Data Analysis Server**: Comprehensive data analysis toolkit including CSV loading, data profiling, filtering, grouping/aggregation, outlier detection, data type conversion, statistical hypothesis testing, and visualization (base64 images) for complete analytical workflows.

- **MongoDB**: Stores conversation history and user data.

This architecture demonstrates how MCP enables local models to access external tools and data sources, significantly enhancing their capabilities. The backend starts and supervises all MCP services for a scalable, feature-rich setup.

## Demo

- Watch the demo on X: https://x.com/redbuilding/status/2010124029936427450

## Features

- 🔎 **Web-enhanced chat**: Access real-time web search results during conversation.
- 💾 **Persistent Conversations**: Chat history is saved in MongoDB, allowing users to resume conversations.
- 🧠 **Local model execution**: Uses Ollama to run models entirely on your own hardware.
- 🔌 **MCP integration**: Backend manages multiple MCP tools (web, SQL, YouTube, HubSpot, Python) as background services.
- 💻 **Modern Web Interface**: Built with React for a responsive and interactive user experience.
- 📊 **Structured search results**: Clean formatting of web search data for optimal context.
- ⚙️ **Backend API**: FastAPI backend providing robust API endpoints for chat and conversation management.
- 🗃️ **SQL Querying Tool**: Read-only MySQL querying with schema introspection and retry logic.
- 🔄 **Conversation Management**: List, rename, and delete conversations.
- 📺 **YouTube Transcript Tool**: Paste a YouTube URL; transcripts are fetched and stored for multi-turn follow-ups.
- 🧰 **HubSpot Tools**: OAuth-connect, then create/update marketing emails via guided JSON prompts.
- 🐍 **Python Analysis Tool**: Upload a CSV and run comprehensive analysis including data profiling, filtering, grouping, outlier detection, statistical testing, type conversion, and visualization — results stream back with images and detailed insights.
- ⚡ **Streaming Responses**: Frontend renders model output token-by-token and indicators for tool usage.
- 🗓️ **Long‑Running Tasks (Plan & Execute)**: Create autonomous tasks that plan and execute multi‑step workflows (overnight runs supported), with budgets, retries, and verification.
- 📈 **Live Task Progress**: Tasks stream progress via SSE; per‑step outputs (tables/images/text) render in the UI.
- 🧩 **LLM‑only Steps (No MCP)**: Tasks can include steps that run directly on Ollama (e.g., summaries/reasoning) without using any MCP tool.
- 🚦 **Priority Task Queue**: Memory-safe task execution with priority scheduling - scheduled tasks run first, user tasks queue behind them, only one task executes at a time to prevent system overload.

## Task Execution & Memory Management

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

## Requirements
- Python 3.11+
- Node.js (v18+) and npm/yarn for the frontend
- [Ollama](https://ollama.com/) installed and running locally
- A [Serper.dev](https://serper.dev/) API key (free tier available)
- MongoDB instance (local or cloud)
- MySQL server (optional, for the SQL querying tool)
- Internet connection for web searches and package downloads

Optional (enable additional tools):
- Python data analysis: `pandas`, `numpy`, `matplotlib`, `seaborn`
- YouTube transcripts: `youtube-transcript-api`, `pytube`, `yt-dlp`, `requests`
- HubSpot OAuth: valid OAuth app (client ID/secret) and redirect URL

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/redbuilding/ollama-chat-with-mcp.git
    cd ollama-chat-with-mcp
    ```

2.  **Set up Backend:**
    *   Navigate to the backend directory:
        ```bash
        cd backend
        ```
    *   Install Python dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   Create a `.env` file in the `backend` directory. This is where the backend and its managed MCP services will look for environment variables:
        ```dotenv
        # For Web Search (server_search.py)
        SERPER_API_KEY=your_serper_api_key_here

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
        ```

    *   Install optional dependencies for additional tools (if you plan to use them):
        ```bash
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
    The FastAPI application automatically starts and manages all MCP services (Web, SQL, YouTube, HubSpot, Python) as background processes using its lifespan manager. You do **not** need to run the MCP servers separately.

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
-   Click the ✨ Tool Selector to enable one of: Web Search, Database, YouTube, HubSpot, Python.
-   For YouTube: paste a video URL. The transcript is fetched and saved to the conversation for follow-ups.
-   For HubSpot: click “Connect HubSpot” to complete OAuth, then describe the email to create/update.
-   For Python: upload a CSV file when prompted; follow-up questions reuse the loaded DataFrame for advanced analysis including filtering, grouping, outlier detection, statistical testing, and visualization.
-   Manage conversations using the sidebar (create new, select, rename, delete).

### Long‑Running Tasks (Plan & Execute)

-   Open the Tasks panel (Tasks button in the header) to:
    -   Create a new task by entering a high‑level goal.
    -   Monitor progress (live SSE stream), view step outputs (tables, images, text), and Pause/Resume/Cancel.
    -   “Promote to Task” from any user chat message to pre‑fill the goal and link the task to the conversation.
    -   Copy entire task results or individual step outputs using dedicated copy buttons.
    -   Delete completed, failed, or canceled tasks to clean up the task list.-   The backend plans each task as structured JSON (steps, tool, parameters, success criteria), then executes steps sequentially with:
    -   Budgets: max wall‑time and max tool calls.
    -   Per‑step timeouts and capped retries with backoff.
    -   Output verification against success criteria.
-   Completion: When the final step finishes, the task status becomes COMPLETED. On failure/timeouts/budgets exceeded, status is FAILED. A concise summary is posted back into the linked conversation.

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

## How It Works

1.  The **User** interacts with the **React Frontend**.
2.  The **Frontend** sends requests (chat messages, conversation management) to the **FastAPI Backend** API.
3.  For chat messages, the **Backend** (`main.py`) processes the request:
    *   It may interact with **Ollama** to get a response from the local LLM.
    *   If the user enables a tool (e.g., web search, SQL query) via the UI:
        *   The backend prepares the necessary context (e.g., fetching database schema for SQL).
        *   It may prompt the Ollama model to generate a tool-specific input (e.g., a SQL query or HubSpot JSON payload).
        *   The backend then communicates with the relevant **MCP Service Module** (managed as a subprocess: search, SQL, YouTube, HubSpot, Python).
        *   The MCP Service Module executes the tool (e.g., calls Serper.dev API, queries MySQL).
        *   Results from the MCP Service Module are returned to the Backend.
        *   The Backend may re-prompt Ollama with the tool's results to generate a final, informed response.
4.  The **Backend** stores/retrieves conversation history from **MongoDB**.
5.  The final response is streamed back to the **Frontend** and displayed to the user.


## Customization

-   **Ollama Model**: Select from available models in the UI (or set `DEFAULT_OLLAMA_MODEL`). Models well-suited to coding may work better with SQL (e.g., codestral).
-   **Search Results**: Adjust the number of search results processed in `backend/main.py`.
-   **Database Schema Context**: Modify `MAX_TABLES_FOR_SCHEMA_CONTEXT` in `backend/main.py` to control how many tables' schemas are sent to the LLM.
-   **Prompt Engineering**: Modify the system prompts sent to Ollama in `backend/main.py` to tailor responses and SQL generation.
-   **Styling**: Customize the frontend appearance by modifying CSS files or styles within the React components in `frontend/src/`.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
