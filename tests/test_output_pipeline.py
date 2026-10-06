import copy
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest

from src import output_pipeline as pipeline
from src import content_packages as packages
from web.posts_store import load_posts_file, save_posts_file


@pytest.fixture
def intake(tmp_path, monkeypatch):
    (tmp_path / 'output').mkdir()
    (tmp_path / 'jobs.json').write_text('[]')
    (tmp_path / 'posts.json').write_text('[]')
    monkeypatch.setattr(pipeline, 'ROOT', tmp_path)
    monkeypatch.setattr(packages, 'DATA_ROOT', tmp_path)
    monkeypatch.setattr(packages, 'QUEUE_FILE', tmp_path / 'data' / 'content_packages.json')
    monkeypatch.setattr(pipeline, '_OBSERVED', {})
    clock = [100.0]
    monkeypatch.setattr(pipeline.time, 'monotonic', lambda: clock[0])
    pipeline.save_settings({'stable_seconds': 2, 'min_free_gb': 0}, tmp_path)
    return tmp_path, clock


def scan(intake, **kwargs):
    root, clock = intake
    pipeline.process_once(root=root, probe=lambda p: True, **kwargs)
    clock[0] += 3
    return pipeline.process_once(root=root, probe=lambda p: True, **kwargs)


def test_partial_growing_and_invalid_mp4_never_enters_queue(intake):
    root, clock = intake
    (root / 'output' / '.clip.rendering.x.mp4').write_bytes(b'partial')
    path = root / 'output' / 'clip.mp4'
    path.write_bytes(b'one')
    assert pipeline.process_once(root=root, probe=lambda p: True)['imported'] == 0
    clock[0] += 3
    path.write_bytes(b'one-two')
    assert pipeline.process_once(root=root, probe=lambda p: True)['imported'] == 0
    clock[0] += 3
    assert pipeline.process_once(root=root, probe=lambda p: False)['imported'] == 0
    assert packages.list_packages() == []
    assert pipeline.process_once(root=root, probe=lambda p: True)['imported'] == 1


def test_idle_large_intake_does_not_rewrite_package_or_posts_queues(intake, monkeypatch):
    from unittest import mock
    root, _clock = intake
    posts = []
    items = []
    for index in range(800):
        pid, package_id, sha, clip = f'post{index}', f'package{index}', f'sha{index}', f'clip{index}.mp4'
        posts.append({'id': pid, 'output_pipeline': True, 'status': 'preparing', 'title': 'Ready warehouse video',
                      'media_file': clip, 'source_sha256': sha, 'content_package_id': package_id,
                      'content_package_status': 'queued'})
        items.append({'id': package_id, 'clip_filename': clip, 'source_sha256': sha,
                      'status': 'queued', 'post_ids': [pid]})
    save_posts_file(root / 'posts.json', posts)
    packages._write(packages.QUEUE_FILE, items)
    with mock.patch.object(packages, 'ensure_content_package', side_effect=AssertionError('idle source was reenqueued')), \
         mock.patch.object(packages, '_write', side_effect=AssertionError('idle queue was rewritten')), \
         mock.patch.object(pipeline, 'save_posts_file', side_effect=AssertionError('idle posts were rewritten')):
        result = pipeline.process_once(root=root, probe=lambda _: True)
    assert result['imported'] == 0 and result['assigned'] == 0


