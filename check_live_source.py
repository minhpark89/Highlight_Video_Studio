import requests

r = requests.get("http://127.0.0.1:5080/")
print("Status code:", r.status_code)
html = r.text
print("Live HTML len:", len(html))

# Let's inspect where in live HTML modal-edit-group is or why it was false
print("modal-edit-group in html?", "modal-edit-group" in html)
if "modal-edit-group" in html:
    pos = html.find("modal-edit-group")
    print(html[pos-50:pos+200])
else:
    print("NOT in live html!")
