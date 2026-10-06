"""Isolated scheduling, queue revision and lightweight view regressions."""
import copy
import json
import os
import threading
from unittest import mock

import pytest

from src import output_pipeline as pipeline
from web import posts_store as store
from web.token_audit import token_audit


def group(times=('10:50', '19:30')):
    return {'id': 'g', 'name': 'NEW', 'page_ids': ['p'], 'schedule_config': {
        'times': list(times), 'stagger_minutes': 15}}


def plan(root, g, count=None, **kw):
    return pipeline.save_plan({'id': 'group:g', 'group_ids': ['g'],
        'slots': g['schedule_config']['times'], 'posts_per_day': count or len(g['schedule_config']['times']),
        'daily': True, **kw}, [{'page_id': 'p', 'token_id': 't'}], [g], root)


def test_group_edit_expands_full_daily_plan_without_touching_assigned_posts(tmp_path):
    old = group()
    plan(tmp_path, old, approval_mode='automatic', publish_mode='meta_scheduled')
    ledger = tmp_path / 'posts.json'
    store.save_posts_file(ledger, [{'id': 'existing', 'scheduled_time': '2026-10-06 10:50:00'}])
    before = ledger.read_bytes()
    new = group(('10:50', '15:00', '04:00'))
    updated = pipeline.sync_group_daily_plan(old, new, tmp_path)
    assert updated['slots'] == ['04:00', '10:50', '15:00']
    assert updated['posts_per_day'] == 3 and updated['group_schedule_times'] == updated['slots']
    assert updated['approval_mode'] == 'automatic' and updated['publish_mode'] == 'meta_scheduled'
    assert ledger.read_bytes() == before


def test_group_edit_preserves_intentional_limit_and_disabled_state(tmp_path):
    old = group(('04:00', '10:50', '15:00'))
    plan(tmp_path, old, 1, enabled=False, daily=False)
    new = group(('05:00', '11:00', '16:00', '20:00'))
    updated = pipeline.sync_group_daily_plan(old, new, tmp_path)
    assert updated['posts_per_day'] == 1 and updated['slots'] == ['05:00']
    assert len(updated['group_schedule_times']) == 4
    assert not updated['enabled'] and not updated['daily']


def test_group_edit_does_not_opt_in_or_modify_other_plans(tmp_path):
    old = group()
    assert pipeline.sync_group_daily_plan(old, group(('11:00',)), tmp_path) is None
    assert not (tmp_path / 'config/output_pipeline.json').exists()
    pipeline.save_plan({'id': 'rules', 'group_ids': ['g'], 'daily': True}, [{'page_id': 'p'}], [old], tmp_path)
    before = (tmp_path / 'config/output_pipeline.json').read_bytes()
    assert pipeline.sync_group_daily_plan(old, group(('11:00',)), tmp_path) is None
    assert (tmp_path / 'config/output_pipeline.json').read_bytes() == before


@pytest.mark.parametrize('slots', [[], ['25:00'], ['bad'], '11:30', [None]])
def test_invalid_slots_rejected(slots):
    with pytest.raises(ValueError):
        pipeline.normalize_daily_slots(slots)


def test_distinct_slots_and_count_consistent(tmp_path):
    g = group(('10:50', '04:00', '10:50', '15:00'))
    saved = plan(tmp_path, g, 2)
    assert saved['slots'] == ['04:00', '10:50']
    assert saved['group_schedule_times'] == ['04:00', '10:50', '15:00']


def test_snapshot_reuses_revision_without_writable_baselines(tmp_path):
    path = tmp_path / 'posts.json'
    path.write_text('[{"id":"p","status":"scheduled"}]', encoding='utf-8')
    with mock.patch.object(store, '_remember', side_effect=AssertionError('writable baseline in view')):
        first = store.posts_snapshot(path)
        assert store.posts_snapshot(path) is first
    replacement = tmp_path / 'replace.json'
    replacement.write_text('[{"id":"p","status":"published"}]', encoding='utf-8')
    os.replace(replacement, path)
    assert store.posts_snapshot(path)[0]['status'] == 'published'
    path.write_text('[{"id":"p","status":"failed"}]', encoding='utf-8')
    assert store.posts_snapshot(path)[0]['status'] == 'failed'


