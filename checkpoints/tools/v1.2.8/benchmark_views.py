"""Compare v127 and v128 views on an anonymized queue in a temporary folder."""
import ast
import copy
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
import time
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'checkpoints/evidence/v1.2.8'
EVIDENCE.mkdir(parents=True, exist_ok=True)

def tagged(name):
    return subprocess.check_output(['git','show','v1.2.7:'+name], cwd=ROOT, text=True, encoding='utf-8')

def measure(call, runs=7):
    values = []
    for _ in range(runs):
        start = time.perf_counter()
        call()
        values.append((time.perf_counter()-start)*1000)
    return {'median_ms':round(statistics.median(values),2), 'min_ms':round(min(values),2),
            'max_ms':round(max(values),2), 'runs':runs}

def main():
    live_path = ROOT.parent / 'Highlight destop test/posts.json'
    raw = json.loads(live_path.read_text(encoding='utf-8'))
    ids = {}
    def anonymous(value):
        value = str(value or '')
        if not value:
            return ''
        ids.setdefault(value, 'fixture-'+str(len(ids)))
        return ids[value]
    stable = {'status','publish_mode','requested_publish_mode','retry_stage','created_at','scheduled_time',
              'website_status','website_video_status','website_media_mode','meta_schedule_status',
              'meta_scheduled_publish_time','output_pipeline','outcome_unknown'}
    def redact(value, key=''):
        if isinstance(value, dict):
            return {k:redact(v,k) for k,v in value.items() if k not in ('token','access_token','page_token','password','secret')}
        if isinstance(value, list):
            return [redact(v,key) for v in value]
        if isinstance(value, str):
            if key in stable:
                return value
            if key.endswith('_id') or key == 'id':
                return anonymous(value)
            if key in ('title','content','first_comment','first_comment_snapshot'):
                text = 'Watch the original recording for complete context and details. '
                return (text * (len(value)//len(text)+1))[:len(value)]
            if key in ('media_file','clip_filename'):
                return 'fixture.mp4' if value else ''
            if key in ('article_url','website_url'):
                return 'https://example.test/article' if value else ''
            return 'x'*len(value)
        return value
    rows = [redact(p) for p in raw]
    source_bytes = live_path.stat().st_size
    del raw
    tokens = [{'id':tid,'name':'Fixture'} for tid in sorted({p['token_id'] for p in rows if p.get('token_id')})]
    pages = list({p['page_id']:{'page_id':p['page_id'],'token_id':p.get('token_id','')} for p in rows if p.get('page_id')}.values())
    # Import with continuous/background work disabled and every HTTP transport blocked.
    with mock.patch('threading.Thread.start'), mock.patch('requests.Session.request', side_effect=AssertionError('HTTP forbidden')):
        from web import app as api
        from web.posts_store import load_posts_file, posts_snapshot
        from web.post_queries import select_posts
        import web.token_audit as audit
        import web.meta_handoff as handoff
        old_audit = {}
        exec(tagged('web/token_audit.py'), old_audit)
        old_handoff = {'__name__':'offline_benchmark'}
        exec(tagged('web/meta_handoff.py'), old_handoff)
        old_source = tagged('web/app.py')
        node = next(n for n in ast.parse(old_source).body if isinstance(n, ast.FunctionDef) and n.name == '_enrich_post_rows')
        old_enrichment = '\n'.join(old_source.splitlines()[node.lineno-1:node.end_lineno])
        with tempfile.TemporaryDirectory(prefix='hvs-v128-view-benchmark-') as temp:
            path = Path(temp) / 'posts.json'
            path.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
            with mock.patch.object(api,'POSTS_FILE',path), mock.patch.object(api,'OUTPUT_DIR',Path(temp)/'output'), \
                 mock.patch.object(api.token_vault,'list_tokens',return_value=tokens), \
                 mock.patch.object(api.page_manager,'list_pages',return_value=pages), \
                 mock.patch.object(api,'load_token_groups',return_value=[]):
                namespace = dict(api.__dict__)
                exec(old_enrichment,namespace)
                def old_request():
                    all_rows = load_posts_file(path)
                    result = select_posts(all_rows)
                    result['items'] = namespace['_enrich_post_rows'](result['items'],audit_posts=all_rows)
                    result['tokens'] = tokens
                    return api.jsonify({'success':True,**result})
                with api.app.test_request_context('/api/posts/list'):
                    with mock.patch.object(audit,'token_audit',old_audit['token_audit']), \
                         mock.patch.object(handoff,'handoff_eligibility',old_handoff['handoff_eligibility']):
                        old_request()  # warm language classifier / lexicon
                        before = measure(old_request)
                    cold_start = time.perf_counter()
                    response = api.api_list_posts()
                    cold_ms = round((time.perf_counter()-cold_start)*1000,2)
                    after = measure(api.api_list_posts)
                    old_read = measure(lambda:load_posts_file(path))
                    new_read = measure(lambda:posts_snapshot(path))
                    assert response.status_code == 200
                    assert posts_snapshot(path) == rows
    report = {'success':True,'queue_rows':len(rows),'source_bytes':source_bytes,
              'anonymized_bytes':path.stat().st_size if path.exists() else len(json.dumps(rows,ensure_ascii=False).encode()),
              'selected_rows':len(select_posts(rows)['items']), 'tokens':len(tokens),'pages':len(pages),
              'v127_list_response':before,'v128_list_response':after,'v128_cold_ms':cold_ms,
              'v127_writable_read':old_read,'v128_revision_read':new_read,
              'list_speedup':round(before['median_ms']/max(after['median_ms'],0.001),2),
              'scope':'Local backend with anonymized current queue; no real media, network or browser paint timing',
              'live_state_modified':False,'live_http':False}
    (EVIDENCE / 'views_benchmark.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__ == '__main__':
    main()
