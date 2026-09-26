from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect CSS for #content-area and .pane
pos = html.find('#content-area {')
print(html[pos:pos+400])

# Check if #pane-groups has any style or if there are empty elements above it
pos_pg = html.find('id="pane-groups"')
print(html[pos_pg-200:pos_pg+300])
