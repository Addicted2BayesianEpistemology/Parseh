# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.render -- one page of the guide, Markdown in, HTML out.

The blocks come from engine/blocks.py.  What only Hugo has -- fenced code,
headings of every level with Hugo's ids, nested and loose lists, task items,
definition lists, rules, shortcodes -- is drawn here.  What the Parseh
dialect has -- paragraphs and their target-language forms, lemma headings,
boxes, tables, figures, recordings, videos, exercises, formulas, footnotes
-- is handed to the studio's own renderer (htmlgen), with its class names,
so the studio's stylesheet draws it exactly as a studio document.  Inline
text goes through the studio's inline() too, with the Hugo layer in front
of it (engine/inline.py).

A heading is the one place both have a say: `## Title` is the studio's
numbered section (a number typed by hand is taken off, as is a trailing
`= *gloss*`, and `## head | translit | ...` is a lemma), and it carries the
id Hugo would give it, so an address like page.html#code-blocks is the same
one Hugo would have made.
"""
import html
import re
import unicodedata

from . import blocks as B
from . import highlight
from . import shortcodes
from .frontmatter import FrontMatterError, split as split_front_matter
from .inline import Inline, Store
from .studio import htmlgen, mdparser, texgen, isolated_render

esc = htmlgen.esc

# The button every page with scored exercises ends on -- the markup
# htmlgen.render_document() writes after a document's last exercise, which
# app.js's bindExercises() wires to judge them all.
CHECK_EXERCISES = ('<section class="exercise-correction" data-exercise-results>'
                   '<button type="button" class="btn primary ex-correct-all">'
                   'Check exercises</button><output class="ex-score" hidden></output>'
                   '</section>')

SAFE_SCHEMES = ("http://", "https://", "mailto:", "tel:")
_AUDIO_EXTS = B.AUDIO_EXTS


def slug(text):
    """A heading's id the way Hugo makes it (autoHeadingIDType "github"):
    lower case, letters and digits of any script kept, spaces to `-`,
    other punctuation dropped."""
    out = []
    for ch in text.strip().lower():
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch.isspace():
            out.append("-")
        elif unicodedata.category(ch).startswith("M"):
            out.append(ch)
    return "".join(out)


def plain(html_text):
    """HTML -> its text, the way a reader sees it."""
    t = re.sub(r"<[^>]+>", "", html_text)
    return html.unescape(t)


def add_attrs(fragment, attrs):
    """`{#id .class key=val}` onto the first tag of a rendered block."""
    if not attrs:
        return fragment
    m = re.match(r"\s*<([a-zA-Z][\w-]*)([^>]*)>", fragment)
    if not m:
        return fragment
    tag_attrs = m.group(2)
    for key, value in attrs.items():
        if key.lower().startswith("on") or not re.fullmatch(r"[A-Za-z_][\w\-:]*", key):
            continue            # no event handlers through the back door
        if key == "class":
            cm = re.search(r'\sclass="([^"]*)"', tag_attrs)
            if cm:
                tag_attrs = (tag_attrs[:cm.start(1)] + cm.group(1) + " " + esc(value)
                             + tag_attrs[cm.end(1):])
                continue
        am = re.search(r'\s%s="[^"]*"' % re.escape(key), tag_attrs)
        if am:
            tag_attrs = tag_attrs[:am.start()] + ' %s="%s"' % (key, esc(value)) + tag_attrs[am.end():]
        else:
            tag_attrs += ' %s="%s"' % (key, esc(value))
    return fragment[:m.start(2)] + tag_attrs + fragment[m.end(2):]


class Renderer:
    """Renders one page (or one parseh-example inside it).  `ctx` answers the
    questions only the site can: where a link or a picture goes, what a
    shortcode says, and it hears the warnings (engine/site.py PageContext)."""

    def __init__(self, ctx, store=None, id_prefix=""):
        self.ctx = ctx
        self.store = store or Store()
        self.inline_layer = Inline(ctx, self.store)
        self.id_prefix = id_prefix
        self.ids = {}
        self.toc = []
        self.sec = 0
        self.examples = 0
        self.hctx = {"sec": 0, "sub": 0, "voce": 0, "img": 0, "exercise": 0,
                     "scored": 0, "toc": [], "asset_base": self._asset,
                     "editor_preview": False, "deck_button": False}

    # ---------------------------------------------------------- the page
    def render_body(self, body, first_line, fm):
        """The page's Markdown body -> HTML of its sheet (title block, blocks,
        footnotes, the exercises' check button), placeholders still in."""
        nodes, footnotes, linkdefs, problems = B.parse(body.split("\n"), first_line)
        for line, message in problems:
            self.ctx.warn(message, line=line)
        self.ctx.link_defs.update(linkdefs)
        htmlgen.reset_state(footnotes)
        title = fm.get("title")
        # Hugo takes the title from the front matter; the studio also takes a
        # first `# heading` when there is none -- and a first `# heading` that
        # only repeats the title is not drawn twice
        if nodes and nodes[0]["kind"] == "heading" and nodes[0]["level"] == 1:
            if not title:
                title = nodes.pop(0)["text"]
            elif plain(self._inline(nodes[0]["text"])).strip() == plain(self._inline(title)).strip():
                nodes.pop(0)
        head = htmlgen._titleblock({"title": title or "",
                                    "subtitle": fm.get("subtitle") or "",
                                    "note": fm.get("note") or ""})
        out = [head, self.render_nodes(nodes)]
        notes = htmlgen._footnote_list()
        if notes:
            # the studio's heading is the Italian "Note"; this guide is English
            out.append(notes.replace("<h4>Note</h4>", "<h4>Notes</h4>", 1))
        if self.hctx["scored"] and not self.id_prefix:
            out.append(CHECK_EXERCISES)
        return "\n".join(x for x in out if x)

    def render_fragment(self, text, first_line):
        """Markdown inside a shortcode (`details`) -> its blocks, drawn with
        the page's footnotes and link definitions."""
        nodes, footnotes, linkdefs, problems = B.parse(text.split("\n"), first_line)
        for line, message in problems:
            self.ctx.warn(message, line=line)
        self.ctx.link_defs.update(linkdefs)
        htmlgen._FN["defs"].update(footnotes)
        return self.render_nodes(nodes)

    def finish(self, fragment):
        """Placeholders -> their HTML, pictures loaded lazily."""
        page = self.store.restore(fragment)
        return re.sub(r"<img(?![^>]*\bloading=)", '<img loading="lazy" decoding="async"', page)

    # ---------------------------------------------------------- helpers
    def _inline(self, text):
        return htmlgen.inline(text)

    def _asset(self, path):
        """Where a picture or recording an exercise or figure names is, from
        this page: its path is read relative to the page, as Hugo reads a
        page bundle's resources."""
        return self.ctx.media_url(path) or path

    def _unique(self, ident):
        ident = self.id_prefix + (ident or "section")
        if ident not in self.ids:
            self.ids[ident] = 0
            return ident
        while True:
            self.ids[ident] += 1
            cand = "%s-%d" % (ident, self.ids[ident])
            if cand not in self.ids:
                self.ids[cand] = 0
                return cand

    def para_text(self, lines):
        """A paragraph's lines -> one line of text, as the studio joins them,
        with Hugo's hard breaks (two spaces or a backslash at a line's end)
        kept as breaks."""
        parts = []
        for k, raw in enumerate(lines):
            piece = raw.strip()
            last = k == len(lines) - 1
            hard = not last and (raw.endswith("  ") or piece.endswith("\\"))
            if hard and piece.endswith("\\"):
                piece = piece[:-1].rstrip()
            parts.append(piece)
            if not last:
                parts.append(self.store.put("<br>", "\n") if hard else " ")
        return "".join(parts)

    # ---------------------------------------------------------- blocks
    def render_nodes(self, nodes, in_box=False):
        out = []
        for node in nodes:
            self.ctx.line = node.get("line", self.ctx.line)
            try:
                piece = self.node(node, in_box)
            except FrontMatterError as e:
                self.ctx.warn(str(e), line=node.get("line"), level="error")
                piece = ""
            if piece and node.get("attrs") and node["kind"] != "heading":
                piece = add_attrs(piece, node["attrs"])
            if piece:
                out.append(piece)
        return "\n".join(out)

    def studio(self, block, in_box=False):
        """One block of the studio's model, drawn by the studio."""
        block.pop("_line", None)
        return htmlgen.render_blocks([block], self.hctx, inside_box=in_box)

    def node(self, node, in_box):
        kind = node["kind"]
        if kind == "para":
            return self.studio({"type": "para", "text": self.para_text(node["lines"])}, in_box)
        if kind == "heading":
            return self.heading(node)
        if kind == "code":
            if node["lang"].lower() == "parseh-example":
                return self.example(node)
            return self.code(node["code"], node["lang"], node["opts"])
        if kind == "hr":
            return "<hr>"
        if kind == "box":
            return '<div class="box">%s</div>' % self.render_nodes(node["children"], True)
        if kind == "list":
            return self.list(node)
        if kind == "dl":
            return self.dl(node)
        if kind == "table":
            return self.table(node, in_box)
        if kind == "figure":
            return self.figure(node)
        if kind == "video":
            return self.video(node)
        if kind in ("exercise", "math"):
            return self.parseh_block(node, in_box)
        if kind == "shortcode":
            return shortcodes.block(self, node)
        return ""

    def heading(self, node):
        level, text = node["level"], node["text"]
        attrs = dict(node.get("attrs") or {})
        numbered = ""
        if level in (2, 3):
            # the studio reads it first: a lemma, or a section whose typed
            # number and trailing gloss it takes off
            _fm, got = mdparser.parse(("## " if level == 2 else "### ") + text,
                                      target=texgen.cur_lang().code)
            b = got[0] if got else {"type": "section", "text": text}
            if b["type"] == "voce":
                return self.studio(b)
            text = b.get("text", text)
            if level == 2:
                self.sec += 1
                numbered = '<span class="secnum">%d.</span> ' % self.sec
        inner = self._inline(text)
        ident = self._unique(attrs.pop("id", None) or slug(plain(self.store.restore(inner))))
        cls = {2: "section", 3: "subsection"}.get(level, "g-h%d" % level)
        if attrs.get("class"):
            cls += " " + attrs.pop("class")
        extra = "".join(' %s="%s"' % (k, esc(v)) for k, v in attrs.items()
                        if re.fullmatch(r"[A-Za-z_][\w\-:]*", k) and not k.lower().startswith("on"))
        if level in (2, 3) and not self.id_prefix:
            self.toc.append((level, ident, inner))
        anchor = ('<a class="g-anchor" href="#%s" aria-label="Link to this section">#</a>'
                  % esc(ident))
        return '<h%d class="%s" id="%s"%s>%s%s%s</h%d>' % (
            level, cls, esc(ident), extra, numbered, inner, anchor, level)

    def table(self, node, in_box):
        """A table: the studio draws it whole, asking its inline() for one
        cell after another.  So that a warning in a cell (a dead link, a
        missing picture) names the cell's own row and not the table's first
        line, the page's context is told which line each cell's text is on
        (cell_lines, read by the seam in engine/site.py) for the time of the
        call."""
        lines = {}
        for c in node["header"]:
            lines.setdefault(c, []).append(node["line"])
        for row, line in zip(node["rows"], node.get("row_lines") or []):
            for c in row:
                lines.setdefault(c, []).append(line)
        self.ctx.cell_lines = lines
        try:
            return self.studio({"type": "table", "header": node["header"],
                                "align": node["align"], "rows": node["rows"]}, in_box)
        finally:
            self.ctx.cell_lines = None

    def list(self, node):
        items = node["items"]
        # THE STUDIO'S DESCRIPTION LIST WINS: a plain bullet list, more than
        # one item, every item one line opening with **a label** -- drawn as
        # the studio draws it (a two-column list, or the lexicon layout for a
        # long target-language label)
        if (not node["ordered"] and not node["loose"] and len(items) > 1
                and all(len(it["children"]) == 1 and it["children"][0]["kind"] == "para"
                        and it["task"] is None
                        and re.match(r"^\*\*.+?\*\*", it["children"][0]["lines"][0].strip())
                        for it in items)):
            return htmlgen._render_list(
                {"items": [[0, self.para_text(it["children"][0]["lines"])] for it in items]},
                ordered=False)
        tag = "ol" if node["ordered"] else "ul"
        start = node.get("start")
        attrs = ' start="%d"' % start if node["ordered"] and start not in (None, 1) else ""
        tasks = any(it["task"] is not None for it in items)
        out = ['<%s%s%s>' % (tag, ' class="g-tasks"' if tasks else "", attrs)]
        for it in items:
            kids = it["children"]
            self.ctx.line = it["line"]      # a warning names the item's own line
            if node["loose"]:
                body = self.render_nodes(kids)
            elif kids and kids[0]["kind"] == "para":
                body = self._inline(self.para_text(kids[0]["lines"]))
                rest = self.render_nodes(kids[1:])
                body = body + ("\n" + rest if rest else "")
            else:
                body = self.render_nodes(kids)
            box = ""
            cls = ""
            if it["task"] is not None:
                cls = ' class="g-task"'
                box = ('<input type="checkbox" disabled%s aria-label="%s"> '
                       % (" checked" if it["task"] else "", "done" if it["task"] else "to do"))
            out.append("<li%s>%s%s</li>" % (cls, box, body))
        out.append("</%s>" % tag)
        return "".join(out)

    def dl(self, node):
        # The studio's two description lists.  "desc" runs a definition on
        # after its term, on the term's line: right for one term and one
        # definition, but a term with two definitions -- or two terms to one
        # definition -- would run together, "Term Definition aDefinition b".
        # Such a list is the studio's other one, "lex": every term and every
        # definition on a line of its own, the definitions set in under the
        # term, as Hugo draws any definition list.  The whole list, so that
        # its entries look alike.
        many = any(len(it["terms"]) > 1 or len(it["defs"]) > 1 for it in node["items"])
        out = ['<dl class="%s g-dl">' % ("lex" if many else "desc")]
        for item in node["items"]:
            out.append('<div class="di">')
            # each term and definition says its own line in a warning
            for t, line in zip(item["terms"], item.get("term_lines") or [None] * len(item["terms"])):
                self.ctx.line = line or self.ctx.line
                out.append("<dt>%s</dt>" % self._inline(t))
            for d, line in zip(item["defs"], item.get("def_lines") or [None] * len(item["defs"])):
                self.ctx.line = line or self.ctx.line
                out.append("<dd>%s</dd>" % self._inline(d))
            out.append("</div>")
        out.append("</dl>")
        return "".join(out)

    def figure(self, node):
        attrs = mdparser.parse_image_attrs(node["layout"] or "")
        path = node["path"]
        ext = path.split("?")[0].rsplit(".", 1)[-1].lower()
        kind = "audio" if ext in _AUDIO_EXTS else "image"
        b = dict({"type": kind, "caption": node["caption"].strip(), "path": path,
                  "valid": True}, **attrs)
        # laid out as a card lays one out: no layout button (there is no
        # editor here), and no index into a document's figures
        ctx = dict(self.hctx, in_card=True)
        if kind == "audio":
            return htmlgen._render_audio(b, ctx)
        return htmlgen._render_image(b, ctx)

    def video(self, node):
        _fm, got = mdparser.parse(node["source"], target=texgen.cur_lang().code)
        b = got[0] if got else None
        if not b or b["type"] != "video":
            return ""
        if not b.get("valid"):
            self.ctx.warn("not a YouTube address or id: %s" % b.get("url"), line=node["line"])
        return htmlgen._render_video(b, dict(self.hctx, in_card=True))

    def parseh_block(self, node, in_box):
        _fm, got = mdparser.parse("\n".join(node["source"]), target=texgen.cur_lang().code)
        out = []
        for b in got:
            if b["type"] == "exercise":
                self.ctx.uses.add("exercise")
                # drawn as the studio draws it ("needs attention"), and said
                for e in b.get("errors") or []:
                    self.ctx.warn("exercise: %s" % e, line=node["line"])
                out.append(self.studio(b, in_box))
            elif b["type"] == "math":
                self.ctx.uses.add("math")
                out.append(self.studio(b, in_box))
        return "\n".join(out)

    # ---------------------------------------------------------- code
    def code(self, code, lang, opts="", label=None):
        """A fenced block: verbatim, highlighted, in its own coloured region
        with the language named and a Copy button.  Hugo's highlight options
        work: linenos, linenostart, hl_lines."""
        self.ctx.uses.add("code")
        options = parse_code_options(opts)
        name = highlight.canonical(lang)
        lines = highlight.render_lines(code, name)
        start = options.get("linenostart", 1)
        marked = options.get("hl_lines", set())
        numbers = options.get("linenos", False)
        rows = []
        for k, body in enumerate(lines):
            n = start + k
            cls = "g-line" + (" g-hl" if (k + 1) in marked else "")
            ln = '<span class="g-ln" aria-hidden="true">%d</span>' % n if numbers else ""
            rows.append('<span class="%s">%s%s</span>' % (cls, ln, body or ""))
        shown = label or (lang if lang and name == "text" else highlight.LABELS.get(name, name))
        return ('<div class="g-code%s" data-code="%s">'
                '<div class="g-code-bar"><span class="g-code-lang">%s</span>'
                '<button type="button" class="g-copy" title="Copy this code">Copy</button></div>'
                '<pre class="g-pre"><code>%s</code></pre></div>'
                % (" g-numbered" if numbers else "", esc(name), esc(shown or "text"),
                   "".join(rows)))

    def example(self, node):
        """```parseh-example: the source, with its Copy button, and beside it
        what the studio draws from it -- rendered on its own, as a document
        of its own (its own footnotes, its own front matter and target)."""
        self.examples += 1
        n = self.examples
        source = node["code"]
        shown = self.code(source, "parseh", label="Parseh Markdown")
        try:
            fm, body, first, _fmt = split_front_matter(source)
        except FrontMatterError as e:
            self.ctx.warn("parseh-example: %s" % e, line=node["line"], level="error")
            fm, body, first = {}, source, 1
        target = str(fm.get("target") or texgen.cur_lang().code).strip().lower()
        from .studio import languages
        L = languages.get_or_default(target)
        if target != L.code:
            self.ctx.warn("parseh-example: unknown target %r" % target, line=node["line"])
        prefix = "%sex%d-" % (self.id_prefix, n)
        sub = Renderer(self.ctx, self.store, id_prefix=prefix)
        sub.hctx["exercise"] = self.hctx["exercise"]
        with isolated_render(L.code):
            saved_defs = dict(self.ctx.link_defs)
            try:
                inner = sub.render_body(body, node["line"] + first, fm)
            finally:
                self.ctx.link_defs.clear()
                self.ctx.link_defs.update(saved_defs)
        # the studio numbers its footnote clouds per document: inside a page
        # they must not share ids with the page's own
        inner = re.sub(r'(id="|aria-describedby="|href="#)(fn-|fnlist-)', r"\1%s\2" % prefix, inner)
        self.hctx["exercise"] = sub.hctx["exercise"]
        self.hctx["scored"] += sub.hctx["scored"]
        return ('<div class="g-example">%s<div class="g-example-out" lang="%s" data-lang="%s"'
                ' style="--fa-scale:%s"><div class="g-example-label">Result</div>%s</div></div>'
                % (shown, esc(str(fm.get("lang") or self.ctx.prose_lang)), esc(L.code),
                   texgen.default_scale(L), inner))


def parse_code_options(opts):
    """Hugo's highlighting options, `{linenos=true,hl_lines=[2,"4-5"]}` in a
    fence's braces or `linenos=table,hl_lines=8 15-17` in a shortcode ->
    {"linenos": bool, "linenostart": int, "hl_lines": {line numbers}}."""
    out = {}
    if not opts:
        return out
    s = opts.strip().strip("{}")
    m = re.search(r"linenos\s*=\s*\"?(\w+)", s)
    if m:
        out["linenos"] = m.group(1).lower() not in ("false", "0", "no", "none")
    m = re.search(r"linenostart\s*=\s*\"?(\d+)", s)
    if m:
        out["linenostart"] = int(m.group(1))
    m = re.search(r"hl_lines\s*=\s*(\[[^\]]*\]|\"[^\"]*\"|[\d\-\s]+(?=,|$))", s)
    if m:
        marked = set()
        for part in re.findall(r"\d+\s*-\s*\d+|\d+", m.group(1)):
            if "-" in part:
                a, b = (int(x) for x in part.split("-"))
                marked.update(range(a, b + 1))
            else:
                marked.add(int(part))
        out["hl_lines"] = marked
    return out
