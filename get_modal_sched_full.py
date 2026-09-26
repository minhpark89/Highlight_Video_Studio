with open(r"D:\Highlight_Video_Studio\web\templates\index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find('id="modal-schedule-config"')
end = text.find('</form>', pos)
if end == -1: end = text.find('</div>\n  </div>', pos)
print(text[pos:pos+2000])
