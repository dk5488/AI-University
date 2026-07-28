# System Startup Commands

This document explains the commands used to bring up all components of the AI University system.

## 1. Starting the Infrastructure (Docker Compose)
**Command:** `docker-compose up -d`
**Directory:** `c:\Users\divyp\Documents\AI University`

**Explanation:**
- `docker-compose up`: This command reads the `docker-compose.yml` file and starts all the defined services.
- `-d`: Runs the containers in "detached" mode, meaning they run in the background and don't block the terminal. 
- **Services Started:**
  - **PostgreSQL:** The relational database (running on port 5433).
  - **Redis:** Used for caching or background tasks (running on port 6379).
  - **Qdrant:** The vector database for AI embeddings (running on ports 6333/6334).

## 2. Starting the Backend API (FastAPI)
**Command:** `.venv\Scripts\python -m uvicorn app.main:app --reload`
**Directory:** `c:\Users\divyp\Documents\AI University`

**Explanation:**
- `.venv\Scripts\python -m uvicorn`: Runs the Uvicorn ASGI server using the Python interpreter from the virtual environment (`.venv`). This ensures all the required backend dependencies are used.
- `app.main:app`: Tells Uvicorn where to find the FastAPI application instance. It looks in the `app` package, inside the `main.py` module, for an object named `app`.
- `--reload`: Enables auto-reloading. Whenever you make changes to the Python code, the backend server will automatically restart to reflect those changes.
- **Port:** The backend typically runs on `http://127.0.0.1:8000` (or `http://localhost:8000`).

## 3. Starting the RAG Pipeline API
**Command:** `..\.venv\Scripts\python -m uvicorn api:app --port 8001 --reload`
**Directory:** `c:\Users\divyp\Documents\AI University\RAG Pipeline`

**Explanation:**
- This starts the RAG Pipeline's FastAPI server, which exposes a `/search` endpoint.
- The main backend calls this API to retrieve relevant document chunks from the knowledge base (Qdrant Cloud / `rag_notes` collection) for teaching/explanation queries.
- The RAG Pipeline handles embedding queries with FastEmbed (BAAI/bge-small-en-v1.5) and searching the vector store internally.
- `--port 8001`: Runs on port 8001 to avoid conflict with the main backend on port 8000.
- **Port:** The RAG Pipeline API runs on `http://127.0.0.1:8001`.

## 4. Starting the Frontend UI (React / Vite)
**Command:** `npm install && npm run dev`
**Directory:** `c:\Users\divyp\Documents\AI University\web`

**Explanation:**
- `npm install`: Ensures that all the Node.js dependencies defined in `package.json` are installed in the `node_modules` folder.
- `&&`: Chains the two commands so that the second one only runs if the first one succeeds.
- `npm run dev`: Executes the `dev` script defined in `package.json` (which is typically `vite`). This starts the Vite development server for the frontend.
- **Port:** The frontend development server typically runs on `http://localhost:5173`.
