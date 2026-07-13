# GridForge

GridForge is a distributed task execution system. It allows users to upload Python projects as ZIP files, which are then executed in a sandboxed Docker environment. A React-based frontend provides an interface for uploading projects and viewing task status and logs in real-time.

This repository contains the fully repaired and operational GridForge application.

## Architecture

The system consists of four main components:

1.  **Frontend:** A React application (`frontend/`) that allows users to upload a `.zip` file containing a Python project. It polls the backend for task status updates and displays them on a dashboard.
2.  **Backend:** A FastAPI server (`backend/`) that provides a REST API for submitting tasks and retrieving task information. It uses a simple JSON file (`uploads/tasks_db.json`) for persistence and a Redis queue for dispatching tasks to workers.
3.  **Worker:** A Python script (`worker/main.py`) that listens to the Redis queue for new tasks. When a task is received, it downloads the associated project, creates a secure Docker container, and executes the user's code.
4.  **Redis:** Acts as a message broker, decoupling the backend from the worker.

## Prerequisites

-   **Python 3.10+** and `pip`
-   **Node.js and npm** (for the frontend)
-   **Docker Desktop:** Must be running to execute tasks.
-   **Redis:** A Redis instance must be accessible. The simplest way is to run it via Docker.

## How to Run the System

To run GridForge, you need to start Redis, the backend server, the worker, and the frontend application in separate terminals.

### 1. Start Redis

If you don't have a Redis instance running, open a terminal and run:

```sh
docker run --rm --name gridforge-redis -p 6379:6379 redis:7-alpine
```

### 2. Set up the Python Environment

All Python components share the same virtual environment.

```powershell
# From the project root (gridforge)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt -r worker/requirements.txt
```

### 3. Start the Backend Server

In a new terminal, from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The API server will be available at `http://127.0.0.1:8000`.

### 4. Start the Worker

In another new terminal, from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python worker/main.py
```

The worker will connect to Redis and wait for tasks.

### 5. Start the Frontend

Finally, in a fourth terminal, navigate to the `frontend` directory:

```powershell
cd frontend
npm install
npm start
```

This will open the user interface in your browser at `http://localhost:3000`.

## How to Use

1.  Navigate to `http://localhost:3000` in your web browser.
2.  Create a simple Python project containing a `main.py` file and, optionally, a `requirements.txt` file.
3.  Compress the project into a `.zip` archive.
4.  Drag and drop the ZIP file onto the upload area on the web page.
5.  The task will appear in the dashboard. You can expand the task card to view the execution logs once it completes.

