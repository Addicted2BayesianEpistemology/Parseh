# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent optional audio-to-IPA installation; standard library only.

No model code is downloaded or imported while displaying status.  The pinned
2.3 GB safetensors checkpoint and its audited source tree are fetched on an
explicit model-install action.  CPU PyTorch lives in its own pip-target tree,
not in the Whisper runtime or Parseh's ordinary environment.
"""
import argparse
import atexit
import contextlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import unquote, urlsplit

import download
from phoneticpins import MODEL, RUNTIME, PARTS, MODEL_BYTES

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / 'stt' / 'phonetic'
WORKER = Path(__file__).resolve().with_name('phoneticworker.py')
LOCK = threading.RLock()
INSTALL = threading.RLock()
LIVE = set()
USERS = 0
SIZES = {}


class PhoneticError(ValueError):
    def __init__(self, code, say):
        super().__init__(say)
        self.code, self.say = code, say


def platform_key():
    machine = platform.machine().lower()
    if sys.platform == 'win32' and machine in ('amd64', 'x86_64'):
        return 'windows amd64'
    if sys.platform == 'darwin' and machine in ('arm64', 'aarch64', 'x86_64'):
        return 'macOS ' + ('arm64' if machine in ('arm64', 'aarch64') else 'x86_64')
    if sys.platform.startswith('linux') and machine in ('x86_64', 'amd64', 'aarch64', 'arm64'):
        return 'linux ' + ('x86_64' if machine in ('x86_64', 'amd64') else 'aarch64')
    return None


def unavailable_reason():
    if sys.version_info[:2] != (3, 12):
        return 'PhoneticXeus needs Parseh’s Python 3.12 installation.'
    if platform_key() not in RUNTIME['platforms']:
        return 'The PhoneticXeus runtime is not packaged for this kind of computer.'
    if sys.platform.startswith('linux'):
        libc, revision = platform.libc_ver()
        if libc and libc != 'glibc':
            return 'PhoneticXeus needs a Linux installation using glibc 2.28 or newer.'
        try:
            if revision and tuple(int(n) for n in revision.split('.')[:2]) < (2, 28):
                return 'PhoneticXeus needs glibc 2.28 or newer on Linux.'
        except ValueError:
            pass
    if sys.platform == 'darwin':
        try:
            major = int(platform.mac_ver()[0].split('.')[0])
        except (ValueError, IndexError):
            major = 0
        if major and major < 13:
            return 'PhoneticXeus needs macOS 13 or newer.'
    return None


def model_dir():
    return DIRECTORY / 'models' / MODEL['revision']


def runtime_dir():
    return DIRECTORY / 'runtime' / ('%s-cp312' % RUNTIME['generation'])


def _rows():
    return RUNTIME['platforms'].get(platform_key(), [])


def _record(folder):
    try:
        p = folder / '.parseh.json'
        if p.stat().st_size > 65536:
            return {}
        value = json.loads(p.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _distribution_versions(folder):
    result = {}
    for p in folder.glob('*.dist-info/METADATA'):
        try:
            name = version = None
            for line in p.read_text(encoding='utf-8').splitlines():
                if line.startswith('Name: '):
                    name = line[6:].lower().replace('_', '-')
                elif line.startswith('Version: '):
                    version = line[9:]
                if name and version:
                    result[name] = version
                    break
        except OSError:
            continue
    return result


def runtime_ready():
    folder = runtime_dir()
    rec = _record(folder)
    if (rec.get('generation') != RUNTIME['generation'] or rec.get('platform') != platform_key()
            or rec.get('python') != '3.12'):
        return False
    got = _distribution_versions(folder)
    return bool(_rows()) and all(got.get(row['package'].lower().replace('_', '-')) == row['version']
                                for row in _rows())


def model_ready():
    folder = model_dir()
    rec = _record(folder)
    if rec.get('revision') != MODEL['revision'] or rec.get('files') != MODEL['files']:
        return False
    try:
        return all((folder / name).is_file() and not (folder / name).is_symlink()
                   and (folder / name).stat().st_size == size
                   for name, (_sha, size) in MODEL['files'].items())
    except OSError:
        return False


def _size(path):
    key = str(path)
    now = time.monotonic()
    with LOCK:
        held = SIZES.get(key)
        if held and now - held[0] < 30:
            return held[1]
    try:
        size = sum(p.stat().st_size for p in path.rglob('*') if p.is_file())
    except OSError:
        size = 0
    with LOCK:
        if len(SIZES) > 32:
            SIZES.clear()
        SIZES[key] = now, size
    return size


def plan(part, **_kwargs):
    if part not in PARTS:
        raise PhoneticError('bad-part', 'Choose the PhoneticXeus program or model.')
    amount = sum(row['size'] for row in _rows()) if part == 'phonetic-runtime' else MODEL_BYTES
    partial = (DIRECTORY / 'wheels' / (platform_key() or 'unknown').replace(' ', '-')
               if part == 'phonetic-runtime' else model_dir().with_name(MODEL['revision'] + '.part'))
    return download.plan(download=amount, measured=True,
                         kept=amount * 3 if part == 'phonetic-runtime' else amount,
                         have=min(amount, _size(partial)), peak=amount * 4 if part == 'phonetic-runtime' else amount)


def status():
    reason = unavailable_reason()
    runtime, model = runtime_ready(), model_ready()
    runtime_have, model_have = runtime_dir().exists(), model_dir().exists()
    return {'ready': runtime and model and reason is None, 'available': reason is None,
            'say': reason or ('Ready to estimate heard IPA.' if runtime and model else
                             'Install the separate program and model to add heard IPA.'),
            'source': MODEL['repo'], 'revision': MODEL['revision'], 'licence': MODEL['licence'],
            'licence_url': MODEL['license_url'], 'backend': 'CPU',
            'runtime': {'ready': runtime, 'have': runtime_have,
                        'state': 'ready' if runtime else 'broken' if runtime_have else 'absent',
                        'say': reason or ('Installed · CPU' if runtime else
                                         'Incomplete program. Install it again.' if runtime_have else 'Not installed'),
                        'download': sum(r['size'] for r in _rows()), 'kept': _size(runtime_dir())},
            'model': {'ready': model, 'have': model_have,
                      'state': 'ready' if model else 'broken' if model_have else 'absent',
                      'label': 'PhoneticXeus · heard IPA', 'revision': MODEL['revision'],
                      'licence': MODEL['licence'], 'download': MODEL_BYTES,
                      'kept': _size(model_dir()), 'say': 'Installed' if model else
                      'Incomplete model. Get it again.' if model_have else 'Not installed'},
            'limits': 'Audio-derived IPA is an estimate; cropped word boundaries may include nearby sounds. '
                      'This separate 575M-parameter model uses CPU float32 and needs several GB of memory. '
                      'GPU and Apple Metal acceleration are not included in this runtime.'}


def track(proc):
    with LOCK:
        LIVE.add(proc)


def untrack(proc):
    with LOCK:
        LIVE.discard(proc)


def terminate(proc):
    if proc.poll() is not None:
        return
    try:
        if os.name == 'nt':
            proc.kill()
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass


def stop_all():
    with LOCK:
        children = list(LIVE)
    for proc in children:
        terminate(proc)


atexit.register(stop_all)


@contextlib.contextmanager
def using():
    global USERS
    with LOCK:
        USERS += 1
    try:
        yield
    finally:
        with LOCK:
            USERS -= 1


def _swap(stage, final):
    """Publish a verified complete tree; restore the old tree on rename failure."""
    final.parent.mkdir(parents=True, exist_ok=True)
    backup = final.with_name(final.name + '.old')
    if backup.exists():
        shutil.rmtree(backup)
    old = final.exists()
    if old:
        os.replace(final, backup)
    try:
        os.replace(stage, final)
    except OSError:
        if old:
            os.replace(backup, final)
        raise
    if old:
        shutil.rmtree(backup)


def _fetch(url, path, sha, size, say, progress, stop, done, total):
    download.check(stop)
    if not path.is_file() or path.stat().st_size != size or download.digest(path) != sha:
        download.fetch(url, str(path), sha256=sha, size=size, limit=size, timeout=60,
                       cancel=stop, say=say, progress=download.shifted(progress, done, total))
    if progress:
        progress(done + size, total, 'download')


def _install_model(stop, progress, say):
    if model_ready() and all(download.digest(model_dir() / name) == sha
                             for name, (sha, _size) in MODEL['files'].items()):
        return
    stage = model_dir().with_name(MODEL['revision'] + '.part')
    stage.mkdir(parents=True, exist_ok=True)
    done = 0
    for name, (sha, size) in MODEL['files'].items():
        url = 'https://huggingface.co/%s/resolve/%s/%s' % (MODEL['repo'], MODEL['revision'], name)
        _fetch(url, stage / name, sha, size, say, progress, stop, done, MODEL_BYTES)
        done += size
    download.check(stop)
    (stage / '.parseh.json').write_text(json.dumps({'revision': MODEL['revision'], 'files': MODEL['files'],
        'licence': MODEL['licence'], 'installed': time.strftime('%Y-%m-%d')}), encoding='utf-8')
    _swap(stage, model_dir())


def _install_runtime(stop, progress, say):
    reason = unavailable_reason()
    if reason:
        raise PhoneticError('runtime-unavailable', reason)
    if runtime_ready():
        return
    cache = DIRECTORY / 'wheels' / platform_key().replace(' ', '-')
    cache.mkdir(parents=True, exist_ok=True)
    rows = _rows()
    total = sum(row['size'] for row in rows)
    done = 0
    requirements = []
    for row in rows:
        name = unquote(urlsplit(row['url']).path.rsplit('/', 1)[-1])
        path = cache / name
        _fetch(row['url'], path, row['sha256'], row['size'], say, progress, stop, done, total)
        requirements.append('%s @ %s --hash=sha256:%s' % (row['package'], path.resolve().as_uri(), row['sha256']))
        done += row['size']
    download.check(stop)
    final = runtime_dir()
    final.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='phonetic-stage-', dir=final.parent))
    req = stage.parent / (stage.name + '.txt')
    req.write_text('\n'.join(requirements) + '\n', encoding='utf-8')
    proc = None
    ended = threading.Event()
    try:
        if progress:
            progress(total, total, 'build')
        say('Putting the separate PhoneticXeus program in place.')
        env = dict(os.environ, PYTHONNOUSERSITE='1', PIP_CONFIG_FILE=os.devnull)
        env.pop('PYTHONPATH', None)
        command = [sys.executable, '-u', '-m', 'pip', 'install', '--isolated', '--no-index',
                   '--no-deps', '--require-hashes', '--only-binary=:all:', '--target', str(stage),
                   '-r', str(req), '--disable-pip-version-check', '--no-input', '--no-color']
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                stdin=subprocess.DEVNULL, env=env, start_new_session=os.name != 'nt')
        track(proc)
        while proc.poll() is None:
            if download.stopped(stop):
                terminate(proc)
                raise download.Cancelled()
            ended.wait(.1)
        if proc.returncode:
            raise PhoneticError('runtime-install', 'The separate PhoneticXeus program could not be installed. '
                               'Check disk space and this Python’s supported platform, then retry.')
        got = _distribution_versions(stage)
        if any(got.get(r['package'].lower().replace('_', '-')) != r['version'] for r in rows):
            raise PhoneticError('runtime-incomplete', 'The PhoneticXeus program is incomplete; nothing was installed.')
        (stage / '.parseh.json').write_text(json.dumps({'generation': RUNTIME['generation'],
            'platform': platform_key(), 'python': '3.12', 'backend': 'CPU'}), encoding='utf-8')
        download.check(stop)
        _swap(stage, final)
    finally:
        if proc is not None:
            terminate(proc)
            proc.wait()
            untrack(proc)
        shutil.rmtree(stage, ignore_errors=True)
        req.unlink(missing_ok=True)


def get(part, stop=None, progress=None, say=print):
    if part not in PARTS:
        raise PhoneticError('bad-part', 'Choose the PhoneticXeus program or model.')
    while not INSTALL.acquire(timeout=.1):
        download.check(stop)
    try:
        download.check(stop)
        with LOCK:
            if USERS or LIVE:
                raise PhoneticError('in-use', 'PhoneticXeus is working. Stop or finish transcription first.')
        if part == 'phonetic-model':
            _install_model(stop, progress, say)
        else:
            _install_runtime(stop, progress, say)
        with LOCK:
            SIZES.clear()
        say('PhoneticXeus %s installed.' % ('model' if part == 'phonetic-model' else 'program'))
        return _size(model_dir() if part == 'phonetic-model' else runtime_dir())
    finally:
        with LOCK:
            SIZES.clear()
        INSTALL.release()


def build(part, say=print, progress=None, cancel=None):
    return get(part, stop=cancel, progress=progress, say=say)


def remove(part):
    if part not in PARTS:
        raise PhoneticError('bad-part', 'Choose the PhoneticXeus program or model.')
    if not INSTALL.acquire(blocking=False):
        raise PhoneticError('in-use', 'PhoneticXeus is being installed. Stop its download first.')
    try:
        with LOCK:
            if USERS or LIVE:
                raise PhoneticError('in-use', 'PhoneticXeus is working. Stop or finish transcription first.')
            if part == 'phonetic-model':
                freed = _size(DIRECTORY / 'models')
                shutil.rmtree(DIRECTORY / 'models', ignore_errors=True)
            else:
                freed = _size(DIRECTORY / 'runtime') + _size(DIRECTORY / 'wheels')
                shutil.rmtree(DIRECTORY / 'runtime', ignore_errors=True)
                shutil.rmtree(DIRECTORY / 'wheels', ignore_errors=True)
            SIZES.clear()
            return freed
    finally:
        INSTALL.release()


def discard(part):
    """Discard stopped downloads without touching a complete installed tree."""
    if part not in PARTS:
        raise PhoneticError('bad-part', 'Choose the PhoneticXeus program or model.')
    if not INSTALL.acquire(blocking=False):
        raise PhoneticError('in-use', 'PhoneticXeus is being installed. Stop its download first.')
    try:
        if part == 'phonetic-model':
            folder = model_dir().with_name(MODEL['revision'] + '.part')
        else:
            folder = DIRECTORY / 'wheels'
        freed = _size(folder)
        shutil.rmtree(folder, ignore_errors=True)
        with LOCK:
            SIZES.clear()
        return freed
    finally:
        INSTALL.release()


def worker_env():
    env = dict(os.environ, PYTHONPATH=str(runtime_dir()), PYTHONNOUSERSITE='1',
               PYTHONIOENCODING='utf-8', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', HF_HOME=str(DIRECTORY / 'cache'),
               TOKENIZERS_PARALLELISM='false')
    return env


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', nargs='?', choices=('status', 'get', 'remove'), default='status')
    p.add_argument('part', nargs='?', choices=PARTS)
    args = p.parse_args()
    if args.action == 'status':
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    elif args.part is None:
        p.error('Choose phonetic-runtime or phonetic-model.')
    elif args.action == 'get':
        get(args.part)
    else:
        remove(args.part)


if __name__ == '__main__':
    main()