def test_snapshot_save_delete_and_backup_recovery(tmp_path):
    path = tmp_path / 'posts.json'
    store.save_posts_file(path, [{'id': 'p', 'status': 'scheduled'}])
    first = store.posts_snapshot(path)
    rows = store.load_posts_file(path)
    rows[0]['status'] = 'published'
    store.save_posts_file(path, rows)
    assert first[0]['status'] == 'scheduled'
    assert store.posts_snapshot(path)[0]['status'] == 'published'
    path.unlink()
    assert store.posts_snapshot(path)[0]['status'] == 'published'
    path.write_text('broken', encoding='utf-8')
    assert store.posts_snapshot(path)[0]['status'] == 'published'
    path.with_name(path.name + '.bak').unlink()
    path.write_text('broken again', encoding='utf-8')
    with pytest.raises(store.PostsStoreError):
        store.posts_snapshot(path)


def test_snapshot_does_not_wait_for_writer_lock(tmp_path):
    path = tmp_path / 'posts.json'
    path.write_text('[{"id":"p"}]', encoding='utf-8')
    completed = threading.Event()
    with store._LOCK:
        thread = threading.Thread(target=lambda: (store.posts_snapshot(path), completed.set()))
        thread.start()
        assert completed.wait(2)
    thread.join(2)


def test_snapshot_atomic_replacements_are_consistent(tmp_path):
    path = tmp_path / 'posts.json'
    store.save_posts_file(path, [{'id': 'p', 'version': 0}])
    errors = []
    def write():
        try:
            for index in range(1, 20):
                rows = store.load_posts_file(path)
                rows[0]['version'] = index
                store.save_posts_file(path, rows)
        except Exception as exc:
            errors.append(str(exc))
    thread = threading.Thread(target=write)
    thread.start()
    for _ in range(30):
        rows = store.posts_snapshot(path)
        assert len(rows) == 1 and 0 <= rows[0]['version'] < 20
    thread.join(5)
    assert not errors and not thread.is_alive()
    assert store.posts_snapshot(path)[0]['version'] == 19


def test_indexed_audit_matches_v127_and_annotates_only_selected():
    # Compare the retained implementation from the immutable release tag.
    import subprocess
    namespace = {}
    exec(subprocess.check_output(['git', 'show', 'v1.2.7:web/token_audit.py'], text=True, encoding='utf-8'), namespace)
    posts = [{'id': str(i), 'token_id': tid, 'page_id': str(i % 3), 'token_group_id': 'tg',
              'token_name': 'Historical', 'status': status} for i, (tid, status) in enumerate([
        ('a','published'), ('b','scheduled'), ('gone','failed'), ('a','meta_handoff'), ('','success')])]
    pages = [{'page_id': str(i), 'token_id': tid, 'page_name': str(i)} for i,tid in enumerate(['a','b','a'])]
    tokens = [{'id':'a','name':'Same','owner_name':'A'}, {'id':'b','name':'Same','owner_name':'B'}]
    groups = [{'id':'tg','token_ids':['b'], 'page_ids':['0','1'], 'page_token_bindings':{'0':'a','1':'b'}}]
    previous = copy.deepcopy(posts)
    expected = namespace['token_audit'](previous, pages, tokens, groups)
    selected = copy.deepcopy(posts[:2])
    assert token_audit(posts, pages, tokens, groups, annotate_posts=selected) == expected
    assert selected == previous[:2]
    assert all('token_stats' not in p for p in posts)


def test_ineligible_handoff_skips_english_but_scheduled_keeps_validation(tmp_path):
    from web.meta_handoff import handoff_eligibility
    with mock.patch('web.meta_handoff.assert_english', side_effect=ValueError('foreign')) as english:
        assert not handoff_eligibility({'status':'published'}, tmp_path)[0]
        assert not handoff_eligibility({'status':'scheduled','meta_video_id':'remote'}, tmp_path)[0]
        english.assert_not_called()
        assert not handoff_eligibility({'status':'scheduled'}, tmp_path)[0]
        assert english.call_count == 1


def test_paged_views_never_mutate_snapshot_or_return_secrets(tmp_path, monkeypatch):
    from web import app as api
    rows = [{'id':str(i),'status':'published','page_id':'p','token_id':'t','token':'secret',
             'content_package':{'article_html':'private-body'}} for i in range(120)]
    path = tmp_path / 'posts.json'
    path.write_text(json.dumps(rows), encoding='utf-8')
    monkeypatch.setattr(api, 'POSTS_FILE', path)
    monkeypatch.setattr(api.token_vault, 'list_tokens', lambda **kw: [{'id':'t','name':'Fixture'}])
    monkeypatch.setattr(api.page_manager, 'list_pages', lambda: [{'page_id':'p','token_id':'t'}])
    monkeypatch.setattr(api.page_manager, 'list_groups', lambda: [])
    monkeypatch.setattr(api, 'load_token_groups', lambda: [])
    monkeypatch.setattr(api, 'load_posts', lambda: pytest.fail('writable read in view'))
    monkeypatch.setattr(pipeline, 'ROOT', tmp_path)
    client = api.app.test_client()
    for url in ['/api/posts/list?page_size=10', '/api/posts/0', '/api/posts/token-audit', '/api/groups/post-summary', '/api/posts/alerts', '/api/pages']:
        response = client.get(url)
        assert response.status_code == 200
        assert 'secret' not in response.get_data(as_text=True) and 'private-body' not in response.get_data(as_text=True)
        assert store.posts_snapshot(path) == rows


