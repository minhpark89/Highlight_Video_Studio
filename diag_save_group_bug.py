from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's search for "def api_save_group" or where POST to /api/groups is handled
pos = app_py.find('@app.route("/api/groups", methods=["POST"])')
print("=== /api/groups POST handler ===")
print(app_py[pos:pos+600])

# Let's inspect page_manager.add_or_update_group
pos_fn = app_py.find("def add_or_update_group")
print("\n=== add_or_update_group ===")
print(app_py[pos_fn:pos_fn+600])
