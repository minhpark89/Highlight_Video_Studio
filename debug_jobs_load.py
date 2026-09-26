from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect Flask app definition and load_jobs
pos_app = app_text.find('Flask(')
print("Flask def:\n", app_text[pos_app-20:pos_app+200])

pos_jobs = app_text.find('def load_jobs')
print("\nload_jobs def:\n", app_text[pos_jobs:pos_jobs+400])

pos_jf = app_text.find('JOBS_FILE')
print("\nJOBS_FILE:\n", app_text[pos_jf-30:pos_jf+150])
