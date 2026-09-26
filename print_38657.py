from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect line 38600 to 38700
pos = 38657
print("=== Around 38657 ===")
print(html[pos-200:pos+200])
