"""Verify public release links without authentication or printing redirect URLs."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

import requests

root = Path(__file__).resolve().parents[3]
release = root / 'release'
metadata = json.loads((root / 'checkpoints/evidence/v1.2.2/release.json').read_text(encoding='utf-8'))
assert not metadata['draft'] and metadata['public_downloads_verified']
results = []
for asset in metadata['assets']:
    path = release / asset['name']
    if path.suffix == '.exe':
        with requests.get(asset['browser_download_url'], headers={'Range': 'bytes=0-65535'},
                          stream=True, timeout=(20, 40)) as response:
            assert response.status_code in (200, 206)
            block = response.raw.read(65536)
            with path.open('rb') as local:
                assert len(block) == 65536 and block == local.read(65536)
            results.append({'name': path.name, 'http': response.status_code, 'public_bytes_checked': len(block),
                'prefix_matches': True, 'github_full_digest_matches': asset['digest'] == 'sha256:' + metadata['installer_sha256']})
    else:
        response = requests.get(asset['browser_download_url'], timeout=(20, 40))
        assert response.status_code == 200 and response.content == path.read_bytes()
        results.append({'name': path.name, 'http': response.status_code, 'public_bytes_checked': len(response.content),
            'full_content_matches': True, 'sha256': hashlib.sha256(response.content).hexdigest()})
report = {'observed_at': datetime.now().astimezone().isoformat(), 'tag': metadata['tag_name'],
          'release_id': metadata['id'], 'authenticated': False, 'assets': results, 'success': True}
(root / 'checkpoints/evidence/v1.2.2/public_download_verify.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
