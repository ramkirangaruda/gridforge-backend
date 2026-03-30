from fastapi import FastAPI
from pydantic import BaseModel
import uuid

from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks = []

class Task(BaseModel):
    code: str
    requires_gpu: bool = False

@app.post("/submit-task")
def submit_task(task: Task):
    task_id = str(uuid.uuid4())

    tasks.append({
        "task_id": task_id,
        "code": task.code,
        "requires_gpu": task.requires_gpu,
        "status": "pending"
    })

    print(f"[SERVER] Task received: {task_id}")
    return {"task_id": task_id}

@app.get("/get-task")
def get_task():
    for task in tasks:
        if task["status"] == "pending":
            task["status"] = "processing"
            print(f"[SERVER] Assigning task: {task['task_id']}")
            return task
    return {}

@app.post("/result")
def submit_result(data: dict):
    for task in tasks:
        if task["task_id"] == data["task_id"]:
            task["status"] = "completed"
            task["output"] = data["output"]
            task["worker_id"] = data["worker_id"]

    print(f"[SERVER] Result received: {data['task_id']}")
    return {"message": "stored"}

@app.get("/results")
def get_results():
    return tasks