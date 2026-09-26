from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where @app.route("/api/groups" is in app.py
lines = text.splitlines()
matches = [i for i, l in enumerate(lines) if "/api/groups" in l]
print("All /api/groups line indices:", matches)
for m in matches:
    print(f"--- Line {m+1} ---")
    for j in range(max(0, m-2), min(len(lines), m+15)):
        print(f"  {j+1}: {lines[j]}")
