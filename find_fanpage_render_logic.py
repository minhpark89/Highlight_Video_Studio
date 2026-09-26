from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 1550 to 1600 in index.html where the placeholder is
lines = html.splitlines()
for idx, l in enumerate(lines):
    if "Đang nạp danh sách Fanpage" in l:
        print(f"Placeholder at line {idx+1}: {l}")
        for j in range(max(0, idx-5), min(len(lines), idx+15)):
            print(f"  {j+1}: {lines[j]}")
        break

# Now search where "loadTokensAndPages" or "renderFbPageCards" is defined
pos_fn = html.find("async function loadTokensAndPages")
if pos_fn == -1: pos_fn = html.find("function loadTokensAndPages")
print("\n=== loadTokensAndPages pos ===", pos_fn)
if pos_fn != -1:
    print(html[pos_fn:pos_fn+1500])
