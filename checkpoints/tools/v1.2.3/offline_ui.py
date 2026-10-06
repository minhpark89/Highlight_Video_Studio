import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from web.post_queries import select_posts, group_summary
from src import output_pipeline
from src.output_scheduling import schedule_today
from web.posts_store import save_posts_file, load_posts_file

repo = Path(__file__).resolve().parents[3]
evidence = repo / 'checkpoints/evidence/v1.2.3'
evidence.mkdir(exist_ok=True)
html = (repo / 'web/templates/index.html').read_text(encoding='utf-8').replace('{{ app_version }}', '1.2.3')
groups = [{'id':'g', 'name':'Bodycam Group', 'page_ids':['a'], 'schedule_config':{'times':['11:30','19:30']}},
          {'id':'h', 'name':'Travel Group', 'page_ids':['b']}]
pages = [{'page_id':'a','page_name':'Bodycam Page','token_id':'t'}, {'page_id':'b','page_name':'Travel Page','token_id':'u'}]
plans = []
posts = [{'id':'stock'+str(i),'status':'preparing','output_pipeline':True} for i in range(800)]
for i in range(65):
    posts.append({'id':'draft'+str(i), 'status':'draft','output_pipeline':True,'group_id':'g','group_name':'Bodycam Group',
        'page_id':'a','page_name':'Bodycam Page','token_id':'t','token_display_name':'Group Token',
        'title':'Bodycam: the full recording and its context','content':'Watch the complete original recording for full context.',
        'first_comment':'Read https://cms.test/blog/story','article_url':'https://cms.test/blog/story',
        'media_file':'clip.mp4','local_video_url':'/api/clips/play/clip.mp4','website_status':'ready','content_package_status':'ready',
        'website_video_status':'youtube_embed_verified','requested_publish_mode':'meta_scheduled',
        'scheduled_time':'2026-10-07 19:30:00','created_at':f'2026-10-06T08:{i//60:02}:{i%60:02}'})
for i in range(493):
    posts.append({'id':'published'+str(i),'status':'published','title':'Published clip '+str(i),'page_id':'a',
                  'page_name':'Bodycam Page','token_id':'t','post_bucket':'published','media_file':'clip.mp4',
                  'first_comment_status':'posted','scheduled_time':'2026-10-05 19:30:00'})
report = {'errors':[], 'requests':[], 'approvals':[], 'draft_actions':[], 'plans':[], 'checks':[], 'retry_requests':[], 'today_actions':[]}
scratch = tempfile.TemporaryDirectory(prefix='highlight-today-ui-')
schedule_root = Path(scratch.name)
ui_now = datetime(2026, 10, 6, 10)

