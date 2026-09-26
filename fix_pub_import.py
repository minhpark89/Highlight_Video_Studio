from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

old_imp = "from web.scheduled_publisher import scheduled_publisher_worker_loop"
new_imp = "from scheduled_publisher import scheduled_publisher_worker_loop"

if old_imp in text:
    text = text.replace(old_imp, new_imp)
    app_path.write_text(text, encoding="utf-8")
    print("Fixed scheduled_publisher import!")
else:
    print("Could not find old_imp")
