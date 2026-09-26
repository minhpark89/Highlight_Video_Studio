import os, json

file_path = r"D:\Highlight_Video_Studio\web\templates\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Add referrerpolicy="no-referrer" to avatar images so FB CDN loads without 403 Forbidden
target = 'onerror="this.onerror=null;'
replacement = 'referrerpolicy="no-referrer" onerror="this.onerror=null;'

if target in text and 'referrerpolicy="no-referrer"' not in text:
    text = text.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    alt_path = r"D:\Highlight_Video_Studio\web\index.html"
    if os.path.exists(alt_path):
        with open(alt_path, "w", encoding="utf-8") as f:
            f.write(text)
    print("Added referrerpolicy='no-referrer' to avatar img successfully!")
else:
    print("Already has referrerpolicy or target not found.")
