import copy
import json
from datetime import datetime, timedelta
from unittest import mock

import pytest

from src import output_pipeline as pipeline, content_packages as packages
from src.output_scheduling import schedule_today
from web.posts_store import load_posts_file, save_posts_file

NOW = datetime(2026, 10, 6, 11)


@pytest.fixture
def warehouse(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'ROOT', tmp_path)
    monkeypatch.setattr(packages, 'DATA_ROOT', tmp_path)
    pages = [{'page_id': p, 'page_name': p.upper(), 'token_id': 'wrong-default'} for p in ('a', 'b', 'c')]
    groups = [{'id': 'g', 'name': 'NEW', 'page_ids': ['a', 'b', 'c']}]
    token_groups = [{'id': 'tg', 'page_group_id': 'g', 'page_ids': ['a', 'b', 'c'],
                     'token_ids': ['t', 'u'], 'page_token_bindings': {'a': 't', 'b': 't', 'c': 'u'}}]
    rows = []
    with pipeline._connect(tmp_path) as db:
        for i in range(8):
            assigned = i < 4
            pid = ('a', 'b', 'c', 'a')[i % 4]
            post = {'id': f'p{i}', 'source_sha256': f'sha{i}', 'media_file': f'clip{i}.mp4',
                    'output_pipeline': True, 'status': 'preparing' if i % 2 == 0 else 'draft',
                    'title': 'Original title', 'content': '', 'first_comment': '', 'approval_mode': 'automatic',
                    'created_at': (NOW - timedelta(minutes=i)).isoformat()}
            if assigned:
                post.update(page_id=pid, token_id='u' if pid == 'c' else 't', token_group_id='tg',
                            group_id='g', group_name='NEW', scheduled_time=f'2026-10-07 {11+i}:00:00')
                db.execute('INSERT INTO slots VALUES(?,?,?,?,?)',
                           (pid, post['scheduled_time'], post['source_sha256'], 'daily', json.dumps(post)))
            db.execute('INSERT INTO sources(sha256,path,post_id,assigned,created_at) VALUES(?,?,?,?,?)',
                       (post['source_sha256'], post['media_file'], post['id'], int(assigned), NOW.isoformat()))
            rows.append(post)
    save_posts_file(tmp_path / 'posts.json', rows)
    options = {'scope': 'group', 'group_id': 'g', 'start_time': '11:30', 'interval_minutes': 15}
    def call(body=None, **kwargs):
        return schedule_today(body or options, pages, groups, token_groups, root=tmp_path, now=kwargs.get('now', NOW))
    return tmp_path, pages, groups, token_groups, options, call


def apply_preview(call, options):
    preview = call(options)
    return call({**options, 'revision': preview['revision'], 'apply': True})


def test_preview_then_apply_preserves_content_status_binding_and_claims(warehouse):
    root, _, _, _, options, call = warehouse
    before = copy.deepcopy(load_posts_file(root / 'posts.json'))
    preview = call()
    assert preview['count'] == 4 and preview['date'] == '2026-10-06'
    assert preview['first_time'] == '2026-10-06 11:30:00' and preview['last_time'] == '2026-10-06 12:00:00'
    assert load_posts_file(root / 'posts.json') == before
    applied = call({**options, 'revision': preview['revision'], 'apply': True})
    assert applied['count'] == 4 and applied['automatic'] == 4
    after = load_posts_file(root / 'posts.json')
    for old, new in zip(before, after):
        for field in ('id', 'source_sha256', 'status', 'title', 'content', 'first_comment', 'approval_mode'):
            assert new[field] == old[field]
        assert not new.get('draft_edited_at') and not new.get('content_frozen_at')
    with pipeline._connect(root) as db:
        assert db.execute('SELECT count(*) FROM sources').fetchone()[0] == 8
        assert db.execute('SELECT count(*) FROM slots').fetchone()[0] == 4
        assert all(json.loads(s['assignment'])['token_id'] != 'wrong-default' for s in db.execute('SELECT * FROM slots'))
    # A repeated apply cannot create a duplicate or override the new revision.
    with pytest.raises(ValueError, match='xem trước lại'):
        call({**options, 'revision': preview['revision'], 'apply': True})
    assert load_posts_file(root / 'posts.json') == after


