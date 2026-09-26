from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's search for id="pane-website" and id="pane-settings"
pos_web = html.find('id="pane-website"')
pos_sett = html.find('id="pane-settings"')
pos_queue = html.find('id="pane-queue"')
pos_gal = html.find('id="pane-gallery"')

print("pane-website pos:", pos_web)
print("pane-settings pos:", pos_sett)
print("pane-queue pos:", pos_queue)
print("pane-gallery pos:", pos_gal)

# Check their parent element
pos_ca = html.find('id="content-area"')
pos_ca_close = html.find('</div>', pos_ca + 100) # wait, where is content-area closed?

print("content-area pos:", pos_ca)
