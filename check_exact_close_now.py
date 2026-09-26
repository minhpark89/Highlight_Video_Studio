from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect line 38650-38670
pos = 38657
print("=== Around 38657 ===")
print(html[pos-100:pos+200])
