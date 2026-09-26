from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\src\publisher\meta_reel_poster.py").read_text(encoding="utf-8")
print("=== meta_reel_poster.py lines:", len(txt.splitlines()))
for l in txt.splitlines()[:50]:
    print(l)
