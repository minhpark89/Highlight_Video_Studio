import os, re, json, glob

# We need to know:
# 1. In Highlight_Video_Studio, where does a CMD window pop up?
# Or in another studio (News_Video_Studio, etc.)?
# Let's inspect index.html for buttons clicked:
# "Ném vào Cắt Highlight", "Ném vào Render", or inside each video card
html_path = r"D:\Highlight_Video_Studio\web\templates\index.html"
with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

# Let's find video card render buttons in research results
for fn in ["renderVideo", "openVideoPlayerModal", "sendModalUrlToRender", "sendToRender", "performResearch"]:
    idx = html.find(f"function {fn}")
    if idx != -1:
        print(f"=== Function {fn} ===")
        print(html[idx:idx+1200])

