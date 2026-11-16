"""Three-way family + canonical-equivalence split; never relabel data."""
from collections import defaultdict
import numpy as np
from .external_corpus import canonical_key


def strict_split(rows, seed=2026):
    parents = {r['family']: r['family'] for r in rows}
    def find(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x
    seen, labels = {}, defaultdict(set)
    for row in rows:
        if str(row['label']) not in {'0', '1'}:
            raise ValueError('Annotated binary labels required')
        key = canonical_key(row['path'])
        labels[key].add(int(row['label']))
        if len(labels[key]) != 1:
            raise ValueError('Canonical-equivalent rows have conflicting labels; do not auto-relabel')
        if key in seen:
            left, right = sorted([find(row['family']), find(seen[key])])
            parents[right] = left
        seen[key] = row['family']
    components = defaultdict(list)
    for row in rows:
        components[find(row['family'])].append(row)
    rng = np.random.default_rng(seed)
    result = {'train': [], 'validation': [], 'test': []}
    for label in (0, 1):
        groups = sorted(k for k, subset in components.items() if {int(r['label']) for r in subset} == {label})
        if len(groups) < 3:
            raise ValueError('Insufficient independent components for train/validation/test')
        rng.shuffle(groups)
        ntest = min(max(1, round(.2 * len(groups))), len(groups) - 2)
        nval = min(max(1, round(.2 * len(groups))), len(groups) - ntest - 1)
        allocation = [('test', groups[:ntest]), ('validation', groups[ntest:ntest+nval]),
                      ('train', groups[ntest+nval:])]
        for name, selected in allocation:
            result[name].extend(r for group in selected for r in components[group])
    if sum(map(len, result.values())) != len(rows):
        raise ValueError('Mixed-label family/component or incomplete allocation')
    for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        if ({r['family'] for r in result[a]} & {r['family'] for r in result[b]}
                or {canonical_key(r['path']) for r in result[a]} & {canonical_key(r['path']) for r in result[b]}):
            raise ValueError('Partition overlap')
    return result, {'seed': seed, 'components': len(components), 'family_overlap': [], 'path_overlap': [],
                    'canonical_overlap': [], 'rows': {name: len(part) for name, part in result.items()},
                    'labels': {name: {str(label): sum(int(r['label']) == label for r in part) for label in (0, 1)}
                               for name, part in result.items()}}
