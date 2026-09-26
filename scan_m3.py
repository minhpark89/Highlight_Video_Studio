import os, glob, re

# Boss nói: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# 1. Tại sao lại bật 3 tab CMD đen?
# Hãy kiểm tra xem trong UI người dùng đang mở là trang nào:
# Port 5080 (Highlight Video Studio) hay Port 5070 (News Video Studio) hay tool nào khác?
# Kiểm tra các file script, bat, shortcuts trên desktop và code xử lý render.

print("=== 1. Checking port 5080 index.html for any window.open or cmd or href ===")
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    h5080 = f.read()

# Let's search for any 'onclick' in research or studio
for m in re.finditer(r'<button[^>]*onclick="([^"]*)"[^>]*>([\s\S]*?)<\/button>', h5080):
    handler = m.group(1)
    content = m.group(2).strip().replace('\n', ' ')
    if any(k in content.lower() or k in handler.lower() for k in ['render', 'cắt', 'highlight', 'chọn', 'studio', 'ném']):
        print(f"5080 BTN: [{content[:40]}] -> onclick='{handler}'")

print("\n=== 2. Checking port 5070 (News_Video_Studio) index.html for render buttons ===")
path_news = r"D:\News_Video_Studio\web\templates\index.html"
if os.path.exists(path_news):
    with open(path_news, 'r', encoding='utf-8', errors='ignore') as f:
        h5070 = f.read()
    for m in re.finditer(r'<button[^>]*onclick="([^"]*)"[^>]*>([\s\S]*?)<\/button>', h5070):
        handler = m.group(1)
        content = m.group(2).strip().replace('\n', ' ')
        if any(k in content.lower() or k in handler.lower() for k in ['render', 'cào', 'crawl', 'link']):
            print(f"5070 BTN: [{content[:40]}] -> onclick='{handler}'")

