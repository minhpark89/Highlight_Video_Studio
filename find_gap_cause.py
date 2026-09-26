from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-settings and pane-website in index.html
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')

# Print 1000 characters before pane-settings
print("=== 1000 CHARS BEFORE PANE-SETTINGS ===")
print(html[pos_sett-1000:pos_sett])
