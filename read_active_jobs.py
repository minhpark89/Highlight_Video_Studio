import urllib.request
import json

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    jobs = json.loads(r.read().decode('utf-8'))
    print(f"Total jobs in system: {len(jobs)}")
    by_status = {}
    for j in jobs:
        st = j.get('status', 'unknown')
        by_status[st] = by_status.get(st, 0) + 1
    print("Breakdown by status:", by_status)
    active = [j for j in jobs if j.get('status') in ['queued', 'running', 'processing']]
    print(f"Active (queued/running) jobs: {len(active)}")
    for a in active[:5]:
        print(f" - [{a.get('status')}] {a.get('id')}: {a.get('step')} ({a.get('progress')}%) - {a.get('video_title')}")
except Exception as e:
    print("API Error:", e)
