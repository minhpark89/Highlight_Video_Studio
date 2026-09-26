# Let's inspect D:\News_Video_Studio\web\app.py to see if it has an endpoint that opens CMD
import os, re

for studio_path in [r"D:\News_Video_Studio", r"D:\Highlight_Video_Studio", r"D:\FB_Longform_Studio"]:
    app_file = os.path.join(studio_path, "web", "app.py")
    if os.path.exists(app_file):
        with open(app_file, "r", encoding="utf-8", errors="ignore") as fp:
            code = fp.read()
        # Find any route or function that executes cmd or subprocess with shell or new console
        matches = re.findall(r'(@app\.route\([^\)]*\)\s*def\s+[a-zA-Z0-9_]+\s*\([^)]*\):[\s\S]*?(?=\n@app|\Z))', code)
        for m in matches:
            if any(k in m for k in ['cmd', 'subprocess', 'Popen', 'render', 'terminal', 'start']):
                if 'cmd.exe' in m or 'CREATE_NEW_CONSOLE' in m or 'start' in m:
                    print(f"=== Found in {studio_path} ===")
                    print(m[:500])

