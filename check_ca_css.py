from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where #content-area is opened and where it is closed
pos_ca = html.find('id="content-area"')
print("content-area pos:", pos_ca)

# Let's inspect CSS for #content-area
pos_css = html.find('#content-area')
while pos_css != -1 and pos_css < pos_ca:
    print("CSS match for #content-area:")
    print(html[pos_css:pos_css+300])
    pos_css = html.find('#content-area', pos_css+1)

# Check main tag and layout container
pos_main = html.find('<main')
print("main tag pos:", pos_main)
print(html[pos_main:pos_main+500])
