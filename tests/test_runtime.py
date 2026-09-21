"""The one list of what Parseh needs, where it is looked for, and the protocol
an installer reports in.

    python3 -m unittest discover -s tests -p test_runtime.py

Runs under any Python, touches no network and installs nothing: the
environments are directories made here, and the install is walked dry.
"""
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import runtime    # noqa: E402
import segmenter  # noqa: E402


def fake_python(prefix):
    py = Path(runtime.python_in(str(prefix)))
    py.parent.mkdir(parents=True, exist_ok=True)
    py.write_text('#!/bin/sh\n', encoding='utf-8')
    py.chmod(0o755)
    return str(py)


class TheList(unittest.TestCase):
    def test_environment_yml_and_the_list_agree(self):
        spec = runtime.env_spec()
        self.assertEqual({n.lower() for n, _s in spec['pip']},
                         {n.lower() for _m, n, _w in runtime.PACKAGES},
                         'every pip package environment.yml lists is in PACKAGES, and back')
        self.assertEqual({n for n, _s in spec['conda']} - {'python', 'pip'},
                         {n for _p, n, _w in runtime.ENV_TOOLS},
                         'and every program it carries is in ENV_TOOLS')
        self.assertIn(('python', 'python=3.12'), spec['conda'])

    def test_the_word_analyzers_are_on_the_list(self):
        mods = {m for m, _n, _w in runtime.PACKAGES}
        for code, backend in segmenter.BACKENDS.items():
            for m in backend['modules']:
                self.assertIn(m, mods, (code, m))

    def test_the_windows_wizard_reads_the_list_and_keeps_none_of_its_own(self):
        src = (ROOT / 'lib' / 'launcher.py').read_text(encoding='utf-8')
        self.assertIn('runtime.status()', src)
        self.assertNotIn('("brotli", "brotli"', src)

    def test_the_file_is_read_in_conda_s_own_shape(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td, 'e.yml')
            p.write_text('name: x\nchannels:\n  - conda-forge\ndependencies:\n'
                         '  - python=3.12   # a comment\n  - pip:\n      - A>=1\n'
                         '      # a note\n      - b-c\n  - deno\n', encoding='utf-8')
            self.assertEqual(runtime.env_spec(str(p)),
                             {'conda': [('python', 'python=3.12'), ('deno', 'deno')],
                              'pip': [('A', 'A>=1'), ('b-c', 'b-c')]})


class Finding(unittest.TestCase):
    def test_the_checkout_s_own_environment_comes_before_conda_s(self):
        with tempfile.TemporaryDirectory() as td:
            local = Path(td, 'checkout', '.runtime', 'env')
            conda_root = Path(td, 'miniconda3')
            conda_env = conda_root / 'envs' / runtime.ENVNAME
            conda_py = fake_python(conda_env)
            env = {k: v for k, v in os.environ.items() if k != 'PARSEH_PYTHON'}
            with patch.object(runtime, 'LOCAL_ENV', str(local)), \
                    patch.object(runtime, 'conda_roots', lambda: [str(conda_root)]), \
                    patch.dict(os.environ, env, clear=True):
                self.assertEqual(runtime.find_env(), (str(conda_env), conda_py))
                local_py = fake_python(local)
                self.assertEqual(runtime.find_env(), (str(local), local_py))
                os.environ['PARSEH_PYTHON'] = conda_py
                self.assertEqual(runtime.find_env()[1], conda_py, '$PARSEH_PYTHON before everything')

    @unittest.skipIf(os.name == 'nt' or not shutil.which('sh'), 'no sh')
    def test_env_sh_looks_in_the_same_places_in_the_same_order(self):
        with tempfile.TemporaryDirectory() as td:
            home, checkout = Path(td, 'home'), Path(td, 'checkout')
            home.mkdir()
            checkout.mkdir()
            script = ('. "%s"; parseh_env; printf "%%s|%%s|%%s" "$PARSEH_PY" "$PARSEH_PREFIX" "$PATH"'
                      % (ROOT / 'lib' / 'env.sh'))

            def ask(**extra):
                env = dict({'HOME': str(home), 'PATH': '/usr/bin:/bin', 'PARSEH_ROOT': str(checkout)}, **extra)
                out = subprocess.run(['sh', '-c', script], env=env, capture_output=True, text=True).stdout
                return out.split('|')

            py, prefix, _path = ask()
            self.assertEqual(prefix, '', 'no environment anywhere: no prefix')
            conda_py = fake_python(home / 'miniforge3' / 'envs' / runtime.ENVNAME)
            py, prefix, path = ask()
            self.assertEqual(py, conda_py)
            self.assertTrue(path.startswith(prefix + '/bin:'), 'its programs first on the PATH')
            local_py = fake_python(checkout / '.runtime' / 'env')
            self.assertEqual(ask()[0], local_py, "the checkout's own first")
            self.assertEqual(ask(PARSEH_PYTHON=conda_py)[0], conda_py, '$PARSEH_PYTHON before it')

    def test_micromamba_s_name_for_every_machine(self):
        for plat, machine, win, want in (('linux', 'x86_64', False, 'linux-64'),
                                         ('linux', 'aarch64', False, 'linux-aarch64'),
                                         ('darwin', 'arm64', False, 'osx-arm64'),
                                         ('darwin', 'x86_64', False, 'osx-64'),
                                         ('win32', 'AMD64', True, 'win-64')):
            with patch.object(runtime.sys, 'platform', plat), \
                    patch.object(runtime.platform, 'machine', lambda m=machine: m), \
                    patch.object(runtime, 'WIN', win):
                self.assertEqual(runtime.micromamba_platform(), want)


