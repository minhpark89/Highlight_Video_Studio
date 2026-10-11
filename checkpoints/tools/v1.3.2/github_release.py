"""Publish only the installer that passed local payload verification."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import requests

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "checkpoints" / "evidence" / "v1.3.2"
RELEASE = ROOT / "release"
REPO = "minhpark89/Highlight_Video_Studio"
TAG = "v1.3.2"
API = "https://api.github.com/repos/" + REPO
PROOF = EVIDENCE / "github_release.json"
sys.stdout.reconfigure(encoding="utf-8")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Progress:
    def __init__(self, stream, size):
        self.stream, self.size, self.reported = stream, size, 0

    def __len__(self):
        return self.size

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def read(self, size=-1):
        block = self.stream.read(size)
        sent = self.stream.tell()
        if sent - self.reported >= 64 * 1024 * 1024:
            self.reported = sent
            print(json.dumps({"bytes_sent":sent, "total_bytes":self.size}), flush=True)
        return block


def main():
    proof = json.loads((EVIDENCE / "installer_payload.json").read_text(encoding="utf-8-sig"))
    installer = RELEASE / "Highlight_Desktop_Test_Setup_v1.3.2.exe"
    local_hash = digest(installer)
    assert proof["success"] and proof["sha256"] == local_hash
    assert proof["size"] == installer.stat().st_size
    source_commit = proof["source_identity"]["source_commit"]
    tag_commit = subprocess.check_output(["git","rev-parse",TAG + "^{commit}"], cwd=ROOT, text=True).strip()
    assert tag_commit == source_commit
    credential = subprocess.run(["git","credential","fill"], cwd=ROOT,
        input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, check=True).stdout
    token = next((line[9:] for line in credential.splitlines() if line.startswith("password=")), "")
    if not token:
        raise RuntimeError("GitHub credential unavailable")
    session = requests.Session()
    session.headers.update({"Authorization":"Bearer " + token, "Accept":"application/vnd.github+json"})
    def request(method, suffix, **kwargs):
        response = session.request(method, API + suffix, timeout=45, **kwargs)
        response.raise_for_status()
        return response.json()
    response = session.get(API + "/releases/tags/" + TAG, timeout=45)
    if response.status_code == 404:
        release = request("POST","/releases", json={"tag_name":TAG, "target_commitish":source_commit,
            "name":"Highlight Desktop Test v1.3.2", "draft":True, "prerelease":True,
            "body":(RELEASE / "RELEASE_v1.3.2.md").read_text(encoding="utf-8")})
    else:
        response.raise_for_status()
        release = response.json()
    PROOF.write_text(json.dumps({"release_id":release["id"], "draft":release["draft"],
        "source_commit":source_commit, "published":False}, indent=2), encoding="utf-8")
    assets = request("GET", "/releases/" + str(release["id"]) + "/assets")
    delivered = []
    paths = [installer, RELEASE / "Highlight_Desktop_Test_Setup_v1.3.2.sha256",
             RELEASE / "RELEASE_v1.3.2.md"]
    for path in paths:
        expected_digest = "sha256:" + digest(path)
        asset = next((item for item in assets if item["name"] == path.name), None)
        if asset is not None:
            if asset.get("state") != "uploaded" or asset.get("size") != path.stat().st_size:
                raise RuntimeError("Existing release asset is incomplete: " + path.name)
            if asset.get("digest") != expected_digest:
                raise RuntimeError("Existing release asset digest differs: " + path.name)
        else:
            with path.open("rb") as stream:
                response = session.post(release["upload_url"].split("{")[0], params={"name":path.name},
                    headers={"Content-Type":"application/octet-stream"},
                    data=Progress(stream,path.stat().st_size), timeout=(30,600))
            response.raise_for_status()
            asset = response.json()
            assert asset["state"] == "uploaded" and asset["size"] == path.stat().st_size
            assert asset.get("digest") == expected_digest
        delivered.append({"name":path.name, "size":asset["size"], "digest":asset["digest"],
                          "url":asset["browser_download_url"]})
        print(json.dumps({"uploaded":path.name, "size":asset["size"]}), flush=True)
    release = request("PATCH","/releases/" + str(release["id"]), json={"draft":False, "prerelease":True})
    assert release["draft"] is False and release["tag_name"] == TAG
    report = {"success":True, "published":True, "prerelease":True, "release_id":release["id"],
        "url":release["html_url"], "source_commit":source_commit, "assets":delivered,
        "server_sha256_matches":True}
    PROOF.write_text(json.dumps(report,indent=2), encoding="utf-8")
    print(json.dumps(report,indent=2), flush=True)


if __name__ == "__main__":
    main()
