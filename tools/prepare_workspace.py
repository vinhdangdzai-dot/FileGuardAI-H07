"""Restore ignored local inputs from versioned evidence, without overwriting."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.generate_dataset import write_dataset
from ml.evaluate import sha256


def main():
    data = ROOT / 'data/paths_synthetic.csv'
    if not data.exists():
        write_dataset(data)
        print('Generated deterministic synthetic dataset')
    model = ROOT / 'artifacts/model.joblib'
    frozen = ROOT / 'docs/evaluations/20261116T154448Z_7a27a7/baseline_model.joblib'
    expected = '4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322'
    if not model.exists():
        if sha256(frozen) != expected:
            raise ValueError('Trusted versioned reference model hash mismatch')
        model.parent.mkdir(exist_ok=True)
        shutil.copy2(frozen, model)
        print('Restored exact deployed v1 reference; v2 not deployed')


if __name__ == '__main__':
    main()
