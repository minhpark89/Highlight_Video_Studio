import copy
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from web.post_retry import can_retry_without_upload, prepare_retry, REMOTE_FIELDS
from web.meta_diagnostics import diagnose


@pytest.fixture
def retry(tmp_path, monkeypatch):
    from web import app as api
    output = tmp_path / 'output'
    output.mkdir()
    (output / 'clip.mp4').write_bytes((Path(__file__).parent / 'fixtures/tiny-video.mp4').read_bytes())
    row = {'id': 'rejected', 'status': 'failed', 'retryable': True, 'retry_stage': 'facebook_publish',
           'error': 'Meta init rejected (HTTP 400): API access blocked',
           'page_id': 'page', 'token_id': 'original', 'media_file': 'clip.mp4',
           'title': 'The original video highlight', 'content': 'Watch the original video for full context.',
           'article_url': 'https://example.test/blog/story', 'website_status': 'ready',
           'first_comment': 'Read the full story here: https://example.test/blog/story',
           'scheduled_time': '2026-10-05 04:00:00', 'publish_mode': 'meta_scheduled',
           'publish_started_at': '2026-10-05T03:00:00'}
    path = tmp_path / 'posts.json'
    path.write_text(json.dumps([row]), encoding='utf-8')
    monkeypatch.setattr(api, 'POSTS_FILE', path)
    monkeypatch.setattr(api, 'OUTPUT_DIR', output)
    return api, api.app.test_client(), row, path, output


def test_meta_init_retry_queues_app_and_fences_repeat_without_remote_call(retry):
    api, client, row, path, output = retry
    with mock.patch.object(api.reel_poster, 'publish_reel') as publish:
        response = client.post('/api/posts/rejected/retry-publish', json={})
        assert response.status_code == 202
        assert client.post('/api/posts/rejected/retry-publish', json={}).status_code == 409
    publish.assert_not_called()
    saved = json.loads(path.read_text())[0]
    assert saved['status'] == 'scheduled' and saved['publish_mode'] == 'app_queue'
    assert saved['token_id'] == 'original' and saved['content_frozen_at']
    assert saved['first_comment_snapshot'] == row['first_comment']
    assert saved['original_scheduled_time'] == row['scheduled_time']
    assert saved['publish_retry_history'][0]['error'] == row['error']
    assert 'publish_started_at' not in saved


@pytest.mark.parametrize('changes', [{field: 'existing'} for field in REMOTE_FIELDS] + [
    {'outcome_unknown': True}, {'meta_cancel_requested': True},
    {'error': 'Meta init non-JSON response (HTTP 502)'}, {'status': 'published'}])
def test_existing_id_and_uncertain_outcome_cannot_be_reuploaded(retry, changes):
    api, client, row, path, output = retry
    row.update(changes)
    path.write_text(json.dumps([row]))
    before = path.read_bytes()
    assert not can_retry_without_upload(row)
    assert client.post('/api/posts/rejected/retry-publish', json={}).status_code == 409
    assert path.read_bytes() == before


@pytest.mark.parametrize('changes', [
    {'first_comment': 'No website URL.'},
    {'first_comment': 'Read https://example.test/blog/story https://example.test/blog/story'},
    {'website_status': 'failed'}, {'content': 'Đây là một đoạn văn tiếng Việt.'},
    {'media_file': 'missing.mp4'}, {'media_file': '../outside.mp4'}])
def test_retry_validates_media_website_comment_and_english_before_queueing(retry, changes):
    api, client, row, path, output = retry
    row.update(changes)
    path.write_text(json.dumps([row]))
    before = path.read_bytes()
    assert client.post('/api/posts/rejected/retry-publish', json={}).status_code == 409
    assert path.read_bytes() == before


@pytest.mark.parametrize('status,remote', [('published', {}), ('failed', {'meta_upload_video_id': '9001'}),
                                         ('failed', {'outcome_unknown': True})])
def test_duplicate_same_page_is_blocked_even_for_failed_remote_rows(retry, status, remote):
    api, client, row, path, output = retry
    duplicate = {**row, 'id': 'other', 'status': status, 'media_file': str(output / 'clip.mp4'), **remote}
    path.write_text(json.dumps([row, duplicate]))
    assert client.post('/api/posts/rejected/retry-publish', json={}).status_code == 409


def test_meta_retry_requires_new_future_time_and_preserves_failure_on_rejection(retry):
    api, client, row, path, output = retry
    now = datetime.now()
    original = copy.deepcopy(row)
    with pytest.raises(ValueError):
        prepare_retry(row, [row], output, mode='meta_scheduled', schedule_time=now.isoformat(), now=now)
    assert row == original
    prepare_retry(row, [row], output, mode='meta_scheduled', schedule_time=(now + timedelta(hours=1)).isoformat(), now=now)
    assert row['status'] == 'meta_handoff' and row['meta_schedule_status'] == 'handoff_queued'


@pytest.mark.parametrize('seen', [{}, {'http_status': 400, 'error': 'API access blocked'},
    {'http_status': 200, 'publishing_status': 'scheduled'}])
def test_overdue_schedule_is_explicit_with_missing_or_blocked_observation(seen):
    post = {'status': 'meta_scheduled', 'meta_scheduled_publish_time': datetime.now().timestamp() - 600}
    result = diagnose(post, seen)
    assert result['state'] == 'schedule_overdue'
    assert not result['can_finish_existing']


def test_published_observation_takes_precedence_over_overdue_time():
    result = diagnose({'status': 'meta_scheduled', 'meta_scheduled_publish_time': 1},
                      {'http_status': 200, 'publishing_status': 'published'})
    assert result['state'] == 'published'
