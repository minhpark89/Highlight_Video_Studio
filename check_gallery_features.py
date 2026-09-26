with open("D:/Highlight_Video_Studio/web/app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Let's check posts.json or where posted status is recorded
import json

print("Checking posts.json:")
try:
    with open("D:/Highlight_Video_Studio/posts.json", "r", encoding="utf-8") as pf:
        pdata = json.load(pf)
        print("posts.json type/keys:", type(pdata), list(pdata.keys()) if isinstance(pdata, dict) else len(pdata))
except Exception as e:
    print("posts.json error:", e)

