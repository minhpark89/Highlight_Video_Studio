import json
from pathlib import Path

import pytest

from src import storage_retention as retention


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


@pytest.fixture
def media(tmp_path, monkeypatch):
    from web import scheduled_publisher as worker
    from src import content_packages
    output = tmp_path / 'output'
    output.mkdir()
    clip = output / 'clip.mp4'
    clip.write_bytes(b'finished reel')
    monkeypatch.setattr(worker, 'OUTPUT_DIR', output)
    monkeypatch.setattr(worker, 'POSTS_FILE', tmp_path / 'posts.json')
    monkeypatch.setattr(worker, 'POSTED_CLIPS_FILE', tmp_path / 'posted_clips.json')
    monkeypatch.setattr(content_packages, 'QUEUE_FILE', tmp_path / 'data/content_packages.json')
    posts = [{'id': 'p1', 'media_file': clip.name, 'status': 'published', 'post_fb_id': '123', 'fb_url': 'https://facebook.com/reel/123'}]
    write(tmp_path / 'posts.json', posts)
    return worker, clip, posts


def test_confirmed_reel_deleted_with_history_and_statistics(media):
    worker, clip, posts = media
    result = worker.cleanup_published_clip_files(posts)
    assert result == {'deleted_count': 1, 'freed_bytes': len(b'finished reel')}
    assert not clip.exists()
    assert posts[0]['fb_url'].endswith('/123')
    assert posts[0]['status'] == 'published'
    assert posts[0]['local_video_deleted_at']
    assert retention.cleanup_statistics(clip.parent.parent)['published_reels_deleted'] == 1
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0


def test_local_cycle_does_not_call_or_wait_for_meta_scheduler(media, monkeypatch):
    worker, clip, posts = media
    def forbidden(*args, **kwargs):
        raise AssertionError('Cleanup must not call the Meta scheduler')
    monkeypatch.setattr(worker, '_process_scheduled_posts_once', forbidden)
    result = retention.cleanup_cycle(clip.parent.parent)
    assert result['reels']['deleted_count'] == 1
    assert not clip.exists()
    persisted = json.loads((clip.parent.parent / 'posts.json').read_text(encoding='utf-8'))
    assert persisted[0]['status'] == 'published' and persisted[0]['local_video_deleted_at']


def test_worker_startup_cleans_with_independent_lease(media, monkeypatch):
    worker, clip, posts = media
    import threading
    monkeypatch.setattr(retention, '_WORKER', None)
    monkeypatch.setattr(threading.Thread, 'start', lambda self: None)
    class OneCycle:
        def wait(self, seconds):
            raise StopIteration
    monkeypatch.setattr(threading, 'Event', OneCycle)
    thread = retention.start_storage_retention_worker(clip.parent.parent)
    with pytest.raises(StopIteration):
        thread._target()
    assert not clip.exists()
    persisted = json.loads((clip.parent.parent / 'posts.json').read_text(encoding='utf-8'))
    assert persisted[0]['local_video_deleted_at']


@pytest.mark.parametrize('status', ['scheduled', 'meta_scheduled', 'processing', 'publishing', 'failed', 'preparing', 'meta_handoff'])
def test_shared_file_kept_until_every_consumer_published(media, status):
    worker, clip, posts = media
    posts.append({'id': 'p2', 'media_file': str(clip), 'status': status})
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    assert clip.exists()
    posts[1].update(status='published', post_fb_id='456')
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 1
    assert all(p.get('local_video_deleted_at') for p in posts)


@pytest.mark.parametrize('changes', [{'post_fb_id': ''}, {'outcome_unknown': True}])
def test_unconfirmed_result_never_deleted(media, changes):
    worker, clip, posts = media
    posts[0].update(changes)
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    assert clip.exists()


def test_setting_off_and_explicit_manual_cleanup(media):
    worker, clip, posts = media
    write(clip.parent.parent / 'config.json', {'storage_retention': {'delete_published_reels': False}})
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    assert worker.cleanup_published_clip_files(posts, respect_policy=False)['deleted_count'] == 1


def test_locked_file_retry_does_not_change_published_status(media, monkeypatch):
    worker, clip, posts = media
    original = Path.unlink
    def locked(path, *args, **kwargs):
        if path == clip:
            raise PermissionError('in use')
        return original(path, *args, **kwargs)
    with monkeypatch.context() as scope:
        scope.setattr(Path, 'unlink', locked)
        assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    assert posts[0]['status'] == 'published'
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 1


def test_active_or_unreadable_content_queue_preserves_clip(media):
    worker, clip, posts = media
    queue = clip.parent.parent / 'data/content_packages.json'
    write(queue, [{'status': 'running', 'clip_filename': str(clip)}])
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    queue.write_text('{broken', encoding='utf-8')
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    write(queue, [])
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 1


def test_outside_output_and_link_are_preserved(media):
    worker, clip, posts = media
    outside = clip.parent.parent / 'outside.mp4'
    outside.write_bytes(b'keep')
    posts[0]['media_file'] = str(outside)
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    assert outside.exists()
    link = clip.parent / 'link.mp4'
    try:
        link.symlink_to(clip)
    except OSError:
        pytest.skip('Windows does not allow creating test symlinks')
    posts[0]['media_file'] = link.name
    assert worker.cleanup_published_clip_files(posts)['deleted_count'] == 0
    assert clip.exists()


