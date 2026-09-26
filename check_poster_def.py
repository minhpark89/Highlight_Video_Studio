from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\src\publisher\meta_reel_poster.py").read_text(encoding="utf-8")
pos = txt.find("def publish_reel")
print(txt[pos:pos+400])