def test_stock_uses_existing_claims_balances_pages_and_respects_other_token_schedules(warehouse):
    root, _, _, _, options, call = warehouse
    posts = load_posts_file(root / 'posts.json')
    posts.append({'id': 'remote', 'status': 'meta_scheduled', 'page_id': 'a', 'token_id': 't',
                  'scheduled_time': '2026-10-06 11:35:00', 'token_gap_seconds': 900, 'meta_video_id': '123'})
    save_posts_file(root / 'posts.json', posts)
    result = apply_preview(call, {**options, 'scope': 'stock', 'stock_count': 4})
    assert result['count'] == 4
    assert {p['page_id'] for p in result['items']} == {'a', 'b', 'c'}
    assert all(p['scheduled_time'] >= '2026-10-06 11:50:00' for p in result['items'] if p['token_id'] == 't')
    after = load_posts_file(root / 'posts.json')
    assert len(after) == 9 and after[-1] == posts[-1]
    assert sum(bool(p.get('page_id')) for p in after) == 9


@pytest.mark.parametrize('field,value', [('meta_upload_video_id', '123'), ('outcome_unknown', True),
                                        ('publish_started_at', '2026-10-06 10:00:00'), ('content_frozen_at', 'approved')])
def test_selected_remote_or_frozen_row_is_untouched(warehouse, field, value):
    root, _, _, _, options, call = warehouse
    posts = load_posts_file(root / 'posts.json')
    posts[0][field] = value
    save_posts_file(root / 'posts.json', posts)
    result = apply_preview(call, {**options, 'scope': 'selected', 'post_ids': ['p0', 'p1']})
    assert result['count'] == 1 and len(result['skipped']) == 1
    assert load_posts_file(root / 'posts.json')[0] == posts[0]


def test_midnight_overflow_keeps_original_claim_and_schedule(warehouse):
    root, _, _, _, options, call = warehouse
    result = apply_preview(call, {**options, 'start_time': '23:50'})
    assert result['count'] == 2 and len(result['overflow']) == 2
    assert all(p['scheduled_time'].startswith('2026-10-06') for p in result['items'])
    after = load_posts_file(root / 'posts.json')
    skipped = {p['post_id'] for p in result['overflow']}
    assert all(p['scheduled_time'].startswith('2026-10-07') for p in after if p['id'] in skipped)
    with pipeline._connect(root) as db:
        assert db.execute('SELECT count(*) FROM slots').fetchone()[0] == 4


def test_overflow_old_today_slot_is_reserved_when_replanning(warehouse):
    root, _, _, _, options, call = warehouse
    posts = load_posts_file(root / 'posts.json')
    posts[3]['scheduled_time'] = '2026-10-06 23:50:00'
    save_posts_file(root / 'posts.json', posts)
    with pipeline._connect(root) as db:
        db.execute('UPDATE slots SET scheduled_time=? WHERE sha256=?', (posts[3]['scheduled_time'], 'sha3'))
    # Force the row with the old reservation to the back of a selected batch.
    result = apply_preview(call, {**options, 'scope': 'selected', 'post_ids': ['p0', 'p1', 'p2', 'p3'], 'start_time': '23:50'})
    after = load_posts_file(root / 'posts.json')
    assert after[3]['scheduled_time'] == '2026-10-06 23:50:00'
    assert 'p3' in {r['post_id'] for r in result['overflow']}
    assert not any(r['page_id'] == 'a' and r['scheduled_time'] == after[3]['scheduled_time'] for r in result['items'])


def test_preview_must_be_repeated_if_publish_claim_binding_or_schedule_changes(warehouse):
    root, _, _, tokens, options, call = warehouse
    preview = call()
    tokens[0]['page_token_bindings']['a'] = 'u'
    with pytest.raises(ValueError, match='xem trước lại'):
        call({**options, 'revision': preview['revision'], 'apply': True})
    assert load_posts_file(root / 'posts.json')[0]['scheduled_time'].startswith('2026-10-07')


