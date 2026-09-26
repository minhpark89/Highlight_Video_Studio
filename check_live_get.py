import requests

r = requests.get("http://127.0.0.1:5080/")
print("Status code:", r.status_code)
html = r.text
print("Live HTML len:", len(html))
print("modal-edit-group in live HTML?", "id=\"modal-edit-group\"" in html)
print("edit-group-id in live HTML?", "id=\"edit-group-id\"" in html)
