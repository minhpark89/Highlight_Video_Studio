import os, glob, time, json, datetime

base_dirs = [r"D:\Highlight_Video_Studio", r"D:\News_Video_Studio", r"D:\FB_Longform_Studio", r"C:\Users\Admin\Desktop", r"C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Recent"]

now = time.time()
print("=== FILES MODIFIED OR ACCESSED IN LAST 60 MINUTES ===")
for b in base_dirs:
    if not os.path.exists(b): continue
    for root, dirs, files in os.walk(b):
        if any(x in root for x in [".git", "venv", "node_modules", "downloads", "temp"]): continue
        for f in files:
            p = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(p)
                if now - mtime < 3600:
                    dt = datetime.datetime.fromtimestamp(mtime).strftime("%H:%M:%S")
                    print(f"[{dt}] {p} ({os.path.getsize(p)} bytes)")
            except:
                pass

print("\n=== POWERSHELL CONSOLE HISTORY ===")
ps_hist = r"C:\Users\Admin\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"
if os.path.exists(ps_hist):
    with open(ps_hist, "r", encoding="utf-8", errors="ignore") as fp:
        lines = fp.readlines()
        print("".join(lines[-30:]))

