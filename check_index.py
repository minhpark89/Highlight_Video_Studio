path = 'D:/Highlight_Video_Studio/web/templates/index.html'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Check if loadTokensAndPages is in DOMContentLoaded
if 'loadTokensAndPages()' not in c[c.find('DOMContentLoaded'):c.find('DOMContentLoaded')+300]:
    print("DOMContentLoaded missing loadTokensAndPages")
    c = c.replace("loadScheduleRulesConfig();", "loadScheduleRulesConfig();\n      loadTokensAndPages();")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Added loadTokensAndPages to DOMContentLoaded in templates/index.html")

# Sync to web/index.html as well
with open('D:/Highlight_Video_Studio/web/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
print("Synced to web/index.html")