def test_json_write_failure_replays_committed_schedule_without_another_claim(warehouse, monkeypatch):
    from src import output_scheduling as scheduling
    root, _, _, _, options, call = warehouse
    preview = call()
    with mock.patch.object(scheduling, 'save_posts_file', side_effect=OSError('simulated crash')):
        with pytest.raises(OSError):
            call({**options, 'revision': preview['revision'], 'apply': True})
    call()  # Recover SQLite intent before previewing again.
    after = load_posts_file(root / 'posts.json')
    assert all(p['scheduled_time'].startswith('2026-10-06') for p in after[:4])
    with pipeline._connect(root) as db:
        assert db.execute('SELECT count(*) FROM sources').fetchone()[0] == 8
        assert db.execute('SELECT count(*) FROM sources WHERE interface_written=0 AND intake!=""').fetchone()[0] == 0


@pytest.mark.parametrize('change', [{'start_time': '11:10'}, {'start_time': '2026-10-07T12:00'},
                                  {'interval_minutes': True}, {'scope': 'selected', 'post_ids': []},
                                  {'scope': 'stock', 'stock_count': 0}, {'apply': 'yes'}])
def test_invalid_options_do_not_change_storage(warehouse, change):
    root, _, _, _, options, call = warehouse
    before = (root / 'posts.json').read_bytes()
    with pytest.raises(ValueError):
        call({**options, **change})
    assert (root / 'posts.json').read_bytes() == before


def test_today_schedule_does_not_block_generation_of_pending_first_comment(warehouse):
    root, _, _, _, options, call = warehouse
    result = apply_preview(call, options)
    post = load_posts_file(root / 'posts.json')[0]
    item = {'id': 'package', 'post_ids': [post['id']], 'status': 'ready', 'website_status': 'ready',
            'website_video_status': 'verified', 'article_url': 'https://cms.test/blog/original',
            'result': packages.fallback_package('Original recording', article_url='https://cms.test/blog/original')}
    with mock.patch.object(packages, 'datetime', wraps=datetime) as clock:
        clock.now.return_value = NOW
        packages._apply_to_posts(item)
    after = load_posts_file(root / 'posts.json')[0]
    assert after['status'] == 'scheduled' and after['article_url'] in after['first_comment']
    assert after['scheduled_time'] == result['items'][0]['scheduled_time']


def test_package_finished_next_day_waits_for_reschedule(warehouse):
    root, _, _, _, options, call = warehouse
    apply_preview(call, options)
    post = load_posts_file(root / 'posts.json')[0]
    item = {'id': 'package', 'post_ids': [post['id']], 'status': 'ready', 'website_status': 'ready',
            'website_video_status': 'verified', 'article_url': 'https://cms.test/blog/original',
            'result': packages.fallback_package('Original recording', article_url='https://cms.test/blog/original')}
    with mock.patch.object(packages, 'datetime', wraps=datetime) as clock:
        clock.now.return_value = NOW + timedelta(days=1)
        packages._apply_to_posts(item)
    after = load_posts_file(root / 'posts.json')[0]
    assert after['status'] == 'draft' and 'hẹn lại' in after['schedule_error']
    assert not after.get('content_frozen_at')


def test_publisher_does_not_dispatch_today_only_queue_after_midnight(tmp_path):
    from web import scheduled_publisher as worker
    path = tmp_path / 'posts.json'
    save_posts_file(path, [{'id': 'expired', 'output_pipeline': True, 'status': 'scheduled',
        'page_id': 'a', 'token_id': 't', 'schedule_day': '2026-10-06',
        'scheduled_time': '2026-10-06 23:30:00', 'requested_publish_mode': 'meta_scheduled',
        'content_frozen_at': 'approved', 'approved_at': 'approved', 'first_comment_snapshot': 'original'}])
    with mock.patch.object(worker, 'POSTS_FILE', path), \
         mock.patch('src.publisher.first_comment_queue.process_due_first_comments', return_value={}), \
         mock.patch('src.publisher.token_vault.TokenVault'), mock.patch('src.publisher.page_manager.PageManager'), \
         mock.patch('web.meta_handoff.queue_handoffs') as handoff, \
         mock.patch.object(worker, '_publish_claimed_post') as publish:
        result = worker.process_scheduled_posts_once(now=NOW+timedelta(days=1))
    after = load_posts_file(path)[0]
    assert result['claimed'] == 0 and after['status'] == 'draft'
    assert 'hẹn lại' in after['schedule_error'] and not after.get('content_frozen_at')
    handoff.assert_not_called()
    publish.assert_not_called()


