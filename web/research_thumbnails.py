"""Bounded YouTube thumbnails with a local fallback for deleted videos."""
from collections import OrderedDict
import re
import threading
import time

from flask import Response
import requests


_CACHE = OrderedDict()
_LOCK = threading.Lock()
_FALLBACK = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><rect width="640" height="360" fill="#172235"/><path d="M280 130v100l90-50z" fill="#64748b"/><text x="320" y="290" text-anchor="middle" font-family="sans-serif" font-size="21" fill="#94a3b8">Preview unavailable</text></svg>'


def thumbnail(video_id):
    if video_id == 'placeholder' or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        return _FALLBACK, 'image/svg+xml'
    now = time.monotonic()
    with _LOCK:
        cached = _CACHE.get(video_id)
        if cached and cached[0] > now:
            _CACHE.move_to_end(video_id)
            return cached[1:]
    payload, content_type = _FALLBACK, 'image/svg+xml'
    try:
        # IDs only: the endpoint cannot be used as an arbitrary URL proxy.
        with requests.get(f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
                          timeout=(3, 4), allow_redirects=False, stream=True) as response:
            mime = response.headers.get('Content-Type', '').split(';')[0].lower()
            if response.status_code == 200 and mime in ('image/jpeg', 'image/png', 'image/webp'):
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > 1024 * 1024:
                        break
                else:
                    if data:
                        payload, content_type = bytes(data), mime
    except requests.RequestException:
        pass
    with _LOCK:
        _CACHE[video_id] = (now + 3600, payload, content_type)
        _CACHE.move_to_end(video_id)
        while len(_CACHE) > 256:
            _CACHE.popitem(last=False)
    return payload, content_type


def register(app):
    @app.get('/api/youtube-thumbnail/<video_id>')
    def youtube_thumbnail(video_id):
        payload, content_type = thumbnail(video_id)
        return Response(payload, mimetype=content_type,
                        headers={'Cache-Control': 'private, max-age=3600',
                                 'X-Content-Type-Options': 'nosniff'})
