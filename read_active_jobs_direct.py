import json

with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
    jobs = json.load(f)

print(f"Total jobs: {len(jobs)}")
statuses = {}
for j in jobs:
    s = j.get("status", "unknown")
    statuses[s] = statuses.get(s, 0) + 1
print("Statuses in jobs.json:", statuses)

# Check active jobs
active = [j for j in jobs if j.get("status") in ["queued", "running", "processing"]]
print(f"Active count: {len(active)}")
for a in active[:5]:
    print(" -", a.get("id"), a.get("status"), a.get("step"), a.get("progress"))
