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

- **MCP Python Data Analysis Server**: Load CSVs, inspect/clean data, compute statistics, query DataFrames, and produce plots (base64 images) for analysis workflows.

- **MongoDB**: Stores conversation history and user data.

This architecture demonstrates how MCP enables local models to access external tools and data sources, significantly enhancing their capabilities. The backend starts and supervises all MCP services for a scalable, feature-rich setup.

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
- 🐍 **Python Analysis Tool**: Upload a CSV and run analysis, cleaning, stats, and plots — results can stream back with images.
- ⚡ **Streaming Responses**: Frontend renders model output token-by-token and indicators for tool usage.

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
        pip install pandas numpy matplotlib seaborn
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
-   For Python: upload a CSV file when prompted; follow-up questions reuse the loaded DataFrame.
-   Manage conversations using the sidebar (create new, select, rename, delete).

### Legacy Clients (Phasing Out)

The original `chat_client.py` (terminal) and `chat_frontend.py` (Gradio) are still in the repository but are not part of the main refactored application. They are not maintained and may not work correctly with the new backend, and will be phased out in a future update.

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
