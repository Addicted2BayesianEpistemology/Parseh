"""engine.inline -- Hugo's inline Markdown, laid over the studio's.

The studio's inline() (markdown/app/htmlgen.py) knows its own dialect --
`**bold**`, `*italic*`, target-language runs and marks, colours, footnotes,
`[text](url)`, `✗`, `→`, `⏎` -- and nothing of Hugo's.  prepare() below runs
first, on the same text, and does what Hugo (Goldmark with its default
extensions) adds:

    `code`, ``code with ` inside``   code spans, OPAQUE (nothing inside is read)
    \\*  \\_  \\[ ...                  backslash escapes
    &copy; &#169;                     entities
    [text](url "title")               links, with titles, relative .md links
    [text][label]  [label][]  [label] reference links, with `[label]: url`
    <https://...>  <a@b.org>          autolinks, and bare URLs (linkify)
    ![alt](src "title")               images inside running text
    _em_  __strong__  ***both***      the underscore forms, and the triple
    ~~strikethrough~~                 GFM's strikethrough
    "quotes" 'quotes' -- --- ...      the typographer: “ ” ‘ ’ – — …  « »
    {{< ref "x.md" >}} ...            shortcodes inside a line
    <!-- a comment -->                dropped

Each construct becomes a PLACEHOLDER: a run of Unicode private-use
characters that no rule of the studio's matches -- not a target script (no
registry language has a character up there), not a word character, not a
bracket -- so it passes through htmlgen.inline() untouched, wherever the
studio's rules put the text around it.  restore() puts the HTML in at the
very end, over the whole page.  A placeholder the studio copied into an
attribute (the source of a Latin block, say, `data-la-src="..."`) gets the
Markdown it stood for, escaped, instead of its HTML: an attribute holds
text, and a tag inside one would break the page.

WHERE PARSEH WINS.  A `[...]{...}` is a Parseh mark and never Goldmark's
attribute syntax.  `[...]{tl}` and `[...]{math}` are opaque in the studio,
and stay so here: nothing inside them is read as Hugo Markdown either (a
`*` inside a target-language block is a star).  Any other mark -- a colour,
a transliteration, `{la}` -- keeps its shell for the studio and has its text
read as usual.  `*` and `**` are the studio's, which is why only the
underscore forms are added.  `->` is the studio's arrow, so the typographer
leaves a dash before `>` alone.  Footnotes are the studio's (`[^id]`,
`^[inline]`), with its hover clouds and numbering.
"""
import html
import re

from .studio import ORIGINAL_INLINE, texgen

# ------------------------------------------------------------ placeholders
# PH_OPEN n PH_CLOSE stands for stored HTML; RAW_OPEN n RAW_CLOSE for stored
# SOURCE text, put back before the studio sees the line (a mark the Hugo
# passes below must not touch, but the studio must read).  n is written in
# private-use "digits", so not even a digit reaches the studio's regexes.
PH_OPEN, PH_CLOSE = "\ue000", "\ue001"
RAW_OPEN, RAW_CLOSE = "\ue002", "\ue003"
_DIGIT0 = 0xE010
_PH_RE = re.compile("\ue000([\ue010-\ue01f]+)\ue001")
_RAW_RE = re.compile("\ue002([\ue010-\ue01f]+)\ue003")
_ANY_RE = re.compile("[\ue000-\ue0ff]")


def _enc(i):
    return "".join(chr(_DIGIT0 + int(d, 16)) for d in "%x" % i)


def _dec(s):
    return int("".join("%x" % (ord(c) - _DIGIT0) for c in s), 16)


