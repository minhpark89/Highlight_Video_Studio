import urllib.request
import json

print("=== 1. TEST API CALLS ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    jobs = json.loads(r.read().decode('utf-8'))
    print("Jobs API len:", len(jobs))
    if jobs:
        print("First 2 jobs:", jobs[0].get('id'), jobs[0].get('status'), jobs[0].get('step'))
except Exception as e:
    print("Jobs API error:", e)

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/pages")
    pages_res = json.loads(r.read().decode('utf-8'))
    pages = pages_res.get('pages', [])
    print("Pages API len:", len(pages))
    if pages:
        print("Sample page:", pages[0].get('page_id'), pages[0].get('page_name'), pages[0].get('token_id'))
except Exception as e:
    print("Pages API error:", e)

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/tokens")
    tokens_res = json.loads(r.read().decode('utf-8'))
    tokens = tokens_res.get('tokens', [])
    print("Tokens API len:", len(tokens))
    if tokens:
        print("Sample token:", tokens[0].get('id'), tokens[0].get('name'))
except Exception as e:
    print("Tokens API error:", e)

