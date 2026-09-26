import os, re, json, glob, psutil

print("=== 1. Check all CMD and PowerShell processes and their parent/command line ===")
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
    try:
        n = p.info['name'].lower()
        if 'cmd' in n or 'powershell' in n:
            parent = psutil.Process(p.info['ppid']).name() if p.info['ppid'] else "None"
            print(f"[{n}] PID: {p.info['pid']}, Parent: {parent}, CMD: {' '.join(p.info['cmdline'] or [])[:120]}")
    except:
        pass

print("\n=== 2. Check Port 5080 (Highlight) and 5070 (News) to see what UI boss was clicking ===")
# Check index.html in Highlight_Video_Studio:
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    h5080 = f.read()

# Let's inspect where video cards in research results are generated:
idx = h5080.find('container.innerHTML = results.map')
if idx != -1:
    print("--- 5080 Research Card template ---")
    print(h5080[idx:idx+1500])

