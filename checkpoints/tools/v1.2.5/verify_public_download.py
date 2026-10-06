"""Download and hash all published assets anonymously; never execute the installer."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
source = Path(__file__).resolve().parents[3]
release = source / "release"
evidence = source / "checkpoints/evidence/v1.2.5"
tag = "v1.2.5"
repo = "minhpark89/Highlight_Video_Studio"
names = {"Highlight_Desktop_Test_Setup_v1.2.5.exe", "Highlight_Desktop_Test_Setup_v1.2.5.sha256",
         "CODEX_CHECKPOINT_v1.2.5.md"}
public = requests.Session()
public.trust_env = False  # No netrc credentials or inherited authentication.
public.headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})


def local_hash(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify():
    started = datetime.now(timezone.utc).isoformat()
    url = f"https://github.com/{repo}/releases/tag/{tag}"
    response = public.get(f"https://api.github.com/repos/{repo}/releases/tags/{tag}", timeout=(20, 40))
    if response.status_code != 200:
        raise RuntimeError(f"Anonymous release API returned HTTP {response.status_code}")
    metadata = response.json()
    if metadata.get("draft") or not metadata.get("prerelease") or metadata.get("tag_name") != tag:
        raise RuntimeError("Release is not the expected public prerelease")
    if {asset["name"] for asset in metadata["assets"]} != names:
        raise RuntimeError("Published release asset set differs from the prepared files")
    with public.get(url, stream=True, timeout=(20, 40)) as page:
        if page.status_code != 200:
            raise RuntimeError(f"Anonymous release page returned HTTP {page.status_code}")
        page_http = page.status_code
    results = []
    for asset in metadata["assets"]:
        path = release / asset["name"]
        expected_digest, expected_size = local_hash(path), path.stat().st_size
        if (asset.get("state") != "uploaded" or asset.get("size") != expected_size
                or asset.get("digest") != "sha256:" + expected_digest):
            raise RuntimeError(f"GitHub digest/state/size mismatch: {path.name}")
        digest = hashlib.sha256()
        size = 0
        progress = 0
        with public.get(asset["browser_download_url"], stream=True, timeout=(20, 60)) as download:
            if download.status_code != 200:
                raise RuntimeError(f"Anonymous asset download returned HTTP {download.status_code}: {path.name}")
            for block in download.iter_content(1024 * 1024):
                if block:
                    size += len(block)
                    digest.update(block)
                    if size - progress >= 128 * 1024 * 1024:
                        progress = size
                        print(json.dumps({"downloading": path.name, "bytes_received": size}), flush=True)
            http = download.status_code
        if size != expected_size or digest.hexdigest() != expected_digest:
            raise RuntimeError(f"Anonymous full download differs from local file: {path.name}")
        row = {"name": path.name, "size": size, "sha256": digest.hexdigest(),
               "browser_download_url": asset["browser_download_url"], "anonymous_get_status": http,
               "matches_local_bytes": True}
        results.append(row)
        print(json.dumps(row), flush=True)
    report = {"success": True, "release_id": metadata["id"], "tag": tag, "release_url": url,
              "draft": False, "prerelease": True, "authenticated_download": False,
              "release_page_http_status": page_http, "release_api_http_status": response.status_code,
              "started_at_utc": started, "verified_at_utc": datetime.now(timezone.utc).isoformat(), "assets": results}
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "public_download_verify.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


try:
    verify()
except requests.RequestException:
    print(json.dumps({"success": False, "error": "Anonymous download connection failed; redirect/request details withheld"}))
    sys.exit(1)
except (RuntimeError, ValueError, TypeError, KeyError) as error:
    print(json.dumps({"success": False, "error": str(error)}))
    sys.exit(1)
