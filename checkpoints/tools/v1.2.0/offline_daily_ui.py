"""Browser QA against isolated API fixtures; never touches installed app state."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parents[2] / 'evidence/v1.2.0'
EVIDENCE.mkdir(parents=True, exist_ok=True)
html = (REPO / 'web/templates/index.html').read_text(encoding='utf8').replace('{{ app_version }}', '1.2.0')
pages = [{'page_id':'a','page_name':'Page Alpha','token_id':'t'}, {'page_id':'b','page_name':'Page Beta','token_id':'t'}]
groups = [{'id':'g','name':'Group Alpha','page_ids':['a'],'schedule_config':{'times':['11:30','19:30']}},
          {'id':'h','name':'Group Beta','page_ids':['b'],'schedule_config':{'times':['10:00']}}]
plans = []
posts = [{'id':'output_fixture','output_pipeline':True,'status':'draft','title':'Cycling finish', 'content':'Watch the complete recording.',
          'first_comment':'See the full video https://cms.test/blog/finish','article_url':'https://cms.test/blog/finish','media_file':'clip.mp4',
          'content_package_status':'ready','website_status':'ready','website_video_status':'verified','page_id':'a','scheduled_time':'2026-10-06 19:30:00'}]
report = {'errors':[], 'saved_plans':[], 'draft_actions':[], 'batch_requests':[], 'group_modal_checks':[]}

def route(request_route):
    request = request_route.request
    path = request.url.split('pipeline.test')[-1].split('?')[0]
    if path == '/':
        request_route.fulfill(status=200, content_type='text/html', body=html)
        return
    payload = {'success':True}
    if path == '/api/groups': payload['groups'] = groups
    elif path == '/api/pages': payload['pages'] = pages
    elif path == '/api/token-groups': payload['groups'] = []
    elif path == '/api/tokens': payload['tokens'] = []
    elif path == '/api/posts': payload = posts
    elif path == '/api/schedule/rules': payload = {'status':'ok','rules':{'slots':['11:30','19:30'],'stagger_min':15}}
    elif path == '/api/output-pipeline/status': payload['pipeline'] = {'alive':True,'backlog':2,'free_gb':40}
    elif path == '/api/output-pipeline/plans':
        if request.method == 'POST':
            plan = request.post_data_json
            report['saved_plans'].append(plan)
            plans[:] = [p for p in plans if p['id'] != plan['id']] + [plan]
            payload['plan'] = plan
        else: payload['plans'] = plans
    elif path == '/api/distribute/batch':
        body = request.post_data_json
        report['batch_requests'].append(body)
        if body.get('post_daily'):
            plan = {'id': 'group:' + body['group_id'], 'enabled': True, 'daily': True,
                    'group_ids': [body['group_id']], 'page_ids': groups[0]['page_ids'], 'explicit_page_ids': [],
                    'slots': body.get('daily_slots') or ['11:30','19:30'], 'posts_per_day': body.get('posts_per_page',2),
                    'approval_mode': body['approval_mode'], 'publish_mode': body['publish_mode'],
                    'stagger_minutes': body.get('stagger_minutes') or 15, 'use_llm': body.get('use_llm_comment', True),
                    'start_date': '2026-10-05', 'token_group_id': body.get('token_group_id', '')}
            plans[:] = [p for p in plans if p['id'] != plan['id']] + [plan]
            payload.update({'post_daily': True, 'plan': plan, 'scheduled_count': 0, 'message': 'Đã lưu Post hàng ngày'})
    elif path.endswith('/draft'):
        report['draft_actions'].append({'method':request.method,'body':request.post_data_json})
        payload['post'] = posts[0]
    elif path == '/api/settings': payload.update({'llm':{},'image_provider':{}})
    elif path == '/api/jobs': payload = []
    elif path == '/api/content-studio/queue': payload['items'] = []
    elif path == '/api/posts/token-audit': payload.update({'tokens':[],'total_posts':1})
    request_route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, channel='chrome')
    page = browser.new_page(viewport={'width':1280,'height':1000})
    page.route('http://pipeline.test/**', route)
    page.route('https://**', lambda r: r.abort())
    page.on('pageerror', lambda e: report['errors'].append(str(e)))
    page.on('dialog', lambda dialog: dialog.accept())
    page.goto('http://pipeline.test/', wait_until='domcontentloaded')
    page.evaluate('openScheduleRulesModal()')
    page.wait_for_selector('.daily-group-check')
    assert page.input_value('#loha-daily-mode') == 'automatic'
    assert page.input_value('#loha-daily-publish-mode') == 'meta_scheduled'
    page.check('#loha-post-daily')
    page.select_option('#loha-daily-mode','automatic')
    page.check('.daily-group-check[value="g"]')
    page.check('.daily-page-check[value="b"]')
    page.screenshot(path=str(EVIDENCE / 'daily_rules.png'))
    page.evaluate('saveLoHaScheduleRules()')
    page.wait_for_timeout(200)
    assert report['saved_plans'][-1]['page_ids'] == ['b']
    assert report['saved_plans'][-1]['group_ids'] == ['g']
    assert report['saved_plans'][-1]['approval_mode'] == 'automatic'
    assert report['saved_plans'][-1]['publish_mode'] == 'meta_scheduled'
    assert page.locator('#cfg_video_method option[value="cms"]').inner_text() == 'Nhúng YouTube gốc + upload ảnh qua CMS (khuyên dùng)'
    page.evaluate('window.allGroupsCached = ' + json.dumps(groups))
    page.evaluate('runLoHaBatchSchedule("g", "Group Alpha")')
    assert not page.is_checked('#sched-conf-daily')
    assert page.input_value('#sched-conf-publish-mode') == 'meta_scheduled'
    page.check('#sched-conf-daily')
    page.evaluate('executeBatchSchedule()')
    assert report['batch_requests'][-1]['post_daily']
    assert report['batch_requests'][-1]['daily_slots'] == ['11:30','19:30']
    page.evaluate('runLoHaBatchSchedule("g", "Group Alpha")')
    assert page.is_checked('#sched-conf-daily')
    assert page.input_value('#sched-conf-posts-per-page') == '2'
    page.screenshot(path=str(EVIDENCE / 'daily_group_saved.png'))
    page.select_option('#sched-conf-review-mode','manual')
    page.select_option('#sched-conf-publish-mode','app_queue')
    page.evaluate('executeBatchSchedule()')
    page.evaluate('runLoHaBatchSchedule("g", "Group Alpha")')
    assert page.is_checked('#sched-conf-daily')
    assert page.input_value('#sched-conf-review-mode') == 'manual'
    assert page.input_value('#sched-conf-publish-mode') == 'app_queue'
    page.evaluate('runLoHaBatchSchedule("h", "Group Beta")')
    assert not page.is_checked('#sched-conf-daily')
    assert page.input_value('#sched-conf-review-mode') == 'automatic'
    assert page.input_value('#sched-conf-publish-mode') == 'meta_scheduled'
    page.evaluate('closeScheduleConfigModal(); openDistributeModal()')
    assert page.is_checked('#modal-dist-daily')
    assert page.input_value('#modal-dist-daily-mode') == 'manual'
    assert page.is_checked('input[name="modal-dist-mode"][value="app_queue"]')
    page.select_option('#modal-dist-group','h')
    page.wait_for_function('groupDailyModalState.dist.groupId === "h" && !groupDailyModalState.dist.loading')
    assert not page.is_checked('#modal-dist-daily')
    assert page.input_value('#modal-dist-daily-mode') == 'automatic'
    assert page.is_checked('#modal-dist-mode-meta')
    page.select_option('#modal-dist-group','g')
    page.wait_for_function('groupDailyModalState.dist.groupId === "g" && !groupDailyModalState.dist.loading')
    batch_count = len(report['batch_requests'])
    page.uncheck('#modal-dist-daily')
    page.evaluate('executeBatchDistribute()')
    assert len(report['batch_requests']) == batch_count, 'Unchecking must disable daily intake without scheduling a one-time batch'
    page.evaluate('runLoHaBatchSchedule("g", "Group Alpha")')
    assert not page.is_checked('#sched-conf-daily')
    page.evaluate('closeScheduleConfigModal()')
    report['group_modal_checks'] = ['default_native', 'saved_checkbox', 'saved_manual_app_mode', 'switch_group_resets_state', 'unchecked_disables_plan']
    page.evaluate('openOutputDraft("output_fixture")')
    page.wait_for_selector('#draft-review-modal',state='visible')
    page.fill('#draft-review-caption','Edited caption for the complete recording.')
    page.select_option('#draft-review-page','b')
    page.fill('#draft-review-time','2026-10-07T20:30')
    page.evaluate('saveOutputDraft()')
    assert report['draft_actions'][-1]['method'] == 'PUT'
    assert report['draft_actions'][-1]['body']['page_id'] == 'b'
    assert report['draft_actions'][-1]['body']['scheduled_time'] == '2026-10-07T20:30'
    page.evaluate('openOutputDraft("output_fixture")')
    page.screenshot(path=str(EVIDENCE / 'draft_review.png'))
    page.evaluate('saveOutputDraft(true,false)')
    page.wait_for_timeout(200)
    assert report['draft_actions'][-1]['method'] == 'POST'
    assert report['draft_actions'][-1]['body']['page_id'] == 'a'
    assert report['draft_actions'][-1]['body']['scheduled_time'] == '2026-10-06T19:30'
    assert report['errors'] == [], report['errors']
    browser.close()
(EVIDENCE / 'daily_ui_verify.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'success':True,'plan_saves':len(report['saved_plans']),'draft_actions':len(report['draft_actions']),'errors':report['errors']}))
