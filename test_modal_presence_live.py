import requests

r = requests.get("http://127.0.0.1:5080/")
print("Status code:", r.status_code)
html = r.text
print("Live length:", len(html))
print("modal-edit-group in live GET:", 'id="modal-edit-group"' in html)
print("edit-group-id in live GET:", 'id="edit-group-id"' in html)
print("edit-group-name in live GET:", 'id="edit-group-name"' in html)