def test_default_manual_group_claims_correct_token_then_approves_meta_mode(intake, monkeypatch):
    from unittest import mock
    from web import app as api
    root, _clock = intake
    (root / 'output' / 'clip.mp4').write_bytes(b'video ready for selected group')
    pages = [{'page_id': 'a', 'page_name': 'Selected Page', 'token_id': 'other-default'}]
    groups = [{'id': 'chosen', 'name': 'Selected Group', 'page_ids': ['a']}]
    token_groups = [{'id': 'tg', 'page_group_id': 'chosen', 'token_ids': ['group-token'],
                     'page_ids': ['a'], 'page_token_bindings': {'a': 'group-token'}}]
    now = datetime(2026, 10, 5, 8)
    pipeline.save_plan({'daily': True, 'group_ids': ['chosen'], 'slots': ['19:30'],
                        'publish_mode': 'meta_scheduled'}, pages, groups, root)
    assert scan(intake, pages=pages, groups=groups, token_groups=token_groups, now=now)['assigned'] == 1
    post = load_posts_file(root / 'posts.json')[0]
    assert post['status'] == 'preparing' and post['group_id'] == 'chosen'
    assert post['token_id'] == 'group-token' and post['token_group_id'] == 'tg'
    packages._apply_to_posts(ready_item(post))
    assert load_posts_file(root / 'posts.json')[0]['status'] == 'draft'
    # Saving a Meta selection does not dispatch a remote write.
    saved = pipeline.review_draft(post['id'], {'publish_mode': 'meta_scheduled'}, pages, root=root, now=now)
    assert saved['requested_publish_mode'] == 'meta_scheduled' and saved['status'] == 'draft'
    monkeypatch.setattr(api.page_manager, 'list_pages', lambda: pages)
    monkeypatch.setattr(pipeline, 'datetime', mock.Mock(wraps=datetime))
    pipeline.datetime.now.return_value = now
    with mock.patch.object(api.reel_poster, 'publish_reel') as publish:
        response = api.app.test_client().post('/api/posts/review-batch', json={'post_ids': [post['id']]})
    assert response.status_code == 200 and response.get_json()['approved'] == 1
    approved = load_posts_file(root / 'posts.json')[0]
    assert approved['status'] == 'scheduled' and approved['token_id'] == 'group-token'
    assert approved['requested_publish_mode'] == 'meta_scheduled' and approved['first_comment_snapshot']
    publish.assert_not_called()


def test_hash_dedupe_survives_restart_rename_deletion_reimport(intake):
    root, clock = intake
    path = root / 'output' / 'original.mp4'
    path.write_bytes(b'identical-video')
    assert scan(intake)['imported'] == 1
    posts = load_posts_file(root / 'posts.json')
    assert posts[0]['status'] == 'preparing'
    assert len(packages.list_packages()) == 1
    assert packages.list_packages()[0]['require_video_upload'] is False
    assert posts[0]['website_media_mode'] == 'youtube'
    sha = posts[0]['source_sha256']
    path.rename(root / 'output' / 'renamed.mp4')
    pipeline._OBSERVED.clear()
    assert scan(intake)['imported'] == 0
    assert len(load_posts_file(root / 'posts.json')) == 1
    posts = load_posts_file(root / 'posts.json')
    posts[0].update(status='published', post_fb_id='meta-123')
    save_posts_file(root / 'posts.json', posts)
    assert pipeline.record_receipt(sha, posts, root)
    (root / 'output' / 'renamed.mp4').unlink()
    (root / 'output' / 'reimport.mp4').write_bytes(b'identical-video')
    pipeline._OBSERVED.clear()
    assert scan(intake)['imported'] == 0
    assert len(packages.list_packages()) == 1
    with pipeline._connect(root) as db:
        row = db.execute('SELECT * FROM sources').fetchone()
        assert row['published'] == 1 and 'meta-123' in row['receipt']


def test_daily_scope_reserves_before_content_then_continues_next_day(intake):
    root, clock = intake
    pages = [{'page_id': 'a', 'token_id': 't'}, {'page_id': 'b', 'token_id': 't'}, {'page_id': 'outside', 'token_id': 'u'}]
    groups = [{'id': 'g', 'name': 'Group', 'page_ids': ['a', 'b']}]
    now = datetime(2026, 10, 5, 8)
    pipeline.save_plan({'daily': True, 'group_ids': ['g'], 'slots': ['09:00'], 'start_date': '2026-10-05',
                        'approval_mode': 'automatic'}, pages, groups, root)
    for index in range(6):
        (root / 'output' / f'clip{index}.mp4').write_bytes(f'video-{index}'.encode())
    result = scan(intake, pages=pages, groups=groups, now=now)
    assert result['assigned'] == 4
    posts = load_posts_file(root / 'posts.json')
    assigned = [p for p in posts if p.get('page_id')]
    assert {p['page_id'] for p in assigned} == {'a', 'b'}
    assert all(p['status'] == 'preparing' for p in assigned)
    assert len({p['source_sha256'] for p in assigned}) == 4
    assert pipeline.process_once(root=root, pages=pages, groups=groups, now=now)['assigned'] == 0
    assert pipeline.process_once(root=root, pages=pages, groups=groups, now=now + timedelta(days=1))['assigned'] == 2
    assert len(packages.list_packages()) == 6
    assert len({p['scheduled_time'] + p['page_id'] for p in load_posts_file(root / 'posts.json')}) == 6


