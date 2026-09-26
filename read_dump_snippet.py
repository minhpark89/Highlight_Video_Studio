from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\distribute_dump.txt").read_text(encoding="utf-8")
print(txt[:2500])
