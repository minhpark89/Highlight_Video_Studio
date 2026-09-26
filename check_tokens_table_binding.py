from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect what happens in loadLoHaGroups and loadTokensOnly
# And check how tokens-table-body is defined
pos_tb = html.find('id="tokens-table-body"')
print("tokens-table-body at:", pos_tb)

pos_t_fn = html.find('async function loadTokensOnly()')
pos_t_fn_end = html.find('};', pos_t_fn)
print("loadTokensOnly implementation:")
print(html[pos_t_fn:pos_t_fn_end+2])
