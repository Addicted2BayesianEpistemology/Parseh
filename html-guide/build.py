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
                                                (what GitHub Pages publishes;
                                                in Parseh's own checkout also
                                                lib/icons/ and the slim bar
                                                that leads to parseh.io)
    python3 html-guide/build.py --export DIR    copy the guide, with a snapshot of
                                                the studio it needs, into a
                                                project of its own
    python3 html-guide/build.py --strict        warnings fail the build too
    python3 html-guide/build.py --draw          draw the LaTeX drawings the pages
                                                ask for and markdown/drawings/ has
                                                not got yet, and stop (a developer
                                                step: needs TeX and the checkout's
                                                environment); with --check, only
                                                say what it would draw

Standard library only: any Python 3.8 or newer builds it, the checkout's
environment or not -- and it never draws: a page's LaTeX drawings are the
pictures in markdown/drawings/, made beforehand by --draw and committed, so
that a machine with no TeX compiles the same guide.  The installers run it (lib/runtime.py, the `guide`
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
    # WHAT THIS COMPILE DID NOT WRITE, AND DID NOT DELETE EITHER.  A compile
    # carries over whatever the site had that it cannot make itself -- the
    # PDF of a machine with no TeX, say -- rather than deleting it (site.py's
    # _keep_whatever_it_had).  Said here, because a file in site/ that no
    # compile wrote is otherwise a small mystery; and NOT counted as a
    # warning, since --strict would then fail a machine for doing the right
    # thing.
    if getattr(report, "kept", None):
        few = report.kept[:4]
        print("kept from the site that was there (this compile did not write them): %s%s"
              % (", ".join(few),
                 "" if len(report.kept) <= len(few) else ", and %d more" % (len(report.kept) - len(few))))


# What --pages leaves in the folder it lays out, and the one thing that lets
# a later --pages empty that folder: a website's own folder may well hold a
# .nojekyll of its own, so that is no sign the folder is ours.
PAGES_MARKER = ".parseh-guide-pages"


def _parseh_s_own():
    """lib/project.py -- where Parseh lives, its one list of addresses -- of
    the checkout this guide stands in, or None.

    None is a guide copied into a project of its own (`--export`): that
    project has no lib/ beside its build.py, and its guide is somebody's, not
    Parseh's, so the layout it publishes has neither Parseh's bar nor Parseh's
    icons.  project.py is standard library only, as this script is."""
    lib = HERE.parent / "lib"
    if not (lib / "project.py").is_file():
        return None
    if str(lib) not in sys.path:
        sys.path.append(str(lib))
    import project
    return project


def assemble_pages(dest):
    """index.html, assets/, lib/icons/ and site/ in one directory, as GitHub
    Pages (or any static host) publishes them -> the Report.  The folder is
    emptied first, so it must be new, empty, or an earlier --pages (its marker
    file says so): any other is refused (NotOurs), untouched.

    THIS IS PARSEH'S PUBLISHED GUIDE, the one at project.GUIDE_URL, and it
    differs from the guide an install carries (html-guide/site/, which this
    never touches) in two things:
      * the phone app's icons.  Chrome's WebAPK server fetches them from the
        internet, from project.ICONS_URL, so the site serves them where that
        says: lib/icons/*.png, and only those (lib/icons/make.mjs says how
        they were drawn and is not part of the site);
      * a slim bar on every page, with Parseh's logo and a link to
        project.WEBSITE_URL (engine/bar.py).
    A copy exported into a project of its own has neither (_parseh_s_own)."""
    from engine import bar
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
    project = _parseh_s_own()
    front = (HERE / "index.html").read_bytes()
    if project:
        front = bar.put_on_the_front_page(front.decode("utf-8"), project.WEBSITE_URL).encode("utf-8")
    (dest / "index.html").write_bytes(front)
    shutil.copytree(HERE / "assets", dest / "assets")
    icons = HERE.parent / "lib" / "icons"
    if project and icons.is_dir():
        (dest / "lib" / "icons").mkdir(parents=True)
        for png in sorted(icons.glob("*.png")):
            shutil.copyfile(png, dest / "lib" / "icons" / png.name)
    # GitHub Pages would otherwise run Jekyll, which drops site/_parseh/
    (dest / ".nojekyll").write_text("", encoding="utf-8")
    return Site(HERE, bar_home=project.WEBSITE_URL if project else None).build(dest / "site")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compile the Parseh guide (markdown/ -> site/).")
    ap.add_argument("--out", help="compile into this directory instead of html-guide/site/")
    ap.add_argument("--check", action="store_true", help="compile into a scratch directory, keep nothing")
    ap.add_argument("--clean", action="store_true", help="remove the compiled site/ and stop")
    ap.add_argument("--pages", metavar="DIR", help="assemble a deployable site in DIR")
    ap.add_argument("--export", metavar="DIR", help="copy the guide into a project of its own")
    ap.add_argument("--strict", action="store_true", help="warnings fail the build too")
    ap.add_argument("--draw", action="store_true",
                    help="draw the LaTeX drawings markdown/drawings/ lacks (needs TeX), then stop; "
                         "with --check, only say which")
    ap.add_argument("--quiet", "-q", action="store_true", help="say only what is wrong")
    args = ap.parse_args(argv)

    if args.draw:
        if args.out or args.pages or args.export or args.clean or args.strict:
            print("error: --draw draws and stops; it goes with --check and --quiet alone",
                  file=sys.stderr)
            return 2
        from engine import drawings
        return drawings.main(HERE, check=args.check, quiet=args.quiet)

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
