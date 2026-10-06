"""Publish this approved release; keep the GitHub credential in memory only."""
import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from urllib.parse import quote

SOURCE = pathlib.Path(__file__).resolve().parents[3]
ROOT = SOURCE.parent
RELEASE = SOURCE / "release"
REPO = "minhpark89/Highlight_Video_Studio"
TAG = "v1.2.8"
META = RELEASE / "v1.2.8_release.json"
sys.stdout.reconfigure(encoding="utf-8")
import requests


def connection_failure(exc):
    """Report only error codes, never requests, headers or credential values."""
    seen = set()
    def denied(error):
        if not isinstance(error, BaseException) or id(error) in seen:
            return False
        seen.add(id(error))
        if getattr(error, "winerror", None) == 10013:
            return True
        return any(denied(child) for child in (getattr(error, "__cause__", None),
                   getattr(error, "__context__", None), getattr(error, "reason", None), *error.args))
    if denied(exc):
        return "Windows denied the TCP connection (WinError 10013); no GitHub authentication response was received"
    return "GitHub connection unavailable; credential-bearing network details withheld"

raw = (ROOT / "token github.txt").read_text(encoding="utf-8-sig")
match = re.search(r"\b(?:ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+)\b", raw)
if not match:
    raise RuntimeError("No supported GitHub credential found in the existing local credential file")
credential = match.group(0)
del raw, match
session = requests.Session()
session.headers.update({"Authorization": "Bearer " + credential, "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"})
api_base = "https://api.github.com/repos/" + REPO

def request(method, suffix, *, expected=(200,), **kwargs):
    try:
        response = session.request(method, api_base + suffix, timeout=45, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(connection_failure(exc)) from None
    if response.status_code not in expected:
        raise RuntimeError(f"GitHub {method} {suffix} returned HTTP {response.status_code}; response body withheld")
    return None if response.status_code == 404 else (response.json() if response.content else None)

def save(metadata):
    META.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

def git(*arguments):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "Never"
    index = int(env.get("GIT_CONFIG_COUNT", "0"))
    env["GIT_CONFIG_COUNT"] = str(index + 1)
    env[f"GIT_CONFIG_KEY_{index}"] = "http.https://github.com/.extraheader"
    env[f"GIT_CONFIG_VALUE_{index}"] = "AUTHORIZATION: basic " + base64.b64encode(("x-access-token:" + credential).encode()).decode()
    result = subprocess.run(["git", *arguments], cwd=SOURCE, env=env, capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        if "Failed to connect" in result.stderr or "Could not resolve host" in result.stderr:
            raise RuntimeError("Git could not connect to GitHub; credential-bearing details withheld")
        raise RuntimeError("Git operation failed; credential-bearing details withheld")
    return result.stdout.strip()

def clean_commit():
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("Source is dirty; commit the approved fixes before publishing")
    return git("rev-parse", "HEAD")

def file_digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

class ProgressUpload:
    def __init__(self, handle, path):
        self.handle = handle
        self.path = path
        self.last_reported = 0

    def __getattr__(self, name):
        return getattr(self.handle, name)

    def read(self, size=-1):
        block = self.handle.read(size)
        sent = self.handle.tell()
        if sent - self.last_reported >= 64 * 1024 * 1024:
            self.last_reported = sent
            print(json.dumps({"uploading": self.path.name, "bytes_sent": sent,
                              "total_bytes": self.path.stat().st_size}), flush=True)
        return block

def installer_info():
    file = RELEASE / "Highlight_Desktop_Test_Setup_v1.2.8.exe"
    return file, file_digest(file), file.stat().st_size

def packaged_commit():
    proof = json.loads((SOURCE / 'checkpoints/evidence/v1.2.8/installer_payload.json').read_text(encoding='utf-8-sig'))
    _, digest, size = installer_info()
    assert proof['success'] and not proof['source_identity']['source_dirty']
    assert proof['sha256'] == digest and proof['size'] == size
    return proof['source_identity']['source_commit']

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["deploy", "inspect", "status", "push", "draft", "resume", "upload", "publish", "verify"])
args = parser.parse_args()

if args.action == "deploy":
    from github_deploy import deploy
    def invoke(action):
        print(json.dumps({"deployment_step": action}), flush=True)
        completed = subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()), action],
                                  cwd=SOURCE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
        output = []
        for line in completed.stdout:
            output.append(line)
            print(line.rstrip(), flush=True)
        stderr = completed.stderr.read()
        completed.wait()
        if completed.returncode:
            reason = "Windows denied TCP (WinError 10013) before GitHub authentication" if "WinError 10013" in stderr else "action failed; run this action directly for sanitized diagnostics"
            raise RuntimeError(f"Deployment stopped at {action}: {reason}")
        return json.loads(output[-1]) if output else {}
    deploy(invoke)
