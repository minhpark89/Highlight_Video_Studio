import requests

r = requests.get("http://127.0.0.1:5080/")
print("Status code:", r.status_code)
html = r.text
print("Has modal-edit-group in live HTTP GET?", 'id="modal-edit-group"' in html)
print("Has edit-group-id in live HTTP GET?", 'id="edit-group-id"' in html)
print("Has editGroupModal in live HTTP GET?", 'function editGroupModal' in html)
