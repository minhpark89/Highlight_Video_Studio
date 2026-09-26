from pathlib import Path

# Check page_manager implementation
txt = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where POST /api/groups is defined
pos = txt.find('@app.route("/api/groups", methods=["POST"])')
print(txt[pos:pos+600])

# Check page_manager file
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*page*manager*.py"):
    print("Page manager file:", p)
    t = p.read_text(encoding="utf-8")
    pos_add = t.find("add_or_update_group")
    print(t[pos_add:pos_add+500])
