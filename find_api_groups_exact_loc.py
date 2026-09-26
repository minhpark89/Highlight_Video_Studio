from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where groups are saved in app.py
# Look for api_save_group
pos = text.find("def api_save_group")
if pos != -1:
    pos_end = text.find("@app.route", pos+10)
    print("=== api_save_group ===")
    print(text[pos:pos_end])
else:
    print("api_save_group not found")

# Look for /api/groups
for idx, line in enumerate(text.splitlines()):
    if "/api/groups" in line:
        print(f"Line {idx+1}: {line}")
