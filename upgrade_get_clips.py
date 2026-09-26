from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect get_all_clips in app.py
# Currently: it only returns clips that are in jobs.json:
# "for j in jobs: for c in j.get('clips', []): ..."
# BUT in output/ there are 343 video files! If jobs.json was cleared or empty, get_all_clips returned []!
# Let's upgrade get_all_clips so that if jobs.json is empty or has missing clips, it also scans output/*.mp4 directly!

old_get_clips = """def get_all_clips():
    jobs = load_jobs()
    all_clips = []
    posted_file = BASE_DIR / "posted_clips.json"
    posted_set = set()
    if posted_file.exists():
        try:
            import json
            posted_set = set(json.loads(posted_file.read_text(encoding="utf-8")))
        except:
            pass

    for j in jobs:
        for c in j.get("clips", []):
            clip_copy = dict(c)
            clip_copy["job_id"] = j["id"]
            clip_copy["video_source"] = j.get("video_title", j.get("youtube_url"))
            clip_copy["is_posted"] = (c.get("filename") in posted_set)
            all_clips.append(clip_copy)
    return jsonify(all_clips)"""

new_get_clips = """def get_all_clips():
    jobs = load_jobs()
    all_clips = []
    posted_file = BASE_DIR / "posted_clips.json"
    posted_set = set()
    if posted_file.exists():
        try:
            import json
            posted_set = set(json.loads(posted_file.read_text(encoding="utf-8")))
        except:
            pass

    seen_files = set()
    for j in jobs:
        for c in j.get("clips", []):
            fn = c.get("filename")
            if fn:
                seen_files.add(fn)
            clip_copy = dict(c)
            clip_copy["job_id"] = j["id"]
            clip_copy["video_source"] = j.get("video_title", j.get("youtube_url"))
            clip_copy["is_posted"] = (fn in posted_set)
            all_clips.append(clip_copy)
            
    # Also auto-discover any mp4 files in output/ directory directly
    if OUTPUT_DIR.exists():
        for f in sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.name not in seen_files:
                all_clips.append({
                    "filename": f.name,
                    "title": f.stem,
                    "duration": 0,
                    "file_size": f.stat().st_size,
                    "is_posted": (f.name in posted_set),
                    "job_id": "direct_scan",
                    "video_source": "Kho video ổ D"
                })
                
    return jsonify(all_clips)"""

if old_get_clips in text:
    text = text.replace(old_get_clips, new_get_clips)
    app_path.write_text(text, encoding="utf-8")
    print("Upgraded get_all_clips to also discover all output/*.mp4 files directly!")
else:
    print("Could not find exact old_get_clips")
