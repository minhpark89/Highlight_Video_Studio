from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect POST /api/groups
pos = txt.find('@app.route("/api/groups", methods=["POST"])')
pos_end = txt.find('@app.route', pos+10)
print("=== POST /api/groups ===")
print(txt[pos:pos_end])

# Check how PageManager is implemented
pos_pm = txt.find("page_manager.")
print("\n=== page_manager calls ===")
while pos_pm != -1:
    print(txt[pos_pm:pos_pm+150])
    pos_pm = txt.find("page_manager.", pos_pm+1)
    if pos_pm > 30000: break
