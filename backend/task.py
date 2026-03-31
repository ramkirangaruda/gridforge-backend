import time

print("🔥 Controlled CPU load started")

start = time.time()

while time.time() - start < 8:  # runs for 8 seconds
    x = 0
    for i in range(1_000_000):
        x += i * i

print("🔥 Finished")