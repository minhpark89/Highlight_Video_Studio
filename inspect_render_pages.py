from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages JS logic: loadTokensAndPages / renderFbPageCards
pos_render = html.find('function renderFbPageCards')
if pos_render != -1:
    print("renderFbPageCards preview:\n", html[pos_render:pos_render+1500])
