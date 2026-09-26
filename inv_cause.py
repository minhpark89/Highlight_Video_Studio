import os, re, json, glob

# Check where CMD windows are spawned
# Boss says: "Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# 1. Could it be a browser protocol handler (e.g. terminal:// or bat file download or custom scheme)?
# 2. Could it be an extension or local script listening to something?
# 3. Could it be in web/templates/index.html or web/app.py?
# 4. Could it be in News_Video_Studio or another studio? Let's check both index.html!

for studio_name in [r"D:\Highlight_Video_Studio", r"D:\News_Video_Studio"]:
    idx_path = os.path.join(studio_name, "web", "templates", "index.html")
    if os.path.exists(idx_path):
        with open(idx_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        print(f"=== {studio_name} index.html ===")
        # Search for any window.open, exec, cmd, bat, or links
        for m in re.finditer(r'(window\.open|href="[^"]*"|onclick="[^"]*")', html):
            snippet = m.group(0)
            if any(k in snippet.lower() for k in ['.bat', 'cmd', 'render', 'studio', 'run']):
                print("  Found link/action:", snippet[:120])

