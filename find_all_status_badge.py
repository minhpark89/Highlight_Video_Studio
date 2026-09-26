from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where statusBadge is defined in index.html
pos = html.find("statusBadge")
while pos != -1:
    print(f"=== statusBadge at {pos} ===")
    print(html[pos-50:pos+350])
    print("-" * 50)
    pos = html.find("statusBadge", pos + 1)
