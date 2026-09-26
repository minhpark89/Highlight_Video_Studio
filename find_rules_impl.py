from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see why /api/schedule/rules threw 500
pos = app_py.find("def handle_schedule_rules")
print(app_py[pos:pos+400])

# Let's search get_schedule_rules across all files
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*.py"):
    if "venv" in str(p): continue
    try:
        t = p.read_text(encoding="utf-8")
        if "get_schedule_rules" in t or "save_schedule_rules" in t:
            print(f"Found in {p.name}")
    except Exception:
        pass
