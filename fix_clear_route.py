from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's check clear endpoint in app.py
# Make sure it accepts both POST and DELETE, and has no trailing slash issues
old_rt = '@app.route("/api/posts/clear", methods=["POST"])'
new_rt = '@app.route("/api/posts/clear", methods=["GET", "POST", "DELETE"])'

if old_rt in text:
    text = text.replace(old_rt, new_rt)
    app_path.write_text(text, encoding="utf-8")
    print("Updated /api/posts/clear route methods!")
else:
    print("Could not find old_rt in app.py")
