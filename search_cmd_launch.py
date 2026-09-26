import os, glob, re

# Boss nói: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# Hãy tìm xem trong tất cả các file mã nguồn:
# 1. Đoạn code nào chạy lệnh mở cmd (ví dụ: start cmd, cmd.exe /k, os.system("start ..."))
# 2. Hoặc giao diện nào có nút bấm gọi mở cmd
for d in [r"D:\Highlight_Video_Studio", r"D:\News_Video_Studio", r"D:\FB_Longform_Studio"]:
    if not os.path.exists(d): continue
    for root, dirs, files in os.walk(d):
        if any(x in root for x in [".git", "venv", "__pycache__", "downloads"]): continue
        for f in files:
            if f.endswith(('.py', '.html', '.js', '.bat')):
                p = os.path.join(root, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                        txt = fp.read()
                    if "start cmd" in txt.lower() or "cmd.exe /k" in txt.lower() or "create_new_console" in txt.lower():
                        print(f"MATCH: {p}")
                        for line in txt.splitlines():
                            if any(k in line.lower() for k in ["start cmd", "cmd.exe /k", "create_new_console"]):
                                print("   ", line.strip()[:140])
                except:
                    pass

