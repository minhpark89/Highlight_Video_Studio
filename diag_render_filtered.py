from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'pages-cards-container' is in index.html
pos = html.find('id="pages-cards-container"')
print("pages-cards-container pos:", pos)

# Find all occurrences of renderFilteredPages or renderFbPageCards
pos_rfp = html.find('function renderFilteredPages()')
print("renderFilteredPages pos:", pos_rfp)

pos_rfp_call = html.find('renderFilteredPages()')
while pos_rfp_call != -1:
    print(f"Call at {pos_rfp_call}: {html[max(0, pos_rfp_call-40):pos_rfp_call+60]}")
    pos_rfp_call = html.find('renderFilteredPages()', pos_rfp_call + 1)
