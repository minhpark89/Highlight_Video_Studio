import os, re

# Scan port 5070 (News_Video_Studio) and port 5080 (Highlight_Video_Studio)
# to see where "cào link" and render buttons are!
for path, name in [(r"D:\News_Video_Studio", "News_Video_Studio"), (r"D:\Highlight_Video_Studio", "Highlight_Video_Studio")]:
    app_py = os.path.join(path, "web", "app.py")
    index_html = os.path.join(path, "web", "templates", "index.html")
    print(f"================ {name} ================")
    if os.path.exists(index_html):
        with open(index_html, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        # Find buttons that might trigger cmd or render
        for kw in ["Ném vào Render", "Ném vào Cắt Highlight", "Cào Link", "Render"]:
            count = html.count(kw)
            print(f"  Word '{kw}': {count} occurrences")

    if os.path.exists(app_py):
        with open(app_py, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        for kw in ["cmd", "subprocess.Popen", "os.system", "create_job", "render"]:
            print(f"  app.py '{kw}': {code.count(kw)} occurrences")

