import urllib.request
import json

res = urllib.request.urlopen("http://127.0.0.1:5080/api/tokens")
print("Tokens status:", res.status)
toks = json.loads(res.read().decode())
print("Tokens count:", len(toks.get("tokens", [])))

res = urllib.request.urlopen("http://127.0.0.1:5080/api/pages")
print("Pages status:", res.status)
pages = json.loads(res.read().decode())
print("Pages count:", len(pages.get("pages", [])))
