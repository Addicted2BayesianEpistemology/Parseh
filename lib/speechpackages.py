# SPDX-License-Identifier: GPL-3.0-or-later
"""Import the catalogue's prebuilt, hash-pinned Whisper packages.

No browser-supplied path, recipe, checkpoint or executable is accepted. Model
packages contain only the exact files already pinned in our release catalogue.
Large archives and model files are streamed, and a cancelled/failed import
cannot replace a complete package or installed model.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

import download
import speechmodels

ROOT = Path(__file__).resolve().parents[1]
PREPARED_ROOT = ROOT / 'dist' / 'speech-models'
MAX_ARCHIVE = 4 << 30
CHUNK = 1 << 20


class PackageError(ValueError):
    pass


def pin(model):
    package = speechmodels.MODEL_PINS.get(model)
    if not package or package.get('distribution') != 'local-package':
        raise PackageError('Choose a model that accepts a prepared package.')
    return package


def cache_root():
    import getstt
    return Path(getstt.STT_DIR) / 'packages'


def _complete(folder, package):
    try:
        return (folder.is_dir() and not folder.is_symlink() and all(
            (folder / name).is_file() and not (folder / name).is_symlink() and
            (folder / name).stat().st_size == size
            for name, (_sha, size) in package['files'].items()))
    except OSError:
        return False


def folder(model):
    """Cheap offline availability check; every byte is hashed again at install."""
    package = pin(model)
    for root in (cache_root(), PREPARED_ROOT):
        candidate = Path(root) / model / package['revision']
        if _complete(candidate, package):
            return candidate
    return None


def available(model):
    try:
        return folder(model) is not None
    except PackageError:
        return False


def describe(model):
    package = pin(model)
    return {'name': package['package_name'], 'size': package['package_size'],
            'sha256': package['package_sha256']}


def _replace(stage, final):
    backup = final.with_name('.old-' + final.name)
    if backup.exists():
        shutil.rmtree(backup)
    had = final.exists()
    if had:
        os.replace(final, backup)
    try:
        os.replace(stage, final)
    except OSError:
        if had:
            os.replace(backup, final)
        raise
    if had:
        shutil.rmtree(backup)


def import_stream(model, stream, length, *, cancel=None, progress=None):
    """Receive and validate a pinned ZIP, then atomically publish its assets."""
    package = pin(model)
    expected = package['package_size']
    if type(length) is not int or length != expected or length > MAX_ARCHIVE:
        raise PackageError('This ZIP does not match the expected model package size.')
    root = cache_root() / model
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.import-', dir=root))
    archive = stage / '.upload.zip'
    try:
        digest, done = hashlib.sha256(), 0
        with archive.open('wb') as target:
            while done < length:
                download.check(cancel)
                chunk = stream.read(min(CHUNK, length - done))
                if not chunk:
                    raise PackageError('The package upload did not finish. Choose it again to retry.')
                target.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, length, 'upload')
        download.check(cancel)
        if digest.hexdigest() != package['package_sha256']:
            raise PackageError('The package checksum does not match this release. The existing model is unchanged.')
        try:
            with zipfile.ZipFile(archive) as bundle:
                entries = bundle.infolist()
                names = [entry.filename for entry in entries]
                if len(names) != len(set(names)) or set(names) != set(package['files']):
                    raise PackageError('This package contains unexpected or missing files.')
                total = sum(size for _sha, size in package['files'].values())
                done = 0
                for entry in entries:
                    download.check(cancel)
                    mode = entry.external_attr >> 16
                    sha, size = package['files'][entry.filename]
                    if (entry.is_dir() or stat.S_ISLNK(mode) or
                            (stat.S_IFMT(mode) not in (0, stat.S_IFREG)) or
                            entry.flag_bits & 1 or entry.file_size != size):
                        raise PackageError('This package contains an unsupported file.')
                    digest, copied = hashlib.sha256(), 0
                    with bundle.open(entry) as source, (stage / entry.filename).open('wb') as target:
                        while True:
                            download.check(cancel)
                            chunk = source.read(min(CHUNK, size - copied + 1))
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > size:
                                raise PackageError('A model file exceeds its expected size.')
                            target.write(chunk)
                            digest.update(chunk)
                            if progress:
                                progress(done + copied, total, 'verify')
                    if copied != size or digest.hexdigest() != sha:
                        raise PackageError('A model file failed its checksum. The existing model is unchanged.')
                    done += copied
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
            raise PackageError('This is not a complete supported model package.') from None
        speechmodels.validate_assets(model, stage)
        archive.unlink()
        (stage / '.package.json').write_text(json.dumps({
            'model': model, 'revision': package['revision'], 'sha256': package['package_sha256']
        }), encoding='utf-8')
        download.check(cancel)
        _replace(stage, root / package['revision'])
        return sum(size for _sha, size in package['files'].values())
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def copy_verified(source, destination, sha, size, *, cancel=None, progress=None):
    """Resume a local file copy and verify the complete file before publishing."""
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_file() or source.stat().st_size != size:
        raise PackageError('The prepared model package is incomplete. Import it again.')
    if destination.is_file() and not destination.is_symlink() and destination.stat().st_size == size:
        digest = hashlib.sha256()
        with destination.open('rb') as existing:
            while True:
                download.check(cancel)
                chunk = existing.read(CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
        if digest.hexdigest() == sha:
            if progress:
                progress(size)
            return
    partial = destination.with_name(destination.name + '.part')
    if partial.is_symlink():
        raise PackageError('The model staging folder contains an unsupported link.')
    have = partial.stat().st_size if partial.is_file() else 0
    if have > size:
        partial.unlink()
        have = 0
    digest = hashlib.sha256()
    if have:
        with partial.open('rb') as existing:
            while True:
                download.check(cancel)
                chunk = existing.read(CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
    with source.open('rb') as original, partial.open('ab' if have else 'wb') as target:
        original.seek(have)
        while have < size:
            download.check(cancel)
            chunk = original.read(min(CHUNK, size - have))
            if not chunk:
                raise PackageError('The prepared model package was changed during installation.')
            target.write(chunk)
            digest.update(chunk)
            have += len(chunk)
            if progress:
                progress(have)
    download.check(cancel)
    if digest.hexdigest() != sha:
        partial.unlink()
        raise PackageError('A prepared model file failed its checksum. Import it again.')
    os.replace(partial, destination)


def remove(model):
    """Remove imported copies only; a maintainer's prepared output is preserved."""
    root = cache_root() / model
    if not root.exists():
        return 0
    total = sum(path.stat().st_size for path in root.rglob('*') if path.is_file())
    shutil.rmtree(root)
    return total


def sweep():
    root = cache_root()
    if root.is_dir():
        for stage in root.glob('*/.import-*'):
            shutil.rmtree(stage, ignore_errors=True)
