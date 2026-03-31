from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uuid
import redis
import json

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

combined_done = set()


# -------------------------------
# Helper: Push task to Redis queue
# -------------------------------
def push_task(task):
    task_id = task["task_id"]

    # Store task data
    r.set(f"task:{task_id}", json.dumps(task))

    # Push into correct queue
    if task.get("requires_gpu", False):
        r.rpush("gpu_queue", task_id)
    else:
        r.rpush("cpu_queue", task_id)


# -------------------------------
# Submit Task
# -------------------------------
@app.post("/submit-task")
def submit_task(task: dict):

    code = task["code"]
    requires_gpu = task.get("requires_gpu", False)
    split = task.get("split", False)

    # ---------------- SPLIT LOGIC ----------------
    if split and "for" in code and "range" in code:

        parent_id = str(uuid.uuid4())

        part1 = {
            "task_id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "part": 1,
            "code": code + "\nprint('--- Part 1 done ---')",
            "requires_gpu": False,
            "status": "pending",
            "output": ""
        }

        part2 = {
            "task_id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "part": 2,
            "code": code + "\nprint('--- Part 2 done ---')",
            "requires_gpu": requires_gpu,
            "status": "pending",
            "output": ""
        }

        push_task(part1)
        push_task(part2)

        print(f"[SERVER] Split task {parent_id}")

        return {
            "parent_id": parent_id,
            "message": "Task split into subtasks"
        }

    # ---------------- NORMAL TASK ----------------
    else:
        task_id = str(uuid.uuid4())

        new_task = {
            "task_id": task_id,
            "parent_id": None,
            "part": None,
            "code": code,
            "requires_gpu": requires_gpu,
            "status": "pending",
            "output": ""
        }

        push_task(new_task)

        print(f"[SERVER] Normal task {task_id}")

        return {
            "task_id": task_id,
            "message": "Task submitted normally"
        }


# -------------------------------
# Get Task (Worker pulls)
# -------------------------------
@app.get("/get-task")
def get_task(requires_gpu: bool = None):

    queue_name = "gpu_queue" if requires_gpu else "cpu_queue"

    task_id = r.lpop(queue_name)

    if not task_id:
        return {}

    task_data = json.loads(r.get(f"task:{task_id}"))

    # mark processing
    task_data["status"] = "processing"
    r.set(f"task:{task_id}", json.dumps(task_data))

    # track processing
    r.rpush("processing_queue", task_id)

    print(f"[SERVER] Assigned task {task_id}")

    return task_data


# -------------------------------
# Submit Result
# -------------------------------
@app.post("/result")
def submit_result(data: dict):

    task_id = data["task_id"]

    task_data = json.loads(r.get(f"task:{task_id}"))

    task_data["status"] = "completed"
    task_data["output"] = data["output"]
    task_data["worker_id"] = data["worker_id"]

    r.set(f"task:{task_id}", json.dumps(task_data))

    # remove from processing queue
    r.lrem("processing_queue", 0, task_id)

    print(f"[SERVER] Result received: {task_id}")

    return {"message": "stored"}


# -------------------------------
# Combine Split Tasks
# -------------------------------
def combine_split_tasks():

    combined_results = []

    keys = r.keys("task:*")
    all_tasks = [json.loads(r.get(k)) for k in keys]

    parent_ids = set(t["parent_id"] for t in all_tasks if t["parent_id"])

    for pid in parent_ids:

        if pid in combined_done:
            continue

        parts = [t for t in all_tasks if t["parent_id"] == pid]

        if len(parts) == 2 and all(p["status"] == "completed" for p in parts):

            combined_output = "\n".join([p["output"] for p in parts])

            combined_results.append({
                "task_id": pid,
                "status": "completed",
                "worker_id": "multi-node",
                "output": combined_output
            })

            combined_done.add(pid)

            print(f"[SERVER] Combined result for {pid}")

    return combined_results


# -------------------------------
# Get Results
# -------------------------------
@app.get("/results")
def get_results():

    keys = r.keys("task:*")

    all_tasks = [json.loads(r.get(k)) for k in keys]

    return all_tasks + combine_split_tasks()