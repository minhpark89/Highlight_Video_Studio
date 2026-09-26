from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect where #content-area is opened and where each section is
pos_ca = html.find('id="content-area"')
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')

print("content-area pos:", pos_ca)
print("pane-settings pos:", pos_sett)
print("pane-website pos:", pos_web)

# Let's see what is immediately preceding pane-settings
print("\n=== 400 chars before pane-settings ===")
print(html[pos_sett-400:pos_sett])

# Let's see what is immediately preceding pane-website
print("\n=== 400 chars before pane-website ===")
print(html[pos_web-400:pos_web])