def test_overlap_plans_and_concurrent_scans_cannot_duplicate_source_or_slot(intake):
    root, clock = intake
    pages = [{'page_id': 'a', 'token_id': 't'}]
    for plan_id in ('one', 'two'):
        pipeline.save_plan({'id': plan_id, 'daily': True, 'page_ids': ['a'], 'slots': ['09:00'],
                            'start_date': '2026-10-05'}, pages, [], root)
    for index in range(4):
        (root / 'output' / f'clip{index}.mp4').write_bytes(str(index).encode())
    scan(intake, pages=pages, now=datetime(2026, 10, 5, 8))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: pipeline.process_once(root=root, pages=pages, now=datetime(2026, 10, 5, 8)), range(2)))
    assert all(result['assigned'] == 0 for result in results)
    posts = load_posts_file(root / 'posts.json')
    assert len(posts) == 4 and len(packages.list_packages()) == 4
    assert sum(bool(p.get('page_id')) for p in posts) == 2


def test_claim_crash_repairs_json_without_reimport(intake, monkeypatch):
    root, clock = intake
    (root / 'output' / 'clip.mp4').write_bytes(b'video')
    pipeline.process_once(root=root, probe=lambda p: True)
    clock[0] += 3
    real_save = pipeline.save_posts_file
    monkeypatch.setattr(pipeline, 'save_posts_file', lambda *a: (_ for _ in ()).throw(OSError('interrupted write')))
    with pytest.raises(OSError):
        pipeline.process_once(root=root, probe=lambda p: True)
    monkeypatch.setattr(pipeline, 'save_posts_file', real_save)
    pipeline._OBSERVED.clear()
    scan(intake)
    assert len(load_posts_file(root / 'posts.json')) == 1
    assert len(packages.list_packages()) == 1


def ready_item(post):
    result = packages.fallback_package('The cycling finish', article_url='https://cms.test/blog/finish')
    return {'id': 'content-ready', 'post_ids': [post['id']], 'result': result, 'status': 'ready',
            'website_status': 'ready', 'article_url': 'https://cms.test/blog/finish',
            'website_video_status': 'verified', 'website_video_url': 'https://cms.test/videos/finish.mp4'}


def test_daily_plan_promotes_attached_text_only_cache_without_changing_package_id(intake):
    root, _clock = intake
    (root / 'output' / 'clip.mp4').write_bytes(b'video')
    scan(intake)
    post = load_posts_file(root / 'posts.json')[0]
    item = packages.get_package(post['content_package_id'])
    item.update(create_website_article=False, status='ready', website_status='not_configured',
                website_video_status='youtube_embed_verified', error='stale', website_error='stale')
    packages._write(packages.QUEUE_FILE, [item])
    pipeline.save_plan({'daily': True, 'page_ids': ['a'], 'slots': ['19:30']}, [{'page_id': 'a', 'token_id': 't'}], [], root)
    pipeline.process_once(root=root, pages=[{'page_id': 'a', 'token_id': 't'}], now=datetime(2026, 10, 6, 8))
    saved = packages.get_package(item['id'])
    assert saved['create_website_article'] and saved['status'] == 'queued'
    assert saved['website_status'] == 'pending_generation' and not saved['error'] and not saved['website_error']
    assert len(packages.list_packages()) == 1
    post = load_posts_file(root / 'posts.json')[0]
    assert post['page_id'] == 'a' and post['content_package_id'] == item['id'] and post['status'] == 'preparing'


def test_invalid_cached_package_is_quarantined_and_valid_package_still_applies(intake):
    root, _clock = intake
    for name in ('a', 'b'):
        (root / 'output' / (name + '.mp4')).write_bytes(name.encode())
    scan(intake)
    posts = load_posts_file(root / 'posts.json')
    items = []
    for post in posts:
        item = packages.get_package(post['content_package_id'])
        item.update(ready_item(post), id=post['content_package_id'])
        items.append(item)
    items[0]['result']['article_html'] = '<p>Đây là nội dung tiếng Việt không được đăng.</p>'
    packages._write(packages.QUEUE_FILE, items)
    result = pipeline.process_once(root=root, probe=lambda p: True)
    saved = load_posts_file(root / 'posts.json')
    assert result['imported'] == 0
    assert saved[0]['content_package_status'] == 'failed' and saved[0]['website_status'] == 'failed'
    assert 'article_html' in saved[0]['content_package_error']
    assert packages.get_package(items[0]['id'])['article_url'] == items[0]['article_url']
    assert packages.get_package(items[0]['id'])['status'] == 'failed'
    assert saved[1]['status'] == 'draft' and saved[1]['content_package_status'] == 'ready'
    pipeline.process_once(root=root, probe=lambda p: True)
    assert load_posts_file(root / 'posts.json')[1]['status'] == 'draft'


