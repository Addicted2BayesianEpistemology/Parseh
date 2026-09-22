#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the Parseh guide: markdown/ -> site/, static pages.

    python3 html-guide/build.py                 compile into html-guide/site/
    python3 html-guide/build.py --check         compile into a scratch directory,
                                                say what is wrong, keep nothing
    python3 html-guide/build.py --out DIR       compile into DIR instead of site/
    python3 html-guide/build.py --clean         remove site/ and stop
    python3 html-guide/build.py --pages DIR     a whole deployable site in DIR:
                                                index.html + assets/ + site/
                                                (what GitHub Pages publishes)
    python3 html-guide/build.py --export DIR    copy the guide, with a snapshot of
                                                the studio it needs, into a
                                                project of its own
    python3 html-guide/build.py --strict        warnings fail the build too

Standard library only: any Python 3.8 or newer builds it, the checkout's
environment or not.  The installers run it (lib/runtime.py, the `guide`
step; ./install.sh --guide does only this), and so does the front page's
"Compile the guide" button when Parseh serves it.  README.md beside this file
says how a page is written.

Exits 1 when a page has an error (a broken ref, front matter that does not
read), after writing everything it could; 2 for a wrong argument -- among
them a folder for --out, --pages or --export that already holds something
else: a compile replaces its folder whole, so it goes only into a new or
empty folder, or one an earlier compile, --pages or --export made.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def say_report(report, where, quiet=False):
    for p in report.problems:
        print(p, file=sys.stderr if p.level == "error" else sys.stdout)
    if not quiet or report.problems:
        print("the guide: %d page%s and %d other file%s -> %s; %d warning%s, %d error%s"
              % (report.pages, "" if report.pages == 1 else "s",
                 report.media, "" if report.media == 1 else "s", where,
                 len(report.warnings), "" if len(report.warnings) == 1 else "s",
                 len(report.errors), "" if len(report.errors) == 1 else "s"))


# What --pages leaves in the folder it lays out, and the one thing that lets
# a later --pages empty that folder: a website's own folder may well hold a
# .nojekyll of its own, so that is no sign the folder is ours.
PAGES_MARKER = ".parseh-guide-pages"


def assemble_pages(dest):
    """index.html, assets/ and site/ in one directory, as GitHub Pages (or any
    static host) publishes them -> the Report.  The folder is emptied first,
    so it must be new, empty, or an earlier --pages (its marker file says
    so): any other is refused (NotOurs), untouched."""
    from engine.site import NotOurs, Site
    dest = Path(dest).resolve()
    marker = dest / PAGES_MARKER
    if dest.exists() and not dest.is_dir():
        raise NotOurs("%s is a file, not a folder" % dest)
    if dest.exists() and any(dest.iterdir()) and not marker.is_file():
        raise NotOurs("%s is not empty and was not laid out by --pages (no %s in it): "
                      "nothing was touched -- name a new or empty folder" % (dest, PAGES_MARKER))
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    marker.write_text("This folder was laid out by html-guide/build.py --pages, and the next\n"
                      "--pages into it empties it whole: keep nothing else here.\n",
                      encoding="utf-8")
    shutil.copyfile(HERE / "index.html", dest / "index.html")
    shutil.copytree(HERE / "assets", dest / "assets")
    # GitHub Pages would otherwise run Jekyll, which drops site/_parseh/
    (dest / ".nojekyll").write_text("", encoding="utf-8")
    return Site(HERE).build(dest / "site")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compile the Parseh guide (markdown/ -> site/).")
    ap.add_argument("--out", help="compile into this directory instead of html-guide/site/")
    ap.add_argument("--check", action="store_true", help="compile into a scratch directory, keep nothing")
    ap.add_argument("--clean", action="store_true", help="remove the compiled site/ and stop")
    ap.add_argument("--pages", metavar="DIR", help="assemble a deployable site in DIR")
    ap.add_argument("--export", metavar="DIR", help="copy the guide into a project of its own")
    ap.add_argument("--strict", action="store_true", help="warnings fail the build too")
    ap.add_argument("--quiet", "-q", action="store_true", help="say only what is wrong")
    args = ap.parse_args(argv)

    if args.clean:
        site = HERE / "site"
        if site.exists():
            shutil.rmtree(site)
        if not args.quiet:
            print("removed %s" % site)
        return 0
    from engine.site import NotOurs
    try:
        if args.export:
            from engine.export import export
            export(args.export)
            return 0

        from engine.site import Site
        from engine import studio
        if args.pages:
            report = assemble_pages(args.pages)
            where = args.pages
        elif args.check:
            scratch = Path(tempfile.mkdtemp(prefix="parseh-guide-check-"))
            try:
                report = Site(HERE).build(scratch / "site")
            finally:
                shutil.rmtree(scratch, ignore_errors=True)
            where = "(checked, nothing kept)"
        else:
            out = Path(args.out).resolve() if args.out else HERE / "site"
            out.parent.mkdir(parents=True, exist_ok=True)
            report = Site(HERE).build(out)
            where = os.path.relpath(out)
    except NotOurs as e:
        # a folder that holds something else: a wrong argument, said, and
        # nothing in it touched
        print("error: %s" % e, file=sys.stderr)
        return 2
    if not args.quiet and studio.KIND != "live":
        print("the studio's renderer: the snapshot in engine/vendor/")
    say_report(report, where, args.quiet)
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
