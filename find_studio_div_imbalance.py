from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect line 38657 where content-area closed early
pos = 38657
print("Snippet around 38657:")
print(html[pos-150:pos+150])

# Notice:
# </div>
# </section>
# <!-- PANE: RESEARCH ...
# Why did content-area close at 38657?
# Because inside pane-studio there was an EXTRA </div>!
# Let's trace pane-studio div balance
pos_ps = html.find('id="pane-studio"')
pos_ps_end = html.find('</section>', pos_ps)
sub_studio = html[pos_ps:pos_ps_end]

opens = len(re.findall(r'<div\b', sub_studio))
closes = len(re.findall(r'</div\b', sub_studio))
print(f"Inside pane-studio: <div count = {opens}, </div count = {closes}")
