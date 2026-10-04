import copy
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from src import content_packages as packages
from src.article_format import normalize_article, sentences, viewing_article, word_count
from src.first_comment_profiles import builtin_profiles, normalize_profile, profile_first_comment
from src.publisher import website_publisher as publisher
from web.token_audit import token_audit


def test_fallback_article_has_long_single_sentence_paragraphs_and_full_video_cta():
    article = viewing_article('A cyclist returns to the finish line', 'The source title describes a cycling video.', 'cycling')
    assert word_count(article) >= 750
    paragraphs = re.findall(r'<p>(.*?)</p>', article)
    assert len(paragraphs) >= 40
    assert all(len(sentences(paragraph)) == 1 for paragraph in paragraphs)
    assert 'A cyclist returns to the finish line' in article
    assert 'full video player below' in article
    cleaned = normalize_article('<script>alert(1)</script><p>Dr. Lane watched at 2.5 seconds. Replay the passage!</p>')
    assert '<script>' not in cleaned and 'alert(1)' not in cleaned
    assert cleaned.count('<p>') == 2


def test_custom_niche_and_rotation_survive_retries_and_use_all_samples(tmp_path):
    profile = normalize_profile({**builtin_profiles()[0], 'name': 'Cycling', 'niche': 'Road cycling', 'fallback_strategy': 'rotate'})
    store = {'profiles': [profile], 'default_profile_id': profile['id'], 'rotation_path': str(tmp_path / 'rotation.json')}
    comments = [profile_first_comment(f'Video {i}', f'https://cms.test/blog/{i}', store=store) for i in range(31)]
    leads = [comment.rsplit(' https://', 1)[0] for comment in comments]
    assert len(set(leads[:30])) == 30 and leads[30] == leads[0]
    assert profile_first_comment('Video 0', 'https://cms.test/blog/0', store=copy.deepcopy(store)) == comments[0]
    assert 'Road cycling'.lower() == profile['niche']
    assert not profile_first_comment('Invalid', 'javascript:alert(1)', store=store)
    assert 'Video 0' not in (tmp_path / 'rotation.json').read_text()


def test_two_workers_claim_distinct_clips_and_fence_duplicate(tmp_path):
    queue = tmp_path / 'queue.json'
    items = [{'id': key, 'clip_filename': clip, 'status': 'queued', 'title': key, 'result': {}}
             for key, clip in [('a', 'same.mp4'), ('b', 'same.mp4'), ('c', 'other.mp4')]]
    queue.write_text(json.dumps(items))
    entered = threading.Barrier(2)
    def process(item):
        entered.wait(timeout=5)
        item['status'] = 'ready'
        item['result'] = {'caption': item['title']}
    with mock.patch.object(packages, 'QUEUE_FILE', queue), mock.patch.object(packages, '_process_new_content_package', side_effect=process), mock.patch.object(packages, '_apply_to_posts'):
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = [pool.submit(packages.process_content_packages_once) for _ in range(2)]
            results = [outcome.result(timeout=10)['item']['id'] for outcome in outcomes]
    assert set(results) == {'a', 'c'}
    saved = json.loads(queue.read_text())
    assert next(item for item in saved if item['id'] == 'b')['status'] == 'queued'
    assert len([item for item in saved if item['status'] == 'ready']) == 2


def test_single_text_package_overlaps_images_and_is_the_cms_article(tmp_path):
    cfg = tmp_path / 'cms.json'
    cfg.write_text('{}')
    barrier = threading.Barrier(2)
    generated = {'hero_title': 'Cycling story', 'article_html': viewing_article('Cycling story'), 'caption': 'Caption', 'source': 'llm'}
    calls = []
    def factory(url, metadata):
        calls.append(url)
        barrier.wait(timeout=5)
        generated['first_comment'] = 'Watch ' + url
        return generated
    def assets(*args, **kwargs):
        barrier.wait(timeout=5)
        kwargs['metadata'].update(image_source='image_model', image_model='fixture-image')
        return 'https://cdn.test/hero.jpg', ['https://cdn.test/one.jpg', 'https://cdn.test/two.jpg']
    service = mock.Mock()
    service.publish_article.side_effect = lambda **kwargs: {'status': 'success', 'article_url': calls[0]}
    missing = mock.Mock(status_code=404)
    stages = []
    with mock.patch.object(publisher, 'get_website_config', return_value=({'base_url': 'https://cms.test'}, cfg)), mock.patch.object(
        publisher, 'get_clip_metadata', return_value={'youtube_id': 'abcdefghijk', 'video_title': 'Cycling story'}
    ), mock.patch.object(publisher.requests, 'get', return_value=missing), mock.patch.object(
        publisher, 'extract_and_upload_article_assets', side_effect=assets
    ), mock.patch.object(publisher, 'WebsiteArticleService', return_value=service):
        url, hero = publisher.publish_clip_to_website_cms('clip.mp4', 'Cycling story', content_factory=factory, progress=stages.append)
    assert len(calls) == 1 and url == calls[0]
    body = service.publish_article.call_args.kwargs['body_html']
    assert 'Editorial illustration' in body and generated['article_html'].splitlines()[1] in body
    assert body.index('hero.jpg') < body.index('Original video summary')
    assert body.count('<img ') == 3 and body.count('<iframe ') == 1
    assert service.publish_article.call_args.kwargs['image_url'] == hero
    assert stages[-1] == 'verifying_article'
    service.verify_article_quality.assert_called_once()


