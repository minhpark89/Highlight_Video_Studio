from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = tmpl.read_text(encoding="utf-8")

# Let's inspect modal-schedule-config in index.html
pos = text.find('id="modal-schedule-config"')
end = text.find('function executeBatchSchedule', pos)
print("=== MODAL SCHEDULE CONFIG ===")
print(text[pos:end+600])