class Protocol(unittest.TestCase):
    def events(self, text):
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_a_dry_run_speaks_the_protocol_docs_installer_md_describes(self):
        r = subprocess.run([sys.executable, str(ROOT / 'lib' / 'runtime.py'), 'install', '--json', '--dry-run'],
                           capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        events = self.events(r.stdout)
        self.assertEqual([e['id'] for e in events if e['event'] == 'step'],
                         ['env', 'packages', 'guide', 'models', 'readers'])
        self.assertEqual(events[-1]['event'], 'done')
        self.assertTrue(events[-1]['ok'])
        doc = (ROOT / 'docs' / 'installer.md').read_text(encoding='utf-8')
        for said in ('"event": "step"', '"event": "log"', '"event": "done"', '--dry-run'):
            self.assertIn(said, doc)

    def test_a_step_that_fails_is_said_and_the_install_fails(self):
        out = io.StringIO()

        def offline(report):
            raise OSError('offline')
        with patch.object(runtime, 'find_env', lambda: (None, None)), \
                patch.object(runtime, 'get_micromamba', offline):
            self.assertFalse(runtime.install(runtime.Report(True, out)))
        events = self.events(out.getvalue())
        self.assertEqual(events[0], {'event': 'step', 'id': 'env', 'title': 'the environment',
                                     'state': 'failed', 'detail': 'could not download micromamba: offline'})
        self.assertEqual(events[-1], {'event': 'done', 'ok': False})

    def test_a_guide_that_does_not_compile_is_a_warning_not_a_failure(self):
        """The guide's step runs html-guide/build.py; a compile that fails is
        said as a `warning` and the install goes on, a compile that works is
        `done` -- docs/installer.md's two states for it."""
        for rc, state in ((0, 'done'), (1, 'warning')):
            out, calls = io.StringIO(), []

            def run(cmd, report, env=None, cwd=None):
                calls.append(cmd)
                return rc
            with patch.object(runtime, 'run', run):
                self.assertTrue(runtime.build_guide('/env/bin/python3', None, runtime.Report(True, out)))
            self.assertEqual(calls, [['/env/bin/python3', str(ROOT / 'html-guide' / 'build.py')]])
            events = self.events(out.getvalue())
            self.assertEqual([(e['id'], e['state']) for e in events],
                             [('guide', 'running'), ('guide', state)])
        doc = (ROOT / 'docs' / 'installer.md').read_text(encoding='utf-8')
        self.assertIn('`warning`', doc)
        self.assertIn('**guide**', doc)

    def test_an_older_environment_gets_only_what_it_lacks(self):
        calls, have = [], {m: True for m, _n, _w in runtime.PACKAGES}
        have['zstandard'] = False

        def run(cmd, report, env=None, cwd=None):
            calls.append(cmd)
            have['zstandard'] = True
            return 0
        with patch.object(runtime, 'modules', lambda python: dict(have)), \
                patch.object(runtime, 'tool', lambda name, prefix=None, system=True: '/env/bin/' + name), \
                patch.object(runtime, 'run', run):
            self.assertTrue(runtime.complete_env('/env', '/env/bin/python3',
                                                 runtime.Report(True, io.StringIO())))
        self.assertEqual(calls, [['/env/bin/python3', '-m', 'pip', 'install', 'zstandard>=0.22']])


class TheWindowsWizard(unittest.TestCase):
    """serve.bat's first run (lib/launcher.py's wizard) compiles the guide
    every time, as install.sh and install.bat do -- not only when it has an
    environment to install, whose install compiles it on the way."""

    def wizard(self, guide_status):
        import contextlib
        import guidebuild
        import launcher
        ran, out = [], io.StringIO()
        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as st:
            for obj, name, value in (
                    (launcher, 'interactive', lambda: False),
                    (launcher, 'MARKER', os.path.join(td, '.setup-done')),
                    (launcher, 'bundled_web_fonts', lambda: []),
                    (launcher, 'cjk_content', lambda: []),
                    (launcher, 'find_openssl', lambda: '/usr/bin/openssl'),
                    (launcher, 'find_tailscale', lambda: None),
                    (launcher, 'all_books', lambda: []),
                    (launcher, 'build_readers', lambda: True),
                    (launcher, 'have_cert', lambda: True),
                    (launcher, 'run_tool', lambda args, cwd=None: ran.append(args) or True),
                    # an environment with everything in it: nothing to install
                    (launcher.runtime, 'find_env', lambda: ('/env', sys.executable)),
                    (launcher.runtime, 'status', lambda: {'packages': [], 'models': [], 'missing': []}),
                    (launcher.runtime, 'install', lambda *a, **k: self.fail('nothing to install')),
                    (guidebuild, 'status', lambda guide=None: dict(guide_status))):
                st.enter_context(patch.object(obj, name, value))
            st.enter_context(patch('sys.stdout', out))
            self.assertTrue(launcher.wizard())
        return ran, out.getvalue()

    def test_it_compiles_the_guide_with_the_environment_already_complete(self):
        ran, said = self.wizard({'built': False, 'stale': None})
        self.assertEqual(ran, [[str(ROOT / 'html-guide' / 'build.py')]])
        self.assertIn('ok    the guide compiled', said)
        # so the README's claim is true
        readme = (ROOT / 'html-guide' / 'README.md').read_text(encoding='utf-8')
        self.assertIn('the Windows wizard', readme)

    def test_a_guide_compiled_from_these_very_pages_is_left_alone(self):
        ran, said = self.wizard({'built': True, 'stale': False})
        self.assertEqual(ran, [])
        self.assertIn('ok    the guide, already compiled from these pages', said)


class Scripts(unittest.TestCase):
    @unittest.skipIf(not shutil.which('sh'), 'no sh')
    def test_the_shell_scripts_parse(self):
        for f in ('install.sh', 'serve.sh', 'build.sh', 'lib/env.sh', 'Parseh.command'):
            r = subprocess.run(['sh', '-n', str(ROOT / f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, (f, r.stderr))

    @unittest.skipIf(not shutil.which('sh'), 'no sh')
    def test_install_sh_guide_only_compiles_the_guide(self):
        """./install.sh --guide runs html-guide/build.py with the Python
        lib/env.sh finds and stops there, with its exit status -- nothing is
        installed and no report is printed.  Run on a copy of the script over
        a stand-in build.py that says what ran it."""
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            shutil.copy(ROOT / 'install.sh', t / 'install.sh')
            (t / 'lib').mkdir()
            shutil.copy(ROOT / 'lib' / 'env.sh', t / 'lib' / 'env.sh')
            (t / 'html-guide').mkdir()
            (t / 'html-guide' / 'build.py').write_text(
                'import sys, os\nprint("compiled by", sys.executable)\n'
                'sys.exit(int(os.environ.get("GUIDE_EXIT", "0")))\n', encoding='utf-8')
            for code in (0, 3):
                env = dict(os.environ, PARSEH_PYTHON=sys.executable, GUIDE_EXIT=str(code))
                r = subprocess.run(['sh', str(t / 'install.sh'), '--guide'], capture_output=True,
                                   text=True, env=env, cwd=td)
                self.assertEqual(r.returncode, code, r.stdout + r.stderr)
                self.assertIn('compiled by', r.stdout)
                self.assertNotIn('== installing ==', r.stdout)
                self.assertNotIn('== required to serve', r.stdout)

    def test_every_launcher_looks_where_runtime_looks(self):
        for f in ('serve.sh', 'build.sh', 'install.sh', 'Parseh.command'):
            self.assertIn('lib/env.sh', (ROOT / f).read_text(encoding='utf-8'), f)
        for f in ('serve.bat', 'install.bat'):
            self.assertIn('.runtime\\env\\python.exe', (ROOT / f).read_text(encoding='utf-8'), f)

    @unittest.skipIf(os.name == 'nt', 'the mode bit is a POSIX thing')
    def test_the_mac_launcher_can_be_double_clicked(self):
        self.assertTrue((ROOT / 'Parseh.command').stat().st_mode & stat.S_IXUSR)


if __name__ == '__main__':
    unittest.main()
