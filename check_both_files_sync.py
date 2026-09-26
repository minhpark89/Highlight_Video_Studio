from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
web_idx = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

print("tmpl has 'Xem Reel Facebook'?", "Xem Reel Facebook" in tmpl)
print("web_idx has 'Xem Reel Facebook'?", "Xem Reel Facebook" in web_idx)
print("tmpl has 'pages-per-token-input'?", "pages-per-token-input" in tmpl)
print("web_idx has 'pages-per-token-input'?", "pages-per-token-input" in web_idx)
