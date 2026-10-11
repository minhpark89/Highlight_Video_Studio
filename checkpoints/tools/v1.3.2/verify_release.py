"""Verify the public release metadata and download endpoint after publication."""
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "checkpoints" / "evidence" / "v1.3.2"
path = EVIDENCE / "github_release.json"
proof = json.loads(path.read_text(encoding="utf-8"))
response = requests.get("https://api.github.com/repos/minhpark89/Highlight_Video_Studio/releases/tags/v1.3.2",
                        timeout=45)
if response.status_code != 200:
    raise RuntimeError("Release verification returned HTTP " + str(response.status_code))
release = response.json()
assert not release["draft"] and release["prerelease"]
assert release["id"] == proof["release_id"]
assets = {asset["name"]:asset for asset in release["assets"]}
for recorded in proof["assets"]:
    actual = assets[recorded["name"]]
    assert actual["state"] == "uploaded"
    assert actual["size"] == recorded["size"] and actual["digest"] == recorded["digest"]
    recorded["url"] = actual["browser_download_url"]
installer = assets["Highlight_Desktop_Test_Setup_v1.3.2.exe"]
download = requests.head(installer["browser_download_url"], allow_redirects=True, timeout=45)
if download.status_code != 200:
    raise RuntimeError("Installer endpoint returned HTTP " + str(download.status_code))
length = download.headers.get("Content-Length")
if length:
    assert int(length) == installer["size"]
assert "text/html" not in download.headers.get("Content-Type","")
proof["download_http_status"] = download.status_code
proof["canonical_asset_urls_verified"] = True
path.write_text(json.dumps(proof,indent=2), encoding="utf-8")
print(json.dumps({"success":True, "url":release["html_url"],
    "installer_url":installer["browser_download_url"], "bytes":installer["size"],
    "server_digest":installer["digest"], "download_http_status":download.status_code},indent=2))
