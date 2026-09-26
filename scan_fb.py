import os, glob, re

base = r"D:\FB_Longform_Studio"
print("=== Scanning D:\\FB_Longform_Studio ===")
if os.path.exists(base):
    for root, dirs, files in os.walk(base):
        if any(x in root for x in [".git", "venv", "__pycache__", "downloads"]): continue
        for f in files:
            if f.endswith(('.html', '.py', '.js', '.bat')):
                p = os.path.join(root, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                        txt = fp.read()
                    if "cmd.exe" in txt.lower() or "cmd /k" in txt.lower() or "start cmd" in txt.lower():
                        print(f"Match in {os.path.relpath(p, base)}:")
                        for idx, line in enumerate(txt.splitlines(), 1):
                            if any(k in line.lower() for k in ["cmd.exe", "start cmd", "cmd /k", "cmd /c"]):
                                print(f"  {idx}: {line.strip()[:140]}")
                except:
                    pass

