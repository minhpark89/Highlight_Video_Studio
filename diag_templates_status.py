import sys
from pathlib import Path

# Check where app is loading templates
app_py_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py_path.read_text(encoding="utf-8")

# Let's inspect where render_template("index.html") is
pos = text.find('render_template("index.html")')
print("render_template at:", pos)

# Check all index.html files
for p in Path(r"D:\Highlight_Video_Studio").glob("**/index.html"):
    content = p.read_text(encoding="utf-8")
    print(f"File: {p}")
    print(f"  Size: {p.stat().st_size}")
    print(f"  Has 'pages-per-token-input': {'pages-per-token-input' in content}")
    print(f"  Has 'Xem Reel Facebook': {'Xem Reel Facebook' in content}")
    print(f"  Has 'rebalanceTokenPageAllocation': {'rebalanceTokenPageAllocation' in content}")
