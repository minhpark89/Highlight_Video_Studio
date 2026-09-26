from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\src\publisher\meta_reel_poster.py").read_text(encoding="utf-8")
print(txt[:1500])
