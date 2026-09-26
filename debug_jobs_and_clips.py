from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect get_all_clips
pos = text.find('def get_all_clips')
print("=== get_all_clips ===")
print(text[pos:pos+1000])

# Let's inspect get_jobs
pos_jobs = text.find('def get_jobs')
print("\n=== get_jobs ===")
print(text[pos_jobs:pos_jobs+600])
