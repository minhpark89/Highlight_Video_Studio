from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

print("has </body>?", "</body>" in html)
print("has </html>?", "</html>" in html)
print("modal-edit-group in templates/index.html?", "modal-edit-group" in html)
print("modal-edit-group in web/index.html?", "modal-edit-group" in Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8"))
