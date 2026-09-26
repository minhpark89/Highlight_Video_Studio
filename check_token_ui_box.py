from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where loha-posts-per-page or token configuration box is in pane-tokens
pos = html.find('id="loha-token-threads"')
print("=== PANE-TOKENS TOP BOXES ===")
print(html[pos-300:pos+1500])
