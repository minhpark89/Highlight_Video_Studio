from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\curr_pane_pages.txt").read_text(encoding="utf-8")
print(txt[:1500])
