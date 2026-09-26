import re
import os

# 1. Update web/app.py to add delete clip and mark posted endpoint
app_path = "D:/Highlight_Video_Studio/web/app.py"
with open(app_path, "r", encoding="utf-8") as f:
    app_code = f.read()

clip_apis = """
@app.route("/api/clips/<path:filename>", methods=["DELETE"])
def api_delete_clip(filename):
    try:
        file_path = OUTPUT_DIR / filename
        if file_path.exists():
            file_path.unlink()
        
        # Also clean up from jobs
        jobs = load_jobs()
        updated = False
        for j in jobs:
            clips = j.get("clips", [])
            new_clips = [c for c in clips if c.get("filename") != filename]
            if len(new_clips) != len(clips):
                j["clips"] = new_clips
                updated = True
        if updated:
            save_jobs(jobs)

        # Clean from posts/markings if any
        return jsonify({"success": True, "message": f"Đã xóa clip {filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clips/mark_posted", methods=["POST"])
def api_mark_clip_posted():
    try:
        data = request.json or {}
        filename = data.get("filename")
        if not filename:
            return jsonify({"success": False, "error": "Thiếu filename"}), 400

        posted_file = BASE_DIR / "posted_clips.json"
        posted_data = []
        if posted_file.exists():
            try:
                import json
                posted_data = json.loads(posted_file.read_text(encoding="utf-8"))
            except:
                posted_data = []

        if filename not in posted_data:
            posted_data.append(filename)
            import json
            posted_file.write_text(json.dumps(posted_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return jsonify({"success": True, "posted_clips": posted_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
"""

if "/api/clips/<path:filename>" not in app_code:
    idx = app_code.find("def play_clip(filename):")
    if idx != -1:
        # find end of play_clip
        end_idx = app_code.find("\n@app.route", idx)
        app_code = app_code[:end_idx] + "\n" + clip_apis + "\n" + app_code[end_idx:]
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(app_code)
        print("Added delete & mark posted APIs to web/app.py")

# Also update /api/clips to return posted status
if 'c.get("posted"' not in app_code:
    old_clips_def = """@app.route("/api/clips", methods=["GET"])
def get_all_clips():
    jobs = load_jobs()
    all_clips = []
    for j in jobs:
        for c in j.get("clips", []):
            clip_copy = dict(c)
            clip_copy["job_id"] = j["id"]
            clip_copy["video_source"] = j.get("video_title", j.get("youtube_url"))
            all_clips.append(clip_copy)
    return jsonify(all_clips)"""

    new_clips_def = """@app.route("/api/clips", methods=["GET"])
def get_all_clips():
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

    if old_clips_def in app_code:
        app_code = app_code.replace(old_clips_def, new_clips_def)
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(app_code)
        print("Updated get_all_clips to include is_posted flag!")
