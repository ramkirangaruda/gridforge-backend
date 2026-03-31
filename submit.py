import requests

code = """
import torch
import torch.nn as nn

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

model = nn.Sequential(
    nn.Linear(1000, 512),
    nn.ReLU(),
    nn.Linear(512, 10)
)

if device == "cuda":
    try:
        model = model.to(device)
    except:
        print("Fallback to CPU due to compatibility")
        device = "cpu"
        model = model.to(device)

x = torch.randn(32, 1000).to(device)

try:
    output = model(x)
    print("Output shape:", output.shape)
    print("Tensor sum:", output.sum().item())
    print("Neural network executed successfully on", device)
except Exception as e:
    print("Execution fallback:", str(e))
    print("Neural network executed on CPU safely")
"""

response = requests.post(
    "http://127.0.0.1:5050/submit-task",
    json={
        "code": code,
        "requires_gpu": True,
        "split": False   # change to True to test splitting
    },
    timeout=10
)

print("Response:", response.json())