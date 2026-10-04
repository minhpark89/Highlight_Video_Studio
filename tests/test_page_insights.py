import json
from datetime import date, timedelta
from unittest import mock
import pytest

from web.page_insights import PageInsightsService, missing, parse_daily, period_for


def test_daily_insights_maps_meta_end_dates_to_the_seven_day_window():
    period = period_for()
    rows = [{'name': 'page_media_view', 'period': 'day', 'values': [
        {'value': index, 'end_time': f'{date.fromisoformat(day) + timedelta(days=1)}T07:00:00+0000'}
        for index, day in enumerate(period['dates'], 1)
    ]}]
    result = parse_daily({'data': rows}, 'page_media_view', period)
    assert result['status'] == 'ok'
    assert result['value'] == sum(range(1, 8))
    assert [row['date'] for row in result['series']] == period['dates']


def test_reach_unsupported_is_explicit_and_never_replaced_by_views():
    from web.page_insights import parse_reach
    period = period_for()
    result = parse_reach({'error': {'code': 100, 'message': 'The value must be a valid insights metric'}}, period)
    assert result['status'] == 'no_data'
    assert missing('unsupported')['message'] == 'Meta không còn cung cấp chỉ số này qua API'


class FakeVault:
    def __init__(self):
        self.token = {'id': 'token-1', 'status': 'ACTIVE', 'rate_status': 'NORMAL', 'app_usage_pct': 0}
        self.calls = 0

    def get_token_by_id(self, token_id):
        return self.token if token_id == self.token['id'] else None

    def record_usage(self, token_id, headers):
        self.calls += 1


class FakeManager:
    def resolve_verified_mapping(self, page_id, entry):
        if entry and entry.get('id') == 'token-1':
            return {'page_id': page_id, 'token_id': 'token-1', 'page_token': 'fixture'}, None
        return None, 'missing_mapping'


def test_collect_and_summary_keep_partial_coverage_and_never_invent_missing_values(tmp_path):
    service = PageInsightsService(tmp_path, FakeVault(), FakeManager())
    period = period_for()
    daily = lambda name, value: {'name': name, 'period': 'day', 'values': [
        {'value': value, 'end_time': f'{date.fromisoformat(day) + timedelta(days=1)}T07:00:00+0000'} for day in period['dates']
    ]}
    responses = [
        {'id': 'p1', 'followers_count': 64},
        {'data': [daily('page_post_engagements', 2), daily('page_media_view', 10)]},
        {'error': {'code': 100, 'message': 'The value must be a valid insights metric'}},
    ]
    class Response:
        status_code = 200
        headers = {}
        def __init__(self, data): self.data = data
        def json(self): return self.data
    with mock.patch('web.page_insights.requests.get', side_effect=[Response(item) for item in responses]):
        record = service._collect({'page_id': 'p1', 'token_id': 'token-1', 'page_name': 'Page'}, period, {})
    assert record['metrics']['followers']['value'] == 64
    assert record['metrics']['engagement']['value'] == 14
    assert record['metrics']['views']['value'] == 70
    assert record['metrics']['reach']['status'] == 'unsupported'
    cache = {'schema': 1, 'pages': {'p1': record}}
    service._save(cache)
    summary = service.summary([{'page_id': 'p1', 'token_id': 'token-1', 'page_name': 'Page'}])
    assert summary['metrics']['followers']['value'] == 64
    assert summary['metrics']['engagement']['value'] == 14
    assert summary['metrics']['views']['value'] == 70
    assert summary['metrics']['reach']['value'] is None
    assert summary['metrics']['reach']['status'] == 'unavailable'
    partial = service.summary([{'page_id': 'p1'}, {'page_id': 'p2'}])
    assert partial['metrics']['views']['value'] == 70
    assert partial['metrics']['views']['coverage'] == 1
    assert partial['metrics']['views']['total_pages'] == 2
    assert partial['metrics']['views']['partial']
    assert 'fixture' not in service.path.read_text(encoding='utf-8')
    empty = service.summary([{'page_id': 'p2'}])
    assert all(metric['value'] is None for metric in empty['metrics'].values())


def test_start_sync_avoids_concurrent_duplicate_syncs(tmp_path):
    service = PageInsightsService(tmp_path, FakeVault(), FakeManager())
    pages = [{'page_id': 'p1', 'token_id': 'token-1'}]
    with mock.patch.object(service, '_run_sync') as run:
        first = service.start_sync(pages)
        second = service.start_sync(pages)
    assert first['started'] and first['running']
    assert not second['started']
    run.assert_called_once()


@pytest.mark.parametrize('bad_value', [False, '0', -1, {}, None])
def test_missing_or_invalid_insights_never_become_zero(tmp_path, bad_value):
    service = PageInsightsService(tmp_path, FakeVault(), FakeManager())
    service._save({'schema': 1, 'pages': {'p1': {'metrics': {'followers': {'value': bad_value, 'status': 'ok'}}}}})
    assert service.summary([{'page_id': 'p1'}])['metrics']['followers']['value'] is None


def test_verified_binding_and_cooldown_gate_every_analytics_read(tmp_path):
    vault = FakeVault()
    service = PageInsightsService(tmp_path, vault, FakeManager())
    with mock.patch('web.page_insights.requests.get') as read:
        record = service._collect({'page_id': 'p1', 'token_id': 'missing'}, period_for(), {})
        assert all(metric['status'] == 'missing_binding' for metric in record['metrics'].values())
        vault.token['rate_status'] = 'COOLDOWN_80'
        record = service._collect({'page_id': 'p1', 'token_id': 'token-1'}, period_for(), {})
        assert all(metric['status'] == 'cooldown' for metric in record['metrics'].values())
    read.assert_not_called()


def test_cache_period_changes_invalidate_seven_day_values_and_sync_cooldown_blocks_calls(tmp_path):
    service = PageInsightsService(tmp_path, FakeVault(), FakeManager())
    import time
    service._save({'schema': 1, 'pages': {'p1': {'checked_at': time.time(), 'period': {'until': '2000-01-01'},
                  'metrics': {key: {'value': 20, 'status': 'ok'} for key in ['followers','engagement','views','reach']}}}})
    summary = service.summary([{'page_id': 'p1'}])
    assert summary['metrics']['followers']['value'] == 20
    assert summary['metrics']['views']['value'] is None
    with mock.patch('web.page_insights.threading.Thread') as worker:
        assert not service.start_sync([{'page_id': 'p1'}])['started']
        assert not worker.called


def test_insights_routes_are_local_reads_and_validate_selection(tmp_path, monkeypatch):
    from web import app as api
    service = PageInsightsService(tmp_path, FakeVault(), FakeManager())
    monkeypatch.setattr(api, 'page_insights_service', service)
    monkeypatch.setattr(api.page_manager, 'list_pages', lambda: [{'page_id': 'p1', 'page_name': 'Fixture'}])
    client = api.app.test_client()
    with mock.patch('web.page_insights.requests.get') as remote:
        result = client.get('/api/dashboard/insights').get_json()
        assert result['success'] and result['insights']['metrics']['views']['value'] is None
        assert client.get('/api/dashboard/insights?page_id=missing').status_code == 404
        assert client.post('/api/dashboard/insights/sync', json={'page_id': 5}).status_code == 400
        assert client.post('/api/dashboard/insights/sync', json=['bad']).status_code == 400
    remote.assert_not_called()
    assert not service.path.exists()
