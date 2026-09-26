import urllib.request
import re

url = "http://127.0.0.1:5080/"
try:
    resp = urllib.request.urlopen(url, timeout=5)
    html = resp.read().decode('utf-8', errors='replace')
    print("Page fetched, size:", len(html))

    # Check pane-pages structure
    m = re.search(r'<section id="pane-pages".*?</section>', html, re.DOTALL)
    if m:
        pane_pages = m.group(0)
        print("Found pane-pages section, length:", len(pane_pages))
        # Check elements inside
        for el_id in ['tokens-list-container', 'pages-tbody', 'stat-total-tokens', 'stat-total-pages', 'stat-total-groups', 'modal-token-alloc', 'groups-list-container']:
            print(f"Element #{el_id} in pane-pages:", el_id in pane_pages or el_id in html)
    else:
        print("pane-pages NOT FOUND!")

    # Check JS functions
    for fn in ['loadTokensAndPages', 'renderTokensList', 'renderPagesTable', 'renderGroupsList', 'autoDistributeTokens']:
        print(f"JS function {fn}:", fn in html)

except Exception as e:
    print("Fetch error:", e)
