from web.app import app
print("app.template_folder:", app.template_folder)
print("app.root_path:", app.root_path)

with app.test_client() as client:
    res = client.get("/")
    print("test_client get / status:", res.status_code)
    print("test_client len:", len(res.data))
    print("modal-edit-group in test_client?", b"modal-edit-group" in res.data)
