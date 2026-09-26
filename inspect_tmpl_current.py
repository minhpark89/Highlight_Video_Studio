from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
txt = tmpl.read_text(encoding="utf-8")
print("Size of tmpl:", len(txt))

# Let's search where pane-tokens is
pos = txt.find('id="pane-tokens"')
print("pos of pane-tokens:", pos)
if pos != -1:
    print("=== pane-tokens content (1000 chars) ===")
    print(txt[pos:pos+1000])

# Let's search where loadPostsTable is
pos_lp = txt.find("loadPostsTable")
print("\npos of loadPostsTable:", pos_lp)
while pos_lp != -1:
    if "function loadPostsTable" in txt[pos_lp-20:pos_lp+30]:
        print(f"Function definition at {pos_lp}:")
        print(txt[pos_lp-10:pos_lp+500])
        print("="*40)
    pos_lp = txt.find("loadPostsTable", pos_lp+1)
