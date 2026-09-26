from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-pages search / filter bar
pos = html.find('id="fb-page-filter-group"')
if pos != -1:
    print(html[pos-300:pos+500])
else:
    print("fb-page-filter-group not found")
