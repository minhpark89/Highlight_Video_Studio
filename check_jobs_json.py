import json
from pathlib import Path

jobs_file = Path(r"D:\Highlight_Video_Studio\jobs.json")
if jobs_file.exists():
    jobs = json.loads(jobs_file.read_text(encoding="utf-8"))
    print("Total jobs in jobs.json:", len(jobs))
    for j in jobs[:5]:
        print(j.get("id"), j.get("status"), j.get("youtube_url") or j.get("video_title"))
else:
    print("jobs.json does not exist!")
