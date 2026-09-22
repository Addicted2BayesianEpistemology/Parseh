# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.export -- the guide, copied into a project of its own.

    build.py --export DIR

The guide is meant to become part of the website of Parseh one day, in a
repository that holds nothing else.  This copies html-guide/ there -- the
engine, the assets, the pages, the front page -- together with a SNAPSHOT
of exactly what the engine takes from Parseh (engine/manifest.py: the
studio's parser and renderer, the language registry, the exercises' script
and stylesheet, MathJax, the fonts the sheet names and their licences) under
engine/vendor/, laid out as it is in Parseh.  The copy then builds with any
Python 3, on its own, into the same pages: engine/studio.py finds no Parseh
around it and imports the snapshot instead.

In the copy engine/vendor/ is part of the project and is committed; its
.gitignore leaves out only site/.  Exporting again later refreshes the
snapshot from the Parseh it is run in.
"""
import re
import shutil
from pathlib import Path

from .manifest import MODULE_FILES, RUNTIME_FILES
from .site import NotOurs
from .studio import GUIDE, ROOT, find_font

SKIP_DIRS = {"site", "vendor", "__pycache__", ".git"}

WORKFLOW = """\
# Publish the guide on GitHub Pages.  One-time setup: the repository's
# Settings -> Pages -> Source: GitHub Actions.  Every push to main then
# compiles the pages (build.py --pages _site) and publishes them.
name: guide on GitHub Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Compile the guide
        run: python3 build.py --pages _site
      # Pages refuses a site with a file others cannot read or a folder
      # they cannot enter (deployment_perms_error)
      - name: Every file readable
        run: chmod -c -R +rX _site
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Publish
        id: deployment
        uses: actions/deploy-pages@v4
"""


def _ignore(directory, names):
    d = Path(directory)
    out = set()
    for n in names:
        if n in SKIP_DIRS and (d / n).is_dir():
            out.add(n)
        elif n.startswith((".site-", ".old-")) or n.endswith((".pyc", ".pyo")):
            out.add(n)
    return out


def earlier_export(folder):
    """Does `folder` hold a guide an earlier export made?  A build.py alone is
    no sign -- any Python project may have one, and an export replaces its
    engine/, markdown/ and README.md -- so it takes the engine's manifest and
    the snapshot only an export writes."""
    folder = Path(folder)
    return ((folder / "build.py").is_file() and (folder / "engine" / "manifest.py").is_file()
            and (folder / "engine" / "vendor").is_dir())


def export(dest, say=print):
    """Copy the guide and its snapshot of Parseh into `dest` -> dest.  Raises
    NotOurs, touching nothing, when `dest` holds anything but an earlier
    export."""
    dest = Path(dest).resolve()
    if dest == GUIDE or GUIDE in dest.parents:
        raise NotOurs("--export needs a directory outside html-guide/ (got %s)" % dest)
    if dest.exists() and not dest.is_dir():
        raise NotOurs("%s is a file, not a folder" % dest)
    if dest.exists() and any(dest.iterdir()) and not earlier_export(dest):
        raise NotOurs("%s is not empty and does not hold an exported guide: nothing was "
                      "touched -- export into a new or empty folder" % dest)
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(GUIDE.iterdir()):
        if item.name in SKIP_DIRS or item.name.startswith((".site-", ".old-")):
            continue
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target, ignore=_ignore)
        else:
            shutil.copyfile(item, target)
    vendor = dest / "engine" / "vendor"
    if vendor.exists():
        shutil.rmtree(vendor)
    for rel in MODULE_FILES + RUNTIME_FILES:
        src = ROOT / rel
        if src.is_file():
            (vendor / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, vendor / rel)
    # the fonts the sheet names, wherever this machine has them (TeX's
    # Pagella and Heros included: the copy may be built where there is no TeX)
    css = (ROOT / "markdown/app/static/app.css").read_text(encoding="utf-8")
    fonts = vendor / "lib" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for name in sorted(set(re.findall(r"url\((?:['\"])?fonts/([^)'\"]+)", css))):
        found = find_font(name)
        if found:
            shutil.copyfile(found, fonts / name)
    (dest / ".gitignore").write_text(
        "# the compiled pages: build.py makes them, from markdown/\nsite/\n_site/\n"
        "__pycache__/\n", encoding="utf-8")
    wf = dest / ".github" / "workflows" / "pages.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(WORKFLOW, encoding="utf-8")
    say("exported the guide to %s (the studio's files in engine/vendor/)" % dest)
    return dest
