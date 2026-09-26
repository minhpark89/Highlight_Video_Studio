from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\load_pages_js.txt").read_text(encoding="utf-8")
print(txt[:2500])
