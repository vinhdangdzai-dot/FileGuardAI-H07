"""Whitelist log filters and normalize explicit UTC/offset timestamps."""
from datetime import datetime, timezone

LABELS = {'benign', 'suspicious', 'unavailable', 'error', 'skipped'}
ACTIONS = {'ALLOW', 'BLOCK', 'MISS'}
STATUSES = {200, 403, 404}


def normalize_time(value):
    if not value:
        return None
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Invalid time filter')
    try:
        instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Use ISO 8601 time; timezone-free form fields mean UTC') from exc
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(timezone.utc).isoformat(timespec='seconds')


def normalize_filters(action=None, ml_label=None, http_status=None, start=None, end=None):
    action, ml_label = action or None, ml_label or None
    if action is not None and (not isinstance(action, str) or action not in ACTIONS):
        raise ValueError('Invalid action filter')
    if ml_label is not None and (not isinstance(ml_label, str) or ml_label not in LABELS):
        raise ValueError('Invalid AI label filter')
    if http_status in ('', None):
        status = None
    elif isinstance(http_status, bool) or str(http_status) not in {'200', '403', '404'}:
        raise ValueError('Invalid HTTP filter')
    else:
        status = int(http_status)
    start, end = normalize_time(start), normalize_time(end)
    if start and end and start > end:
        raise ValueError('Start time must not exceed end time')
    return {'action': action, 'ml_label': ml_label, 'http_status': status, 'start': start, 'end': end}


def where_clause(**filters):
    values = normalize_filters(**filters)
    predicates, parameters = [], []
    for key in ('action', 'ml_label', 'http_status'):
        if values[key] is not None:
            predicates.append(key + '=?')
            parameters.append(values[key])
    for key, operator in [('start', '>='), ('end', '<=')]:
        if values[key]:
            predicates.append('created_at' + operator + '?')
            parameters.append(values[key])
    return (' WHERE ' + ' AND '.join(predicates) if predicates else ''), parameters
