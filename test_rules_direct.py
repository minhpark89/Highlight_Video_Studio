from pathlib import Path
import traceback

try:
    from web.app import app
    with app.test_client() as client:
        res = client.get("/api/schedule/rules")
        print("Status code:", res.status_code)
        print("Data:", res.data.decode('utf-8', errors='ignore'))
except Exception as e:
    print("Caught error:")
    traceback.print_exc()