class Store:
    """The placeholders of one page: (html, source) pairs, and raw texts."""

    def __init__(self):
        self.items = []
        self.raws = []

    def put(self, html_text, source):
        self.items.append((html_text, source))
        return PH_OPEN + _enc(len(self.items) - 1) + PH_CLOSE

    def raw(self, text):
        self.raws.append(text)
        return RAW_OPEN + _enc(len(self.raws) - 1) + RAW_CLOSE

    def unraw(self, text):
        # a raw text may itself hold raw placeholders (a mark inside a
        # footnote): put back until none is left
        for _ in range(64):
            new = _RAW_RE.sub(lambda m: self.raws[_dec(m.group(1))], text)
            if new == text:
                return new
            text = new
        return text

    def source(self, text):
        """The Markdown a string of placeholders stood for."""
        for _ in range(64):
            new = _PH_RE.sub(lambda m: self.items[_dec(m.group(1))][1], text)
            new = _RAW_RE.sub(lambda m: self.raws[_dec(m.group(1))], new)
            if new == text:
                return new
            text = new
        return text

    def restore(self, page):
        """The finished HTML of a page -> with every placeholder replaced:
        by its HTML in text, by its escaped source inside a tag."""
        def in_tag(m):
            return _PH_RE.sub(lambda p: html.escape(self.source(p.group(0)), quote=True),
                              m.group(0))

        for _ in range(64):
            if PH_OPEN not in page:
                break
            page = re.sub(r"<[^<>]*>", in_tag, page)
            page = _PH_RE.sub(lambda m: self.items[_dec(m.group(1))][0], page)
        # anything private-use left is a marker nobody claimed: never shown
        return _ANY_RE.sub("", page)


# ------------------------------------------------------------ the scanner
_ASCII_PUNCT = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_ENTITY_RE = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
_AUTOLINK_RE = re.compile(r"<([A-Za-z][A-Za-z0-9+.\-]{1,31}:[^\s<>]*)>")
_AUTOMAIL_RE = re.compile(r"<([A-Za-z0-9.!#$%&'*+/=?^_`{|}~\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?"
                          r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+)>")
