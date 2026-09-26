import subprocess
import os

res = subprocess.run([
    "powershell", "-Command",
    "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' } | Select-Object ProcessId, Name, CommandLine, WorkingDirectory"
], capture_output=True, text=True)
print(res.stdout)

# Check netstat for port 5080
res_net = subprocess.run([
    "powershell", "-Command",
    "netstat -ano | Select-String -Pattern ':5080'"
], capture_output=True, text=True)
print("PORT 5080 LISTENERS:")
print(res_net.stdout)
