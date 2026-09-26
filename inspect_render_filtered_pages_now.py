from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where "loadTokensAndPages" or "renderFbPageCards" is called in index.html
pos = html.find('renderFilteredPages()')
print("renderFilteredPages called at:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

# Let's see what happens inside renderFilteredPages
pos_def = html.find('function renderFilteredPages()')
print("\n=== renderFilteredPages definition ===")
print(html[pos_def:pos_def+1500])
