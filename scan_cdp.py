import urllib.request, json

for port in [9444, 9445, 9222, 9223]:
    try:
        url = f"http://127.0.0.1:{port}/json"
        req = urllib.request.urlopen(url, timeout=2)
        tabs = json.loads(req.read().decode('utf-8'))
        print(f"=== Port {port} CDP Tabs ({len(tabs)}) ===")
        for t in tabs:
            print("  Title:", t.get("title"))
            print("  URL  :", t.get("url"))
    except Exception as e:
        print(f"Port {port}: {e}")

