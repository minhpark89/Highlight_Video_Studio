from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect api_save_group:
old_code = """@app.route("/api/groups", methods=["POST"])
def api_save_group():
    data = request.json or {}
    group_id = data.get("id")
    name = data.get("name", "").strip()"""

new_code = """@app.route("/api/groups", methods=["POST"])
def api_save_group():
    data = request.json or {}
    group_id = data.get("id") or data.get("group_id")
    name = data.get("name", "").strip()"""

if old_code in text:
    text = text.replace(old_code, new_code)
    app_py.write_text(text, encoding="utf-8")
    print("Fixed api_save_group to accept both 'id' and 'group_id'!")
else:
    print("Could not find exact old_code, checking...")
    pos = text.find("def api_save_group")
    print(text[pos:pos+300])
