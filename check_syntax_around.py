with open("D:/Highlight_Video_Studio/web/templates/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "WEBSITE ARTICLE CMS CONFIG" in line:
        for j in range(max(0, idx - 5), min(len(lines), idx + 15)):
            print(f"{j+1}: {repr(lines[j])}")
        break
