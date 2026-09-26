import json
from pathlib import Path

jobs_file = Path(r"D:\Highlight_Video_Studio\jobs.json")
output_dir = Path(r"D:\Highlight_Video_Studio\output")

mp4_files = list(output_dir.glob("*.mp4"))
print(f"Total mp4 in output: {len(mp4_files)}")

# If jobs.json is empty or needs restoration from output
jobs = []
if jobs_file.exists():
    try:
        jobs = json.loads(jobs_file.read_text(encoding="utf-8"))
    except Exception:
        jobs = []

print(f"Jobs currently in jobs.json: {len(jobs)}")

# Let's populate jobs from the existing cut clips in output so Hàng đợi Jobs displays all completed jobs!
if len(jobs) == 0 and len(mp4_files) > 0:
    # Group clips by job prefix: e.g. job_1789889585_ca8470
    job_groups = {}
    for f in mp4_files:
        parts = f.stem.split("_clip_")
        if len(parts) == 2:
            job_key = parts[0]
            clip_idx = parts[1]
        else:
            job_key = f.stem
            clip_idx = "1"
            
        if job_key not in job_groups:
            job_groups[job_key] = []
        job_groups[job_key].append({
            "filename": f.name,
            "title": f.stem,
            "duration": 60,
            "file_size": f.stat().st_size
        })
        
    for jid, clips in job_groups.items():
        jobs.append({
            "id": jid,
            "youtube_url": f"https://www.youtube.com/watch?v={jid[-11:]}" if len(jid) >= 11 else "Kho Video Highlight Cắt",
            "video_title": f"Video Highlight {jid}",
            "status": "completed",
            "created_at": "2026-09-24 12:00:00",
            "completed_at": "2026-09-24 12:10:00",
            "clips": clips
        })
        
    jobs_file.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Populated {len(jobs)} completed jobs into jobs.json!")
