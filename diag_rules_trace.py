from web.app import app
import traceback

with app.test_client() as client:
    try:
        res = client.get("/api/schedule/rules")
        print("Status code:", res.status_code)
        print("Response data:", res.data.decode('utf-8', errors='ignore')[:300])
    except Exception as e:
        print("Exception caught:")
        traceback.print_exc()
