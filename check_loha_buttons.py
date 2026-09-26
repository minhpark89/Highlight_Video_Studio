from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadLoHaGroups where buttons are rendered
pos_lg = html.find('async function loadLoHaGroups()')
pos_end = html.find('</script>', pos_lg)
snippet = html[pos_lg:pos_end]

# Look for 'Sửa' or 'editGroup' or '<button'
lines = snippet.splitlines()
for idx, l in enumerate(lines[:100]):
    if 'Sửa' in l or 'edit' in l or 'onclick' in l:
        print(f"{idx}: {l}")
