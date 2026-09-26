import os, glob, re

# Let's inspect News_Video_Studio and Highlight_Video_Studio
for studio_name in [r"D:\News_Video_Studio", r"D:\Highlight_Video_Studio"]:
    print(f"================ {studio_name} ================")
    # Search for cào link or research or crawl in web/templates/index.html
    html_file = os.path.join(studio_name, "web", "templates", "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        print(f"HTML size: {len(html)}")
        # Check buttons with "Ném vào Render" or "render" or "cmd"
        for m in re.finditer(r'(ném vào render|cào link|chọn 3|batch|checkbox|startrender|open.*cmd)', html, re.IGNORECASE):
            s = max(0, m.start() - 50)
            e = min(len(html), m.end() + 100)
            print(f"  Match in {studio_name} HTML: {html[s:e].replace('\n', ' ')}")

