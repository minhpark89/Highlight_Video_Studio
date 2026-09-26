import requests

r = requests.get("http://127.0.0.1:5080/")
html = r.text

print("Has 'Xem Reel Facebook' in live HTML GET?", "Xem Reel Facebook" in html)
if "Xem Reel Facebook" in html:
    pos = html.find("Xem Reel Facebook")
    print(html[pos-100:pos+200])
else:
    print("NOT FOUND in live HTML!")
