from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line where 'Đang nạp danh sách Fanpage' is
lines = html.splitlines()
for idx, l in enumerate(lines):
    if "Đang nạp danh sách Fanpage" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(max(0, idx-4), min(len(lines), idx+15)):
            print(f"  {j+1}: {lines[j]}")
        break
