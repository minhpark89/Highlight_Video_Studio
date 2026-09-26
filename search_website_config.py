import os

for root, dirs, files in os.walk("D:/Highlight_Video_Studio"):
    for f in files:
        if f.endswith((".py", ".html", ".js")) and not f.startswith("test_"):
            p = os.path.join(root, f)
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as file:
                    c = file.read()
                    if "loadWebsiteConfig" in c:
                        print(f"Found in {p}")
            except:
                pass
