#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install optional, versioned component-only packs. Runtime needs no internet.

python3 lib/getdecomposition.py kanjivg|makemeahanzi|cjkvi
python3 lib/getdecomposition.py kanjivg --input path/to/source.zip

Downloads are pinned, checked, parsed in a temporary file and atomically
published. Source notices and transformation details travel inside each pack.

A download goes through lib/download.py: it resumes where a cut line or Stop
left it (components/.download-<pack>-<file>.part), says how far it has got,
and is refused unless it has the digest pinned below. A pack's build reports
its entries against the count the pinned source is known to hold.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import time
import zipfile
from contextlib import closing
from pathlib import Path

import decomposition as domain
import decomposition_sources as parsers
import download                 # resumable, stoppable, and says how far
import version                  # who is asking, in the User-Agent

# the User-Agent every request here sends, as the other downloaders' UA
UA = 'Parseh/%s (local component installer)' % version.VERSION

SOURCES = {
    'kanjivg': ('KanjiVG/kanjivg', '422b5538595676da918c288a4230cb5e22a1ee7e', 'data.zip',
                'ac165db15581cfd40f1ac774d23743f61ce1c48e50ce57681f39575607ee9626'),
    'makemeahanzi': ('skishore/makemeahanzi', 'bddc96d41bef78427ed0e034e9f7e31d71fd1b92', 'dictionary.txt',
                    '744bb05d5b0742e9ee35c37791f94d56a173349b3367569e7ca11e510364d203'),
    'cjkvi': ('cjkvi/cjkvi-ids', '86b4d16159f0079437870408f0ca186e529015db', 'ids.txt',
              'bfc70a8c09f9f5616ebf0543bd6681e67314e9f7ae2307e5ae8c6f15bdc5c6a6'),
}

# WHAT EACH PACK COSTS, MEASURED -- exactly, because each source is pinned by
# its digest and so its size cannot move: (the pinned file's bytes, its
# notices' bytes, the built pack's bytes, the entries it holds). The files'
# sizes as GitHub served them on 2026-09-25 (KanjiVG's generated archive
# names no size of its own, so this is also what its bar counts against);
# the packs as built from them on 2026-09-24 and 2026-09-25. A pack's size
# moves only when the conversion here does.
MEASURED = {
    'kanjivg': (23_497_394, 0, 2_654_208, 6_704),
    'makemeahanzi': (2_570_140, 10_783, 2_000_000, 9_574),
    'cjkvi': (2_161_631, 3_644, 34_488_320, 176_521),
}
LIMIT = 100_000_000             # no pinned source is a quarter of this

# THE SHAPE OF A PACK, components/<source>.db -- the node and meta tables
# build() makes -- as a number (lib/version.py FORMATS).  The one number a
# pack carries itself, as its manifest's "schema", so it is written from
# here.  RAISE IT when the shape changes so that the Parseh before this one
# would read a pack wrong.
PACK_FORMAT = 1


def fetch(url, path, say, progress=None, cancel=None, sha256=None, size=None):
    download.fetch(url, str(path), say=say, progress=progress, cancel=cancel, sha256=sha256,
                   size=size, limit=LIMIT, headers={'User-Agent': UA}, timeout=120)


def _download_path(source):
    """Where a pack's source is downloaded to: beside the packs, and kept there until the pack is built,
    so that a download cut short -- or a build stopped after it -- is carried on from, not started again."""
    _repo, _revision, filename, _expected = SOURCES[source]
    return domain.path_for(source).parent / ('.download-%s-%s' % (source, filename))


def plan(source, input_path=None, *, probe=True):
    """What installing this pack will cost, before anything is fetched: lib/download.py's plan() shape. Every
    size is MEASURED (the sources are pinned), so `probe` is never needed; it is taken for the same shape of call
    as the other downloaders' plan()."""
    if source not in SOURCES:
        raise ValueError('unknown decomposition source')
    size, notices, kept, _entries = MEASURED[source]
    if input_path:
        return download.plan(0, kept=kept)
    dest = str(_download_path(source))
    have = os.path.getsize(dest) if os.path.isfile(dest) else download.leftover(dest)
    return download.plan(size + notices, measured=True, kept=kept, have=have)


def discard(source):
    """Throw away a downloaded or half-downloaded source left by a build that was stopped. Returns the bytes
    freed; an installed pack is untouched."""
    dest = str(_download_path(source))
    freed = download.leftover(dest)
    download.discard(dest)
    if os.path.isfile(dest):
        freed += os.path.getsize(dest)
        os.unlink(dest)
    return freed


def build(source, input_path=None, say=print, progress=None, cancel=None):
    """Install one pack. `progress(done, total, phase)` hears the download ("download": bytes) and the build
    ("build": entries against the pinned source's known count); `cancel` stops either as download.Cancelled,
    keeping the download to carry on from and leaving the installed pack as it was."""
    if source not in SOURCES:
        raise ValueError('unknown decomposition source')
    repo, revision, filename, expected = SOURCES[source]
    raw = 'https://raw.githubusercontent.com/%s/%s/' % (repo, revision)
    url = 'https://codeload.github.com/%s/zip/%s' % (repo, revision) if source == 'kanjivg' else raw + filename
    target = domain.path_for(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    size, _notices, _kept, known = MEASURED[source]
    fetched = None
    if not input_path:
        fetched = _download_path(source)
        if fetched.is_file() and download.digest(fetched) == expected:
            say('Using the component data already here')
        else:
            say('Downloading component data…')
            fetch(url, fetched, say, progress=progress, cancel=cancel, sha256=expected, size=size)
    with tempfile.TemporaryDirectory(prefix='.build-', dir=target.parent) as tmp:
        tmp = Path(tmp)
        data = Path(input_path) if input_path else fetched
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
                    fetch(raw + name, tmp / name, say, cancel=cancel)
                    notices[name] = (tmp / name).read_text(encoding='utf-8')
        say('Building component trees…')
        meter = download.Meter(progress, cancel, total=None if input_path else known)
        db = tmp / 'pack.db'
        with closing(sqlite3.connect(db)) as conn:
            conn.executescript('CREATE TABLE node(lang TEXT, character TEXT, tree TEXT, PRIMARY KEY(lang, character));'
                               'CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);')
            entries = 0
            for lang, character, tree in getattr(parsers, source)(data):
                conn.execute('INSERT OR REPLACE INTO node VALUES(?,?,?)',
                             (lang, character, json.dumps(tree, ensure_ascii=False, separators=(',', ':'))))
                entries += 1
                if entries % 200 == 0:
                    meter.at(min(entries, meter.total) if meter.total else entries)
            if not entries:
                raise ValueError('no component entries found; the previous pack has been kept')
            meta = dict(domain.PACKS[source], source=source, schema=PACK_FORMAT, entries=entries,
                        built=time.strftime('%Y-%m-%d'), revision=revision if digest == expected else 'local import',
                        sha256=digest, source_url=url, notices=notices,
                        transformation='Parseh component-only conversion: IDS parsed; graphical SVG groups flattened; '
                                       'stroke-order parts coalesced. No meanings, readings, paths or pronunciations imported.')
            conn.execute('INSERT INTO meta VALUES(?,?)', ('manifest', json.dumps(meta, ensure_ascii=False)))
            conn.commit()
        os.replace(db, target)
    meter.end()
    if fetched is not None:
        fetched.unlink(missing_ok=True)
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
