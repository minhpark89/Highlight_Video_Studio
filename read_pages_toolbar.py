from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\pages_toolbar.html").read_text(encoding="utf-8")
print(txt[:2000])
