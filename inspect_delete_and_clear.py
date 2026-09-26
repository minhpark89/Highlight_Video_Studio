from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's check api_delete_clip and api_clear_posts to ensure posted_clips.json is also cleaned up
pos = app_py.find("def api_delete_clip")
print("=== api_delete_clip ===")
print(app_py[pos:pos+800])

pos_clear = app_py.find("def api_clear_posts")
print("\n=== api_clear_posts ===")
print(app_py[pos_clear:pos_clear+600])
