import requests

r = requests.get("http://127.0.0.1:5080/")
print("Status code:", r.status_code)
print("Length:", len(r.text))
print("modal-edit-group in live GET?", "id=\"modal-edit-group\"" in r.text)
print("edit-group-id in live GET?", "id=\"edit-group-id\"" in r.text)