@pytest.mark.parametrize('mode,expected', [('manual', 'draft'), ('automatic', 'scheduled')])
def test_manual_draft_and_explicit_auto_transition_use_same_fallback(intake, mode, expected):
    root, clock = intake
    (root / 'output' / 'clip.mp4').write_bytes(b'video')
    scan(intake)
    posts = load_posts_file(root / 'posts.json')
    posts[0].update(approval_mode=mode, page_id='a', scheduled_time='2026-10-05 19:00:00')
    save_posts_file(root / 'posts.json', posts)
    packages._apply_to_posts(ready_item(posts[0]))
    row = load_posts_file(root / 'posts.json')[0]
    assert row['status'] == expected
    assert row['article_url'] in row['first_comment'] and row['content']
    assert bool(row.get('content_frozen_at')) == (mode == 'automatic')


def test_failed_website_and_late_llm_cannot_make_false_ready_or_replace_frozen_content(intake):
    root, clock = intake
    (root / 'output' / 'clip.mp4').write_bytes(b'video')
    scan(intake)
    post = load_posts_file(root / 'posts.json')[0]
    item = ready_item(post)
    item['website_video_status'] = 'failed'
    packages._apply_to_posts(item)
    assert load_posts_file(root / 'posts.json')[0]['status'] == 'preparing'
    item['website_video_status'] = 'verified'
    packages._apply_to_posts(item)
    posts = load_posts_file(root / 'posts.json')
    posts[0].update(content_frozen_at='approved', status='scheduled')
    save_posts_file(root / 'posts.json', posts)
    approved = copy.deepcopy(posts[0])
    item['result'] = packages.fallback_package('Another event', article_url='https://cms.test/blog/other')
    packages._apply_to_posts(item)
    assert load_posts_file(root / 'posts.json')[0] == approved


def test_stale_worker_revision_cannot_overwrite_approval(intake):
    root, clock = intake
    posts = [{'id': 'p', 'status': 'draft', 'content': 'approved caption'}]
    save_posts_file(root / 'posts.json', posts)
    stale = load_posts_file(root / 'posts.json')
    fresh = load_posts_file(root / 'posts.json')
    fresh[0].update(content_frozen_at='now', status='scheduled', content='user edit')
    save_posts_file(root / 'posts.json', fresh)
    stale[0]['content'] = 'late LLM caption'
    save_posts_file(root / 'posts.json', stale)
    assert load_posts_file(root / 'posts.json')[0]['content'] == 'user edit'


def test_pause_plan_and_backlog_stop_new_allocations_not_content_consumption(intake):
    root, clock = intake
    pages = [{'page_id': 'a', 'token_id': 't'}]
    plan = pipeline.save_plan({'daily': False, 'page_ids': ['a'], 'slots': ['09:00']}, pages, [], root)
    pipeline.save_settings({'max_backlog': 1}, root)
    (root / 'output' / 'clip.mp4').write_bytes(b'video')
    result = scan(intake, pages=pages, now=datetime(2026, 10, 5, 8))
    assert result['paused'] and result['reason'] == 'backlog_limit'
    assert result['assigned'] == 0 and len(packages.list_packages()) == 1


def test_real_probe_rejects_incomplete_container_and_accepts_finished_video(tmp_path):
    if not shutil.which('ffprobe') or not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg/ffprobe unavailable')
    video = tmp_path / 'video.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=64x64:d=0.1',
                    '-c:v', 'libx264', '-y', str(video)], check=True, capture_output=True)
    assert pipeline.valid_mp4(video)
    broken = tmp_path / 'broken.mp4'
    broken.write_bytes(video.read_bytes()[:32])
    assert not pipeline.valid_mp4(broken)


