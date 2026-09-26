from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's see loadLoHaGroups
pos_g = html.find('async function loadLoHaGroups(')
if pos_g != -1:
    print("=== loadLoHaGroups JS ===")
    print(html[pos_g:pos_g+1200])
else:
    print("loadLoHaGroups not found")

# Let's see loadTokensAndPages / renderFbPageCards
pos_p = html.find('function renderFbPageCards(')
if pos_p != -1:
    print("\n=== renderFbPageCards JS ===")
    print(html[pos_p:pos_p+1200])
else:
    print("renderFbPageCards not found")
