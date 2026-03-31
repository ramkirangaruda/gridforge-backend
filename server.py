from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uuid
import redis
import json
import time
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

combined_done = set()

# 🔥 NEW: stats storage
worker_stats = {}
worker_history = {}


# -------------------------------
# Helper: Push task
# -------------------------------
def push_task(task):
    task_id = task["task_id"]

    r.set(f"task:{task_id}", json.dumps(task))

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

    def base_task():
        return {
            "status": "pending",
            "output": "",
            "retry_count": 0,
            "max_retries": 2,
            "assigned_at": None
        }

    if split and "for" in code and "range" in code:

        parent_id = str(uuid.uuid4())

        part1 = {
            **base_task(),
            "task_id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "part": 1,
            "code": code + "\nprint('--- Part 1 done ---')",
            "requires_gpu": False,
        }

        part2 = {
            **base_task(),
            "task_id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "part": 2,
            "code": code + "\nprint('--- Part 2 done ---')",
            "requires_gpu": requires_gpu,
        }

        push_task(part1)
        push_task(part2)

        return {"parent_id": parent_id}

    else:
        task_id = str(uuid.uuid4())

        new_task = {
            **base_task(),
            "task_id": task_id,
            "parent_id": None,
            "part": None,
            "code": code,
            "requires_gpu": requires_gpu,
        }

        push_task(new_task)

        return {"task_id": task_id}


# -------------------------------
# Get Task
# -------------------------------
@app.get("/get-task")
def get_task(requires_gpu: bool = None):

    queue_name = "gpu_queue" if requires_gpu else "cpu_queue"

    task_id = r.lpop(queue_name)

    if not task_id:
        return {}

    task_data = json.loads(r.get(f"task:{task_id}"))

    task_data["status"] = "processing"
    task_data["assigned_at"] = time.time()

    r.set(f"task:{task_id}", json.dumps(task_data))
    r.rpush("processing_queue", task_id)

    return task_data


# -------------------------------
# Submit Result (retry + failure)
# -------------------------------
@app.post("/result")
def submit_result(data: dict):

    task_id = data["task_id"]
    success = data.get("success", True)

    task_data = json.loads(r.get(f"task:{task_id}"))

    if success:
        task_data["status"] = "completed"
        task_data["output"] = data["output"]
    else:
        task_data["retry_count"] += 1

        if task_data["retry_count"] <= task_data["max_retries"]:
            task_data["status"] = "pending"
            task_data["assigned_at"] = None

            queue = "gpu_queue" if task_data.get("requires_gpu") else "cpu_queue"
            r.rpush(queue, task_id)

            print(f"[SERVER] Retrying {task_id}")
        else:
            task_data["status"] = "failed"
            task_data["output"] = data["output"]

            print(f"[SERVER] Failed permanently {task_id}")

    r.set(f"task:{task_id}", json.dumps(task_data))
    r.lrem("processing_queue", 0, task_id)

    return {"message": "updated"}


# -------------------------------
# Timeout Recovery
# -------------------------------
def recover_stuck_tasks(timeout=15):
    processing = r.lrange("processing_queue", 0, -1)

    for task_id in processing:
        task_data = json.loads(r.get(f"task:{task_id}"))

        if task_data["status"] == "processing":
            assigned = task_data.get("assigned_at")

            if assigned and time.time() - assigned > timeout:

                task_data["retry_count"] += 1

                if task_data["retry_count"] <= task_data["max_retries"]:
                    task_data["status"] = "pending"
                    task_data["assigned_at"] = None

                    queue = "gpu_queue" if task_data.get("requires_gpu") else "cpu_queue"
                    r.rpush(queue, task_id)

                    print(f"[SERVER] Timeout retry {task_id}")
                else:
                    task_data["status"] = "failed"

                r.set(f"task:{task_id}", json.dumps(task_data))
                r.lrem("processing_queue", 0, task_id)


def background_recovery():
    while True:
        recover_stuck_tasks()
        time.sleep(5)


threading.Thread(target=background_recovery, daemon=True).start()


# -------------------------------
# 🔥 Stats endpoint
# -------------------------------
@app.post("/stats")
def update_stats(data: dict):
    worker_id = data["worker_id"]

    worker_stats[worker_id] = data

    if worker_id not in worker_history:
        worker_history[worker_id] = []

    worker_history[worker_id].append({
        "time": time.time(),
        "cpu": data["cpu"],
        "gpu": data["gpu"]
    })

    if len(worker_history[worker_id]) > 50:
        worker_history[worker_id].pop(0)

    return {"status": "ok"}


@app.get("/stats-history")
def get_stats_history():
    return worker_history


# -------------------------------
# Results
# -------------------------------
@app.get("/results")
def get_results():
    keys = r.keys("task:*")
    return [json.loads(r.get(k)) for k in keys]