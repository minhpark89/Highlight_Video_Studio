from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = tmpl.read_text(encoding="utf-8")

print("Length of templates/index.html:", len(text))
print("Has 'pages-per-token-input':", "pages-per-token-input" in text)
print("Has 'Xem Reel Facebook':", "Xem Reel Facebook" in text)

# Let's inspect where statusBadge is defined in text
pos = text.find("statusBadge")
while pos != -1:
    print(f"statusBadge at {pos}:")
    print(text[pos-40:pos+350])
    print("="*40)
    pos = text.find("statusBadge", pos+1)
