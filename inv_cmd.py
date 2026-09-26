import os, glob, re

base_dir = r"D:\Highlight_Video_Studio"

print("--- Checking all occurrences of cmd, terminal, os.system, subprocess, open in web and src ---")
for root, dirs, files in os.walk(base_dir):
    if any(x in root for x in [".git", "venv", "__pycache__", "downloads", "temp", "output"]):
        continue
    for f in files:
        if f.endswith((".py", ".html", ".js", ".bat", ".ps1")):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                txt = fp.read()
            # check for cmd or terminal or process spawning
            for m in re.finditer(r'(cmd|powershell|terminal|subprocess|Popen|start\s|exec|system)', txt, re.IGNORECASE):
                start = max(0, m.start() - 60)
                end = min(len(txt), m.end() + 100)
                snippet = txt[start:end].replace("\n", " ")
                if any(k in snippet.lower() for k in ["cmd", "start", "popen", "spawn", "terminal"]):
                    print(f"{os.path.relpath(p, base_dir)}: {snippet[:120]}")

print("--- Check processes currently running on PC ---")
import subprocess
try:
    p = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process cmd, powershell, python* | Select-Object Id, ProcessName, MainWindowTitle, CommandLine | Format-List"], capture_output=True, text=True)
    print(p.stdout)
except Exception as e:
    print("Proc error:", e)