def test_batch_claim_recovers_canonical_post_id_after_interrupted_save(intake):
    root, _clock = intake
    (root / "output" / "clip.mp4").write_bytes(b"video")
    scan(intake)
    original = load_posts_file(root / "posts.json")[0]
    batch = {**original, "id": "temporary-batch-id", "page_id": "a", "token_id": "t",
             "token": "must-not-be-stored", "status": "preparing"}
    pipeline.reserve_batch([batch], root)
    assert batch["id"] == original["id"]
    # Crash before writing batch to posts.json; recover the committed claim.
    pipeline.process_once(root=root, probe=lambda _path: True)
    recovered = load_posts_file(root / "posts.json")
    assert len(recovered) == 1 and recovered[0]["id"] == original["id"]
    assert recovered[0]["page_id"] == "a"
    assert "token" not in recovered[0]
    with pipeline._connect(root) as db:
        snapshot = json.loads(db.execute("SELECT intake FROM sources").fetchone()[0])
    assert snapshot["id"] == original["id"] and "token" not in snapshot


def test_finish_batch_only_acknowledges_posts_actually_saved(intake):
    root, _clock = intake
    first = {"id": "first", "source_sha256": "a" * 64, "media_file": "a.mp4", "status": "scheduled"}
    missing = {"id": "missing", "source_sha256": "b" * 64, "media_file": "b.mp4", "status": "scheduled"}
    pipeline.reserve_batch([first, missing], root)
    save_posts_file(root / "posts.json", [first])
    pipeline.finish_batch(root)
    with pipeline._connect(root) as db:
        written = {row["post_id"]: row["interface_written"] for row in db.execute("SELECT * FROM sources")}
    assert written == {"first": 1, "missing": 0}


def test_daily_plan_waits_for_inventory_and_resumes_only_for_selected_groups(intake):
    root, _clock = intake
    pages = [{"page_id": "a", "token_id": "t"}, {"page_id": "outside", "token_id": "u"}]
    groups = [{"id": "chosen", "page_ids": ["a"]}, {"id": "unchecked", "page_ids": ["outside"]}]
    now = datetime(2026, 10, 5, 8)
    plan = pipeline.save_plan({"daily": True, "group_ids": ["chosen"], "slots": ["11:30"],
                              "approval_mode": "automatic", "publish_mode": "meta_scheduled"}, pages, groups, root)
    assert scan(intake, pages=pages, groups=groups, now=now)["assigned"] == 0
    (root / "output" / "clip.mp4").write_bytes(b"new inventory")
    assert scan(intake, pages=pages, groups=groups, now=now)["assigned"] == 1
    post = load_posts_file(root / "posts.json")[0]
    assert post["page_id"] == "a" and post["requested_publish_mode"] == "meta_scheduled"
    pipeline.save_plan({**plan, "daily": False, "enabled": False}, pages, groups, root)
    (root / "output" / "another.mp4").write_bytes(b"next inventory")
    assert scan(intake, pages=pages, groups=groups, now=now)["assigned"] == 0
    assert len([p for p in load_posts_file(root / "posts.json") if p.get("page_id")]) == 1


def test_legacy_ready_cms_package_reuses_recorded_original_youtube_embed(intake):
    root, _clock = intake
    (root / "output" / "clip.mp4").write_bytes(b"existing warehouse clip")
    item = packages.enqueue_content_package(clip_filename="clip.mp4", title="Cycling finish", create_website_article=True)
    url = "https://cms.test/blog/existing"
    item.update({"status": "ready", "website_status": "ready", "embed_status": "ready", "article_url": url,
                 "youtube_id": "abcdefghijk", "video_url": "https://youtu.be/abcdefghijk",
                 "result": packages.fallback_package("Cycling finish", article_url=url)})
    packages._write(packages.QUEUE_FILE, [item])
    scan(intake)
    assert len(packages.list_packages()) == 1
    post = load_posts_file(root / "posts.json")[0]
    assert post["status"] == "draft" and post["article_url"] == url
    assert post["website_video_status"] == "youtube_embed_verified"


