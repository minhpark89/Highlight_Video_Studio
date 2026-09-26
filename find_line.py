with open("D:/Highlight_Video_Studio/extracted_script.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
start = max(0, 1280)
end = min(len(lines), 1315)
for i in range(start, end):
    print(f"{i+1}: {repr(lines[i])}")
