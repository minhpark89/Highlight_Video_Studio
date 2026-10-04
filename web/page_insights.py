"""Read and cache Page analytics without changing publishing or render state."""
import json
import math
import os
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from multi_pc.json_io import replace_with_retry
from multi_pc.publishing_settings import credential_ready

METRICS = ('followers', 'reach', 'engagement', 'views')
STALE_SECONDS = 900
SYNC_COOLDOWN = 300
GRAPH_BASE = 'https://graph.facebook.com/v22.0'
REASONS = {
    'not_synced': 'Chưa đồng bộ Meta', 'missing_binding': 'Cần Sync Page với Token đã xác minh',
    'cooldown': 'Token đang cooldown; đồng bộ lại sau', 'permission': 'Token thiếu quyền đọc Insights hoặc đã hết hạn',
    'unsupported': 'Meta không còn cung cấp chỉ số này qua API',
    'no_data': 'Meta chưa trả dữ liệu', 'incomplete': 'Meta chưa trả đủ 7 ngày',
    'error': 'Không đọc được Meta; thử đồng bộ lại',
}


def numeric(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def missing(reason):
    return {'value': None, 'status': reason, 'message': REASONS.get(reason, REASONS['error']), 'series': []}


def period_for(now=None):
    now = now or datetime.now(timezone.utc)
    end = now.astimezone(timezone.utc).date()
    start = end - timedelta(days=7)
    return {'since': start.isoformat(), 'until': end.isoformat(),
            'dates': [(start + timedelta(days=i)).isoformat() for i in range(7)]}


def graph_error(data, http):
    error = data.get('error') if isinstance(data, dict) else None
    if http == 200 and not error:
        return None
    error = error if isinstance(error, dict) else {}
    if error.get('code') == 100 and 'valid insights metric' in str(error.get('message') or '').lower():
        return 'unsupported'
    if error.get('code') in (10, 190, 200):
        return 'permission'
    if http == 429 or error.get('code') in (4, 17, 32, 613):
        return 'cooldown'
    return 'error'


def parse_daily(data, name, period):
    """Daily Insights are labelled by their exclusive end time, not today's date."""
    rows = data.get('data') if isinstance(data, dict) else []
    entry = next((x for x in (rows or []) if isinstance(x, dict) and x.get('name') == name
                  and x.get('period') == 'day'), None)
    if not entry:
        return missing('no_data')
    values = {}
    for row in entry.get('values') or []:
        try:
            day = (date.fromisoformat(str(row.get('end_time'))[:10]) - timedelta(days=1)).isoformat()
        except (ValueError, TypeError):
            continue
        if day in period['dates'] and numeric(row.get('value')):
            values[day] = row['value']
    if set(values) != set(period['dates']):
        return missing('incomplete')
    return {'value': sum(values.values()), 'status': 'ok', 'message': '', 'metric': name,
            'series': [{'date': day, 'value': values[day]} for day in period['dates']]}


def parse_reach(data, period):
    """Use one seven-day unique count; adding daily reach would double count."""
    for entry in data.get('data') or []:
        if entry.get('name') != 'page_impressions_unique' or entry.get('period') != 'week':
            continue
        for row in entry.get('values') or []:
            if str(row.get('end_time') or '')[:10] == period['until'] and numeric(row.get('value')):
                return {'value': row['value'], 'status': 'ok', 'message': '', 'series': [],
                        'metric': 'page_impressions_unique'}
    return missing('no_data')


class PageInsightsService:
    def __init__(self, root, vault, manager):
        self.path = Path(root) / 'data' / 'page_insights.json'
        self.vault, self.manager = vault, manager
        self.lock = threading.RLock()
        self.progress = {'running': False, 'completed': 0, 'total': 0, 'error': ''}
        self.reach_unsupported = False
        self.blocked_tokens = set()

    def _load(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            return value if isinstance(value, dict) and value.get('schema') == 1 and isinstance(value.get('pages'), dict) else {'schema': 1, 'pages': {}}
        except (OSError, ValueError):
            return {'schema': 1, 'pages': {}}

    def _save(self, cache):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f'.{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp')
        try:
            temp.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
            replace_with_retry(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)

    def _get(self, mapping, suffix, params):
        if mapping['token_id'] in self.blocked_tokens or not credential_ready(self.vault.get_token_by_id(mapping['token_id'])):
            return {}, 'cooldown'
        try:
            response = requests.get(GRAPH_BASE + '/' + mapping['page_id'] + suffix,
                                    params={**params, 'access_token': mapping['page_token']}, timeout=15)
            self.vault.record_usage(mapping['token_id'], response.headers)
            data = response.json()
            if not isinstance(data, dict):
                return {}, 'error'
            error = graph_error(data, response.status_code)
            if error == 'cooldown':
                self.blocked_tokens.add(mapping['token_id'])
            return data, error
        except (requests.RequestException, ValueError, TypeError):
            # Never persist exception text: request URLs contain credentials.
            return {}, 'error'

    def _collect(self, page, period, previous):
        record = {'page_id': str(page['page_id']), 'checked_at': time.time(), 'period': period,
                  'metrics': {key: missing('no_data') for key in METRICS},
                  'follower_history': list(previous.get('follower_history') or [])[-30:]}
        entry = self.vault.get_token_by_id(str(page.get('token_id') or ''))
        mapping, error = self.manager.resolve_verified_mapping(page['page_id'], entry)
        if error or not mapping:
            record['metrics'] = {key: missing('missing_binding') for key in METRICS}
            return record
        record['token_id'] = mapping['token_id']
        data, error = self._get(mapping, '', {'fields': 'id,followers_count'})
        if error:
            record['metrics']['followers'] = missing(error)
        elif str(data.get('id')) == record['page_id'] and numeric(data.get('followers_count')):
            value = data['followers_count']
            history = list(previous.get('follower_history') or [])
            today = datetime.now(timezone.utc).date().isoformat()
            history = [row for row in history if row.get('date') != today and numeric(row.get('value'))]
            history.append({'date': today, 'value': value})
            record['follower_history'] = sorted(history, key=lambda row: row['date'])[-30:]
            record['metrics']['followers'] = {'value': value, 'status': 'ok', 'message': '',
                                              'series': record['follower_history'][-7:], 'metric': 'followers_count'}
        data, error = self._get(mapping, '/insights', {'metric': 'page_post_engagements,page_media_view',
                                'period': 'day', 'since': period['since'], 'until': period['until']})
        for key, name in [('engagement', 'page_post_engagements'), ('views', 'page_media_view')]:
            if error == 'unsupported':
                single, single_error = self._get(mapping, '/insights', {'metric': name, 'period': 'day',
                                              'since': period['since'], 'until': period['until']})
                record['metrics'][key] = missing(single_error) if single_error else parse_daily(single, name, period)
            else:
                record['metrics'][key] = missing(error) if error else parse_daily(data, name, period)
        if self.reach_unsupported:
            record['metrics']['reach'] = missing('unsupported')
        else:
            data, error = self._get(mapping, '/insights', {'metric': 'page_impressions_unique', 'period': 'week',
                                    'since': period['since'], 'until': period['until']})
            self.reach_unsupported = error == 'unsupported'
            record['metrics']['reach'] = missing(error) if error else parse_reach(data, period)
        return record

    def start_sync(self, pages, page_id=''):
        selected = [page for page in pages if not page_id or str(page.get('page_id')) == str(page_id)]
        if page_id and not selected:
            raise ValueError('Không tìm thấy Page.')
        with self.lock:
            if self.progress['running']:
                return {**self.progress, 'started': False}
            cache = self._load()
            fresh = [page for page in selected if time.time() - cache.get('pages', {}).get(str(page['page_id']), {}).get('checked_at', 0) >= SYNC_COOLDOWN]
            if not fresh:
                return {**self.progress, 'started': False, 'message': 'Dữ liệu vừa đồng bộ; chờ 5 phút trước lần tiếp theo.'}
            self.progress = {'running': True, 'completed': 0, 'total': len(fresh), 'error': '', 'started_at': time.time()}
            # One analytics worker bounds load and respects each credential's cooldown.
            threading.Thread(target=self._run_sync, args=(fresh, period_for()), daemon=True, name='page-insights').start()
            return {**self.progress, 'started': True}

    def _run_sync(self, pages, period):
        self.reach_unsupported = False
        self.blocked_tokens.clear()
        try:
            for page in pages:
                with self.lock:
                    previous = self._load().get('pages', {}).get(str(page['page_id']), {})
                record = self._collect(page, period, previous)
                with self.lock:
                    cache = self._load()
                    cache.setdefault('pages', {})[str(page['page_id'])] = record
                    self._save(cache)
                    self.progress['completed'] += 1
        except Exception:
            with self.lock:
                self.progress['error'] = 'Đồng bộ bị gián đoạn; dữ liệu đã đọc vẫn được giữ. Hãy thử lại.'
        finally:
            with self.lock:
                self.progress.update(running=False, finished_at=time.time())

    def summary(self, pages, page_id=''):
        period = period_for()
        selected = {str(page['page_id']): page for page in pages if not page_id or str(page['page_id']) == str(page_id)}
        with self.lock:
            cache, progress = self._load(), dict(self.progress)
        records, details, checked = {}, [], []
        for ident, page in selected.items():
            saved = cache.get('pages', {}).get(ident, {})
            metrics = {}
            for key in METRICS:
                metric = saved.get('metrics', {}).get(key) or missing('not_synced')
                if key != 'followers' and saved.get('period', {}).get('until') != period['until']:
                    metric = missing('not_synced')
                # Reject malformed persisted values rather than turn them into zero.
                if metric.get('status') == 'ok' and not numeric(metric.get('value')):
                    metric = missing('no_data')
                metrics[key] = metric
            records[ident] = metrics
            if numeric(saved.get('checked_at')):
                checked.append(saved['checked_at'])
            details.append({'page_id': ident, 'page_name': page.get('page_name') or ident,
                            'checked_at': saved.get('checked_at'), 'metrics': metrics})
        totals = {}
        for key in METRICS:
            available = [metrics[key] for metrics in records.values() if metrics[key].get('status') == 'ok']
            reasons = sorted({metrics[key].get('message') for metrics in records.values()
                              if metrics[key].get('status') != 'ok' and metrics[key].get('message')})
            value = sum(item['value'] for item in available) if available else None
            series = []
            dates = period['dates'] if key != 'followers' else sorted({r['date'] for m in available for r in m.get('series', [])})[-7:]
            for day in dates:
                values = [row['value'] for item in available for row in item.get('series', [])
                          if row.get('date') == day and numeric(row.get('value'))]
                if available and len(values) == len(available):
                    series.append({'date': day, 'value': sum(values)})
            totals[key] = {'value': value, 'coverage': len(available), 'total_pages': len(selected),
                           'status': 'ok' if available else 'unavailable',
                           'partial': bool(available) and len(available) != len(selected),
                           'reasons': reasons, 'series': series}
        return {'metrics': totals, 'period': period, 'progress': progress, 'pages': details,
                'page_id': page_id, 'updated_at': max(checked) if checked else None,
                'stale': bool(checked) and time.time() - min(checked) > STALE_SECONDS,
                'reach_note': 'Reach là tổng reach riêng từng Page; cùng một người có thể được tính ở nhiều Page.'}
