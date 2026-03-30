import time

start = time.time()

total = 0
for i in range(1, 30):
    total += i * i

end = time.time()

print("Result:", total)
print("Time:", end - start)
print('--- Part 2 done ---')