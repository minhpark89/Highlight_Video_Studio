from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line by line around 'Đang nạp danh sách Fanpage Facebook'
lines = html.splitlines()
for idx, l in enumerate(lines):
    if "Đang nạp danh sách Fanpage" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(max(0, idx-5), min(len(lines), idx+15)):
            print(f"  {j+1}: {lines[j]}")
        break
