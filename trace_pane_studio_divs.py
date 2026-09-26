from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect line 38600-38700
print(html[38600:38750])

# Trace all opening and closing <div> tags inside pane-studio:
pos_ps = html.find('id="pane-studio"')
pos_ps_end = html.find('</section>', pos_ps)
sub = html[pos_ps:pos_ps_end]

depth = 0
for m in re.finditer(r'<\/?div\b[^>]*>', sub):
    tag = m.group(0)
    pos = pos_ps + m.start()
    if tag.startswith('</div'):
        depth -= 1
        # print if depth < 0
        if depth < 0:
            print(f"IMBALANCE: </div at {pos} dropped depth to {depth}!")
            print(html[pos-80:pos+80])
    elif not tag.endswith('/>'):
        depth += 1

print("Final depth at end of pane-studio:", depth)