def test_save_draft_persists_page_and_time_without_approving_and_survives_restart(intake):
    root, _clock = intake
    (root / 'output' / 'clip.mp4').write_bytes(b'draft')
    scan(intake)
    post = load_posts_file(root / 'posts.json')[0]
    ready = {**packages.list_packages()[0], **ready_item(post)}
    packages._write(packages.QUEUE_FILE, [ready])
    packages._apply_to_posts(ready)
    pages = [{'page_id': 'a', 'page_name': 'Alpha', 'token_id': 't'},
             {'page_id': 'b', 'page_name': 'Beta', 'token_id': 'u'}]
    now = datetime(2026, 10, 5, 8)
    saved = pipeline.review_draft(post['id'], {'page_id': 'b', 'scheduled_time': '2026-10-06T19:30',
        'content': 'User caption'}, pages, root=root, now=now)
    assert saved['status'] == 'draft' and not saved.get('content_frozen_at')
    assert saved['page_id'] == 'b' and saved['token_id'] == 'u'
    assert saved['scheduled_time'] == '2026-10-06 19:30:00'
    pipeline._OBSERVED.clear()
    pipeline.process_once(root=root, pages=pages, now=now, probe=lambda _: True)
    approved = pipeline.review_draft(post['id'], {}, pages, approve=True, root=root, now=now)
    assert approved['status'] == 'scheduled' and approved['content'] == 'User caption'
    assert approved['page_id'] == 'b' and approved['scheduled_time'] == saved['scheduled_time']


@pytest.mark.parametrize('approve', [False, True])
def test_interrupted_draft_save_recovers_full_revision(intake, monkeypatch, approve):
    root, _clock = intake
    (root / 'output' / 'clip.mp4').write_bytes(b'draft revision')
    scan(intake)
    post = load_posts_file(root / 'posts.json')[0]
    packages._apply_to_posts(ready_item(post))
    pages = [{'page_id': 'a', 'token_id': 't'}]
    now = datetime(2026, 10, 5, 8)
    real_save = pipeline.save_posts_file
    monkeypatch.setattr(pipeline, 'save_posts_file', lambda *args: (_ for _ in ()).throw(OSError('interrupted JSON save')))
    with pytest.raises(OSError):
        pipeline.review_draft(post['id'], {'page_id': 'a', 'scheduled_time': '2026-10-06T19:30',
            'content': 'Recovered edit'}, pages, root=root, now=now, approve=approve)
    monkeypatch.setattr(pipeline, 'save_posts_file', real_save)
    pipeline.process_once(root=root, pages=pages, now=now, probe=lambda _: True)
    recovered = load_posts_file(root / 'posts.json')[0]
    assert recovered['page_id'] == 'a' and recovered['content'] == 'Recovered edit'
    assert recovered['scheduled_time'] == '2026-10-06 19:30:00'
    assert recovered['status'] == ('scheduled' if approve else 'draft')
    assert bool(recovered.get('content_frozen_at')) == approve


def test_draft_cannot_take_another_reserved_slot(intake):
    root, _clock = intake
    for name in ('first', 'second'):
        (root / 'output' / f'{name}.mp4').write_bytes(name.encode())
    scan(intake)
    posts = load_posts_file(root / 'posts.json')
    pages = [{'page_id': 'a', 'token_id': 't'}]
    now = datetime(2026, 10, 5, 8)
    changes = {'page_id': 'a', 'scheduled_time': '2026-10-06T19:30'}
    pipeline.review_draft(posts[0]['id'], changes, pages, root=root, now=now)
    with pytest.raises(ValueError, match='khung giờ'):
        pipeline.review_draft(posts[1]['id'], changes, pages, root=root, now=now)
    assert not load_posts_file(root / 'posts.json')[1].get('page_id')


def test_daily_api_saves_selected_group_without_inventory_or_meta_call(intake, monkeypatch):
    from web import app as api
    root, _clock = intake
    pages = [{'page_id': 'a', 'token_id': 't'}]
    groups = [{'id': 'g', 'page_ids': ['a'], 'schedule_config': {'times': ['11:30', '19:30']}}]
    monkeypatch.setattr(api.page_manager, 'list_pages', lambda: pages)
    monkeypatch.setattr(api.page_manager, 'list_groups', lambda: groups)
    monkeypatch.setattr(api, '_ensure_recent_meta_health', lambda: pytest.fail('Daily plan must not upload or require live Meta'))
    response = api.app.test_client().post('/api/distribute/batch', json={
        'group_id': 'g', 'post_daily': True, 'approval_mode': 'automatic', 'publish_mode': 'meta_scheduled',
        'posts_per_page': 2, 'daily_slots': ['09:30', '20:30']})
    assert response.status_code == 200
    plan = response.get_json()['plan']
    assert plan['page_ids'] == ['a'] and plan['slots'] == ['09:30', '20:30']
    assert plan['daily'] and plan['publish_mode'] == 'meta_scheduled'
    assert load_posts_file(root / 'posts.json') == []


