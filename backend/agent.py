import requests
import time
import subprocess
import os
import psutil

SERVER_URL = "http://127.0.0.1:5050"

WORKER_ID = "cpu-node2"
USE_GPU = False


# -------------------------------
# Get Task
# -------------------------------
def get_task():
    try:
        res = requests.get(
            f"{SERVER_URL}/get-task",
            params={"requires_gpu": USE_GPU}
        )
        return res.json()
    except:
        return {}


# -------------------------------
# Run Task
# -------------------------------
def run_task(code):
    with open("task.py", "w", encoding="utf-8") as f:
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
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return out.decode(), True
    except subprocess.CalledProcessError as e:
        return e.output.decode(), False


# -------------------------------
# Send Result
# -------------------------------
def send_result(task_id, output, success):
    requests.post(
        f"{SERVER_URL}/result",
        json={
            "task_id": task_id,
            "worker_id": WORKER_ID,
            "output": output,
            "success": success
        }
    )


# -------------------------------
# 🔥 Stats functions
# -------------------------------
def get_cpu_usage():
    return psutil.cpu_percent(interval=0.5)


def get_gpu_usage():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"]
        )
        return int(output.decode().strip())
    except:
        return 0


def send_stats():
    try:
        requests.post(
            f"{SERVER_URL}/stats",
            json={
                "worker_id": WORKER_ID,
                "cpu": get_cpu_usage(),
                "gpu": get_gpu_usage()
            }
        )
    except:
        pass


# -------------------------------
# Worker Loop
# -------------------------------
while True:
    send_stats()

    task = get_task()

    if task and "code" in task:
        print(f"[AGENT] Running {task['task_id']}")

        output, success = run_task(task["code"])

        send_result(task["task_id"], output, success)

        print(f"[AGENT] Done {task['task_id']}")

    else:
        print("[AGENT] No task")

    time.sleep(2)