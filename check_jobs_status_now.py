import urllib.request
import json

try:
    r = urllib.request.urlopen("http://127.0.0.1:5080/api/jobs")
    jobs = json.loads(r.read().decode())
    print("API jobs count:", len(jobs))
    by_st = {}
    for j in jobs:
        s = j.get("status")
        by_st[s] = by_st.get(s, 0) + 1
    print("Breakdown:", by_st)
except Exception as e:
    print("API err:", e)
