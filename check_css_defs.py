from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect CSS for #content-area and .pane
pos_css = html.find('#content-area {')
if pos_css != -1:
    print("=== #content-area CSS ===")
    print(html[pos_css:pos_css+400])

pos_pane = html.find('.pane {')
if pos_pane != -1:
    print("\n=== .pane CSS ===")
    print(html[pos_pane:pos_pane+400])
