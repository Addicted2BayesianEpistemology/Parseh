#!/usr/bin/env python3
"""Install optional, versioned component-only packs. Runtime needs no internet.

python3 lib/getdecomposition.py kanjivg|makemeahanzi|cjkvi
python3 lib/getdecomposition.py kanjivg --input path/to/source.zip

Downloads are pinned, checked, parsed in a temporary file and atomically
published. Source notices and transformation details travel inside each pack.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import time
import urllib.request
import zipfile
from contextlib import closing
from pathlib import Path

import decomposition as domain
import decomposition_sources as parsers

SOURCES = {
    'kanjivg': ('KanjiVG/kanjivg', '422b5538595676da918c288a4230cb5e22a1ee7e', 'data.zip',
                'ac165db15581cfd40f1ac774d23743f61ce1c48e50ce57681f39575607ee9626'),
    'makemeahanzi': ('skishore/makemeahanzi', 'bddc96d41bef78427ed0e034e9f7e31d71fd1b92', 'dictionary.txt',
                    '744bb05d5b0742e9ee35c37791f94d56a173349b3367569e7ca11e510364d203'),
    'cjkvi': ('cjkvi/cjkvi-ids', '86b4d16159f0079437870408f0ca186e529015db', 'ids.txt',
              'bfc70a8c09f9f5616ebf0543bd6681e67314e9f7ae2307e5ae8c6f15bdc5c6a6'),
}


def fetch(url, path, say):
    request = urllib.request.Request(url, headers={'User-Agent': 'Parseh/1.0 (local component installer)'})
    with urllib.request.urlopen(request, timeout=120) as response, open(path, 'wb') as out:
        total = 0
        while True:
            block = response.read(1 << 18)
            if not block:
                break
            total += len(block)
            if total > 100_000_000:
                raise ValueError('component download exceeded its size limit')
            out.write(block)
            say('Downloading component data: %.1f MB' % (total / 1e6))


def build(source, input_path=None, say=print):
    if source not in SOURCES:
        raise ValueError('unknown decomposition source')
    repo, revision, filename, expected = SOURCES[source]
    raw = 'https://raw.githubusercontent.com/%s/%s/' % (repo, revision)
    url = 'https://codeload.github.com/%s/zip/%s' % (repo, revision) if source == 'kanjivg' else raw + filename
    target = domain.path_for(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.build-', dir=target.parent) as tmp:
        tmp = Path(tmp)
        data = Path(input_path) if input_path else tmp / filename
        if not input_path:
            fetch(url, data, say)
        digest = hashlib.sha256(data.read_bytes()).hexdigest()
        if not input_path and digest != expected:
            raise ValueError('download checksum does not match the tested source revision')
        notices = {}
        if source == 'kanjivg':
            with zipfile.ZipFile(data) as archive:
                for name in archive.namelist():
                    if name.endswith('/COPYING'):
                        notices['COPYING'] = archive.read(name).decode('utf-8')
                        break
        else:
            for name in (['COPYING', 'LGPL'] if source == 'makemeahanzi' else ['README.md']):
                local = data.parent / name
                if input_path:
                    if local.exists():
                        notices[name] = local.read_text(encoding='utf-8')
                else:
                    fetch(raw + name, tmp / name, say)
                    notices[name] = (tmp / name).read_text(encoding='utf-8')
        say('Building component trees…')
        db = tmp / 'pack.db'
        with closing(sqlite3.connect(db)) as conn:
            conn.executescript('CREATE TABLE node(lang TEXT, character TEXT, tree TEXT, PRIMARY KEY(lang, character));'
                               'CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);')
            entries = 0
            for lang, character, tree in getattr(parsers, source)(data):
                conn.execute('INSERT OR REPLACE INTO node VALUES(?,?,?)',
                             (lang, character, json.dumps(tree, ensure_ascii=False, separators=(',', ':'))))
                entries += 1
            if not entries:
                raise ValueError('no component entries found; the previous pack has been kept')
            meta = dict(domain.PACKS[source], source=source, schema=1, entries=entries,
                        built=time.strftime('%Y-%m-%d'), revision=revision if digest == expected else 'local import',
                        sha256=digest, source_url=url, notices=notices,
                        transformation='Parseh component-only conversion: IDS parsed; graphical SVG groups flattened; '
                                       'stroke-order parts coalesced. No meanings, readings, paths or pronunciations imported.')
            conn.execute('INSERT INTO meta VALUES(?,?)', ('manifest', json.dumps(meta, ensure_ascii=False)))
            conn.commit()
        os.replace(db, target)
    say('Installed %s: %s component entries' % (domain.PACKS[source]['name'], entries))
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', choices=SOURCES)
    parser.add_argument('--input', help='local upstream source archive/file, for offline installation')
    args = parser.parse_args()
    build(args.source, args.input)


if __name__ == '__main__':
    main()
