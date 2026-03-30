import requests
import time
import subprocess
import os

SERVER_URL = "http://127.0.0.1:5050"
WORKER_ID = "cpu-node"
USE_GPU = False  # set False if you want CPU worker

def get_task():
    try:
        return requests.get(f"{SERVER_URL}/get-task").json()
    except:
        return {}

def run_task(code):
    with open("task.py", "w") as f:
        f.write(code)

    cmd = ["docker", "run", "--rm"]

    if USE_GPU:
        cmd += ["--gpus", "all"]

    cmd += [
    "-v", f"{os.getcwd()}:/app",
    "-w", "/app",
    "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
    "python", "task.py"
]

    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return output.decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode()

def send_result(task_id, output):
    requests.post(f"{SERVER_URL}/result", json={
        "task_id": task_id,
        "worker_id": WORKER_ID,
        "output": output
    })

while True:
    task = get_task()

    if task and "code" in task:
        print(f"[AGENT] Running task {task['task_id']}")
        result = run_task(task["code"])
        send_result(task["task_id"], result)
        print(f"[AGENT] Done")

    time.sleep(3)