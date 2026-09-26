from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)

# Replace the confirm path in runLoHaBatchSchedule so it shows D:\Highlight_Video_Studio\output cleanly (escape backslashes properly)
html = html.replace('D:\\Highlight_Video_Studio\\output', 'D:\\\\Highlight_Video_Studio\\\\output')

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved escape fix!")