def route(r):
    req = r.request
    parsed = urlparse(req.url)
    path = parsed.path
    report['requests'].append({'path':path, 'method':req.method, 'query':parsed.query})
    if path == '/':
        return r.fulfill(status=200, content_type='text/html', body=html)
    if path == '/static/group_review.js':
        return r.fulfill(status=200, content_type='text/javascript', body=(repo / 'web/static/group_review.js').read_text(encoding='utf-8'))
    result = {'success':True}
    if path == '/api/groups': result['groups'] = groups
    elif path == '/api/pages': result['pages'] = pages
    elif path == '/api/token-groups': result['groups'] = []
    elif path == '/api/groups/post-summary': result.update(group_summary(posts, groups, plans), server_now=ui_now.isoformat())
    elif path == '/api/posts/schedule-today':
        body = req.post_data_json
        report['today_actions'].append(body)
        for p in posts:
            if p.get('output_pipeline'):
                p.setdefault('source_sha256', 'fixture-sha-' + p['id'])
        save_posts_file(schedule_root/'posts.json', posts)
        with output_pipeline._connect(schedule_root) as db:
            for p in posts:
                if p.get('output_pipeline'):
                    db.execute('INSERT OR IGNORE INTO sources(sha256,path,post_id,assigned,created_at) VALUES(?,?,?,?,?)',
                               (p['source_sha256'], 'fixture.mp4', p['id'], int(bool(p.get('page_id'))), ui_now.isoformat()))
        result.update(schedule_today(body, pages, groups, root=schedule_root, now=ui_now))
        if body.get('apply'):
            posts[:] = load_posts_file(schedule_root/'posts.json')
    elif path == '/api/posts/list':
        query = {k:v[0] for k,v in parse_qs(parsed.query).items()}
        for key in ('page','page_size'):
            if key in query: query[key] = int(query[key])
        result.update(select_posts(posts, **query))
        result['tokens'] = [{'id':'t','name':'Group Token'}]
    elif path == '/api/posts/review-batch':
        ids = req.post_data_json['post_ids']
        report['approvals'].append(ids)
        for p in posts:
            if p['id'] in ids: p['status'] = 'scheduled'; p['post_bucket'] = 'sending'
        result.update(approved=len(ids), results=[{'post_id':i,'approved':True} for i in ids])
    elif path.endswith('/draft'):
        report['draft_actions'].append({'method':req.method,'body':req.post_data_json})
    elif path.startswith('/api/posts/') and path not in ('/api/posts/health','/api/posts/token-audit') and not path.endswith(('/meta-diagnosis','/refresh-meta','/retry-publish')):
        result['post'] = next((p for p in posts if p['id'] == path.rsplit('/',1)[-1]), None)
    elif path == '/api/output-pipeline/plans':
        if req.method == 'POST':
            p = req.post_data_json; plans[:] = [x for x in plans if x['id'] != p['id']] + [p]; result['plan'] = p
        else: result['plans'] = plans
    elif path == '/api/distribute/batch':
        body = req.post_data_json
        report['plans'].append(body)
        result.update(post_daily=True, message='Đã lưu Post hàng ngày', scheduled_count=0)
    elif path == '/api/output-pipeline/status':
        result['pipeline'] = {'alive': True, 'paused': True, 'reason': 'backlog_limit', 'backlog': 856, 'max_backlog': 200,
                              'error': 'One invalid cached package needs Website repair'}
    elif path.endswith('/meta-diagnosis') or path.endswith('/refresh-meta'):
        result.update(post_id='late', title='Scheduled video awaiting verification', post_status='meta_scheduled',
                      page_id='a', diagnosis={'state':'schedule_overdue','message':'Meta giữ lịch đã quá giờ',
                      'detail':'Đồng bộ Page đúng Token rồi kiểm tra lại.', 'can_sync_existing':True,
                      'can_retry_existing':False, 'video_id':'9001'}, observation={'http_status':400,'error':'API access blocked'},
                      recovery_credentials=[{'token_id':'t','name':'Group Token','original':True}], recovery_token_id='t')
        if path.endswith('/refresh-meta'): report['checks'].append('read-only refresh called for exact post and selected Token')
    elif path.endswith('/retry-publish'):
        report['retry_requests'].append(req.post_data_json)
        result.update(queued=True, message='Đã đưa bài vào hàng chờ đăng lại bằng App.')
    elif path == '/api/posts/token-audit': result.update(tokens=[],pages=[])
    elif path == '/api/clips': result['clips'] = []
    elif path == '/api/jobs': result = []
    elif path == '/api/scheduler/status': result.update(thread_alive=True,last_cycle_ok=True)
    elif path == '/api/dashboard/overview': result.update(post_counts={},attention=[],series=[])
    r.fulfill(status=200, content_type='application/json', body=json.dumps(result,ensure_ascii=False))

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True,channel='chrome')
    page = browser.new_page(viewport={'width':1600,'height':1000})
    page.route('http://review.test/**',route)
    page.route('https://**',lambda r:r.abort())
    page.on('pageerror',lambda e:report['errors'].append(str(e)))
    page.on('dialog',lambda d:d.accept())
    page.goto('http://review.test/',wait_until='domcontentloaded')
    page.evaluate("switchTab('pane-posts')")
    page.wait_for_function("document.querySelectorAll('#posts-table-body tr[data-post-id]').length === 50")
    assert '493' in page.inner_text('#posts-page-label')
    assert page.locator('#posts-schedule-summary').inner_text().count('493') == 2
    assert not page.locator('#posts-table-body').inner_text().find('stock') >= 0
    assert not any(r['path'] == '/api/posts' or r['path'] == '/api/posts/token-audit' for r in report['requests'])
    page.screenshot(path=str(evidence/'posts_paged.png'))
    page.evaluate("filterPostsSchedule('published')")
    page.wait_for_timeout(150)
    page.evaluate("postsPage=2;loadPostsTable()")
    page.wait_for_function("document.getElementById('posts-page-label').textContent.includes('2/10')")
    report['checks'].append('493 posts, 50 rows per page, global counts, no full queue or eager audit')
    page.evaluate("switchTab('pane-groups')")
    page.wait_for_function("document.querySelectorAll('#group-review-body tr[data-review-post-id]').length === 30")
    page.wait_for_function("document.getElementById('group-review-stock').textContent.includes('800')")
    assert page.locator('#pane-groups #group-review-panel').count() == 1
    assert '800' in page.inner_text('#group-review-stock')
    assert 'Group Token' in page.inner_text('#group-review-body')
    page.evaluate("openGroupReview('g')")
    page.wait_for_timeout(200)
    page.locator('#group-review-panel').scroll_into_view_if_needed()
    page.screenshot(path=str(evidence/'group_review.png'))
    page.evaluate("groupReviewPage=3;loadGroupReview()")
    page.wait_for_function("document.querySelectorAll('#group-review-body tr[data-review-post-id]').length === 5")
    page.check('#group-review-select-all')
    page.click('#group-review-approve')
    page.wait_for_function("document.getElementById('group-review-result').textContent.includes('5/5')")
    assert len(report['approvals'][-1]) == 5
    report['checks'].append('review by group, 30 rows per page, assigned Page/Token/time, five drafts approved once')
    page.evaluate("openOutputDraft('draft0')")
    page.wait_for_selector('#draft-review-modal',state='visible')
    assert page.input_value('#draft-review-mode') == 'meta_scheduled'
    assert 'Group Token' in page.inner_text('#draft-review-token')
    page.fill('#draft-review-caption','Edited caption for the complete original recording.')
    page.select_option('#draft-review-mode','app_queue')
    page.evaluate('saveOutputDraft()')
    page.wait_for_timeout(250)
    assert report['draft_actions'][-1]['body']['publish_mode'] == 'app_queue'
    report['checks'].append('single detail fetch and draft editor saves publishing mode')
    page.evaluate('runLoHaBatchSchedule("g","Bodycam Group")')
    page.wait_for_selector('#modal-schedule-config',state='visible')
    page.wait_for_function('!groupDailyModalState.schedule.loading')
    assert page.input_value('#sched-conf-review-mode') == 'manual'
    page.check('#sched-conf-daily')
    page.select_option('#sched-conf-review-mode','manual')
    page.evaluate('executeBatchSchedule()')
    page.wait_for_timeout(200)
    assert report['plans'][-1]['post_daily'] and report['plans'][-1]['approval_mode'] == 'manual'
    assert report['plans'][-1]['publish_mode'] == 'meta_scheduled'
    report['checks'].append('Post daily persists manual review and Meta mode for selected group')
    assert '856/200' in page.inner_text('#group-review-system-status')
    assert 'One invalid cached package' in page.inner_text('#group-review-system-status')
    report['checks'].append('group review displays worker backlog and package error')
    page.evaluate("switchTab('pane-groups')")
    posts.insert(0, {'id':'preparing-today','output_pipeline':True,'status':'preparing',
        'group_id':'g','page_id':'a','page_name':'Bodycam Page','token_id':'t','approval_mode':'automatic',
        'content_package_status':'queued','website_status':'pending_generation','title':'Waiting for Website',
        'scheduled_time':'2026-10-07 19:30:00','created_at':'2026-10-06T09:59:00'})
    page.evaluate("groupReviewPage=1;loadGroupReview()")
    page.wait_for_selector('tr[data-review-post-id="preparing-today"] input[type=checkbox]')
    page.locator('tr[data-review-post-id="preparing-today"] input[type=checkbox]').check()
    assert page.locator('#group-review-approve').is_disabled()
    page.click('#group-review-today-selected')
    page.wait_for_selector('#group-today-modal',state='visible')
    assert '2026-10-06' in page.inner_text('#group-today-date')
    assert page.locator('#group-today-apply').is_disabled()
    page.fill('#group-today-start','11:30')
    page.click('#group-today-preview')
    page.wait_for_function("!document.getElementById('group-today-apply').disabled")
    assert '1/1' in page.inner_text('#group-today-result')
    page.fill('#group-today-gap','20')
    page.locator('#group-today-gap').dispatch_event('change')
    assert page.locator('#group-today-apply').is_disabled()
    page.click('#group-today-preview')
    page.wait_for_function("!document.getElementById('group-today-apply').disabled")
    page.screenshot(path=str(evidence/'schedule_today.png'))
    page.click('#group-today-apply')
    page.wait_for_function("document.getElementById('group-today-result').textContent.includes('Đã lưu lịch hôm nay')")
    today = next(p for p in posts if p['id']=='preparing-today')
    assert today['status']=='preparing' and today['scheduled_time']=='2026-10-06 11:30:00'
    assert not today.get('content_frozen_at') and not today.get('draft_edited_at')
    assert sum(bool(r.get('apply')) for r in report['today_actions'])==1
    page.click('#group-today-modal button[aria-label="Đóng lịch hôm nay"]')
    report['checks'].append('preparing rows selectable; today preview invalidates on edit; apply retains preparing state and date')
    page.evaluate("openGroupToday('group')")
    page.wait_for_selector('#group-today-modal',state='visible')
    page.fill('#group-today-start','23:40')
    page.click('#group-today-preview')
    page.wait_for_function("!document.getElementById('group-today-apply').disabled")
    assert 'hết chỗ hôm nay' in page.inner_text('#group-today-result')
    assert report['today_actions'][-1]['scope']=='group'
    page.click('#group-today-modal button[aria-label="Đóng lịch hôm nay"]')
    page.evaluate("openGroupToday('stock')")
    page.wait_for_selector('#group-today-modal',state='visible')
    assert page.locator('#group-today-stock-label').is_visible()
    page.fill('#group-today-stock','2')
    page.fill('#group-today-start','13:00')
    page.click('#group-today-preview')
    page.wait_for_function("!document.getElementById('group-today-apply').disabled")
    assert '2/2' in page.inner_text('#group-today-result')
    assert report['today_actions'][-1]['scope']=='stock'
    page.click('#group-today-modal button[aria-label="Đóng lịch hôm nay"]')
    report['checks'].append('whole group handles midnight overflow; stock preview allocates into chosen Page group today')
    posts.insert(0, {'id':'rejected','status':'failed','retryable':True,'can_retry_publish':True,
                    'retry_stage':'facebook_publish','error':'Meta init rejected (HTTP 400): API access blocked',
                    'title':'Rejected initialization','page_id':'a','page_name':'Bodycam Page','media_file':'clip.mp4',
                    'created_at':'2026-10-06T12:00:00'})
    posts.insert(0, {'id':'late','status':'meta_scheduled','title':'Scheduled video awaiting verification',
                    'page_id':'a','page_name':'Bodycam Page','meta_schedule_overdue':True,
                    'meta_schedule_late_seconds':600,'meta_upload_video_id':'9001','created_at':'2026-10-06T12:01:00'})
    page.evaluate("switchTab('pane-posts')")
    page.wait_for_function('!postsTableLoading')
    page.evaluate("filterPostsSchedule('all')")
    try:
        page.wait_for_selector('tr[data-post-id="rejected"]', timeout=5000)
    except Exception:
        print(json.dumps({'errors':report['errors'],'recent_requests':report['requests'][-10:],
                          'table':page.inner_text('#posts-table-body')[:700]}, ensure_ascii=True))
        raise
    assert 'quá giờ' in page.locator('tr[data-post-id="late"]').inner_text()
    assert page.locator('tr[data-post-id="late"]').get_by_text('Đăng lại bằng App', exact=False).count() == 0
    page.locator('tr[data-post-id="rejected"]').get_by_text('Đăng lại bằng App', exact=False).click()
    page.wait_for_timeout(200)
    assert report['retry_requests'] == [{'mode':'app_queue'}]
    page.evaluate("openMetaDiagnosis('late')")
    page.wait_for_selector('#meta-sync-existing', state='visible')
    assert not page.locator('#meta-recover-existing').is_visible()
    assert not page.locator('#meta-finish-existing').is_visible()
    page.screenshot(path=str(evidence/'meta_overdue_recovery.png'))
    page.click('#meta-sync-existing')
    page.wait_for_timeout(300)
    refresh = [req for req in report['requests'] if req['path'] == '/api/posts/late/refresh-meta']
    assert len(refresh) == 1 and refresh[0]['method'] == 'POST'
    assert not any(req['path'].endswith('/recover-existing') or req['path'].endswith('/finish-existing') for req in report['requests'])
    report['checks'].append('overdue action opens diagnosis, blocked read exposes Sync only, Init retry queues App once')
    assert report['errors'] == [], report['errors']
    browser.close()
scratch.cleanup()
(evidence/'ui_verify.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'success':True,'checks':report['checks'],'errors':report['errors']},ensure_ascii=False))
