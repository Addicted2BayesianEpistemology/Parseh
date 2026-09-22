# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.cssscope -- the studio's stylesheet, confined to the guide's article.

A compiled page draws its text with the studio's own app.css: that is what
makes a box, a lemma, a table or an exercise look exactly as it does in the
studio.  But app.css is the whole studio's sheet -- its top bar, its buttons,
its `body` font, its links -- and loaded as it is it would restyle the
guide's own chrome.  So it is rewritten at build time, never by hand: every
selector is put under the article (`.pz`), and the few that name the page
itself are pointed at it too:

    :root, html, body       ->  .pz                (the tokens, the ground)
    body[data-theme=dark]   ->  html[data-sheet=dark] .pz
    body.some-state x       ->  body.some-state .pz x
    anything else x         ->  .pz x

The studio's themes live on body[data-theme] (paper, sepia, dark); the guide
keeps the toolbox's theme on <html data-theme>, and guide.js writes the
studio's name for it beside it as data-sheet -- which is what the rewritten
theme rules read.  @media and @supports are rewritten inside; @font-face and
@keyframes are left as they are (they name nothing on the page).

One thing the studio puts outside any article: the window a flashcard
opens in (app.js openCardZoom, a .modal-overlay appended to <body>).  The
scope is therefore `:is(.pz, .modal-overlay)`, and a rule written for the
overlay itself stays as it was -- no class of the guide's is called that.
"""
import re

SCOPE = ":is(.pz,.modal-overlay)"
THEME_NAMES = {"paper": "paper", "sepia": "sepia", "dark": "dark"}


def _split_selectors(s):
    parts, depth, cur, q = [], 0, [], None
    for c in s:
        if q:
            cur.append(c)
            if c == q:
                q = None
            continue
        if c in "\"'":
            q = c
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(c)
    parts.append("".join(cur).strip())
    return [p for p in parts if p]


_FIRST = re.compile(r"^((?:[A-Za-z][\w-]*|\*|:root)?(?:[.#][\w-]+|\[[^\]]*\]|::?[\w-]+(?:\([^)]*\))?)*)(.*)$", re.S)


def scope_selector(sel):
    """One selector -> the same selector, confined."""
    sel = sel.strip()
    if sel.startswith(".modal-overlay") or sel.startswith(".ex-zoom-overlay"):
        return sel
    m = _FIRST.match(sel)
    first, rest = (m.group(1), m.group(2)) if m else ("", sel)
    tag = re.match(r"^(html|body|:root)(?![\w-])", first)
    if tag:
        quals = first[len(tag.group(1)):]
        theme = re.fullmatch(r'\[data-theme=["\']?(\w+)["\']?\]', quals)
        if theme:
            return 'html[data-sheet="%s"] %s%s' % (theme.group(1), SCOPE, rest)
        if not quals:
            return (SCOPE + rest) if rest.strip() or tag.group(1) != "html" else ""
        return "%s %s%s" % (first, SCOPE, rest if rest.startswith(" ") or not rest else " " + rest)
    return "%s %s" % (SCOPE, sel)


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _blocks(css):
    """Top-level items of a stylesheet -> [(prelude, body or None)]: a rule
    or an at-rule with its braces' content, or a statement (`@import ...;`)."""
    out, i, n = [], 0, len(css)
    while i < n:
        while i < n and css[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        j = i
        q = None
        while j < n:
            c = css[j]
            if q:
                if c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c in "{;":
                break
            j += 1
        prelude = css[i:j].strip()
        if j >= n:
            break
        if css[j] == ";":
            out.append((prelude, None))
            i = j + 1
            continue
        depth, k = 1, j + 1
        q = None
        while k < n and depth:
            c = css[k]
            if q:
                if c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            k += 1
        out.append((prelude, css[j + 1:k - 1]))
        i = k
    return out


def scope(css):
    """A stylesheet -> the same, every rule confined to the guide's article."""
    out = []
    for prelude, body in _blocks(_strip_comments(css)):
        if body is None:
            out.append(prelude + ";")
            continue
        low = prelude.lower()
        if low.startswith(("@media", "@supports", "@container", "@layer")):
            out.append("%s{\n%s}" % (prelude, scope(body)))
        elif low.startswith("@"):
            out.append("%s{%s}" % (prelude, body.strip()))
        else:
            sels = [scope_selector(s) for s in _split_selectors(prelude)]
            sels = [s for s in sels if s]
            if sels:
                out.append("%s{%s}" % (",".join(sels), body.strip()))
    return "\n".join(out) + "\n"