def source_fixture(root):
    for name in ('downloads', 'temp', 'output'):
        (root / name).mkdir(exist_ok=True)
    write(root / 'posts.json', [])
    write(root / 'jobs.json', [{'id': 'job_123_abc', 'status': 'completed'},
                              {'id': 'job_124_def', 'status': 'running'},
                              {'id': 'job_125_ghi', 'status': 'error'}])
    for name in ('job_123_abc.mp4', 'job_124_def.mp4', 'job_125_ghi.mp4', 'unknown.mp4'):
        (root / 'downloads' / name).write_bytes(b'source')
    (root / 'temp/job_123_abc.wav').write_bytes(b'audio')
    (root / 'temp/job_123_abc.json').write_bytes(b'transcript')
    (root / 'output/job_123_abc_clip1.mp4').write_bytes(b'unpublished clip')


def test_completed_sources_only_with_output_and_transcript_retained(tmp_path):
    source_fixture(tmp_path)
    result = retention.cleanup_completed_sources(tmp_path)
    assert result['deleted_count'] == 2
    assert not (tmp_path / 'downloads/job_123_abc.mp4').exists()
    assert (tmp_path / 'downloads/job_124_def.mp4').exists()
    assert (tmp_path / 'downloads/job_125_ghi.mp4').exists()
    assert (tmp_path / 'downloads/unknown.mp4').exists()
    assert (tmp_path / 'temp/job_123_abc.json').exists()
    assert (tmp_path / 'output/job_123_abc_clip1.mp4').exists()
    from src import job_store
    assert job_store.get(tmp_path / 'jobs.json', 'job_123_abc')['source_media_deleted_at']
    assert retention.cleanup_completed_sources(tmp_path)['deleted_count'] == 0

def test_failed_content_package_keeps_source_for_retry_until_terminal(tmp_path):
    source_fixture(tmp_path)
    write(tmp_path / 'data/content_packages.json', [{
        'id': 'pkg-failed',
        'status': 'failed',
        'source_video_path': str(tmp_path / 'downloads/job_123_abc.mp4'),
    }])
    result = retention.cleanup_completed_sources(tmp_path)
    assert result['deleted_count'] < 2
    assert (tmp_path / 'downloads/job_123_abc.mp4').exists()

    write(tmp_path / 'data/content_packages.json', [{
        'id': 'pkg-completed',
        'status': 'completed',
        'source_video_path': str(tmp_path / 'downloads/job_123_abc.mp4'),
    }])
    result = retention.cleanup_completed_sources(tmp_path)
    assert result['deleted_count'] >= 1
    assert not (tmp_path / 'downloads/job_123_abc.mp4').exists()


def test_source_setting_off_and_corrupt_consumer_state(tmp_path):
    source_fixture(tmp_path)
    write(tmp_path / 'config.json', {'storage_retention': {'delete_completed_sources': False}})
    assert retention.cleanup_completed_sources(tmp_path)['deleted_count'] == 0
    write(tmp_path / 'config.json', {'storage_retention': {'delete_completed_sources': True}})
    (tmp_path / 'data').mkdir(exist_ok=True)
    (tmp_path / 'data/content_packages.json').write_text('broken', encoding='utf-8')
    with pytest.raises(ValueError):
        retention.cleanup_completed_sources(tmp_path)
    assert (tmp_path / 'downloads/job_123_abc.mp4').exists()


def test_source_in_active_recovery_preserved(tmp_path):
    source_fixture(tmp_path)
    write(tmp_path / 'data/video_recovery_tasks.json',
          {'p1': {'status': 'running', 'original_filename': 'job_123_abc_clip1.mp4'}})
    assert retention.cleanup_completed_sources(tmp_path)['deleted_count'] == 0
    write(tmp_path / 'data/video_recovery_tasks.json',
          {'p1': {'status': 'ready', 'original_filename': 'job_123_abc_clip1.mp4'}})
    assert retention.cleanup_completed_sources(tmp_path)['deleted_count'] == 2


def test_settings_api_validates_and_preserves_secrets(tmp_path, monkeypatch):
    from web import app as app_module
    monkeypatch.setattr(app_module, 'CONFIG_FILE', tmp_path / 'config.json')
    write(tmp_path / 'config.json', {'llm': {'api_key': 'fixture-secret', 'model': 'fixture'}})
    client = app_module.app.test_client()
    before = (tmp_path / 'config.json').read_bytes()
    response = client.post('/api/settings', json={'storage_retention': {'delete_published_reels': 'false'}})
    assert response.status_code == 400
    assert (tmp_path / 'config.json').read_bytes() == before
    response = client.post('/api/settings', json={'storage_retention': {'delete_published_reels': False}})
    assert response.json['success']
    assert 'fixture-secret' not in response.get_data(as_text=True)
    assert json.loads((tmp_path / 'config.json').read_text())['llm']['api_key'] == 'fixture-secret'
    state = client.get('/api/storage/status').json
    assert state['settings'] == {'delete_published_reels': False, 'delete_completed_sources': True}
    assert state['free_bytes'] > 0
