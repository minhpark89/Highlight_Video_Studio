from web.app import app

print("app.template_folder:", app.template_folder)
print("app.root_path:", app.root_path)

with app.test_client() as client:
    res = client.get("/")
    print("test_client status:", res.status_code)
    data = res.data.decode("utf-8", errors="ignore")
    print("Data length:", len(data))
    print("modal-edit-group in test_client?", "modal-edit-group" in data)
    print("edit-group-id in test_client?", "edit-group-id" in data)
