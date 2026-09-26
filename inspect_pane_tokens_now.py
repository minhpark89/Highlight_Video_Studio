from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# 1. Look for loha-token-threads block in pane-tokens
pos_tokens = text.find('id="pane-tokens"')
pos_table = text.find('<table', pos_tokens)
print("=== CURRENT CONTROLS IN PANE-TOKENS ===")
print(text[pos_tokens:pos_table])
