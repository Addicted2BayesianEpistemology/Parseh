# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.blocks -- the page's blocks: Hugo's, and the Parseh dialect's.

parse(lines, first_line) reads the body of a page (front matter already
taken off) into a list of nodes, dicts with a "kind" and the source line they
start on.  Nothing is rendered here: engine/render.py draws the Hugo-only
nodes itself and hands the Parseh ones to the studio's renderer.

The blocks, in the order a line is tried:

    ```lang {opts} ... ```  ~~~        fenced code, verbatim (the only code block)
    <!-- ... -->                       a comment: dropped
    {{< name >}} ... {{< /name >}}     a shortcode on lines of its own
    :::exercise type ... :::           an exercise (Parseh)
    :::math ... :::                    a formula (Parseh)
    [^id]: text                        a footnote (Parseh's, one paragraph)
    [label]: url "title"               a link reference definition
    # .. ######                        ATX headings; `## a | b` is a lemma (Parseh)
    ***  ---  ___                      a thematic break
    > ...                              a box (Parseh: not a plain blockquote)
    | a | b | + |---|---|              a table
    ![cap](pic.png){width=..}          a figure laid out the studio's way (Parseh)
    ![cap](clip.mp3)                   a recording (Parseh)
    @[cap](youtube url){...}           a video (Parseh)
    - * + 1. 1)                        lists, nested, loose or tight, task items
    Term / : definition                a definition list
    Text / === or ---                  setext headings
    {.class #id key=val}               attributes for the block just above
    anything else                      a paragraph

WHERE PARSEH WINS here: `>` is always the studio's box and takes no lazy
continuation; `## x | y` is a lemma; an image with the studio's layout braces
or a recording's extension is the studio's figure; a table is found the way
the studio finds one (a line with `|` over a delimiter row), and its rows
run while lines hold a `|`; a list item takes no lazy line either -- a line
under it at the margin ends the list, as in the studio, and only a line
indented (two columns or more) carries the item's text on.  A blank line
between two items keeps Hugo's reading, one loose list: the studio would end
the list there and number the next from 1, having no item of more than one
line of text, and the guide needs Hugo's loose lists, start numbers and
items that hold paragraphs, code or a box (README.md's table says so).  Indentation is never code -- the studio never
had indented code blocks, and a Parseh document indents freely -- so an
indented line is paragraph text, and code is always fenced.

A TAB IS READ AS FOUR COLUMNS AND SHOWN AS A TAB.  Every line is kept twice:
with its tabs expanded to the next multiple of four, which is what the
structure is read from (how far a line is indented, where a list item's
text begins), and as it was written, which is what a code block shows and
its Copy button copies -- a Makefile's recipe line begins with a tab, and a
tab-separated table is tabs.  A container (a box, a list item) hands its
lines on less the columns it took, counted the same way (_cut).
"""
import re

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
HR_RE = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
LIST_RE = re.compile(r"^( {0,3}|\t?)([-*+]|\d{1,9}[.)])(?:([ \t]+)(.*)|[ \t]*)$")
FOOTNOTE_RE = re.compile(r"^\[\^([^\]\s]+)\]:\s*(.*)$")
LINKDEF_RE = re.compile(r"^ {0,3}\[((?:[^\[\]\\]|\\.)+)\]:[ \t]*(<[^<>\n]*>|\S+)"
                        r"(?:[ \t]+(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|\((?:[^()\\]|\\.)*\)))?[ \t]*$")
TABLE_DELIM_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$")
EXERCISE_RE = re.compile(r"^:::exercise(?:\s+[a-z][a-z0-9-]*)?\s*$", re.I)
MATH_RE = re.compile(r"^:::math\s*$", re.I)
IMAGE_LINE_RE = re.compile(r"^!\[([^\[\]]*)\]\(\s*([^()\s]+)\s*\)(?:\{([^{}]*)\})?$")
VIDEO_LINE_RE = re.compile(r"^@\[([^\[\]]*)\]\(\s*([^()\s]+)\s*\)(?:\{([^{}]*)\})?$")
# one tag alone on its line: its arguments never run past the first `>}}`,
# so `{{< a >}}text{{< /a >}}` on one line is left to the line's own reading
SHORTCODE_LINE_RE = re.compile(r"^\s*\{\{([<%])\s*(/?)\s*([A-Za-z0-9_.\-/]+)"
                               r"((?:(?![>%]\}\}).)*?)\s*([>%])\}\}\s*$")
ATTR_LINE_RE = re.compile(r"^\s*\{((?:[#.][\w\-:]+|[A-Za-z_][\w\-]*=(?:\"[^\"]*\"|'[^']*'|[^\s{}]+))"
                          r"(?:\s+(?:[#.][\w\-:]+|[A-Za-z_][\w\-]*=(?:\"[^\"]*\"|'[^']*'|[^\s{}]+)))*)\}\s*$")
HEADING_ATTR_RE = re.compile(r"[ \t]+\{((?:[#.][\w\-:]+|[A-Za-z_][\w\-]*=(?:\"[^\"]*\"|'[^']*'|[^\s{}]+))"
                             r"(?:\s+(?:[#.][\w\-:]+|[A-Za-z_][\w\-]*=(?:\"[^\"]*\"|'[^']*'|[^\s{}]+)))*)\}[ \t]*$")
DEF_RE = re.compile(r"^ {0,3}:[ \t]+(.*)$")
# the extensions a recording may have (the studio's list, mdparser.AUDIO_EXTS)
AUDIO_EXTS = ("mp3", "m4a", "aac", "ogg", "oga", "opus", "wav", "flac", "webm")

# the Hugo shortcodes that need a closing tag, and the ones that never take one
PAIRED = {"details", "highlight", "comment"}
SINGLE = {"figure", "youtube", "vimeo", "x", "twitter", "instagram", "gist",
          "param", "ref", "relref"}


def parse_attrs(s):
    """`#id .a .b key=val key="v w"` -> {"id": .., "class": "a b", key: val}."""
    out, classes = {}, []
    for m in re.finditer(r"([#.])([\w\-:]+)|([A-Za-z_][\w\-]*)=(\"[^\"]*\"|'[^']*'|[^\s{}]+)", s or ""):
        if m.group(1) == "#":
            out["id"] = m.group(2)
        elif m.group(1) == ".":
            classes.append(m.group(2))
        else:
            v = m.group(4)
            out[m.group(3)] = v[1:-1] if v[:1] in "\"'" else v
    if classes:
        out["class"] = " ".join(classes)
    return out


def _expand_tabs(line):
    return line.expandtabs(4)


def _cut(text, col, n):
    """`text`, a line as written that begins at column `col` of its line in
    the file, less its first `n` columns -- counted as _expand_tabs counts
    them, a tab reaching the next multiple of four.  A tab the cut goes
    through the middle of leaves the rest of its width as spaces."""
    at, end = col, col + n
    for k, ch in enumerate(text):
        if at >= end:
            return text[k:]
        step = 4 - at % 4 if ch == "\t" else 1
        if at + step > end:
            return " " * (at + step - end) + text[k + 1:]
        at += step
    return ""


class Parser:
    def __init__(self, lines, first_line, raw=None, cols=None, credit=0):
        # the lines with their tabs expanded, for the structure; as written
        # (`raw`), for code; and the column of its line in the file each
        # written one begins at (a container's lines begin inside theirs)
        self.lines = [_expand_tabs(x) for x in lines]
        self.raw = list(lines) if raw is None else list(raw)
        self.cols = [0] * len(self.lines) if cols is None else list(cols)
        self.first = first_line     # the file line of lines[0]
        # the columns of list indentation already taken off these lines (a
        # list item's lines lose its width; a box's lines start afresh after
        # the `>`): the studio reads a list's continuation line by its
        # indentation from the page's -- or the box's -- margin
        self.credit = credit
        self.n = len(self.lines)
        self.nodes = []
        self.footnotes = {}         # id -> text   (the page's, all levels)
        self.linkdefs = {}          # label -> (url, title)
        self.problems = []          # (line, message)

    # -------------------------------------------------------------- helpers
    def at(self, i):
        return self.first + i

    def _starts_block(self, i):
        """Does line i start a block that ends an open paragraph?"""
        s = self.lines[i]
        t = s.strip()
        if FENCE_RE.match(s) or ATX_RE.match(s) or HR_RE.match(s):
            return True
        if t.startswith(">") or t.startswith("<!--"):
            return True
        if EXERCISE_RE.match(t) or MATH_RE.match(t) or FOOTNOTE_RE.match(t):
            return True
        if SHORTCODE_LINE_RE.match(s) and not t.startswith(("{{</*", "{{%/*")):
            return True
        if self._table_at(i):
            return True
        if self._figure_line(t) or VIDEO_LINE_RE.match(t):
            return True
        m = LIST_RE.match(s)
        if m and m.group(4) is not None and m.group(4).strip():
            return True
        return False

    def _figure_line(self, t):
        """A picture the studio lays out (the braces), or a recording."""
        m = IMAGE_LINE_RE.match(t)
        if not m:
            return None
        path = m.group(2).split("?")[0].split("#")[0].lower()
        if m.group(3) is not None or path.rsplit(".", 1)[-1] in AUDIO_EXTS:
            return m
        return None

    def _table_at(self, i):
        if i + 1 >= self.n or "|" not in self.lines[i]:
            return False
        delim = self.lines[i + 1]
        if not TABLE_DELIM_RE.match(delim) or "-" not in delim:
            return False
        if "|" not in delim and "|" not in self.lines[i].strip().strip("|"):
            return False
        return len(split_row(self.lines[i])) == len(split_row(delim))

    # -------------------------------------------------------------- the loop
    def parse(self):
        i = 0
        para = []                   # (line index, text)
        nodes = self.nodes

        def flush():
            if para:
                nodes.append({"kind": "para", "line": self.at(para[0][0]),
                              "lines": [t for _, t in para]})
                para.clear()

        while i < self.n:
            s = self.lines[i]
            t = s.strip()

            if not t:
                flush()
                i += 1
                continue

            # a setext underline turns the open paragraph into a heading
            if para and SETEXT_RE.match(s):
                level = 1 if t.startswith("=") else 2
                text = " ".join(x.strip() for _, x in para)
                line = self.at(para[0][0])
                para.clear()
                nodes.append(self._heading(level, text, line))
                i += 1
                continue

            # attributes for the block above: {.class #id}
            if ATTR_LINE_RE.match(s) and (para or nodes):
                flush()
                if nodes:
                    nodes[-1].setdefault("attrs", {}).update(parse_attrs(ATTR_LINE_RE.match(s).group(1)))
                i += 1
                continue

            m = FENCE_RE.match(s)
            if m and not (m.group(2)[0] == "`" and "`" in m.group(3)):
                flush()
                i = self._fence(i, m)
                continue

            if t.startswith("<!--"):
                flush()
                j = i
                while j < self.n and "-->" not in self.lines[j]:
                    j += 1
                rest = self.lines[j].split("-->", 1)[1] if j < self.n else ""
                i = j + 1
                if rest.strip():
                    # text after the comment on its closing line reads on
                    self.cols[j] += len(self.lines[j]) - len(rest)
                    self.lines[j] = self.raw[j] = rest
                    i = j
                continue

            if t.startswith(("{{<", "{{%")) and not t.startswith(("{{</*", "{{%/*")) \
                    and not re.search(r"[>%]\}\}", t):
                # a shortcode whose arguments run over several lines, as Hugo
                # allows: read as the one line it stands for
                j = i + 1
                while j < self.n and j - i < 20 and not re.search(r"[>%]\}\}", self.lines[j]):
                    j += 1
                joined = " ".join(x.strip() for x in self.lines[i:j + 1]) if j < self.n else ""
                if joined and SHORTCODE_LINE_RE.match(joined):
                    # the lines it took are left blank, so that every line
                    # after it keeps its number for the warnings
                    self.lines[i] = self.raw[i] = joined
                    for k in range(i + 1, j + 1):
                        self.lines[k] = self.raw[k] = ""
                    s, t = joined, joined
            m = SHORTCODE_LINE_RE.match(s)
            if m and not t.startswith(("{{</*", "{{%/*")):
                flush()
                i = self._shortcode(i, m)
                continue

            if EXERCISE_RE.match(t) or MATH_RE.match(t):
                flush()
                j = i + 1
                while j < self.n and self.lines[j].strip() != ":::":
                    j += 1
                kind = "exercise" if EXERCISE_RE.match(t) else "math"
                nodes.append({"kind": kind, "line": self.at(i),
                              "source": self.lines[i:j + 1],
                              "closed": j < self.n})
                if j >= self.n:
                    self.problems.append((self.at(i), "%s opened here is never closed "
                                                      "with a line `:::`" % t))
                i = j + 1
                continue

            m = FOOTNOTE_RE.match(t)
            if m:
                flush()
                text = m.group(2).strip()
                i += 1
                while i < self.n and self.lines[i].strip() and self.lines[i].startswith(("  ", "\t")):
                    text += " " + self.lines[i].strip()
                    i += 1
                self.footnotes[m.group(1)] = text
                continue

            if not para:
                m = LINKDEF_RE.match(s)
                if m and not m.group(1).startswith("^"):
                    url = m.group(2)
                    if url.startswith("<"):
                        url = url[1:-1]
                    title = m.group(3)[1:-1] if m.group(3) else None
                    from .inline import norm_label
                    self.linkdefs.setdefault(norm_label(m.group(1)), (url, title))
                    i += 1
                    continue

            m = ATX_RE.match(s)
            if m:
                flush()
                text = m.group(2) or ""
                # an optional closing sequence of #s, when a space precedes it
                text = re.sub(r"(?:^|[ \t]+)#+[ \t]*$", "", text)
                nodes.append(self._heading(len(m.group(1)), text, self.at(i)))
                i += 1
                continue

            if HR_RE.match(s):
                flush()
                nodes.append({"kind": "hr", "line": self.at(i)})
                i += 1
                continue

            if t.startswith(">"):
                flush()
                j = i
                inner, raw, cols = [], [], []
                while j < self.n and self.lines[j].strip().startswith(">"):
                    inner.append(re.sub(r"^\s*>[ ]?", "", self.lines[j]))
                    took = len(self.lines[j]) - len(inner[-1])
                    raw.append(_cut(self.raw[j], self.cols[j], took))
                    cols.append(self.cols[j] + took)
                    j += 1
                nodes.append({"kind": "box", "line": self.at(i),
                              "children": self._sub(inner, i, raw, cols)})
                i = j
                continue

            if self._table_at(i):
                flush()
                header = split_row(self.lines[i])
                align = []
                for c in split_row(self.lines[i + 1]):
                    c = c.strip()
                    align.append("c" if c.startswith(":") and c.endswith(":")
                                 else "r" if c.endswith(":") else "l")
                j = i + 2
                rows, row_lines = [], []
                while j < self.n and "|" in self.lines[j] and self.lines[j].strip():
                    rows.append(split_row(self.lines[j]))
                    row_lines.append(self.at(j))
                    j += 1
                nodes.append({"kind": "table", "line": self.at(i), "header": header,
                              "align": align, "rows": rows, "row_lines": row_lines})
                i = j
                continue

            m = self._figure_line(t)
            if m:
                flush()
                nodes.append({"kind": "figure", "line": self.at(i), "caption": m.group(1),
                              "path": m.group(2), "layout": m.group(3), "source": t})
                i += 1
                continue

            if VIDEO_LINE_RE.match(t):
                flush()
                nodes.append({"kind": "video", "line": self.at(i), "source": t})
                i += 1
                continue

            if DEF_RE.match(s) and (para or (nodes and nodes[-1]["kind"] == "dl")):
                i = self._definitions(i, para)
                continue

            m = LIST_RE.match(s)
            if m and ((m.group(4) or "").strip() or not para):
                flush()
                i = self._list(i)
                continue

            # a paragraph line; a following indented line is more of it
            if para and self._starts_block(i):
                flush()
                continue
            para.append((i, s))
            i += 1
        flush()
        return self.nodes

    # -------------------------------------------------------------- blocks
    def _sub(self, lines, i, raw=None, cols=None, credit=0):
        """Parse the inside of a container (a box, a list item, a shortcode)
        with this page's footnotes and link definitions."""
        p = Parser(lines, self.at(i), raw, cols, credit)
        p.footnotes, p.linkdefs, p.problems = self.footnotes, self.linkdefs, self.problems
        return p.parse()

    def _heading(self, level, text, line):
        node = {"kind": "heading", "level": level, "line": line}
        m = HEADING_ATTR_RE.search(text)
        if m and not text[:m.start()].rstrip().endswith("]"):
            node["attrs"] = parse_attrs(m.group(1))
            text = text[:m.start()]
        node["text"] = text.strip()
        return node

    def _fence(self, i, m):
        indent, fence, info = len(m.group(1)), m.group(2), m.group(3).strip()
        close = re.compile(r"^ {0,3}%s{%d,}[ \t]*$" % (re.escape(fence[0]), len(fence)))
        j = i + 1
        body = []
        while j < self.n and not close.match(self.lines[j]):
            line = self.lines[j]
            # the fence's own indentation comes off every line, no more; the
            # rest is the line as written, its tabs kept
            k = 0
            while k < indent and k < len(line) and line[k] == " ":
                k += 1
            body.append(_cut(self.raw[j], self.cols[j], k))
            j += 1
        closed = j < self.n
        if not closed:
            self.problems.append((self.at(i), "the code block opened here is never "
                                              "closed (a line of %s)" % fence))
        lang, opts = info, ""
        mo = re.match(r"^([^\s{]*)\s*(\{.*\})?\s*(.*)$", info)
        if mo:
            lang, opts = mo.group(1), (mo.group(2) or "")[1:-1]
            if not opts and mo.group(3):
                opts = mo.group(3)
        self.nodes.append({"kind": "code", "line": self.at(i), "lang": lang,
                           "opts": opts, "code": "\n".join(body), "info": info})
        return j + 1 if closed else j

    def _shortcode(self, i, m):
        name, closing = m.group(3), m.group(2)
        line = self.at(i)
        if closing:
            self.problems.append((line, "{{< /%s >}} closes a shortcode that was never "
                                        "opened" % name))
            return i + 1
        # a closing tag further down, of the same name and at the same depth
        open_re = re.compile(r"^\s*\{\{[<%%]\s*%s(?:\s.*?)?\s*[>%%]\}\}\s*$" % re.escape(name))
        close_re = re.compile(r"^\s*\{\{[<%%]\s*/\s*%s\s*[>%%]\}\}\s*$" % re.escape(name))
        depth, j = 0, i + 1
        end = None
        if name not in SINGLE and not m.group(4).rstrip().endswith("/"):
            while j < self.n:
                if open_re.match(self.lines[j]):
                    depth += 1
                elif close_re.match(self.lines[j]):
                    if depth == 0:
                        end = j
                        break
                    depth -= 1
                j += 1
        if m.group(4).rstrip().endswith("/"):
            end = None          # {{< name ... />}}: closed where it opens
        node = {"kind": "shortcode", "line": line, "name": name, "args": m.group(4),
                "markdown": m.group(1) == "%", "source": self.lines[i].strip()}
        if end is not None:
            node["inner"] = "\n".join(self.lines[i + 1:end])
            # as written too: a highlight's lines are code, shown verbatim
            node["inner_raw"] = "\n".join(self.raw[i + 1:end])
            node["inner_line"] = self.at(i + 1)
            self.nodes.append(node)
            return end + 1
        if name in PAIRED:
            self.problems.append((line, "{{< %s >}} needs its closing {{< /%s >}}" % (name, name)))
        self.nodes.append(node)
        return i + 1

    def _definitions(self, i, para):
        """Term lines (the open paragraph) and `: definition` lines -> a
        definition list, or more of the one just above it (Goldmark's
        definition list: terms separated from the next group by a blank
        line still make one list)."""
        terms = [t.strip() for _, t in para]
        term_lines = [self.at(k) for k, _ in para]
        para.clear()
        last = self.nodes[-1] if self.nodes else None
        if last is not None and last["kind"] == "dl":
            dl = last
        else:
            dl = {"kind": "dl", "line": self.at(i - len(terms)), "items": []}
            self.nodes.append(dl)
        if terms or not dl["items"]:
            dl["items"].append({"terms": terms, "term_lines": term_lines,
                                "defs": [], "def_lines": []})
        item = dl["items"][-1]
        while i < self.n:
            m = DEF_RE.match(self.lines[i])
            if not m:
                break
            text = [m.group(1)]
            item["def_lines"].append(self.at(i))
            i += 1
            # the definition runs on over its continuation lines
            while i < self.n and self.lines[i].strip() and not DEF_RE.match(self.lines[i]) \
                    and (self.lines[i].startswith(("  ", "\t")) or not self._starts_block(i)):
                text.append(self.lines[i].strip())
                i += 1
            item["defs"].append(" ".join(text))
            if i + 1 < self.n and not self.lines[i].strip() and DEF_RE.match(self.lines[i + 1]):
                i += 1
        return i

    def _list(self, i):
        """A list starting at line i -> its node appended; the index after it.

        An item holds its first line and every line indented to where its
        text began (CommonMark's rule), parsed again as blocks -- so lists
        nest to any depth and an item may hold paragraphs, code, a box.  A
        line indented less than that still carries on the item's text when
        it is indented at all, two columns from the margin (the studio's
        continuation line); one at the margin ends the list, as it does in
        the studio -- Hugo would take it into the item as a "lazy" line.  A
        blank line between items, or between two blocks of one item, makes
        the list loose."""
        first = LIST_RE.match(self.lines[i])
        ordered = first.group(2)[0].isdigit()
        kind = first.group(2)[-1] if ordered else first.group(2)
        start = int(first.group(2)[:-1]) if ordered else None
        items, loose = [], False
        j = i
        while j < self.n:
            m = LIST_RE.match(self.lines[j])
            if not m or HR_RE.match(self.lines[j]):
                break
            mk = m.group(2)
            if mk[0].isdigit() != ordered or (mk[-1] if ordered else mk) != kind:
                break
            content = m.group(4) if m.group(4) is not None else ""
            pad = len(m.group(3) or " ")
            if pad > 4 or not content.strip():
                pad = 1
            width = len(m.group(1)) + len(mk) + pad
            body = [content.rstrip()]
            # the item's lines as written, less the columns the item takes
            # (its first line is never inside a code block: only its own)
            raw, cols = [body[0]], [0]
            line = j
            j += 1
            blanks = 0
            while j < self.n:
                s = self.lines[j]
                if not s.strip():
                    blanks += 1
                    j += 1
                    continue
                ind = len(s) - len(s.lstrip(" "))
                if ind >= width:
                    body.extend([""] * blanks)
                    raw.extend([""] * blanks)
                    cols.extend([0] * blanks)
                    blanks = 0
                    body.append(s[width:])
                    raw.append(_cut(self.raw[j], self.cols[j], width))
                    cols.append(self.cols[j] + width)
                    j += 1
                    continue
                if blanks:
                    break
                if self.credit + ind >= 2 and not LIST_RE.match(s) and not self._starts_block(j) \
                        and not ATTR_LINE_RE.match(s) and not DEF_RE.match(s):
                    body.append(s.strip())
                    raw.append(body[-1])
                    cols.append(0)
                    j += 1
                    continue
                break
            task = None
            tm = re.match(r"^\[([ xX])\](?:[ \t]+|$)(.*)$", body[0])
            if tm:
                task = tm.group(1) != " "
                body[0] = raw[0] = tm.group(2)
            if re.search(r"\S\n\s*\n\s*\S", "\n".join(body)):
                loose = True
            items.append({"line": self.at(line), "task": task,
                          "children": self._sub(body, line, raw, cols, self.credit + width)})
            # a blank line before the next item of THIS list makes it loose;
            # before anything else (another kind of list, a paragraph) the
            # list simply ends there
            nxt = LIST_RE.match(self.lines[j]) if j < self.n else None
            if blanks and nxt and not HR_RE.match(self.lines[j]) \
                    and nxt.group(2)[0].isdigit() == ordered \
                    and (nxt.group(2)[-1] if ordered else nxt.group(2)) == kind:
                loose = True
        self.nodes.append({"kind": "list", "line": self.at(i), "ordered": ordered,
                           "start": start, "items": items, "loose": loose})
        return j


def split_row(line):
    """A table row -> its cells: split on every `|` that is not escaped
    (GFM's `\\|`, which then stands for the pipe itself); an outer pipe at
    either end opens or closes the row."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, k = [], [], 0
    while k < len(s):
        c = s[k]
        if c == "\\" and k + 1 < len(s) and s[k + 1] == "|":
            cur.append("|")
            k += 2
            continue
        if c == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        k += 1
    cells.append("".join(cur).strip())
    return cells


def parse(lines, first_line=1):
    """The body's lines -> (nodes, footnotes, link definitions, problems)."""
    p = Parser(lines, first_line)
    nodes = p.parse()
    return nodes, p.footnotes, p.linkdefs, p.problems
