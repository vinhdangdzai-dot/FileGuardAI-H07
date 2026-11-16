"""Hand-crafted numeric features for lexical path intent classification."""
import math
import re
from urllib.parse import unquote

FEATURE_NAMES = [
    'length', 'depth_slash', 'backslashes', 'dotdot', 'percent_count',
    'encoded_dot', 'encoded_slash', 'encoded_backslash', 'leading_slash',
    'drive_prefix', 'contains_colon', 'spaces', 'non_ascii', 'digits',
    'multiple_dots', 'null_encoding', 'contains_question', 'entropy',
]


def extract_features(path: str) -> list[float]:
    # The decoding below is ONLY for ML signal extraction, never file access.
    # Flask's request.args has already decoded the URL query once.
    # This additional, single ML-only view is never passed to open_authorized.
    lowered = path.lower()
    once = unquote(lowered)
    n = max(1, len(path))
    freq = {c: path.count(c) / n for c in set(path)}
    entropy = -sum(p * math.log2(p) for p in freq.values())
    return [
        len(path), path.count('/'), path.count('\\'),
        lowered.count('..') + once.count('../') + once.count('..\\'),
        path.count('%'), int('%2e' in lowered), int('%2f' in lowered),
        int('%5c' in lowered), int(path.startswith(('/', '\\'))),
        int(bool(re.match(r'^[a-z]:', lowered))), int(':' in path),
        path.count(' '), sum(ord(c) > 127 for c in path),
        sum(c.isdigit() for c in path), path.count('...'),
        int('%00' in lowered or '\x00' in path), int('?' in path), entropy,
    ]


def simple_rule(path: str) -> int:
    """Deliberately simple regex comparison baseline, not access control."""
    return int(bool(re.search(r'\.\.[/\\]|%2e|%2f|%5c|^[a-z]:|^[/\\]', path, re.I)))


# V1 remains byte-for-byte compatible with deployed 18-feature artifacts.
# V2 is experimental only: decoded strings MUST NOT reach filesystem access.
FEATURE_NAMES_V2 = FEATURE_NAMES + [
    'view_max_parent_components', 'view_max_parent_fraction',
    'view_max_rooted', 'view_max_drive', 'view_max_unc',
    'view_max_separators', 'view_mixed_separators',
    'view_max_escape_depth', 'view_max_dot_components',
    'view_max_null', 'view_max_structural_escapes', 'decode_changes',
]


def lexical_views(path: str) -> tuple[str, str, str]:
    """Raw plus exactly two bounded URL-decode views, ML analysis ONLY.

    No unquote_plus: '+' in a framework-decoded filename is literal. No
    recursive decoding, filesystem normalization, or compatibility folding.
    Truncate ML-only views at the same 4096-character policy limit.
    """
    raw = path[:4096].lower()
    once = unquote(raw, errors='replace')
    return raw, once, unquote(once, errors='replace')


def extract_features_v2(path: str) -> list[float]:
    views = lexical_views(path)
    signals = []
    for text in views:
        normalized = text.replace('\\', '/')
        parts = normalized.split('/')
        parents = parts.count('..')
        depth = minimum = 0
        for part in parts:
            if part == '..':
                depth -= 1
            elif part not in ('', '.'):
                depth += 1
            minimum = min(minimum, depth)
        signals.append([
            parents, parents / max(1, len(parts)),
            int(normalized.startswith('/')), int(bool(re.match(r'^[a-z]:', normalized))),
            int(normalized.startswith('//')), normalized.count('/'),
            int('/' in text and '\\' in text), -minimum, parts.count('.'),
            int('\x00' in text), len(re.findall(r'%(?:2e|2f|5c|00|3a)', text)),
        ])
    maxima = [max(row[i] for row in signals) for i in range(len(signals[0]))]
    return extract_features(path) + maxima + [sum(a != b for a, b in zip(views, views[1:]))]
