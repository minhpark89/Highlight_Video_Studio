import os, json, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Find pane-pages section
m = re.search(r'(<section[^>]*id=["\']pane-pages["\'][\s\S]*?</section>)', html)
if m:
    pane_content = m.group(1)
    print("Found pane-pages section! Length:", len(pane_content))
    with open(BASE_DIR / "current_pane_pages.html", "w", encoding="utf-8") as out:
        out.write(pane_content)
    print("Written to current_pane_pages.html")
else:
    print("Could not find pane-pages section!")

# Find schedule rules modal
m_rules = re.search(r'(<div[^>]*id=["\']modal-schedule-rules["\'][\s\S]*?</div>\s*</div>\s*</div>)', html)
if m_rules:
    print("Found modal-schedule-rules, length:", len(m_rules.group(1)))
else:
    print("modal-schedule-rules not found via regex, looking for simple id")
    pos = html.find('id="modal-schedule-rules"')
    print("pos:", pos)
