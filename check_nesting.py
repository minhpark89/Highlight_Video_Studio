from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect where #content-area is and how pane-groups is positioned
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')
pos_end_ca = html.find('</div>\n    <!-- Content Panes', pos_ca)
if pos_end_ca == -1: pos_end_ca = html.find('</div>\n    <!-- Modals', pos_ca)
if pos_end_ca == -1: pos_end_ca = html.find('<!-- Modals', pos_ca)

print("pos_ca:", pos_ca)
print("pos_pg:", pos_pg)
print("pos_end_ca:", pos_end_ca)
