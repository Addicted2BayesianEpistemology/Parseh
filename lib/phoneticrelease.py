#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify immutable PhoneticXeus release pins without fetching model weights.

    python lib/phoneticrelease.py          validate local release manifests
    python lib/phoneticrelease.py --online verify upstream metadata/source bytes

This explicit maintainer action reads metadata, tiny source assets and published
wheel hashes only.  It does not install a runtime or download tensors.  Ordinary
Settings and transcription never perform these requests.
"""
import argparse
import hashlib
import json
import re
from urllib.parse import unquote
from urllib.request import Request, urlopen

from phoneticpins import MODEL, RUNTIME, validate

MAX_SMALL_FILE = 1 << 20


def read(url, limit=MAX_SMALL_FILE, headers=None):
    with urlopen(Request(url, headers=headers or {}), timeout=30) as response:
        value = response.read(limit + 1)
    if len(value) > limit:
        raise ValueError('Upstream metadata exceeded the release-check bound.')
    return value


def check_model():
    url = 'https://huggingface.co/api/models/%s/revision/%s?blobs=true' % (MODEL['repo'], MODEL['revision'])
    info = json.loads(read(url))
    if info['sha'] != MODEL['revision'] or info['cardData']['license'] != MODEL['licence']:
        raise ValueError('Upstream revision or licence differs from the release pin.')
    files = {item['rfilename']: item for item in info['siblings']}
    for name, (sha, size) in MODEL['files'].items():
        item = files[name]
        if item['size'] != size:
            raise ValueError('Upstream model asset size differs: ' + name)
        if item.get('lfs'):
            actual = item['lfs']['sha256']
        else:
            if size > MAX_SMALL_FILE:
                raise ValueError('Large assets must expose their upstream SHA-256 metadata.')
            asset = 'https://huggingface.co/%s/resolve/%s/%s' % (MODEL['repo'], MODEL['revision'], name)
            content = read(asset, MAX_SMALL_FILE)
            if len(content) != size:
                raise ValueError('Upstream model asset is incomplete: ' + name)
            actual = hashlib.sha256(content).hexdigest()
        if actual != sha:
            raise ValueError('Upstream model asset checksum differs: ' + name)
    return len(MODEL['files'])


def check_runtime():
    metadata, cpu_indexes = {}, {}
    count = 0
    for rows in RUNTIME['platforms'].values():
        for row in rows:
            package, version = row['package'], row['version']
            if '+cpu' in version:
                if package not in cpu_indexes:
                    cpu_indexes[package] = read('https://download.pytorch.org/whl/cpu/%s/' % package,
                                                limit=8 << 20).decode('utf-8')
                filename = unquote(row['url'].rsplit('/', 1)[-1])
                lines = [line for line in cpu_indexes[package].splitlines() if filename in unquote(line)]
                if not any('sha256=' + row['sha256'] in line for line in lines):
                    raise ValueError('Official CPU runtime checksum differs: ' + package)
                with urlopen(Request(row['url'], method='HEAD'), timeout=30) as response:
                    if int(response.headers['Content-Length']) != row['size']:
                        raise ValueError('Official CPU runtime size differs: ' + package)
            else:
                key = package, version
                if key not in metadata:
                    metadata[key] = json.loads(read('https://pypi.org/pypi/%s/%s/json' % key,
                                                       limit=8 << 20))
                matches = [asset for asset in metadata[key]['urls'] if asset['url'] == row['url']]
                if (len(matches) != 1 or matches[0]['digests']['sha256'] != row['sha256']
                        or matches[0]['size'] != row['size']):
                    raise ValueError('Official runtime checksum/size differs: ' + package)
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--online', action='store_true')
    args = parser.parse_args()
    validate()
    result = {'revision': MODEL['revision'], 'licence': MODEL['licence'],
              'model_assets': len(MODEL['files']), 'runtime_platforms': len(RUNTIME['platforms']),
              'validation': 'local-pins'}
    if args.online:
        result.update(model_assets=check_model(), runtime_wheels=check_runtime(), validation='upstream-verified')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
