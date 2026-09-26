import os

file_path = r"D:\Highlight_Video_Studio\web\templates\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace any calls to missing endpoint /api/pages/groups with /api/groups
old_str = "fetch('/api/pages/groups')"
new_str = "fetch('/api/groups')"

if old_str in text:
    text = text.replace(old_str, new_str)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    alt_file = r"D:\Highlight_Video_Studio\web\index.html"
    if os.path.exists(alt_file):
        with open(alt_file, "w", encoding="utf-8") as f:
            f.write(text)
    print("Fixed 404 /api/pages/groups -> /api/groups successfully!")
else:
    print("Already clean.")
