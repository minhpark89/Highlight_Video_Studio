from unittest import mock

from flask import Flask
import pytest

from web import research_thumbnails as thumbnails


@pytest.fixture
def client():
    thumbnails._CACHE.clear()
    app = Flask('thumbnail-test')
    thumbnails.register(app)
    return app.test_client()


def test_deleted_thumbnail_uses_cached_local_fallback(client):
    remote = mock.MagicMock(status_code=404, headers={})
    remote.__enter__.return_value = remote
    with mock.patch.object(thumbnails.requests, 'get', return_value=remote) as fetch:
        for _ in range(2):
            response = client.get('/api/youtube-thumbnail/c399RMqEOOY')
            assert response.status_code == 200
            assert response.mimetype == 'image/svg+xml'
            assert b'Preview unavailable' in response.data
        assert fetch.call_count == 1
        assert fetch.call_args.args == ('https://i.ytimg.com/vi/c399RMqEOOY/hqdefault.jpg',)
        assert fetch.call_args.kwargs['allow_redirects'] is False


def test_only_exact_video_ids_can_trigger_a_request(client):
    with mock.patch.object(thumbnails.requests, 'get') as fetch:
        assert client.get('/api/youtube-thumbnail/placeholder').status_code == 200
        assert client.get('/api/youtube-thumbnail/example.com').mimetype == 'image/svg+xml'
        fetch.assert_not_called()


def test_valid_image_and_oversized_response(client):
    remote = mock.MagicMock(status_code=200, headers={'Content-Type': 'image/jpeg'})
    remote.__enter__.return_value = remote
    remote.iter_content.return_value = [b'jpeg-fixture']
    with mock.patch.object(thumbnails.requests, 'get', return_value=remote):
        response = client.get('/api/youtube-thumbnail/c399RMqEOOY')
        assert response.mimetype == 'image/jpeg'
        assert response.data == b'jpeg-fixture'
        remote.iter_content.return_value = [b'x' * (1024 * 1024 + 1)]
        response = client.get('/api/youtube-thumbnail/mUjVBAPIR48')
        assert response.mimetype == 'image/svg+xml'
