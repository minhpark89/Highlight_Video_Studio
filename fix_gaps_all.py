from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where id="content-area" starts and where each pane is located
pos_ca = html.find('id="content-area"')
print("content-area pos:", pos_ca)

# Check all pane positions
import re
for m in re.finditer(r'<section\s+id=[\"\']([^\"\']+)[\"\']', html):
    p_name = m.group(1)
    p_pos = m.start()
    print(f"{p_name}: pos {p_pos}")

# Let's check why pane-website and pane-settings are shifted down.
# In earlier code, was there a closing </div> or empty space?
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')

# Print 300 chars before pane-settings
print("\nBefore pane-settings:\n", html[pos_sett-300:pos_sett])

# Print 300 chars before pane-website
print("\nBefore pane-website:\n", html[pos_web-300:pos_web])
