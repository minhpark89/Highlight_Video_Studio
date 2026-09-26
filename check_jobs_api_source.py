from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect /api/jobs in app.py
pos = app_text.find('def get_jobs')
print("get_jobs in app.py:\n", app_text[pos:pos+400])

# Let's see what JOBS_FILE is
pos_jf = app_text.find('JOBS_FILE =')
if pos_jf == -1: pos_jf = app_text.find('jobs.json')
print("JOBS_FILE in app.py:\n", app_text[pos_jf-50:pos_jf+150])
