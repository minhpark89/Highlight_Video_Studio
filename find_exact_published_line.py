from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = content.splitlines()

# 1. Update loadPostsTable to render direct Facebook Reel Link
# In lines 5100-5150
for idx, l in enumerate(lines):
    if "p.status === 'published'" in l:
        print(f"Found published check at line {idx+1}")
        for j in range(max(0, idx-2), min(len(lines), idx+15)):
            print(f"  {j+1}: {lines[j]}")
        break