def test_producer_exposes_clip_metadata_before_rendering_the_next_clip(intake, monkeypatch):
    from web import app as api
    root, _clock = intake
    monkeypatch.setattr("src.media_validation.probe_video", lambda path: {"duration": 100})
    job = {'id': 'render', 'youtube_url': 'https://youtu.be/abcdefghijk', 'num_clips': 2}
    (root / 'jobs.json').write_text(json.dumps([job]))
    monkeypatch.setattr(api, 'BASE_DIR', root)
    monkeypatch.setattr(api, 'OUTPUT_DIR', root / 'output')
    monkeypatch.setattr(api, 'JOBS_FILE', root / 'jobs.json')
    rendered = []
    status_snapshots = []
    real_update_status = api.update_job_status
    def capture_status(job_id, updates):
        if 'clips' in updates:
            status_snapshots.append(list(updates['clips']))
        return real_update_status(job_id, updates)
    monkeypatch.setattr(api, 'update_job_status', capture_status)
    def render(**kwargs):
        if rendered:
            live_job = json.loads((root / 'jobs.json').read_text(encoding='utf-8'))[0]
            assert live_job['status'] == 'running' and len(live_job['clips']) == 1
            assert scan(intake)['imported'] == 1
            assert packages.list_packages()[0]['source_job_id'] == 'render'
        path = root / 'output' / f"render-{kwargs['clip_idx']}.mp4"
        path.write_bytes(str(kwargs['clip_idx']).encode())
        rendered.append(path)
        return path
    monkeypatch.setattr(api, 'get_pipeline_tools', lambda: (
        lambda *args, **kw: {'video_path': root / 'source.mp4', 'audio_path': root / 'audio.wav', 'title': 'Original recording', 'duration': 100},
        lambda _: [{'text': 'The original recording', 'start': 0}], lambda *a, **kw: [],
        lambda *a, **kw: [{'title': f'Highlight {i}', 'start': i, 'end': i+1} for i in (1,2)], render, lambda _: 'abcdefghijk'))
    api.run_job_pipeline(job)
    final = json.loads((root / 'jobs.json').read_text(encoding='utf-8'))[0]
    assert final['status'] == 'completed' and len(final['clips']) == 2, final
    assert [len(snapshot) for snapshot in status_snapshots] == [1, 2, 2]
    assert scan(intake)['imported'] == 1
    assert len(packages.list_packages()) == 2


def test_assigned_daily_content_is_processed_before_unassigned_library_work(intake, monkeypatch):
    root, _clock = intake
    old = packages.enqueue_content_package(clip_filename='library.mp4', title='Library', mode='no_llm')
    pages = [{'page_id': 'a', 'token_id': 't'}]
    pipeline.save_plan({'daily': True, 'page_ids': ['a'], 'slots': ['11:30']}, pages, [], root)
    (root / 'output' / 'daily.mp4').write_bytes(b'daily video')
    scan(intake, pages=pages, now=datetime(2026,10,5,8))
    post = load_posts_file(root / 'posts.json')[0]
    # Stop at the external CMS boundary; selection and claims use the real worker.
    monkeypatch.setattr(packages, 'resolve_article_url', lambda _: (_ for _ in ()).throw(RuntimeError('fixture CMS unavailable')))
    result = packages.process_content_packages_once()
    assert result['item']['id'] == post['content_package_id']
    assert packages.get_package(old['id'])['status'] == 'queued'


def test_renamed_pending_clip_keeps_original_youtube_url_and_content_claim(intake):
    root, _clock = intake
    original_url = 'https://youtu.be/abcdefghijk'
    (root / 'jobs.json').write_text(json.dumps([{'id':'source', 'youtube_url': original_url,
        'clips':[{'filename':'original.mp4','clip_index':1,'title':'Cycling finish'}]}]))
    clip = root / 'output' / 'original.mp4'
    clip.write_bytes(b'original source identity')
    scan(intake)
    first = packages.list_packages()[0]
    assert first['video_url'] == original_url
    clip.rename(root / 'output' / 'renamed.mp4')
    pipeline._OBSERVED.clear()
    scan(intake)
    item = packages.list_packages()[0]
    assert item['id'] == first['id'] and item['clip_filename'] == 'renamed.mp4'
    assert item['video_url'] == original_url and len(load_posts_file(root / 'posts.json')) == 1
