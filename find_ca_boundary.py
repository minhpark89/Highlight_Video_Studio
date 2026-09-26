from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's find where <div id="content-area"> is and where it closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')
pos_pp = html.find('id="pane-posts"')

# Find the closing tag of content-area
# It usually ends before <!-- Modals --> or modals container
pos_modals = html.find('<!-- Modals')
if pos_modals == -1: pos_modals = html.find('id="modal-')

print(f"Content-area starts at {pos_ca}")
print(f"Pane-groups at {pos_pg}")
print(f"Modals at {pos_modals}")

# Let's check </div> right before pos_modals
pos_div_before_modals = html.rfind('</div>', 0, pos_modals)
print("Closing </div> of content-area at:", pos_div_before_modals)
print(html[pos_div_before_modals-200:pos_div_before_modals+100])
