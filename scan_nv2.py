import os, re

# Boss nói: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# Hãy kiểm tra D:\News_Video_Studio\web\app.py và templates xem có nút nào mở CMD không
path = r"D:\News_Video_Studio"
app_file = os.path.join(path, "web", "app.py")
if os.path.exists(app_file):
    with open(app_file, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()
    # Tìm kiếm các lệnh mở cmd
    for m in re.finditer(r'cmd|powershell|subprocess\.Popen|start', code):
        start = max(0, m.start() - 30)
        end = min(len(code), m.end() + 70)
        snippet = code[start:end].replace('\n', ' ')
        if any(k in snippet.lower() for k in ['cmd.exe', 'start cmd', 'conhost', 'terminal', 'open']):
            print("News app.py:", snippet)

