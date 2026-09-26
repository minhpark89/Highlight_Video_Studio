from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages and see why it hangs or fails
pos = html.find('async function loadTokensAndPages')
pos_end = html.find('function updateScheduleGroupSummary', pos)
if pos_end == -1: pos_end = pos + 3500

with open(r"D:\Highlight_Video_Studio\load_pages_js.txt", "w", encoding="utf-8") as f:
    f.write(html[pos:pos_end])

print("Wrote load_pages_js.txt")
