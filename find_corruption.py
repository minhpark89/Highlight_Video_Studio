with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
# Print lines around 4845 - 4860
start = max(0, 4845 - 1)
end = min(len(lines), 4860)
for idx in range(start, end):
    print(f"Line {idx+1}: {repr(lines[idx])}")
