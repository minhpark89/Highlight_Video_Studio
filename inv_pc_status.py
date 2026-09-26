import json, os, subprocess, glob

print("=== 1. Ports listening on PC ===")
net_cmd = "Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 5000,5080,8000,8080,8501,8888,3000 } | Select-Object LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize"
p = subprocess.run(["powershell", "-NoProfile", "-Command", net_cmd], capture_output=True, text=True)
print(p.stdout)

print("=== 2. Highlight_Video_Studio jobs.json contents ===")
jobs_path = r"D:\Highlight_Video_Studio\jobs.json"
if os.path.exists(jobs_path):
    try:
        with open(jobs_path, "r", encoding="utf-8") as f:
            j = json.load(f)
        print(f"Total jobs: {len(j)}")
        for item in j[-5:]:
            print("Job:", item.get("id"), item.get("status"), item.get("youtube_url"), item.get("error"))
    except Exception as e:
        print("Error reading jobs.json:", e)

print("=== 3. Check any other jobs.json or render queues on D: ===")
for root, dirs, files in os.walk(r"D:\\"):
    if any(x in root for x in [".git", "venv", "node_modules", "downloads", "temp"]): continue
    for f in files:
        if "job" in f.lower() or "queue" in f.lower() or "task" in f.lower():
            if f.endswith((".json", ".sqlite", ".db")):
                p = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(p)
                    import time
                    if time.time() - mtime < 3600:
                        print("Recently modified task file:", p, "Size:", os.path.getsize(p))
                except:
                    pass

