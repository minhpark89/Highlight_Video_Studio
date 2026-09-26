from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 80840 in index.html around pane-settings and pane-website
pos_sett = html.find('id="pane-settings"')
pos_sett_end = html.find('</section>', pos_sett)

print("=== PANE-SETTINGS END TO PANE-WEBSITE ===")
print(html[pos_sett_end:pos_sett_end+400])
