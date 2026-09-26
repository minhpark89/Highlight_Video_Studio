import os, glob, re

# Search all files on Desktop or D: drive for bat or shortcuts or recent scripts
# Specifically check what is being run or clicked by user
desktop = r"C:\Users\Admin\Desktop"
print("=== Desktop files ===")
if os.path.exists(desktop):
    for f in os.listdir(desktop):
        p = os.path.join(desktop, f)
        print(f, os.path.getsize(p))

print("\n=== Check News_Video_Studio render / crawl buttons ===")
path_news = r"D:\News_Video_Studio\web\templates\index.html"
if os.path.exists(path_news):
    with open(path_news, 'r', encoding='utf-8', errors='ignore') as fp:
        txt = fp.read()
    for kw in ["cào link", "ném vào render", "render", "3 link", "cmd"]:
        pos = txt.lower().find(kw)
        if pos != -1:
            print(f"News studio match '{kw}' at {pos}: {txt[pos:pos+200].replace(chr(10), ' ')}")

