from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect where groups.forEach is called in the second switchTab or in loadLoHaGroups
pos = html.find('loadLoHaGroups')
while pos != -1:
    print(f"loadLoHaGroups at {pos}:")
    print(html[pos:pos+400])
    print("="*40)
    pos = html.find('loadLoHaGroups', pos+1)
