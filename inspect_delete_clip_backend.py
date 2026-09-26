from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# 1. Inspect api_delete_clip
pos_del = app_py.find("def api_delete_clip")
print("=== api_delete_clip ===")
print(app_py[pos_del:pos_del+800])

# 2. Inspect api_purge_posted_clips
pos_purge = app_py.find("def api_purge_posted_clips")
print("\n=== api_purge_posted_clips ===")
print(app_py[pos_purge:pos_purge+800])
