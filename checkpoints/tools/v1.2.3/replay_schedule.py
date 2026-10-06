"""Offline replay on a private copy; never write the active installation."""
import collections
import copy
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
import time

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo))
from src.output_scheduling import schedule_today
from web.posts_store import load_posts_file

live = repo.parent / 'Highlight destop test'
shadow = repo.parent / 'support/v1.2.3' / ('replay-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
(shadow/'config').mkdir(parents=True)
(shadow/'data').mkdir()
for name in ('posts.json', 'config/output_pipeline.json'):
    (shadow/name).write_bytes((live/name).read_bytes())
with sqlite3.connect((live/'data/output_ledger.sqlite3').as_uri()+'?mode=ro', uri=True) as source, \
        sqlite3.connect(shadow/'data/output_ledger.sqlite3') as destination:
    source.backup(destination)
def read(name):
    return json.loads((live/name).read_text(encoding='utf-8-sig'))
pages = [{k: p.get(k) for k in ('page_id', 'page_name', 'token_id')} for p in read('pages.json')]
groups = read('page_groups.json')
tokens = read('token_groups.json')
before = copy.deepcopy(load_posts_file(shadow/'posts.json'))
now = datetime.now()
options = {'group_id': 'grp_1791020096_3', 'scope': 'group', 'approval_mode': 'preserve',
           'publish_mode': 'meta_scheduled', 'interval_minutes': 15}
started = time.perf_counter()
preview = schedule_today(options, pages, groups, tokens, root=shadow, now=now)
elapsed = time.perf_counter()-started
options['start_time'] = preview['start_time']
result = schedule_today({**options, 'apply': True, 'revision': preview['revision']}, pages, groups, tokens, root=shadow, now=now)
after = load_posts_file(shadow/'posts.json')
moved = {p['post_id'] for p in result['items']}
before_map = {p['id']:p for p in before}
protected = ('status', 'title', 'content', 'hashtags', 'first_comment', 'article_url', 'content_package_id',
             'content_frozen_at', 'post_fb_id', 'meta_video_id', 'meta_upload_video_id', 'first_comment_status')
assert len(before) == len(after)
for p in after:
    old = before_map[p['id']]
    if p['id'] not in moved:
        assert old == p
    else:
        assert all(old.get(k) == p.get(k) for k in protected)
        assert p['scheduled_time'].startswith(now.date().isoformat())
        assert (p['page_id'],p['token_id'],p.get('token_group_id')) == (old['page_id'],old['token_id'],old.get('token_group_id'))
stock_options = {**options, 'scope':'stock', 'stock_count':20}
stock = schedule_today(stock_options, pages, groups, tokens, root=shadow, now=now)
assert all(p['group_id']==options['group_id'] and p['scheduled_time'].startswith(now.date().isoformat()) for p in stock['items'])
report = {'success':True, 'snapshot_at':now.isoformat(), 'live_runtime_unchanged':True,
          'network_calls':False, 'replay_root':str(shadow), 'group_id':options['group_id'],
          'group_before_dates':dict(collections.Counter(str(p.get('scheduled_time') or '')[:10] for p in before if p['id'] in moved)),
          'reserved_today':result['count'], 'overflow':len(result['overflow']), 'skipped':len(result['skipped']),
          'first_time':result['first_time'], 'last_time':result['last_time'], 'preview_seconds':round(elapsed,4),
          'content_and_status_preserved':True, 'unselected_and_remote_posts_unchanged':True,
          'stock_preview_count':stock['count'], 'stock_preview_last_time':stock['last_time']}
evidence=repo/'checkpoints/evidence/v1.2.3/runtime_scheduling_verify.json'
evidence.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