elif args.action == "inspect":
    try:
        who = session.get("https://api.github.com/user", timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(connection_failure(exc)) from None
    if who.status_code != 200:
        raise RuntimeError(f"GitHub authentication returned HTTP {who.status_code}; credential withheld")
    repo = request("GET", "")
    existing = request("GET", "/releases/tags/" + TAG, expected=(200,404))
    print(json.dumps({"authenticated_as":who.json()["login"], "push_permission":repo.get("permissions",{}).get("push"),
        "release_exists":bool(existing and existing.get("id")), "existing_release":{k:existing.get(k) for k in ("id","draft","prerelease","html_url")} if existing and existing.get("id") else None,
        "latest_releases":[{k:r.get(k) for k in ("tag_name","draft","prerelease")} for r in request("GET","/releases?per_page=5")]}, ensure_ascii=False))
elif args.action == "status":
    metadata = json.loads(META.read_text(encoding="utf-8"))
    result = request("GET", "/releases/" + str(metadata["id"]))
    print(json.dumps({"draft":result["draft"], "assets":[{k:a.get(k) for k in ("name","size","state")} for a in result["assets"]]}))
elif args.action == "push":
    commit = clean_commit()
    if git("rev-parse", TAG + "^{commit}") != packaged_commit():
        raise RuntimeError("Local release tag does not match the packaged source")
    git("push", "--atomic", "origin", "HEAD:refs/heads/release/v1.2.8", "refs/tags/" + TAG)
    remote = git("ls-remote", "--heads", "origin", "release/v1.2.8")
    assert remote.split()[0] == commit, "Remote branch does not match the committed fixes"
    print(json.dumps({"source_commit":commit,"branch_pushed":True}))
elif args.action == "draft":
    branch_commit = clean_commit()
    commit = packaged_commit()
    file, digest, size = installer_info()
    existing = request("GET", "/releases/tags/" + TAG, expected=(200,404))
    assert not (existing and existing.get("id")), "Release already exists; refusing to overwrite a published revision"
    body = (RELEASE / "v1.2.8_release_notes.md").read_text(encoding="utf-8")
    result = request("POST", "/releases", expected=(201,), json={"tag_name":TAG,"target_commitish":commit,
        "name":"Highlight Desktop Test v1.2.8 - CMS validation and verified MP4 recovery", "body":body,"draft":True,"prerelease":True})
    metadata = {k:result[k] for k in ("id","tag_name","html_url","upload_url","draft","prerelease")}
    metadata.update(source_commit=commit,branch_commit=branch_commit,installer_sha256=digest,installer_size=size,assets=[])
    save(metadata)
    print(json.dumps({k:metadata[k] for k in ("id","tag_name","source_commit","draft","prerelease")},ensure_ascii=False))
elif args.action == "resume":
    commit = packaged_commit()
    existing = request("GET", "/releases/tags/" + TAG)
    remote = git("ls-remote", "--tags", "origin", TAG + "^{}")
    assert remote.split()[0] == commit, "Existing remote tag differs from the verified installer source"
    expected = {"Highlight_Desktop_Test_Setup_v1.2.8.exe", "Highlight_Desktop_Test_Setup_v1.2.8.sha256", "CODEX_CHECKPOINT_v1.2.8.md"}
    for asset in existing["assets"]:
        assert asset["name"] in expected, "Unexpected existing asset; inspect before continuing"
        path = RELEASE / asset["name"]
        assert asset.get("digest") == "sha256:" + file_digest(path) and asset["size"] == path.stat().st_size, "Existing asset differs; refusing to replace it"
    metadata = {k: existing[k] for k in ("id", "tag_name", "html_url", "upload_url", "draft", "prerelease")}
    file, digest, size = installer_info()
    metadata.update(source_commit=commit, branch_commit=clean_commit(), installer_sha256=digest,
                    installer_size=size, assets=existing["assets"])
    save(metadata)
    print(json.dumps({k:metadata[k] for k in ("id","tag_name","source_commit","draft","prerelease")},ensure_ascii=False))
elif args.action == "upload":
    metadata = json.loads(META.read_text(encoding="utf-8"))
    assert metadata["draft"], "Upload must finish while the release is a draft"
    current = request("GET", "/releases/" + str(metadata["id"]))
    assert current["draft"] and current["tag_name"] == TAG
    files = [RELEASE / name for name in ("Highlight_Desktop_Test_Setup_v1.2.8.exe",
        "Highlight_Desktop_Test_Setup_v1.2.8.sha256","CODEX_CHECKPOINT_v1.2.8.md")]
    by_name = {a["name"]:a for a in current["assets"]}
    for path in files:
        digest = "sha256:" + file_digest(path)
        if path.name in by_name:
            asset = by_name[path.name]
            assert asset.get("digest") == digest and asset.get("size") == path.stat().st_size, "Existing draft asset differs; inspect before replacing"
        else:
            endpoint = metadata["upload_url"].split("{",1)[0] + "?name=" + quote(path.name)
            print(json.dumps({"uploading":path.name,"bytes":path.stat().st_size}),flush=True)
            with path.open("rb") as handle:
                try:
                    response = session.post(endpoint, data=ProgressUpload(handle, path),
                        headers={"Content-Type":"application/octet-stream"}, timeout=(30,1200))
                except requests.RequestException as exc:
                    raise RuntimeError(connection_failure(exc)) from None
            if response.status_code != 201:
                raise RuntimeError(f"Asset upload returned HTTP {response.status_code}; response withheld")
            asset = response.json()
            assert asset.get("state") == "uploaded" and asset.get("digest") == digest and asset.get("size") == path.stat().st_size, "Uploaded asset verification failed"
        print(json.dumps({"asset":path.name,"state":asset.get("state"),"size":asset.get("size"),"digest":asset.get("digest")}),flush=True)
    metadata["assets"] = [{k:a.get(k) for k in ("name","size","digest","state","browser_download_url")} for a in request("GET", "/releases/" + str(metadata["id"]))["assets"]]
    save(metadata)
elif args.action == "publish":
    metadata = json.loads(META.read_text(encoding="utf-8"))
    current = request("GET", "/releases/" + str(metadata["id"]))
    assert current["draft"] and len(current["assets"]) == 3
    expected = {"Highlight_Desktop_Test_Setup_v1.2.8.exe", "Highlight_Desktop_Test_Setup_v1.2.8.sha256", "CODEX_CHECKPOINT_v1.2.8.md"}
    assert {a["name"] for a in current["assets"]} == expected
    for asset in current["assets"]:
        path = RELEASE / asset["name"]
        assert asset["state"] == "uploaded" and asset["digest"] == "sha256:" + file_digest(path) and asset["size"] == path.stat().st_size
    body = (RELEASE / "v1.2.8_release_notes.md").read_text(encoding="utf-8")
    result = request("PATCH", "/releases/" + str(metadata["id"]), json={"draft":False,"prerelease":True,"make_latest":"false","body":body})
    metadata.update({k:result[k] for k in ("html_url","draft","prerelease")})
    save(metadata)
    print(json.dumps({k:metadata[k] for k in ("id","tag_name","html_url","draft","prerelease")},ensure_ascii=False))
else:
    metadata = json.loads(META.read_text(encoding="utf-8"))
    result = request("GET", "/releases/tags/" + TAG)
    assert result["id"] == metadata["id"] and not result["draft"] and result["prerelease"]
    branch_commit = git("rev-parse", "HEAD")
    commit = packaged_commit()
    remote = git("ls-remote", "--tags", "origin", TAG + "^{}")
    assert remote.split()[0] == commit == metadata["source_commit"]
    branch = git("ls-remote", "--heads", "origin", "release/v1.2.8")
    assert branch.split()[0] == branch_commit
    expected = {"Highlight_Desktop_Test_Setup_v1.2.8.exe", "Highlight_Desktop_Test_Setup_v1.2.8.sha256", "CODEX_CHECKPOINT_v1.2.8.md"}
    assert {a["name"] for a in result["assets"]} == expected, "Published release is missing an expected download asset"
    assets = []
    for item in result["assets"]:
        path = RELEASE / item["name"]
        assert item["state"] == "uploaded" and path.stat().st_size == item["size"]
        assert item["digest"] == "sha256:" + file_digest(path)
        public = requests.head(item["browser_download_url"], allow_redirects=True, timeout=40)
        assert public.status_code == 200, "Published asset is not publicly downloadable"
        assets.append({k:item.get(k) for k in ("name","size","digest","state","browser_download_url")})
    metadata.update(assets=assets, draft=False, prerelease=True, public_downloads_verified=True, source_tag_verified=True,
                    branch_commit=branch_commit, branch_verified=True)
    save(metadata)
    print(json.dumps(metadata,ensure_ascii=False))
