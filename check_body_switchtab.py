from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect line 79061 where switchTab was found
pos = html.find('[Tab] Switching to:')
if pos != -1:
    print("Found old switchTab in body script around:", pos)
    print(html[pos-100:pos+1200])
