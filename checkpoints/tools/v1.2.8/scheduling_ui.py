"""Exercise shipped functions in Chromium; HTTP is fully intercepted."""
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'checkpoints/evidence/v1.2.8'
EVIDENCE.mkdir(parents=True, exist_ok=True)
source = (ROOT / 'web/index.html').read_text(encoding='utf-8')
report = {'success': False, 'checks': [], 'errors': [], 'live_http': False}
g = {'id':'g', 'name':'NEW', 'page_ids':['p'], 'folder_binding':'fixture',
     'schedule_config':{'times':['10:50','15:00','04:00'],'stagger_minutes':20}}
old_plan = {'id':'group:g','enabled':True,'daily':True,'slots':['04:00','10:50'],
            'posts_per_day':2,'stagger_minutes':15,'approval_mode':'manual','publish_mode':'meta_scheduled'}
payloads = []

def route(r):
    path = urlparse(r.request.url).path
    if path == '/':
        return r.fulfill(content_type='text/html', body='''<html><meta charset="utf-8"><body>
        <table><tbody id="loha-groups-table-body"></tbody></table>
        <div id="modal-schedule-config"><input id="sched-conf-group-id"><span id="sched-conf-group-name"></span>
        <select id="sched-conf-posts-per-page"></select><div id="sched-conf-times-preview"></div>
        <input type="checkbox" id="sched-conf-daily"><select id="sched-conf-review-mode"><option value="manual">Manual</option></select>
        <select id="sched-conf-publish-mode"><option value="meta_scheduled">Meta</option><option value="app_queue">App</option></select>
        <input type="checkbox" id="sched-conf-use-llm"><button onclick="executeBatchSchedule()">Lưu</button></div>
        <div id="pane-posts" class="active"><select id="posts-token-filter"><option value="">All</option></select>
        <span id="posts-page-label"></span><table><tbody id="posts-table-body"></tbody></table></div>
        </body></html>''')
    if path == '/api/groups':
        return r.fulfill(json={'success':True, 'groups':[g]})
    if path == '/api/output-pipeline/plans':
        return r.fulfill(json={'success':True, 'plans':[old_plan]})
    if path == '/api/distribute/batch':
        payloads.append(r.request.post_data_json)
        return r.fulfill(json={'success':True,'post_daily':True,'message':'Saved'})
    report['errors'].append('Unexpected request: ' + path)
    return r.abort()