def test_token_audit_uses_original_id_counts_unique_pages_and_shows_assignment_difference():
    posts = [{'id': 'a', 'token_id': 'old', 'token_name': 'System User', 'page_id': 'p1', 'status': 'published'},
             {'id': 'b', 'token_id': 'old', 'page_id': 'p1', 'status': 'scheduled'},
             {'id': 'c', 'token_id': 'old', 'page_id': 'p2', 'status': 'published'},
             {'id': 'legacy', 'page_id': 'p1', 'status': 'published'}]
    audit = token_audit(posts, [{'page_id': 'p1', 'token_id': 'new'}, {'page_id': 'p2', 'token_id': 'old'}],
                        [{'id': 'old', 'name': 'BM work token', 'owner_name': 'Meta owner'}, {'id': 'new', 'name': 'New token'}],
                        [{'id': 'group', 'page_ids': ['p1'], 'page_token_bindings': {'p1': 'old'}}])
    original = next(row for row in audit['tokens'] if row['token_id'] == 'old')
    assert original['posting_pages'] == 2 and original['configured_pages'] == 1 and original['group_assigned_pages'] == 1
    assert original['posts'] == 3 and original['published'] == 2 and original['pending'] == 1
    assert posts[0]['token_display_name'] == 'BM work token' and posts[0]['token_assignment_match'] is False
    assert audit['unknown_posts'] == 1 and posts[-1]['token_assignment_match'] is None


def test_start_queue_endpoint_is_nonblocking_and_video_check_reports_embed_capability():
    with mock.patch('threading.Thread.start'):
        from web import app as web
    client = web.app.test_client()
    with mock.patch.object(web, 'start_content_package_worker') as start, mock.patch.object(web, 'process_content_packages_once') as process:
        response = client.post('/api/content-studio/process')
    assert response.status_code == 202
    start.assert_called_once()
    process.assert_not_called()
    service = mock.Mock()
    service._video_settings.return_value = {'method': 'cms'}
    service.test_connection.return_value = {'authenticated': True}
    with mock.patch.object(web, 'WebsiteArticleService', return_value=service):
        response = client.post('/api/website-config/test-video')
    body = response.get_json()
    assert response.status_code == 200 and body['success'] is True
    assert body['video_upload_supported'] is False and body['method'] == 'youtube_embed'
    service.test_video_uploader.assert_not_called()


def test_quick_generate_honors_rotation_and_custom_niche(tmp_path):
    from web import app as web
    client = web.app.test_client()
    comments = []
    for index in range(31):
        response = client.post('/api/content-studio/generate', json={
            'title': f'Cycling video {index}', 'article_url': f'https://cms.test/blog/{index}',
            'mode': 'no_llm', 'niche': 'Road cycling', 'fallback_strategy': 'rotate',
            'first_comment_profile_id': 'builtin_general',
        })
        assert response.status_code == 200
        package = response.get_json()['package']
        assert package['niche'] == 'Road cycling' and 'Road cycling' in package['article_html']
        comments.append(package['first_comment'].rsplit(' https://', 1)[0])
    assert len(set(comments[:30])) == 30 and comments[30] == comments[0]
    assert (tmp_path / 'data/first_comment_rotation.json').is_file()


def test_square_image_normalization_is_safe_for_parallel_same_title(tmp_path):
    import base64
    from io import BytesIO
    from PIL import Image

    data = BytesIO()
    Image.new('RGB', (1024, 1024), color='orange').save(data, format='PNG')
    response = mock.Mock(status_code=200)
    response.json.return_value = {'data': [{'b64_json': base64.b64encode(data.getvalue()).decode()}]}
    barrier = threading.Barrier(2)
    def generate(*args, **kwargs):
        barrier.wait(timeout=5)
        return response
    config = {'model': 'image-fixture', 'api_base': 'https://image.test/v1', 'api_key': 'fixture', 'generation_url': ''}
    with mock.patch.object(publisher, 'HVS_DIR', tmp_path), mock.patch.object(
        publisher, 'get_image_provider_config', return_value=config
    ), mock.patch.object(publisher.requests, 'post', side_effect=generate):
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks = [pool.submit(publisher.generate_llm_hook_image, 'Cycling story') for _ in range(2)]
            images = [task.result(timeout=10) for task in tasks]
    assert all(images) and images[0] == images[1]
    with Image.open(images[0]) as picture:
        assert picture.size == (1280, 720)
        picture.verify()
    assert len(list((tmp_path / 'temp').iterdir())) == 1
