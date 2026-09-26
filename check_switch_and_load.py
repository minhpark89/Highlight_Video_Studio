from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect switchTab for pane-pages
pos_sw = html.find("function switchTab")
if pos_sw == -1: pos_sw = html.find("window.switchTab")
print("=== switchTab ===")
print(html[pos_sw:pos_sw+1000])

# Let's inspect loadTokensAndPages
pos_lt = html.find("async function loadTokensAndPages")
if pos_lt == -1: pos_lt = html.find("function loadTokensAndPages")
print("\n=== loadTokensAndPages ===")
print(html[pos_lt:pos_lt+1500])