_BARE_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\ue000-\ue0ff]*", re.I)
_BARE_MAIL_RE = re.compile(r"[A-Za-z0-9._+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_FN_REF_RE = re.compile(r"\[\^([^\[\]\s]+)\]")
# a blank, but not a formula that is a bracket of its own, `[[A,B]]{math}`
_SLOT_RE = re.compile(r"\[\[[^\[\]]+\]\](?!\{\s*math\s*\})")
_SHORTCODE_RE = re.compile(r"\{\{([<%])\s*(/?)\s*([A-Za-z0-9_.\-/]+)((?:\"(?:[^\"\\]|\\.)*\"|`[^`]*`|[^\"`])*?)\s*([>%])\}\}")
_SC_COMMENT_RE = re.compile(r"\{\{([<%])/\*([\s\S]*?)\*/([>%])\}\}")


def _code_end(text, i):
    """At a backtick run starting at i -> (end of the code span, its
    content) or (None, run length) when the run is never closed."""
    n = len(text)
    j = i
    while j < n and text[j] == "`":
        j += 1
    k = j - i
    at = j
    while True:
        at = text.find("`" * k, at)
        if at < 0:
            return None, k
        end = at + k
        if (end < n and text[end] == "`") or text[at - 1] == "`":
            # a longer run is not the closing one
            while at < n and text[at] == "`":
                at += 1
            continue
        return end, text[j:at]


def _bracket_end(text, i):
    """At `[` -> the index of its matching `]`, skipping code spans and
    backslash escapes, or -1."""
    depth, j, n = 0, i, len(text)
    while j < n:
        c = text[j]
        if c == "\\" and j + 1 < n:
            j += 2
            continue
        if c == "`":
            end, _ = _code_end(text, j)
            if end is not None:
                j = end
                continue
            while j < n and text[j] == "`":
                j += 1
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def _link_dest(text, i):
    """At `(` after `]` -> (dest, title, index after `)`), or None.

    A `doc:` address names a page by its title, and a title has spaces:
    for one, everything up to the closing parenthesis is the address."""
    n = len(text)
    j = i + 1
    while j < n and text[j] in " \t":
        j += 1
    if text.startswith("doc:", j):
        depth, k = 0, j
        while k < n:
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                if depth == 0:
                    return text[j:k].strip(), None, k + 1
                depth -= 1
            k += 1
        return None
    if j < n and text[j] == "<":
        k = text.find(">", j)
        if k < 0 or "\n" in text[j:k]:
            return None
        dest, j = text[j + 1:k], k + 1
    else:
        depth, k = 0, j
        while k < n:
            c = text[k]
            if c == "\\" and k + 1 < n:
                k += 2
                continue
            if c in " \t":
                break
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            k += 1
        dest, j = text[j:k], k
    while j < n and text[j] in " \t":
        j += 1
    title = None
    if j < n and text[j] in "\"'(":
        close = ")" if text[j] == "(" else text[j]
        k = j + 1
        while k < n and text[k] != close:
            if text[k] == "\\":
                k += 1
            k += 1
        if k >= n:
            return None
        title = re.sub(r"\\(.)", r"\1", text[j + 1:k])
        j = k + 1
        while j < n and text[j] in " \t":
            j += 1
    if j >= n or text[j] != ")":
        return None
    dest = re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", dest)
    return dest, title, j + 1


def norm_label(s):
    """A reference label as CommonMark matches it: case and runs of space
    do not count."""
    return re.sub(r"\s+", " ", s.strip()).casefold()


def _trim_url(url):
    """GFM's rule for where a bare URL ends: trailing punctuation is not part
    of it, nor a `)` that closes nothing."""
    while url and url[-1] in "?!.,:*_~'\";":
        url = url[:-1]
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    return url


class Inline:
    """The Hugo layer for one page.  `ctx` is the page's render context
    (engine/render.py), which answers where a link or a picture goes,
    expands a shortcode and hears the warnings."""

    def __init__(self, ctx, store):
        self.ctx = ctx
        self.store = store

    # -- small helpers
    def ph(self, html_text, source):
        return self.store.put(html_text, source)

    def literal(self, s):
        """Text that must come out exactly as it is, escaped."""
        return self.store.put(html.escape(s, quote=False), s)

    # -- the entry point
    def prepare(self, text):
        """A line of the dialect -> the same line with every Hugo construct
        behind a placeholder, ready for the studio's inline()."""
        if not text:
            return text
        text = self._shortcodes(text)
        out = []
        i, n = 0, len(text)
        tl_re = texgen.tl_re()
        while i < n:
            c = text[i]
            if c in (PH_OPEN, RAW_OPEN):
                close = PH_CLOSE if c == PH_OPEN else RAW_CLOSE
                k = text.find(close, i)
                if k > 0:
                    out.append(text[i:k + 1])
                    i = k + 1
                    continue
            if c == "\\" and i + 1 < n and text[i + 1] in _ASCII_PUNCT:
                out.append(self.store.put(html.escape(text[i + 1], quote=False),
                                          text[i:i + 2]))
                i += 2
                continue
            if c == "`":
                end, content = _code_end(text, i)
                if end is None:
                    out.append(self.literal("`" * content))
                    i += content
                    continue
                body = content.replace("\n", " ")
                if len(body) > 1 and body[0] == " " and body[-1] == " " and body.strip():
                    body = body[1:-1]
                out.append(self.ph("<code>%s</code>" % html.escape(self.store.source(body),
                                                                   quote=False),
                                   text[i:end]))
                i = end
                continue
            if c == "<":
                if text.startswith("<!--", i):
                    k = text.find("-->", i + 4)
                    if k >= 0:
                        i = k + 3
                        continue
                m = _AUTOLINK_RE.match(text, i) or _AUTOMAIL_RE.match(text, i)
                if m:
                    url = m.group(1)
                    href = "mailto:" + url if m.re is _AUTOMAIL_RE else url
                    out.append(self.ph(self.ctx.link_html(href, None, html.escape(url)),
                                       m.group(0)))
                    i = m.end()
                    continue
            if c == "&":
                m = _ENTITY_RE.match(text, i)
                if m:
                    ch = html.unescape(m.group(0))
                    if ch != m.group(0):
                        out.append(self.store.put(html.escape(ch, quote=False), m.group(0)))
                        i = m.end()
                        continue
            if c == "!" and text.startswith("![", i):
                got = self._image(text, i)
                if got:
                    out.append(got[0])
                    i = got[1]
                    continue
            if c == "^" and text.startswith("^[", i):
                j = _bracket_end(text, i + 1)
                if j > 0:
                    out.append(self.store.raw("^[" + self.prepare(text[i + 2:j]) + "]"))
                    i = j + 1
                    continue
            if c == "[":
                got = self._bracket(text, i, tl_re)
                if got:
                    out.append(got[0])
                    i = got[1]
                    continue
            if c in "hHwW" and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] in "/:@.")):
                m = _BARE_URL_RE.match(text, i)
                if m:
                    url = _trim_url(m.group(0))
                    if len(url) > (7 if url.lower().startswith("http") else 4) and "." in url:
                        href = url if url.lower().startswith("http") else "http://" + url
                        out.append(self.ph(self.ctx.link_html(href, None, html.escape(url)), url))
                        i += len(url)
                        continue
            if c.isalnum() and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] in "._+-@/")):
                m = _BARE_MAIL_RE.match(text, i)
                if m and "@" in m.group(0):
                    mail = m.group(0).rstrip(".-")
                    out.append(self.ph(self.ctx.link_html("mailto:" + mail, None, html.escape(mail)),
                                       mail))
                    i += len(mail)
                    continue
            out.append(c)
            i += 1
        s = "".join(out)
        s = self._emphasis(s)
        s = typographer(s)
        return self.store.unraw(s)

    # -- shortcodes inside a line
    def _shortcodes(self, text):
        """Hugo expands shortcodes before it reads the Markdown around them
        -- which is why `[a link]({{< ref "page.md" >}})` works -- so they
        go first here too, everywhere but inside a code span."""
        if "{{" not in text:
            return text
        out, i, n = [], 0, len(text)
        while i < n:
            if text[i] == "`":
                end, content = _code_end(text, i)
                stop = end if end is not None else i + content
                out.append(text[i:stop])
                i = stop
                continue
            if text.startswith("{{", i):
                m = _SC_COMMENT_RE.match(text, i)
                if m:
                    # {{</* figure */>}} -- Hugo's own way to write a
                    # shortcode that is shown and not run
                    shown = "{{%s%s%s}}" % (m.group(1), m.group(2), m.group(3))
                    out.append(self.literal(shown))
                    i = m.end()
                    continue
                m = _SHORTCODE_RE.match(text, i)
                if m and not m.group(2):
                    name, args = m.group(3), m.group(4)
                    inner, end = None, m.end()
                    close = re.compile(r"\{\{[<%%]\s*/\s*%s\s*[>%%]\}\}" % re.escape(name))
                    cm = close.search(text, m.end())
                    if cm:
                        inner, end = text[m.end():cm.start()], cm.end()
                    kind, value = self.ctx.inline_shortcode(name, args, inner,
                                                           text[i:end], m.group(1))
                    if kind == "text":
                        out.append(value)
                    else:
                        out.append(self.ph(value, text[i:end]))
                    i = end
                    continue
            out.append(text[i])
            i += 1
        return "".join(out)

    # -- [ ... ]
    def _bracket(self, text, i, tl_re):
        n = len(text)
        m = _FN_REF_RE.match(text, i)
        if m and not text.startswith(":", m.end()):
            return self.store.raw(m.group(0)), m.end()
        m = _SLOT_RE.match(text, i)
        if m:
            return self.store.raw(m.group(0)), m.end()
        j = _bracket_end(text, i)
        if j < 0:
            m = texgen.MATH_RE.match(text, i)
            if m:
                return self._math(m.group(0)), m.end()
            return None
        inner = text[i + 1:j]
        nxt = text[j + 1] if j + 1 < n else ""
        if nxt == "{":
            k = text.find("}", j + 2)
            if k > 0 and "{" not in text[j + 2:k]:
                attrs = text[j + 2:k]
                mark = text[i:k + 1]
                if re.fullmatch(r"\s*math\s*", attrs):
                    return self._math(mark), k + 1
                if tl_re.fullmatch(mark):
                    # a target-language stretch is opaque: the studio reads it
                    # as it is, and nothing here does
                    return self.store.raw(mark), k + 1
                return self.store.raw("[" + self.prepare(inner) + "]{" + attrs + "}"), k + 1
        if nxt == "(":
            got = _link_dest(text, j + 1)
            if got:
                dest, title, end = got
                return self._link(dest, title, inner, text[i:end]), end
        if nxt == "[":
            k = text.find("]", j + 2)
            if k > 0:
                label = text[j + 2:k] or inner
                ref = self.ctx.link_defs.get(norm_label(label))
                if ref:
                    return self._link(ref[0], ref[1], inner, text[i:k + 1]), k + 1
        ref = self.ctx.link_defs.get(norm_label(inner)) if inner.strip() else None
        if ref:
            return self._link(ref[0], ref[1], inner, text[i:j + 1]), j + 1
        m = texgen.MATH_RE.match(text, i)
        if m:
            return self._math(m.group(0)), m.end()
        return None

    def _math(self, mark):
        """A formula, drawn by the studio on its own.  Its body may hold
        brackets a balanced reading does not pair (`[x + [0,1)]{math}`), so
        where it starts and ends is the studio's own MATH_RE's to say: the
        guide and the studio find the same formulas."""
        self.ctx.uses.add("math")
        return self.ph(ORIGINAL_INLINE(mark), mark)

    def _link(self, dest, title, inner, source):
        if inner.strip():
            label = ORIGINAL_INLINE(self.prepare(inner))
        else:
            label = ""
        return self.ph(self.ctx.link_html(dest, title, label, inner=inner), source)

    def _image(self, text, i):
        j = _bracket_end(text, i + 1)
        if j < 0 or j + 1 >= len(text):
            return None
        alt = text[i + 2:j]
        if text[j + 1] == "(":
            got = _link_dest(text, j + 1)
            if not got:
                return None
            src, title, end = got
        elif text[j + 1] == "[":
            k = text.find("]", j + 2)
            if k < 0:
                return None
            ref = self.ctx.link_defs.get(norm_label(text[j + 2:k] or alt))
            if not ref:
                return None
            src, title, end = ref[0], ref[1], k + 1
        else:
            ref = self.ctx.link_defs.get(norm_label(alt))
            if not ref:
                return None
            src, title, end = ref[0], ref[1], j + 1
        plain = re.sub(r"[*_`~]|\[|\]\{[^{}]*\}|\]\([^()]*\)|\]", "", alt)
        return self.ph(self.ctx.image_html(src, title, plain), text[i:end]), end

    # -- emphasis the studio does not have
    _EM_RULES = (
        # ***both***: the studio would nest these the wrong way round
        (re.compile(r"(?<![*\\])\*\*\*(?=[^\s*])(.+?)(?<=[^\s*])\*\*\*(?!\*)"),
         "<strong><em>", "</em></strong>", "***"),
        (re.compile(r"(?<![\w_\\])__(?=[^\s_])(.+?)(?<=[^\s_])__(?![\w_])"),
         "<strong>", "</strong>", "__"),
        (re.compile(r"(?<![\w_\\])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w_])"),
         "<em>", "</em>", "_"),
        (re.compile(r"(?<![~\\])~~(?=[^\s~])(.+?)(?<=[^\s~])~~(?!~)"),
         "<del>", "</del>", "~~"),
    )

    def _emphasis(self, s):
        for rx, open_, close, delim in self._EM_RULES:
            if delim[0] not in s:
                continue
            s = rx.sub(lambda m: (self.store.put(open_, delim) + m.group(1)
                                  + self.store.put(close, delim)), s)
        return s


