import copy
import json
from unittest import mock

import pytest

from src.english_text import assert_english
from web.post_queries import select_posts, group_summary
from web.posts_store import save_posts_file


@pytest.mark.parametrize('text', [
    'Even ideal weapon builds depend heavily on smart movement discipline and engagement distance management.',
    'Sound equipment on modern camera units picks up eerie audio alongside visual elements.',
    'Future Outlook for Realistic Simulators',
])
def test_actual_public_english_false_positives_are_accepted(text):
    assert_english('<p>' + text + '</p>', 'Public CMS article')


@pytest.mark.parametrize('foreign', [
    'Este video muestra todos los detalles de la nueva actualizacion del juego.',
    'Cette video presente les details de la nouvelle mise a jour du jeu.',
    'Dit is een verhaal over een nieuwe camera en het originele beeld.',
    'Este video and watch muestra todos los detalles de la nueva actualizacion del juego.',
])
def test_short_foreign_and_mixed_paragraphs_still_rejected(foreign):
    english = '<p>Read the original recording for the full context of this footage.</p>' * 12
    with pytest.raises(ValueError):
        assert_english(english + '<p>' + foreign + '</p>')


def queue():
    return ([{'id': 'stock-' + str(i), 'status': 'preparing', 'output_pipeline': True} for i in range(800)]
            + [{'id': 'review-' + str(i), 'status': 'draft', 'output_pipeline': True,
                'group_id': 'g', 'page_id': 'p', 'token_id': 't'} for i in range(65)]
            + [{'id': 'published-' + str(i), 'status': 'published', 'page_id': 'p', 'token_id': 't'} for i in range(493)])


def test_large_queue_filters_before_pagination_and_keeps_stock_out_of_review_and_posts():
    posts = queue()
    review = select_posts(posts, view='review', group_id='g', page_size=30, page=3)
    assert review['total'] == 65 and review['counts'] == {'all': 65, 'draft': 65}
    assert len(review['items']) == 5 and all(p['page_id'] and p['token_id'] for p in review['items'])
    live = select_posts(posts)
    assert len(live['items']) == 50 and live['total'] == 493
    assert live['counts'] == {'all': 493, 'published': 493}
    stock = select_posts(posts, view='stock')
    assert stock['total'] == 800
    stats = group_summary(posts, [{'id': 'g', 'name': 'Group'}], [{'enabled': True, 'daily': True, 'group_ids': ['g']}])
    assert stats['stock'] == 800 and stats['groups'][0]['counts']['draft'] == 65 and stats['groups'][0]['daily']


def test_paged_api_enriches_only_requested_rows_and_never_returns_credentials(tmp_path, monkeypatch):
    from web import app as api
    posts = queue()
    for p in posts:
        p['token'] = 'must-never-leak'
        p['content_package'] = {'article_html': 'large-body' * 1000}
    path = tmp_path / 'posts.json'
    save_posts_file(path, posts)
    monkeypatch.setattr(api, 'POSTS_FILE', path)
    monkeypatch.setattr(api.token_vault, 'list_tokens', lambda **kw: [{'id': 't', 'name': 'Operator'}])
    monkeypatch.setattr(api.page_manager, 'list_pages', lambda: [])
    monkeypatch.setattr(api, 'load_token_groups', lambda: [])
    with mock.patch('web.meta_handoff.handoff_eligibility', return_value=(False, 'fixture')) as eligibility:
        response = api.app.test_client().get('/api/posts/list?view=review&group_id=g&page_size=30&page=3')
        assert response.status_code == 200
        assert eligibility.call_count == 5
    data = response.get_json()
    assert len(data['items']) == 5 and data['total'] == 65
    assert 'must-never-leak' not in response.get_data(as_text=True)
    assert 'large-body' not in response.get_data(as_text=True)
    client = api.app.test_client()
    assert client.get('/api/posts/list?page_size=9999').status_code == 400
    assert client.get('/api/posts/list?page=0').status_code == 400
    assert client.get('/api/posts/absent').status_code == 404


def test_daily_uses_selected_linked_token_group_instead_of_default_page_token():
    from src.output_pipeline import _assignment_candidates
    from datetime import datetime
    pages = [{'page_id': 'p', 'token_id': 'wrong-default'}]
    groups = [{'id': 'g', 'page_ids': ['p']}]
    tokens = [{'id': 'tg', 'page_group_id': 'g', 'page_ids': ['p'], 'token_ids': ['correct'],
               'page_token_bindings': {'p': 'correct'}}]
    plan = {'id': 'daily', 'enabled': True, 'daily': True, 'page_ids': ['p'], 'group_ids': ['g'],
            'start_date': '2026-10-05', 'slots': ['12:00'], 'stagger_minutes': 15,
            'approval_mode': 'manual', 'publish_mode': 'meta_scheduled', 'use_llm': True}
    assignments = list(_assignment_candidates([plan], pages, groups, datetime(2026, 10, 5, 8), tokens))
    assert len(assignments) == 2
    assert all(p['token_id'] == 'correct' and p['token_group_id'] == 'tg' and p['group_id'] == 'g' for p in assignments)
    pages[0]['token_id'] = ''
    assert len(list(_assignment_candidates([plan], pages, groups, datetime(2026, 10, 5, 8), tokens))) == 2
    tokens[0]['page_token_bindings']['p'] = 'outside'
    assert list(_assignment_candidates([plan], pages, groups, datetime(2026, 10, 5, 8), tokens)) == []
