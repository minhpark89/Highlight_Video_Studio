"""Verify recovery controls with local API fixtures and no live app access."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[2] / 'evidence/v1.2.0'
OUT.mkdir(parents=True, exist_ok=True)
html = (ROOT / 'web/index.html').read_text(encoding='utf8').replace('{{ app_version }}', '1.2.0')
base = {'title':'Original launch trailer', 'content':'Original recording', 'page_id':'9901', 'page_name':'Fixture Page',
        'media_file':'clip.mp4', 'article_url':'https://example.test/blog/story', 'website_status':'ready',
        'local_video_available':True, 'local_video_url':'/api/clips/play/clip.mp4'}
posts = [{**base,'id':'website','status':'scheduled','website_status':'failed','website_error':'Existing CMS article contains non-English content',
          'first_comment_status':'generation_failed'},
         {**base,'id':'video','status':'processing','meta_upload_video_id':'9001'},
         {**base,'id':'local','status':'failed','retry_stage':'invalid_media','error':'MP4 invalid'}]
report = {'errors':[], 'requests':[], 'checks':[]}

def route(r):
    request = r.request
    path = request.url.split('recovery.test')[-1].split('?')[0]
    if path == '/':
        return r.fulfill(status=200,content_type='text/html',body=html)
    value = {'success':True}
    if path == '/api/posts': value = posts
    elif path == '/api/posts/token-audit': value.update(tokens=[], pages=[])
    elif path == '/api/groups': value['groups'] = []
    elif path == '/api/pages': value['pages'] = []
    elif path == '/api/jobs': value = []
    elif path == '/api/posts/video/meta-diagnosis':
        value.update(post_id='video', title=base['title'], page_name=base['page_name'], media_file='clip.mp4',
            diagnosis={'state':'rejected','message':'Meta báo lỗi xử lý video','detail':'MP4 cần render lại.',
                       'video_id':'9001','can_replace_failed_video':True},
            observation={'video_status':'error','uploading_status':'complete','bytes_transferred':262,'publishing_status':'not_started'})
    elif path == '/api/posts/website/retry-website':
        report['requests'].append({'path':path,'method':request.method})
        value.update(queued=True, message='Đang sửa và xác minh bài Website tại URL hiện tại.')
    elif path.endswith('/replace-failed-video'):
        report['requests'].append({'path':path,'body':request.post_data_json})
        value.update(queued=True, post_id='video_replacement', message='Đã tạo lịch thay thế.')
    elif path.endswith('/retry-media'):
        report['requests'].append({'path':path,'method':request.method})
        value['message'] = 'MP4 đã hợp lệ.'
    r.fulfill(status=200,content_type='application/json',body=json.dumps(value))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True,channel='chrome')
    page = browser.new_page(viewport={'width':1440,'height':1000})
    page.route('http://recovery.test/**', route)
    page.route('https://**', lambda r:r.abort())
    page.on('pageerror',lambda error:report['errors'].append(str(error)))
    page.on('dialog',lambda dialog:dialog.accept())
    page.goto('http://recovery.test/',wait_until='domcontentloaded')
    page.evaluate("switchTab('pane-posts')")
    page.wait_for_selector('tr[data-post-id="website"]')
    page.locator('tr[data-post-id="website"] button',has_text='Thử lại Website').click()
    page.wait_for_function("!postsTableLoading")
    assert any(r['path'].endswith('/retry-website') for r in report['requests'])
    report['checks'].append('retry button visible for failed website with existing URL')
    page.locator('tr[data-post-id="local"] button',has_text='Kiểm tra MP4').click()
    page.wait_for_function("!postsTableLoading")
    page.locator('tr[data-post-id="video"] button',has_text='Kiểm tra Meta').click()
    page.wait_for_selector('#meta-replace-failed',state='visible')
    assert page.is_hidden('#meta-finish-existing') and page.is_hidden('#meta-recover-existing')
    page.fill('#meta-replacement-file','repaired.mp4')
    page.fill('#meta-replacement-schedule','2026-10-07T19:30')
    page.screenshot(path=str(OUT / 'recovery_dialog.png'))
    page.click('#meta-replace-failed')
    page.wait_for_function("!metaFinishBusy")
    replacement = next(r for r in report['requests'] if r['path'].endswith('/replace-failed-video'))
    assert replacement['body'] == {'confirm_replace_failed_video':True,'video_id':'9001','filename':'repaired.mp4','schedule_time':'2026-10-07T19:30'}
    assert page.is_hidden('#meta-replace-failed')
    report['checks'].extend(['MP4 retry button', 'terminal rejection replacement control', 'exact video ID, file and schedule submitted', 'button hidden after successful queue'])
    assert not report['errors'], report['errors']
    browser.close()
(OUT / 'recovery_ui_verify.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'success':True,'checks':report['checks'],'errors':report['errors']}))
