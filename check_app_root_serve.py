from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where render_template or send_from_directory or open() is in app.py
for idx, l in enumerate(app_py.splitlines()):
    if 'render_template' in l or 'template' in l.lower() or 'index.html' in l:
        print(f"Line {idx+1}: {l}")

pos = app_py.find('@app.route("/")')
print("\n=== ROUTE / ===")
print(app_py[pos:pos+400])
