# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.site -- markdown/ in, site/ out.

    Site(guide_dir).build(out_dir) -> Report

WHAT A PAGE IS.  Every .md under markdown/ is a page, at the same path under
site/ with .html for .md: markdown/writing/code.md -> site/writing/code.html.
A directory is a section; its _index.md (Hugo's convention) is the section's
own page, site/<section>/index.html, and gives the section its title and
weight.  The root's markdown/_index.md is the guide's own front matter (its
`title`); the guide's front page is the hand-written html-guide/index.html,
which works before anything is compiled.  Every other file under markdown/
-- a screenshot, a GIF, a PDF -- is copied to the same place under site/, so
a page names its pictures by their path beside it.

EVERY ADDRESS IS RELATIVE AND NAMES ITS FILE.  site/ is opened from the disk
(file://, where a directory does not open its index.html), served by Parseh
under /guide/, and published on GitHub Pages under /<repository>/: an
address that began with / or ended at a directory would be right in one of
the three and wrong in the others.  So every link the engine writes is
relative and ends in a file name.

WHAT IS WRITTEN.  The pages; site/nav.js (the tree of pages, which the front
page reads with a plain <script src>, the one way a file:// page can read
another file); site/search-index.js (the text of every page, for the search
box); site/build.json (what was built from what); and site/_parseh/, the
studio's runtime the pages draw with -- its stylesheet confined to the
article (engine/cssscope.py), the language font tokens, the fonts with their
licences, the exercises' script and MathJax.

The output is deterministic: the same sources give the same bytes, with no
date in them, so a compile that changed nothing changes nothing.

A COMPILE REPLACES ONLY WHAT A COMPILE MADE.  The output folder is swapped
for a new one whole, so whatever else was in it would go with it: a folder
named by mistake (`--out ~/Documents`, `--out .`) must never be that.  So a
compile goes only into a folder that is not there yet, is empty, or holds an
earlier compile -- its build.json says so -- and refuses any other
(NotOurs), touching nothing.  The guide's own site/ is the one exception:
it is the compile's by definition, and the installer must always be able
to remake it.
"""
import json
import os
import posixpath
import re
import shutil
import tempfile
from pathlib import Path

from . import render as R
from . import shortcodes
from .cssscope import scope as scope_css
from .fingerprint import fingerprint
from .frontmatter import FrontMatterError, split as split_front_matter
from .inline import Store
from .manifest import FONT_LICENCES, RUNTIME_DIR
from .studio import (GUIDE, find_font, htmlgen, inline_seam, languages, source,
                     texgen)

esc = htmlgen.esc
ENGINE_VERSION = 1
SITE_TITLE = "Parseh guide"
DEFAULT_TARGET = languages.DEFAULT       # fa, as the studio: see README.md
DEFAULT_PROSE = "en"


class NotOurs(Exception):
    """The folder a compile was asked to replace holds something a compile
    did not make: nothing was touched."""


def made_by_the_guide(folder):
    """Does `folder` hold an earlier compile of the guide?  Its build.json,
    which every compile writes, says so."""
    try:
        info = json.loads((Path(folder) / "build.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(info, dict) and "engine" in info and "fingerprint" in info


def _keep_whatever_it_had(old, fresh):
    """Copy into the new site every file the old one had and the new one
    lacks -> their paths.

    A COMPILE MAY NOT TAKE A FILE AWAY.  The new site is written beside the
    old and swapped in whole, so anything this compile did not write simply
    ceased to exist -- and `html-guide/site/` is TRACKED.  That is how an
    install on a machine without TeX deleted seven tracked font files: the
    compile copied only the faces it could find, and the ones it could not
    went with the old site, leaving a dirty checkout that blocks the next
    `git pull`.  The fonts travel with Parseh now (lib/fonts), but the shape
    of the fault was never really about fonts: whatever the reason a file is
    missing from a compile, keeping it is the safe half of the guess.  A
    stale file is visible and can be deleted by hand; a deleted tracked file
    is neither.  The paths are reported (Report.kept) so nobody has to
    wonder where an unexpected file came from."""
    old, fresh = Path(old), Path(fresh)
    if not old.is_dir():
        return []
    kept = []
    for path in sorted(old.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(old)
        dest = fresh / rel
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        kept.append(rel.as_posix())
    return kept


class Problem:
    def __init__(self, level, path, line, message):
        self.level, self.path, self.line, self.message = level, path, line, message

    def __str__(self):
        where = self.path + (":%d" % self.line if self.line else "")
        return "%s: %s: %s" % (self.level, where, self.message)


class Page:
    def __init__(self, rel, src):
        self.rel = rel                  # markdown/-relative, "writing/code.md"
        self.src = src
        name = posixpath.basename(rel)
        folder = posixpath.dirname(rel)
        self.is_index = name == "_index.md"
        self.section = folder           # the section it belongs to ("" = the root)
        if self.is_index:
            self.out = posixpath.join(folder, "index.html")
            self.section = posixpath.dirname(folder)
        else:
            self.out = posixpath.join(folder, name[:-3] + ".html")
        self.fm, self.body, self.first_line = {}, "", 1
        self.title = ""
        self.weight = 0
        self.draft = False

    @property
    def link_title(self):
        return str(self.fm.get("linktitle") or self.title)


class Section:
    def __init__(self, path):
        self.path = path                # "writing" ; "" is the root
        self.index = None               # its _index.md page
        self.pages = []
        self.sections = []

    @property
    def title(self):
        if self.index:
            return self.index.link_title
        return humanize(posixpath.basename(self.path))

    @property
    def weight(self):
        return self.index.weight if self.index else 0


def humanize(name):
    name = re.sub(r"\.md$", "", name)
    name = re.sub(r"^\d+[-_]", "", name)
    return name.replace("-", " ").replace("_", " ").strip().capitalize() or name


def order_key(item):
    """Hugo's default order: by weight, pages without one (0) after those
    with one; then by title; then by path, so the order never depends on
    the file system."""
    w = item.weight
    return (w == 0, w, item.title.casefold() if isinstance(item, Section)
            else item.link_title.casefold(), getattr(item, "path", getattr(item, "rel", "")))


def rel_url(frm, to):
    """The relative address of `to` from the page at `frm` (both site/-relative)."""
    base = posixpath.dirname(frm)
    return posixpath.relpath(to, base or ".")


class Report:
    def __init__(self):
        self.problems = []
        self.pages = 0
        self.media = 0
        # files the site already had that this compile did not write, and
        # that were carried over rather than dropped (_keep_whatever_it_had)
        self.kept = []

    @property
    def errors(self):
        return [p for p in self.problems if p.level == "error"]

    @property
    def warnings(self):
        return [p for p in self.problems if p.level == "warning"]


class PageContext:
    """What a page's renderer asks the site (engine/render.py and
    engine/inline.py call these)."""

    def __init__(self, site, page):
        self.site = site
        self.page = page
        self.link_defs = {}
        self.uses = set()
        self.line = page.first_line
        # while a table is drawn: each cell's text -> the lines it is on, in
        # row order (engine/render.py Renderer.table)
        self.cell_lines = None
        self.prose_lang = str(page.fm.get("lang") or DEFAULT_PROSE)
        self.renderer = None

    # -- saying
    def warn(self, message, line=None, level="warning"):
        self.site.report.problems.append(Problem(level, "markdown/" + self.page.rel,
                                                 line or self.line, message))

    # -- where things are
    def _target(self, path):
        """A path written in the page -> markdown/-relative, or None when it
        leaves markdown/."""
        path = path.split("#", 1)[0].split("?", 1)[0]
        full = posixpath.normpath(posixpath.join(posixpath.dirname(self.page.rel), path))
        return None if full.startswith("..") or full == "." and not path else full

    def media_url(self, path):
        """A picture's (or any file's) path from the page -> its address from
        the compiled page, when the file is there; said, when it is not."""
        if re.match(r"^[a-z][a-z0-9+.\-]*:", path, re.I) or path.startswith("//"):
            return path
        if path.startswith("/"):
            self.warn("%s: an address that starts with / breaks on the disk and on "
                      "GitHub Pages -- write it relative to the page" % path)
            return path
        full = self._target(path)
        if full is None or not (self.site.src / full).is_file():
            self.warn("no such file: %s (looked for markdown/%s)" % (path, full or path))
            return None
        frag = path[len(path.split("#", 1)[0]):]
        return rel_url(self.page.out, full) + frag

    def find_page(self, ref):
        """A page named by its path (`other.md`, `../sec/`, `sec/_index.md`,
        with or without .md), from this page or from markdown/'s root."""
        ref = ref.split("#", 1)[0].strip()
        if not ref:
            return self.page
        bases = [posixpath.dirname(self.page.rel), ""] if not ref.startswith("/") else [""]
        ref = ref.lstrip("/")
        for base in bases:
            full = posixpath.normpath(posixpath.join(base, ref)) if base else posixpath.normpath(ref)
            for cand in (full, full + ".md", posixpath.join(full, "_index.md"),
                         re.sub(r"\.html$", ".md", full),
                         re.sub(r"index\.html$", "_index.md", full)):
                p = self.site.by_rel.get(cand)
                if p is not None:
                    return p
        return None

    def page_url(self, target, frag=""):
        return rel_url(self.page.out, target.out) + frag

    def ref(self, path, line=None):
        """{{< ref >}} and {{< relref >}}: the page's address, or an error."""
        frag = "#" + path.split("#", 1)[1] if "#" in path else ""
        target = self.find_page(path)
        if target is None:
            self.warn("ref: no page %r" % path, line=line, level="error")
            return "#"
        return self.page_url(target, frag)

    def param(self, key):
        value = self.page.fm
        for part in key.split("."):
            if isinstance(value, dict):
                value = value.get(part.lower(), value.get(part))
            else:
                return None
        if value is None and "." not in key:
            params = self.page.fm.get("params")
            if isinstance(params, dict):
                return params.get(key)
            return self.site.root_fm.get(key.lower())
        return value

    def link_href(self, dest):
        href, _kind = self._resolve(dest)
        return href or "#"

    def _resolve(self, dest):
        d = dest.strip()
        low = d.lower()
        if not d:
            return None, "empty"
        if low.startswith("doc:"):
            return None, "doc"
        if low.startswith(("http://", "https://")):
            return d, "external"
        if low.startswith(("mailto:", "tel:")):
            return d, "mail"
        if d.startswith("#"):
            return d, "anchor"
        if re.match(r"^[a-z][a-z0-9+.\-]*:", low):
            return None, "unsafe"
        if d.startswith("/"):
            self.warn("%s: an address that starts with / breaks on the disk and on "
                      "GitHub Pages -- write it relative to the page" % d)
            return d, "absolute"
        path = d.split("#", 1)[0].split("?", 1)[0]
        frag = d[len(path):]
        if not path:
            return d, "anchor"
        is_page = (path.endswith((".md", "/")) or path.endswith(".html")
                   or (self.site.src / (self._target(path) or "")).is_dir())
        if is_page:
            target = self.find_page(path)
            if target is not None:
                return self.page_url(target, frag), "page"
            if path.endswith(".html"):
                return d, "page"        # a file the author knows is there
            self.warn("link to a page that is not there: %s" % d)
            return re.sub(r"\.md$", ".html", path) + frag, "page"
        url = self.media_url(path)
        return (url + frag if url else d), "file"

    def link_html(self, dest, title, label, inner=None):
        """A link, drawn: `label` is its rendered text (empty: say the address,
        or for doc:, the page's title)."""
        t = ' title="%s"' % esc(title) if title else ""
        if dest.strip().lower().startswith("doc:"):
            name = dest.strip()[4:].strip()
            target = self.site.by_title(name)
            if target is None:
                self.warn("doc: link to a page that is not there: %r" % name)
                return ('<span class="doclink-dead" title="No page of this guide is '
                        'called %s">%s</span>' % (esc("“%s”" % name), label or esc(name)))
            return '<a class="doclink" href="%s"%s>%s</a>' % (
                esc(self.page_url(target)), t, label or esc(target.title))
        href, kind = self._resolve(dest)
        if href is None:
            return label or esc(dest)
        label = label or esc(dest)
        if kind == "external":
            return ('<a class="lnk" href="%s"%s target="_blank" rel="noopener noreferrer">%s</a>'
                    % (esc(href), t, label))
        return '<a href="%s"%s>%s</a>' % (esc(href), t, label)

    def image_html(self, src, title, alt):
        url = self.media_url(src) or src
        return '<img class="g-img" src="%s" alt="%s"%s>' % (
            esc(url), esc(alt), ' title="%s"' % esc(title) if title else "")

    def inline_shortcode(self, name, args, inner, source, delim):
        return shortcodes.inline(self.renderer, name, args, inner, source)


