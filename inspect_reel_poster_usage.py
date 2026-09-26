from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect reel_poster imports and usage
for idx, line in enumerate(app_text.splitlines()[:50]):
    if 'reel' in line.lower() or 'poster' in line.lower():
        print(f"Line {idx+1}: {line}")

pos = app_text.find('def api_publish_reel')
print("\napi_publish_reel snippet:\n", app_text[pos:pos+1500])
