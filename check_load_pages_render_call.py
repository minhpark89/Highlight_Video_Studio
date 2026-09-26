from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages in index.html around line 180119
pos = html.find('async function loadTokensAndPages()')
print("loadTokensAndPages pos:", pos)
print(html[pos:pos+1500])

# Where does loadTokensAndPages call renderFilteredPages or populate pages-cards-container?
pos_rfp = html.find('renderFilteredPages()', pos)
print("renderFilteredPages called at:", pos_rfp)
if pos_rfp != -1:
    print(html[pos_rfp-100:pos_rfp+200])
else:
    print("renderFilteredPages NOT called in loadTokensAndPages!")
