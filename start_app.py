
import subprocess
import time
import requests

# Check how it is usually started
# Let's inspect run_persistent.bat or run_service.ps1
with open(r'D:\Highlight_Video_Studioun_persistent.bat', 'r', encoding='utf-8', errors='ignore') as f:
    bat = f.read()
print("BAT:", bat)

# Start process
subprocess.Popen(["cmd.exe", "/c", r"D:\Highlight_Video_Studioun_persistent.bat"], cwd=r"D:\Highlight_Video_Studio")
time.sleep(3)

try:
    res = requests.get('http://127.0.0.1:5080/api/jobs', timeout=5)
    print("STATUS_CODE:", res.status_code)
except Exception as e:
    print("ERR:", e)
