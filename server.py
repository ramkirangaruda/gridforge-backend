from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks = []
combined_done = set()


@app.post("/submit-task")
def submit_task(task: dict):

    code = task["code"]
    requires_gpu = task.get("requires_gpu", False)
    split = task.get("split", False)

    
    if split and "for" in code and "range" in code:

        parent_id = str(uuid.uuid4())

        # simple demo split (same code, different labels)
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

        tasks.append(part1)
        tasks.append(part2)

        print(f"[SERVER] Split task {parent_id}")

        return {
            "parent_id": parent_id,
            "message": "Task split into subtasks"
        }

    
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

        tasks.append(new_task)

        print(f"[SERVER] Normal task {task_id}")

        return {
            "task_id": task_id,
            "message": "Task submitted normally"
        }



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



def combine_split_tasks():
    combined_results = []

    parent_ids = set(t["parent_id"] for t in tasks if t["parent_id"])

    for pid in parent_ids:

        if pid in combined_done:
            continue

        parts = [t for t in tasks if t["parent_id"] == pid]

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



@app.get("/results")
def get_results():
    return tasks + combine_split_tasks()