def test_group_counts_scan_bound_folders_once_without_jobs(tmp_path, monkeypatch):
    from web import app as api
    folder = tmp_path / 'clips'
    folder.mkdir()
    (folder / 'a.mp4').write_bytes(b'x')
    (folder / 'b.MP4').write_bytes(b'x')
    (folder / 'directory.mp4').mkdir()
    (folder / 'directory.mp4/nested.mp4').write_bytes(b'x')
    groups = [{'id':str(i), 'folder_binding':str(folder)} for i in range(3)] + [{'id':'missing','folder_binding':str(tmp_path / 'absent')}]
    monkeypatch.setattr(api.page_manager, 'list_groups', lambda: groups)
    monkeypatch.setattr(api, 'load_jobs', lambda: pytest.fail('full jobs read during count'))
    with mock.patch.object(api.os, 'scandir', wraps=os.scandir) as scan:
        response = api.app.test_client().get('/api/groups/video-counts')
    assert response.status_code == 200
    assert scan.call_count == 2
    assert [g['file_count'] for g in response.get_json()['groups']] == [2,2,2,None]


def test_group_save_validates_then_syncs_future_plan(tmp_path, monkeypatch):
    from web import app as api
    from src.publisher.page_manager import PageManager
    manager = PageManager(tmp_path)
    old = manager.add_or_update_group('g','NEW',['p'],str(tmp_path),group()['schedule_config'])
    manager.save_pages([{'page_id':'p'}])
    plan(tmp_path, old)
    monkeypatch.setattr(api, 'page_manager', manager)
    monkeypatch.setattr(pipeline, 'ROOT', tmp_path)
    body = {'group_id':'g','name':'NEW','page_ids':['p'],'schedule_config':{
        'times':['10:50','15:00','04:00'], 'stagger_minutes':20}}
    client = api.app.test_client()
    response = client.post('/api/groups', json=body)
    assert response.status_code == 200
    assert response.get_json()['daily_plan']['posts_per_day'] == 3
    assert response.get_json()['group']['schedule_config']['times'] == ['04:00','10:50','15:00']
    before = manager.list_groups()
    body['schedule_config']['times'] = ['invalid']
    assert client.post('/api/groups', json=body).status_code == 400
    assert manager.list_groups() == before


def test_batch_daily_save_uses_three_slots_without_posting(tmp_path, monkeypatch):
    from web import app as api
    g = group(('04:00','10:50','15:00'))
    monkeypatch.setattr(pipeline, 'ROOT', tmp_path)
    monkeypatch.setattr(api.page_manager, 'list_groups', lambda: [g])
    monkeypatch.setattr(api.page_manager, 'list_pages', lambda: [{'page_id':'p'}])
    monkeypatch.setattr(api, '_ensure_recent_meta_health', lambda: pytest.fail('Meta call while saving daily plan'))
    response = api.app.test_client().post('/api/distribute/batch', json={
        'group_id':'g', 'post_daily':True, 'posts_per_page':3, 'daily_slots':['04:00','10:50','15:00']})
    assert response.status_code == 200
    assert response.get_json()['plan']['posts_per_day'] == 3
    assert response.get_json()['plan']['slots'] == ['04:00','10:50','15:00']


def test_editing_name_only_does_not_replace_custom_daily_times(tmp_path):
    g = group(('04:00','10:50','15:00'))
    pipeline.save_plan({'id':'group:g','group_ids':['g'], 'slots':['12:00'], 'posts_per_day':1,
                        'daily':True}, [{'page_id':'p'}], [g], tmp_path)
    before = (tmp_path / 'config/output_pipeline.json').read_bytes()
    renamed = {**g, 'name':'Renamed'}
    assert pipeline.sync_group_daily_plan(g, renamed, tmp_path) is None
    assert (tmp_path / 'config/output_pipeline.json').read_bytes() == before
