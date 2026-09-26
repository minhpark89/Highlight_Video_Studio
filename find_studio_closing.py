from pathlib import Path

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect line 38657 where trace_ca_exact showed content-area closed early
pos = 38657
print("=== Around 38657 ===")
print(html[pos-200:pos+200])

# Let's inspect pane-studio closing tag
pos_studio = html.find('id="pane-studio"')
pos_studio_end = html.find('</section>', pos_studio)
print("pane-studio ends at:", pos_studio_end)
print(html[pos_studio_end-200:pos_studio_end+100])
