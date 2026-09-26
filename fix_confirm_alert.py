from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)

# Replace the alert in runLoHaBatchSchedule to avoid the missing slash issue
# Old: if (!confirm(`Xác nhận quét kho video (D:\Highlight_Video_Studio\output) và phân bổ độc nhất (1 Video : 1 Page) cho nhóm '${groupName}'?`))
# Replace with clean string:
old_confirm = "Xác nhận quét kho video"
pos_c = html.find(old_confirm)
if pos_c != -1:
    line_start = html.rfind('\n', 0, pos_c)
    line_end = html.find('\n', pos_c)
    print("Old confirm line:", html[line_start:line_end])
    clean_line = "    if (!confirm('Xác nhận quét kho video (D:/Highlight_Video_Studio/output) và phân bổ độc nhất (1 Video : 1 Page) cho nhóm ' + groupName + '?')) {"
    html = html[:line_start] + "\n" + clean_line + html[line_end:]
    print("Replaced confirm line cleanly!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html!")