class Site:
    def __init__(self, guide=GUIDE, src=None):
        self.guide = Path(guide)
        self.src = Path(src) if src else self.guide / "markdown"
        self.report = Report()
        self.pages = []
        self.media = []
        self.by_rel = {}
        self.root_fm = {}
        self._titles = {}

    # ------------------------------------------------------------ reading
    def discover(self):
        if not self.src.is_dir():
            raise SystemExit("no markdown/ directory at %s" % self.src)
        for dirpath, dirnames, filenames in os.walk(self.src):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "_parseh")))
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                path = Path(dirpath) / name
                rel = path.relative_to(self.src).as_posix()
                if name.endswith(".md"):
                    self.pages.append(Page(rel, path))
                else:
                    self.media.append(rel)
        for page in self.pages:
            self._read(page)
        root = next((p for p in self.pages if p.rel == "_index.md"), None)
        if root is not None:
            # the root _index.md is the guide's own front matter: its body,
            # if any, is not drawn anywhere (the front page is index.html)
            self.root_fm = root.fm
            self.pages.remove(root)
            if root.body.strip():
                self.report.problems.append(Problem(
                    "warning", "markdown/_index.md", root.first_line,
                    "the root _index.md only names the guide (title, description): "
                    "its text is not shown -- the front page is html-guide/index.html"))
        drafts = [p for p in self.pages if p.draft]
        self.pages = [p for p in self.pages if not p.draft]
        self.drafts = drafts
        self.by_rel = {p.rel: p for p in self.pages}
        for p in self.pages:
            for key in {p.title, p.link_title}:
                if not key:
                    continue
                if key in self._titles and self._titles[key] is not p:
                    self.report.problems.append(Problem(
                        "warning", "markdown/" + p.rel, 1,
                        "two pages are called %r (markdown/%s too): a doc: link "
                        "goes to the first" % (key, self._titles[key].rel)))
                    continue
                self._titles[key] = p

    def _read(self, page):
        text = page.src.read_text(encoding="utf-8")
        try:
            page.fm, page.body, page.first_line, _fmt = split_front_matter(text)
        except FrontMatterError as e:
            self.report.problems.append(Problem("error", "markdown/" + page.rel, e.line, str(e)))
            page.fm, page.body, page.first_line = {}, text, 1
        fm = page.fm
        title = fm.get("title")
        if not title:
            m = re.search(r"^#[ \t]+(.+?)[ \t#]*$", page.body, re.M)
            first = next((ln for ln in page.body.split("\n") if ln.strip()), "")
            if m and first.strip() == m.group(0).strip():
                title = m.group(1)
        page.title = str(title or humanize(posixpath.basename(
            posixpath.dirname(page.rel) if page.is_index else page.rel)))
        try:
            page.weight = int(fm.get("weight") or 0)
        except (TypeError, ValueError):
            self.report.problems.append(Problem("warning", "markdown/" + page.rel, 1,
                                                "weight is not a number: %r" % fm.get("weight")))
        page.draft = fm.get("draft") is True or str(fm.get("draft")).lower() == "true"

    def by_title(self, name):
        p = self._titles.get(name)
        if p is None:
            low = name.casefold()
            p = next((q for t, q in sorted(self._titles.items()) if t.casefold() == low), None)
        return p

    # ------------------------------------------------------------ the tree
    def tree(self):
        sections = {"": Section("")}

        def sec(path):
            if path not in sections:
                s = Section(path)
                sections[path] = s
                sec(posixpath.dirname(path)).sections.append(s)
            return sections[path]

        for p in self.pages:
            if p.is_index:
                sec(posixpath.dirname(p.rel)).index = p
            else:
                sec(p.section).pages.append(p)
        for s in sections.values():
            s.pages.sort(key=order_key)
            s.sections.sort(key=order_key)
        return sections[""]

    def children(self, section):
        """A section's pages and subsections, in one order."""
        return sorted(section.pages + section.sections, key=order_key)

    def reading_order(self, root):
        out = []

        def walk(s):
            if s.index:
                out.append(s.index)
            for item in self.children(s):
                if isinstance(item, Section):
                    walk(item)
                else:
                    out.append(item)
        walk(root)
        return out

    # ------------------------------------------------------------ writing
    def check_out(self, out):
        """Raise NotOurs unless a compile may replace `out` (the module's
        docstring says which folders it may)."""
        out = Path(out)
        if not out.exists():
            return
        if not out.is_dir():
            raise NotOurs("%s is a file, not a folder" % out)
        if out.resolve() == (self.guide / "site").resolve():
            return
        if any(out.iterdir()) and not made_by_the_guide(out):
            raise NotOurs("%s is not empty and does not hold an earlier compile of "
                          "the guide (no build.json of its own): nothing was touched -- "
                          "name a new or empty folder" % out)

    def build(self, out, pages_dir=None):
        """Compile everything into `out` (a clean rebuild: written beside it
        and swapped in, so a server never serves half a site) -> Report.
        Raises NotOurs, before anything is read or written, when `out` holds
        something a compile did not make."""
        out = Path(out)
        self.check_out(out)
        self.discover()
        root = self.tree()
        order = self.reading_order(root)
        # a private box beside `out` holds the new site while it is written
        # and the old one while the two are swapped, and goes with them: no
        # name next to `out` is ever taken over or removed
        box = Path(tempfile.mkdtemp(prefix=".site-", dir=str(out.parent)))
        fresh, old = box / "new", box / "old"
        try:
            # the site itself by mkdir, not mkdtemp: mkdtemp's folders are
            # 0700, readable by their owner alone, and a site of that mode is
            # refused by GitHub Pages (deployment_perms_error) and unreadable
            # to a web server running as another user; mkdir gives the mode
            # any folder the user makes has
            fresh.mkdir()
            self._write(fresh, root, order)
            self.report.kept = _keep_whatever_it_had(out, fresh)
            if out.exists():
                out.rename(old)
            try:
                fresh.rename(out)
            except BaseException:
                if old.exists() and not out.exists():
                    old.rename(out)
                raise
        finally:
            shutil.rmtree(box, ignore_errors=True)
        self.report.pages = len(order)
        self.report.media = len(self.media)
        return self.report

    def _write(self, out, root, order):
        search = []
        nav_tree = self._nav_data(root)
        self._runtime(out)
        with inline_seam(self._prepare_inline):
            for k, page in enumerate(order):
                prev_page = order[k - 1] if k else None
                next_page = order[k + 1] if k + 1 < len(order) else None
                html_text, entry = self._page(page, root, prev_page, next_page)
                dest = out / page.out
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(html_text, encoding="utf-8")
                search.append(entry)
                for alias in _aliases(page):
                    target = out / alias
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(_redirect(rel_url(alias, page.out)), encoding="utf-8")
        for rel in self.media:
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.src / rel, dest)
        (out / "nav.js").write_text(
            "/* generated by html-guide/build.py -- the guide's pages, for the front "
            "page and the sidebar */\nwindow.GUIDE_NAV = %s;\n"
            % json.dumps({"title": self.title, "tree": nav_tree},
                         ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        (out / "search-index.js").write_text(
            "/* generated by html-guide/build.py -- the text of every page, for the "
            "search box */\nwindow.GUIDE_SEARCH = %s;\n"
            % json.dumps(search, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        (out / "build.json").write_text(json.dumps({
            "engine": ENGINE_VERSION, "fingerprint": fingerprint(self.guide),
            "pages": len(order),
            "errors": len(self.report.errors), "warnings": len(self.report.warnings),
        }, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    def _prepare_inline(self, text):
        """What every inline() call of the studio's goes through during a
        compile: the Hugo layer of the page being drawn -- after, for a
        table's cell, the line of the cell's own row is made the one a
        warning names."""
        ctx = self._current.ctx
        if ctx.cell_lines:
            lines = ctx.cell_lines.get(text)
            if lines:
                ctx.line = lines.pop(0)
        return self._current.inline_layer.prepare(text)

    @property
    def title(self):
        return str(self.root_fm.get("title") or SITE_TITLE)

    # ------------------------------------------------------------ one page
    def _page(self, page, root, prev_page, next_page):
        ctx = PageContext(self, page)
        raw_target = str(page.fm.get("target") or DEFAULT_TARGET).strip().lower()
        if raw_target not in languages.LANGS:
            ctx.warn("unknown target language %r: the page is read as %s"
                     % (raw_target, languages.get_or_default(None).name), line=1)
        L = texgen.set_target(raw_target if raw_target in languages.LANGS else None)
        renderer = R.Renderer(ctx, Store())
        ctx.renderer = renderer
        self._current = renderer
        body = renderer.render_body(page.body, page.first_line, page.fm)
        if page.is_index:
            body += self._children_list(page, root)
        body = renderer.finish(body)
        toc = [(lvl, ident, renderer.finish(inner)) for lvl, ident, inner in renderer.toc]
        # the words of the page as a reader sees them: no heading anchors
        # (the "#" beside each heading), no scripts -- all of them, however
        # long the page: a word the index leaves out is a word the search
        # box can never find
        bare = re.sub(r'<a class="g-anchor"[^>]*>#</a>', "", body)
        bare = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", bare, flags=re.S)
        text = re.sub(r"\s+", " ", R.plain(bare)).strip()
        entry = {"u": "site/" + page.out, "t": page.title,
                 "s": self._crumbs(page), "h": [R.plain(h) for _l, _i, h in toc],
                 "d": str(page.fm.get("description") or ""), "x": text}
        doc = self._template(page, root, body, toc, prev_page, next_page, ctx, L)
        return doc, entry

    def _crumbs(self, page):
        parts, path = [], page.section
        while path:
            idx = self.by_rel.get(posixpath.join(path, "_index.md"))
            parts.insert(0, idx.link_title if idx else humanize(posixpath.basename(path)))
            path = posixpath.dirname(path)
        return " › ".join(parts)

    def _children_list(self, page, root):
        """A section's own page ends on the list of what is in it, as Hugo's
        list pages do."""
        folder = posixpath.dirname(page.rel)
        sec = root
        for part in [x for x in folder.split("/") if x]:
            sec = next((s for s in sec.sections if posixpath.basename(s.path) == part), None)
            if sec is None:
                return ""
        items = []
        for item in self.children(sec):
            target = item.index if isinstance(item, Section) else item
            title = item.title if isinstance(item, Section) else item.link_title
            desc = str(target.fm.get("description") or "") if target else ""
            if target is None:
                items.append('<li><span class="g-child-t">%s</span></li>' % esc(title))
                continue
            items.append('<li><a class="g-child-t" href="%s">%s</a>%s</li>' % (
                esc(rel_url(page.out, target.out)), esc(title),
                ('<span class="g-child-d">%s</span>' % esc(desc)) if desc else ""))
        if not items:
            return ""
        return '\n<nav class="g-children" aria-label="In this section"><ul>%s</ul></nav>' % "".join(items)

    # ------------------------------------------------------------ the tree, drawn
    def _nav_data(self, root):
        """The tree as nav.js carries it: {t, u, c} with html-guide/-relative
        addresses (u), children (c) for a section."""
        def node(item):
            if isinstance(item, Section):
                return {"t": item.title, "u": ("site/" + item.index.out) if item.index else None,
                        "p": item.path, "c": [node(x) for x in self.children(item)]}
            return {"t": item.link_title, "u": "site/" + item.out}
        return [node(x) for x in self.children(root)]

    def _nav_html(self, page, root):
        here = page.out
        home = rel_url(here, "../index.html")

        def link(url, title, current):
            return '<a class="g-link%s" href="%s"%s>%s</a>' % (
                " g-here" if current else "", esc(rel_url(here, url)),
                ' aria-current="page"' if current else "", esc(title))

        def section_has(s, p):
            if s.index is p:
                return True
            return p in s.pages or any(section_has(x, p) for x in s.sections)

        def walk(items):
            out = ['<ul class="g-tree">']
            for item in items:
                if isinstance(item, Section):
                    is_open = section_has(item, page)
                    head = (link(item.index.out, item.title, item.index is page) if item.index
                            else '<span class="g-sec-t">%s</span>' % esc(item.title))
                    out.append('<li class="g-sec"><details data-sec="%s"%s><summary>%s</summary>%s'
                               '</details></li>' % (esc(item.path), " open" if is_open else "",
                                                     head, walk(self.children(item))))
                else:
                    out.append("<li>%s</li>" % link(item.out, item.link_title, item is page))
            out.append("</ul>")
            return "".join(out)

        return ('<ul class="g-tree g-top-tree"><li><a class="g-link g-home" href="%s">Home</a></li></ul>%s'
                % (esc(home), walk(self.children(root))))

    def _template(self, page, root, body, toc, prev_page, next_page, ctx, L):
        here = page.out
        up = rel_url(here, "../x")[:-1]              # to html-guide/: "../" or "../../"
        run = rel_url(here, RUNTIME_DIR + "/x")[:-1]  # to site/_parseh/
        title = page.title
        crumbs = self._crumbs(page)
        want_toc = page.fm.get("toc", True) not in (False, "false") and len(toc) >= 2
        toc_html = ""
        if want_toc:
            toc_html = ('<details class="g-toc" open><summary>On this page</summary><ul>%s</ul></details>'
                        % "".join('<li class="g-toc-%d"><a href="#%s">%s</a></li>'
                                  % (lvl, esc(ident), R.plain(h) and esc(R.plain(h)))
                                  for lvl, ident, h in toc))
        pager = []
        if prev_page is not None:
            pager.append('<a class="g-prev" href="%s"><span>Previous</span>%s</a>'
                         % (esc(rel_url(here, prev_page.out)), esc(prev_page.title)))
        else:
            pager.append('<a class="g-prev" href="%sindex.html"><span>Previous</span>Home</a>' % up)
        if next_page is not None:
            pager.append('<a class="g-next" href="%s"><span>Next</span>%s</a>'
                         % (esc(rel_url(here, next_page.out)), esc(next_page.title)))
        scripts = ['<script src="%s"></script>' % esc(rel_url(here, "nav.js"))]
        if "math" in ctx.uses or "exercise" in ctx.uses:
            scripts.append('<script src="%smathjax.js"></script>' % run)
        if "exercise" in ctx.uses:
            scripts.append('<script src="%sapp.js"></script>' % run)
        desc = str(page.fm.get("description") or "")
        return PAGE % {
            "lang": esc(ctx.prose_lang), "up": up, "run": run,
            "title": esc(title), "site": esc(self.title),
            "desc": ('<meta name="description" content="%s">\n' % esc(desc)) if desc else "",
            "crumbs": ('<span class="g-crumbs">%s</span><span class="g-sep">›</span>' % esc(crumbs))
            if crumbs else "",
            "nav": self._nav_html(page, root),
            "toc": toc_html,
            "target": esc(L.code), "dir": esc(L.dir), "scale": texgen.default_scale(L),
            "body": body,
            "pager": "".join(pager),
            "source": esc("html-guide/markdown/" + page.rel),
            "langjson": json.dumps(L.as_json(), ensure_ascii=False).replace("</", "<\\/"),
            "scripts": "\n".join(scripts),
        }

    # ------------------------------------------------------------ the runtime
    def _runtime(self, out):
        """site/_parseh/: what the pages draw with."""
        run = out / RUNTIME_DIR
        (run / "mathjax").mkdir(parents=True, exist_ok=True)
        # THE SHEET AND THE CHROME, IN THAT ORDER.  The studio's sheet was
        # split out of app.css into sheet.css (2026-09-23) so that a bare note
        # page can link the reading sheet alone; the server still answers
        # /studio/static/app.css with both, and this, which reads the DISK,
        # must put them together itself or the guide's examples lose every
        # rule that draws a document.
        css = scope_css(source("markdown/app/static/sheet.css").read_text(encoding="utf-8")
                        + "\n" + source("markdown/app/static/app.css").read_text(encoding="utf-8"))
        (run / "studio.css").write_text(
            "/* generated by html-guide/build.py from markdown/app/static/sheet.css and "
            "app.css, every rule confined to the guide's article (engine/cssscope.py) "
            "-- do not edit */\n"
            + css, encoding="utf-8")
        (run / "langs.css").write_text(languages.css(), encoding="utf-8")
        js = source("markdown/app/static/app.js").read_text(encoding="utf-8")
        (run / "app.js").write_text(js.replace("__FOLD__", languages.FOLD_JS), encoding="utf-8")
        for rel, name in (("lib/mathjax.js", "mathjax.js"), ("lib/mathjax.css", "mathjax.css"),
                          ("lib/mathjax/tex-svg.js", "mathjax/tex-svg.js"),
                          ("lib/mathjax/LICENSE", "mathjax/LICENSE"),
                          ("lib/mathjax/README.md", "mathjax/README.md")):
            if source(rel).is_file():
                shutil.copyfile(source(rel), run / name)
        fonts = sorted(set(re.findall(r"url\((?:['\"])?fonts/([^)'\"]+)", css)))
        (run / "fonts").mkdir(exist_ok=True)
        for name in fonts:
            found = find_font(name)
            if found:
                shutil.copyfile(found, run / "fonts" / name)
        # a font travels with its licence: the OFL with the copyright lines of
        # the toolbox's own faces, the GUST licence of TeX Gyre, and the
        # README that says which font is under which (lib/fonts/)
        for name in FONT_LICENCES:
            if source("lib/fonts/" + name).is_file():
                shutil.copyfile(source("lib/fonts/" + name), run / "fonts" / name)


def _aliases(page):
    """Hugo's `aliases`: old addresses that go on to the page."""
    got = page.fm.get("aliases") or []
    if isinstance(got, str):
        got = [got]
    out = []
    for a in got:
        a = str(a).strip().lstrip("/")
        if not a:
            continue
        if a.endswith("/"):
            a += "index.html"
        elif a.endswith(".md"):
            a = a[:-3] + ".html"
        elif not a.endswith(".html"):
            a += ".html"
        a = posixpath.normpath(a)
        if not a.startswith(".."):
            out.append(a)
    return out


def _redirect(url):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            '<title>Moved</title><link rel="canonical" href="%s">'
            '<meta http-equiv="refresh" content="0; url=%s"></head>'
            '<body><p>This page has moved: <a href="%s">%s</a>.</p></body></html>\n'
            % (esc(url), esc(url), esc(url), esc(url)))


PAGE = """<!DOCTYPE html>
<html lang="%(lang)s" data-guide-root="%(up)s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s — %(site)s</title>
%(desc)s<meta name="generator" content="Parseh guide engine">
<link rel="icon" href="%(up)sassets/favicon.svg">
<link rel="stylesheet" href="%(run)sstudio.css">
<link rel="stylesheet" href="%(run)slangs.css">
<link rel="stylesheet" href="%(run)smathjax.css">
<link rel="stylesheet" href="%(up)sassets/guide.css">
<script src="%(up)sassets/guide.js"></script>
</head>
<body class="guide" data-page="guide">
<a class="g-skip" href="#g-content">Skip to the text</a>
<header class="g-top">
  <button type="button" class="g-menu" data-guide-side aria-controls="g-side" aria-expanded="true" title="Show or hide the list of pages">☰</button>
  <a class="g-brand" href="%(up)sindex.html"><span class="g-glyph" lang="fa">پ</span><span class="g-name">%(site)s</span></a>
  <span class="g-where">%(crumbs)s<span class="g-title">%(title)s</span></span>
  <span class="g-sp"></span>
  <a class="g-hub" href="/" hidden title="Back to Parseh">Parseh</a>
  <button type="button" class="g-theme" data-parseh-theme title="theme">◐</button>
</header>
<div class="g-backdrop" data-guide-close hidden></div>
<div class="g-layout">
<aside class="g-side" id="g-side" aria-label="The guide's pages">
<div class="g-search"><input type="search" placeholder="Search the guide" aria-label="Search the guide" autocomplete="off" data-guide-search><div class="g-results" role="listbox" hidden></div></div>
<nav class="g-nav" id="g-nav" aria-label="Pages">%(nav)s</nav>
</aside>
<main class="g-main" id="g-content">
%(toc)s
<article class="pz g-article">
<div class="sheet" lang="%(lang)s" data-lang="%(target)s" style="--fa-scale:%(scale)s">
%(body)s
</div>
</article>
<nav class="g-pager" aria-label="Previous and next page">%(pager)s</nav>
<footer class="g-foot">Written in <code>%(source)s</code> · compiled by <code>html-guide/build.py</code></footer>
</main>
</div>
<script id="doc-lang" type="application/json">%(langjson)s</script>
%(scripts)s
</body>
</html>
"""