# ------------------------------------------------------------ the typographer
_OPENERS = set(" \t\n([{<\u2014\u2013-/\u00ab\u201c\u2018\"'") | {""}
_PH_CLOSERS = (PH_CLOSE, RAW_CLOSE)


def typographer(s):
    """Goldmark's typographer: -- and --- as dashes, ... as an ellipsis,
    << and >> as guillemets, straight quotes as curly ones.  A dash that
    points (`->`, `-->`) is left for the studio's arrow."""
    if not any(ch in s for ch in "-.<>\"'"):
        return s
    s = re.sub(r"(?<!-)---(?![->])", "\u2014", s)
    s = re.sub(r"(?<!-)--(?![->])", "\u2013", s)
    s = s.replace("...", "\u2026")
    s = re.sub(r"(?<!<)<<(?!<)", "\u00ab", s)
    s = re.sub(r"(?<!>)>>(?!>)", "\u00bb", s)
    if "'" not in s and '"' not in s:
        return s
    out = []
    for k, ch in enumerate(s):
        if ch not in "'\"":
            out.append(ch)
            continue
        prev = s[k - 1] if k else ""
        nxt = s[k + 1] if k + 1 < len(s) else ""
        starts = bool(nxt) and not nxt.isspace()
        if ch == "'":
            # after a letter, a stop or a construct (`code`'s) it is an
            # apostrophe or a closing quote; after a space, an opening one
            if prev and (prev.isalnum() or prev in ".,!?;:)]}" or prev in _PH_CLOSERS):
                out.append("\u2019")
            elif prev in _OPENERS and starts:
                out.append("\u2018")
            else:
                out.append("\u2019")
        else:
            opening = (prev in _OPENERS or prev in _PH_CLOSERS) and starts
            out.append("\u201c" if opening else "\u201d")
    return "".join(out)
