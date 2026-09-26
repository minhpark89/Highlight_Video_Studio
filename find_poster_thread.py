from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where publisher thread is defined or if there is one
for idx, line in enumerate(app_text.splitlines()):
    if 'def publish_' in line or 'def post_' in line or 'def process_queue' in line or 'def run_scheduler' in line:
        print(f"Line {idx+1}: {line}")