def test_api_previews_and_applies_only_local_schedule(warehouse, monkeypatch):
    from web import app as api
    root, pages, groups, tokens, options, _ = warehouse
    monkeypatch.setattr(api.page_manager, 'list_pages', lambda: pages)
    monkeypatch.setattr(api.page_manager, 'list_groups', lambda: groups)
    monkeypatch.setattr(api, 'load_token_groups', lambda: tokens)
    with mock.patch('src.output_scheduling.datetime', wraps=datetime) as clock, \
            mock.patch.object(api.reel_poster, 'publish_reel') as publish:
        clock.now.return_value = NOW
        client = api.app.test_client()
        preview = client.post('/api/posts/schedule-today', json=options).get_json()
        assert preview['success'] and preview['count'] == 4
        response = client.post('/api/posts/schedule-today', json={**options, 'apply': True, 'revision': preview['revision']})
        assert response.status_code == 200 and response.get_json()['applied']
        assert client.post('/api/posts/schedule-today', json=[]).status_code == 409
        publish.assert_not_called()


def test_group_today_prevents_daily_refilling_tomorrow_and_resumes_next_day(warehouse):
    root, pages, groups, tokens, options, call = warehouse
    pipeline.save_plan({'id': 'group:g', 'daily': True, 'group_ids': ['g'], 'slots': ['19:30'],
                        'start_date': '2026-10-06'}, pages, groups, root=root)
    apply_preview(call, options)
    plans = pipeline.settings(root)['plans']
    assert list(pipeline._assignment_candidates(plans, pages, groups, NOW, tokens)) == []
    assert len(list(pipeline._assignment_candidates(plans, pages, groups, NOW+timedelta(days=1), tokens))) == 6


def test_selected_today_retains_normal_daily_intake(warehouse):
    root, pages, groups, tokens, options, call = warehouse
    pipeline.save_plan({'id': 'group:g', 'daily': True, 'group_ids': ['g'], 'slots': ['19:30'],
                        'start_date': '2026-10-06'}, pages, groups, root=root)
    apply_preview(call, {**options, 'scope': 'selected', 'post_ids': ['p0']})
    assert len(list(pipeline._assignment_candidates(pipeline.settings(root)['plans'], pages, groups, NOW, tokens))) == 6


def test_later_explicit_draft_date_edit_replaces_today_boundary(warehouse):
    root, pages, _, _, options, call = warehouse
    apply_preview(call, options)
    row = pipeline.review_draft('p0', {'scheduled_time': '2026-10-07 11:30:00'}, pages, root=root, now=NOW)
    assert row['schedule_day'] == '2026-10-07' and row['schedule_origin'] == 'manual'
    with pipeline._connect(root) as db:
        assignment = json.loads(db.execute('SELECT assignment FROM slots WHERE sha256="sha0"').fetchone()[0])
        assert assignment['schedule_day'] == '2026-10-07'


def test_pipeline_recovers_today_override_after_json_write_failure(warehouse):
    from src import output_scheduling as scheduling
    root, pages, groups, tokens, options, call = warehouse
    pipeline.save_plan({'id': 'group:g', 'daily': True, 'group_ids': ['g'], 'slots': ['19:30'],
                        'start_date': '2026-10-06'}, pages, groups, root=root)
    preview = call(options)
    with mock.patch.object(scheduling, 'save_posts_file', side_effect=OSError('simulated crash')):
        with pytest.raises(OSError):
            call({**options, 'revision': preview['revision'], 'apply': True})
    assert not pipeline.settings(root)['plans'][0].get('allocation_override_date')
    result = pipeline.process_once(root=root, pages=pages, groups=groups, token_groups=tokens, now=NOW)
    after = load_posts_file(root / 'posts.json')
    assert result['assigned'] == 0
    assert all(p['scheduled_time'].startswith('2026-10-06') for p in after[:4])
    assert all(not p.get('page_id') for p in after[4:])
