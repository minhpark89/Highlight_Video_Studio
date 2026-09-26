from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
html_web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

def check_fb_reel(name, text):
    matches = [m.start() for m in re.finditer(r'Xem Reel Facebook', text)]
    print(f"{name}: found 'Xem Reel Facebook': {len(matches)} times")
    for m in matches:
        print(text[m-80:m+150])

check_fb_reel("templates/index.html", html_tmpl)
check_fb_reel("web/index.html", html_web)
