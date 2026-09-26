import subprocess
import os

src = r"D:\Highlight_Video_Studio\temp\job_1790182893_f5d241_web720.mp4"
print("Local H.264 file exists:", os.path.exists(src), "Size:", os.path.getsize(src) / 1024 / 1024, "MB")

# Copy to VPS via SCP
cmd = [
    "scp",
    "-i", r"C:\Users\Admin\.ssh\bob2_auto",
    "-o", "StrictHostKeyChecking=no",
    src,
    "root@157.173.116.71:/var/www/portfolio/videos/job_1790182893_f5d241.mp4"
]
print("Running scp...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("SCP returncode:", res.returncode)
print("SCP stdout:", res.stdout)
print("SCP stderr:", res.stderr)
