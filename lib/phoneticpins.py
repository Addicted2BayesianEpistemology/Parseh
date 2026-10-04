# SPDX-License-Identifier: GPL-3.0-or-later
"""Audited, immutable upstream PhoneticXeus and isolated CPU wheel manifests.

Weights and upstream source are downloaded together only after a user's Install
action.  The ordinary Parseh interpreter never imports that source or PyTorch.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = json.loads((HERE / 'phonetic-model-pins.json').read_text(encoding='utf-8'))
RUNTIME = json.loads((HERE / 'phonetic-runtime-pins.json').read_text(encoding='utf-8'))
PARTS = ('phonetic-runtime', 'phonetic-model')
MODEL_BYTES = sum(value[1] for value in MODEL['files'].values())


def validate():
    import re
    sha = re.compile(r'^[0-9a-f]{64}$')
    if not re.fullmatch(r'[0-9a-f]{40}', MODEL['revision']):
        raise ValueError('PhoneticXeus source revision must be immutable.')
    for name, (digest, size) in MODEL['files'].items():
        if (Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name
                or not sha.fullmatch(digest) or type(size) is not int or size < 0):
            raise ValueError('Invalid PhoneticXeus file pin.')
    for rows in RUNTIME['platforms'].values():
        names = set()
        for row in rows:
            if (not sha.fullmatch(row['sha256']) or row['size'] <= 0
                    or row['package'] in names
                    or not row['url'].startswith(('https://files.pythonhosted.org/',
                                                   'https://download.pytorch.org/'))):
                raise ValueError('Invalid PhoneticXeus runtime wheel pin.')
            names.add(row['package'])


validate()