def section(start, end):
    return source[source.index(start):source.index(end, source.index(start))]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='chrome')
    page = browser.new_page(viewport={'width':1150,'height':800})
    page.route('**/*', route)
    page.on('pageerror', lambda error: report['errors'].append(str(error)))
    page.on('dialog', lambda dialog: dialog.accept())
    page.goto('http://scheduling.test/')
    page.add_script_tag(content='''
    const groupDailyModalState={}; let postsTableRequest=null, postsTableGeneration=0, postsPage=1, postsScheduleFilter='all';
    let postsCounts={}, postsSnapshot=[], metaHandoffBusy=false, postsHealthCheckedAt=Date.now(), postLedgerWarningShown=false;
    const selectedMetaPosts=new Set(); const postBucketLabels={};
    function escapeHtml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
    function showToast(message){window.lastToast=message;}
    function updateMetaHandoffControls(){} function showNewMetaPostErrors(){} function postsMatchScheduleFilter(){return true;}
    function switchTab(){} function nextLocalScheduleTime(){return '2026-10-07T04:00';}
    const originalFetch=window.fetch.bind(window); const pendingPosts=[]; let deferredCounts;
    window.fetch=(url, options)=>{
      if(url.includes('/api/groups/video-counts'))return new Promise(resolve=>deferredCounts=resolve);
      if(url.includes('/api/posts/list'))return new Promise(resolve=>pendingPosts.push({url,options,resolve}));
      return originalFetch(url,options);
    };
    ''')
    page.add_script_tag(content=section('  function groupDailySchedule(', '  async function stopUncheckedGroupDailyPlan('))
    page.add_script_tag(content=section('  async function stopUncheckedGroupDailyPlan(', '  async function openDistributeModal('))
    page.add_script_tag(content=section('  async function runLoHaBatchSchedule(', '  let lohaGroupsGeneration'))
    page.add_script_tag(content=section('  let lohaGroupsGeneration', '// Old runLoHaBatchSchedule'))
    page.add_script_tag(content=section('  async function loadPostsTable(', '  async function retryWebsiteForPost('))
    page.evaluate('loadLoHaGroups()')
    assert page.locator('[data-group-id="g"]').count() >= 1
    assert 'Đang đếm video' in page.locator('[data-group-video-count="g"]').inner_text()
    report['checks'].append('Group rows and scheduling buttons appear before inventory finishes')
    page.evaluate("deferredCounts(new Response(JSON.stringify({success:true,groups:[{id:'g',file_count:17}]}),{status:200}))")
    page.wait_for_function("document.querySelector('[data-group-video-count]').textContent.includes('17')")
    report['checks'].append('Background count updates the correct bound group')
    page.evaluate("runLoHaBatchSchedule('g','NEW')")
    assert page.locator('#sched-conf-posts-per-page option').count() == 3
    assert page.locator('#sched-conf-posts-per-page').input_value() == '3'
    assert page.locator('#sched-conf-times-preview').inner_text() == 'Khung giờ: 04:00 | 10:50 | 15:00 · Giãn cách: 20 phút/page'
    report['checks'].append('Legacy two-slot plan cannot hide the third saved group slot')
    page.locator('#sched-conf-posts-per-page').select_option('3')
    page.evaluate('executeBatchSchedule()')
    assert payloads[-1]['posts_per_page'] == 3 and payloads[-1]['daily_slots'] == ['04:00','10:50','15:00']
    assert payloads[-1]['stagger_minutes'] == 20 and payloads[-1]['post_daily']
    report['checks'].append('Confirm sends all three slots, count and edited stagger')
    # A newly recorded explicit limit is retained, while all configured choices stay visible.
    page.evaluate("groupDailyModalState.schedule.plan={...groupDailyModalState.schedule.plan,group_schedule_times:['04:00','10:50','15:00']};")
    result = page.evaluate("groupDailySchedule(allGroupsCached[0],groupDailyModalState.schedule.plan)")
    assert result['count'] == 2 and len(result['times']) == 3
    result = page.evaluate("groupDailySchedule({schedule_config:{times:['01:00','02:00','03:00','04:00','05:00','06:00','07:00']}},null)")
    assert result['count'] == 7
    report['checks'].append('Intentional two-post cap persists; more than six slots remain selectable')
    # executeBatchSchedule kicked off a posts refresh. Resolve it before race checks.
    page.evaluate("pendingPosts.splice(0).forEach(p=>p.resolve(new Response(JSON.stringify({items:[],page:1,tokens:[]}),{status:200})))")
    page.wait_for_function('postsTableRequest === null')
    page.evaluate("postsScheduleFilter='all'; window.firstLoad=loadPostsTable({quiet:true}); void 0")
    page.evaluate("postsScheduleFilter='failed'; window.secondLoad=loadPostsTable({quiet:true}); void 0")
    assert page.evaluate('pendingPosts.length') == 2
    assert page.evaluate('pendingPosts[0].options.signal.aborted') is True
    page.evaluate("pendingPosts[1].resolve(new Response(JSON.stringify({items:[{id:'new',title:'Latest filtered result',status:'failed',token_id:'t'}],page:1,tokens:[{id:'t',name:'Fixture'}]}),{status:200}))")
    page.wait_for_function("document.querySelector('tr[data-post-id=\"new\"]') !== null")
    page.evaluate("pendingPosts[0].resolve(new Response(JSON.stringify({items:[{id:'old',title:'Stale response',status:'published'}],page:8,tokens:[]}),{status:200}))")
    page.evaluate('Promise.all([firstLoad,secondLoad])')
    assert page.locator('tr[data-post-id="new"]').count() == 1
    assert page.locator('tr[data-post-id="old"]').count() == 0 and page.evaluate('postsPage') == 1
    report['checks'].append('Filter changes abort old fetch and reject a late response, including its page counter')
    page.evaluate("pendingPosts.length=0; window.thirdLoad=loadPostsTable({quiet:true}); loadPostsTable({quiet:true}); void 0")
    assert page.evaluate('pendingPosts.length') == 1
    page.evaluate("pendingPosts[0].resolve(new Response(JSON.stringify({items:[],page:1,tokens:[]}),{status:200}))")
    page.evaluate('thirdLoad')
    report['checks'].append('Identical quiet refreshes share the pending request')
    assert not report['errors'], report['errors']
    page.screenshot(path=str(EVIDENCE / 'three_group_slots.png'), full_page=True)
    report['success'] = True
    (EVIDENCE / 'browser_ui.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print(json.dumps(report, ensure_ascii=False))
