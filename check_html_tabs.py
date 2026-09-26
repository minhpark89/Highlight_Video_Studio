import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

print("HTML Length:", len(html))

# Check pane-pages content
pages_idx = html.find('id="pane-pages"')
if pages_idx != -1:
    print("Found pane-pages at index:", pages_idx)
    print("Snippet around pane-pages:\n", html[pages_idx:pages_idx+600])
else:
    print("NOT FOUND id='pane-pages'!")

# Check loadTokensAndPages in JS
print("loadTokensAndPages in HTML:", "loadTokensAndPages" in html)

# Check boostnews.danhngon.pro in HTML
boost_matches = [m.start() for m in re.finditer(r'boostnews\.danhngon\.pro', html)]
print("boostnews.danhngon.pro matches:", len(boost_matches))
for idx in boost_matches:
    print("Around boostnews:", html[max(0, idx-100):min(len(html), idx+200)])

