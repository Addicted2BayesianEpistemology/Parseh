"""engine.shortcodes -- Hugo's built-in shortcodes, the ones a static page can
honour.

    {{< figure src="shots/x.png" alt="..." caption="..." >}}
    {{< details summary="More" open=true >}} Markdown {{< /details >}}
    {{< highlight python "linenos=table,hl_lines=2" >}} code {{< /highlight >}}
    {{< ref "other.md" >}}  {{< relref "other.md#a-heading" >}}
    {{< youtube id >}}  {{< vimeo id >}}
    {{< param "key" >}}
    {{< qr text="https://..." />}}
    {{< x user=".." id=".." >}}  {{< instagram id >}}  {{< gist user id >}}
    {{% comment %}} not shown {{% /comment %}}

Each is drawn the way Hugo's own template draws it, with the guide's classes.
Where Hugo would fetch something from a service at build time (a post on X,
an Instagram picture, a gist's code) a plain link to it is drawn instead:
the guide is built without the network and opened without it.  `qr` draws
a real QR code (engine/qr.py), as an SVG.

A shortcode the guide does not know is said at build time, with its file
and line, and drawn as a visible error box -- never silently dropped.
`{{</* name */>}}` is Hugo's way of writing a shortcode that is shown and
not run, and it works here too.
"""
import re

from . import qr
from .studio import htmlgen, mdparser

esc = htmlgen.esc

_ARG_RE = re.compile(r'\s*(?:([A-Za-z_][\w\-]*)\s*=\s*)?'
                     r'("(?:[^"\\]|\\.)*"|`[^`]*`|\'[^\']*\'|[^\s"\'`]+)')


def parse_args(s):
    """The arguments of a shortcode -> (positional list, named dict).  Hugo
    takes one kind or the other; both are read, whichever is written."""
    pos, named = [], {}
    s = (s or "").strip()
    if s.endswith("/"):
        s = s[:-1]          # {{< name ... />}}, the self-closing form
    for m in _ARG_RE.finditer(s):
        v = m.group(2)
        if v[:1] == '"':
            v = re.sub(r'\\(.)', r"\1", v[1:-1])
        elif v[:1] in "`'":
            v = v[1:-1]
        if m.group(1):
            named[m.group(1).lower()] = v
        else:
            pos.append(v)
    return pos, named


def _truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes", "on", "open")


def _arg(pos, named, key, index=None, default=""):
    if key in named:
        return named[key]
    if index is not None and index < len(pos):
        return pos[index]
    return default


def error_box(message):
    return '<div class="g-error" role="note">%s</div>' % message


# ------------------------------------------------------------------ the list
def _figure(r, pos, named, inner, line):
    src = named.get("src", "")
    if not src:
        r.ctx.warn("figure: no src", line=line)
        return error_box("A <code>figure</code> with no <code>src</code>.")
    url = r.ctx.media_url(src) or src
    img = '<img src="%s" alt="%s"%s%s%s>' % (
        esc(url), esc(named.get("alt", named.get("caption", ""))),
        ' width="%s"' % esc(named["width"]) if named.get("width") else "",
        ' height="%s"' % esc(named["height"]) if named.get("height") else "",
        ' loading="%s"' % esc(named["loading"]) if named.get("loading") else "")
    if named.get("link"):
        link = r.ctx.link_href(named["link"])
        extra = "".join(' %s="%s"' % (k, esc(named[k])) for k in ("target", "rel") if named.get(k))
        img = '<a href="%s"%s>%s</a>' % (esc(link), extra, img)
    cap = []
    if named.get("title"):
        cap.append("<h4>%s</h4>" % r._inline(named["title"]))
    if named.get("caption") or named.get("attr"):
        text = r._inline(named["caption"]) if named.get("caption") else ""
        if named.get("attr"):
            attr = r._inline(named["attr"])
            if named.get("attrlink"):
                attr = '<a href="%s">%s</a>' % (esc(r.ctx.link_href(named["attrlink"])), attr)
            text = (text + " " + attr).strip()
        cap.append("<p>%s</p>" % text)
    cls = "g-figure" + (" " + esc(named["class"]) if named.get("class") else "")
    return '<figure class="%s">%s%s</figure>' % (
        cls, img, "<figcaption>%s</figcaption>" % "".join(cap) if cap else "")


def _details(r, pos, named, inner, line):
    summary = named.get("summary") or (pos[0] if pos else "Details")
    body = r.render_fragment(inner or "", line + 1)
    cls = "g-details" + (" " + esc(named["class"]) if named.get("class") else "")
    extra = "".join(' %s="%s"' % (k, esc(named[k])) for k in ("name", "title") if named.get(k))
    return '<details class="%s"%s%s><summary>%s</summary>%s</details>' % (
        cls, " open" if _truthy(named.get("open", "")) else "", extra,
        r._inline(summary), body)


def _highlight(r, pos, named, inner, line):
    lang = _arg(pos, named, "lang", 0, "text")
    opts = _arg(pos, named, "options", 1, "")
    code = (inner or "").strip("\n")
    return r.code(code, lang, opts)


def _youtube(r, pos, named, inner, line):
    vid = _arg(pos, named, "id", 0)
    if not mdparser.youtube_id(vid):
        r.ctx.warn("youtube: not a video id: %r" % vid, line=line)
    attrs = mdparser.parse_image_attrs("start=%s end=%s" % (named.get("start", ""),
                                                            named.get("end", "")))
    b = {"type": "video", "caption": "", "url": vid, "vid": mdparser.youtube_id(vid),
         "valid": bool(mdparser.youtube_id(vid)), "width": 100, "align": "left",
         "offset": 0, "start": attrs["start"], "end": attrs["end"]}
    out = htmlgen._render_video(b, dict(r.hctx, in_card=True))
    if named.get("title"):
        # Hugo's title names the player for a screen reader; it is no caption
        out = out.replace('title="YouTube"', 'title="%s"' % esc(named["title"]), 1)
    return out


def _vimeo(r, pos, named, inner, line):
    vid = _arg(pos, named, "id", 0)
    if not re.fullmatch(r"\d+", vid or ""):
        r.ctx.warn("vimeo: not a video id: %r" % vid, line=line)
    return ('<div class="g-embed%s"><iframe src="https://player.vimeo.com/video/%s?dnt=1"'
            ' title="%s" allow="fullscreen; picture-in-picture" allowfullscreen'
            ' loading="lazy"></iframe></div>'
            % (" " + esc(named["class"]) if named.get("class") else "", esc(vid),
               esc(named.get("title", "Vimeo video"))))


def _link_card(url, text):
    return ('<p class="g-social"><a class="lnk" href="%s" target="_blank" '
            'rel="noopener noreferrer">%s</a></p>' % (esc(url), esc(text)))


def _x(r, pos, named, inner, line):
    user, pid = _arg(pos, named, "user", 0), _arg(pos, named, "id", 1)
    return _link_card("https://x.com/%s/status/%s" % (user, pid), "A post by @%s on X" % user)


def _instagram(r, pos, named, inner, line):
    pid = _arg(pos, named, "id", 0)
    return _link_card("https://www.instagram.com/p/%s/" % pid, "A post on Instagram")


def _gist(r, pos, named, inner, line):
    user, gid = _arg(pos, named, "user", 0), _arg(pos, named, "id", 1)
    fname = _arg(pos, named, "file", 2)
    url = "https://gist.github.com/%s/%s" % (user, gid)
    return _link_card(url + ("#file-" + re.sub(r"[^\w-]", "-", fname).lower() if fname else ""),
                      "A gist by %s%s" % (user, (": " + fname) if fname else ""))


def _qr(r, pos, named, inner, line):
    text = named.get("text") or (inner or "").strip() or (pos[0] if pos else "")
    if not text:
        r.ctx.warn("qr: nothing to encode", line=line)
        return error_box("A <code>qr</code> with no text.")
    try:
        svg = qr.svg(text, level=named.get("level", "medium"),
                     scale=int(named.get("scale", 4) or 4))
    except ValueError as e:
        r.ctx.warn("qr: %s" % e, line=line)
        return error_box("This text is too long for a QR code: %s" % esc(str(e)))
    alt = named.get("alt") or text
    link = ('<a href="%s">%s</a>' % (esc(text), esc(text))
            if re.match(r"https?://", text) else esc(text))
    cls = "g-qr" + (" " + esc(named["class"]) if named.get("class") else "")
    return ('<figure class="%s" role="img" aria-label="%s">%s<figcaption>%s</figcaption></figure>'
            % (cls, esc("QR code: " + alt), svg, link))


def _comment(r, pos, named, inner, line):
    return ""


BLOCK = {"figure": _figure, "details": _details, "highlight": _highlight,
         "youtube": _youtube, "vimeo": _vimeo, "x": _x, "twitter": _x,
         "instagram": _instagram, "gist": _gist, "qr": _qr, "comment": _comment}
# the ones whose answer is a piece of text, used where it is written: inside
# a link's address, inside a sentence
TEXT = {"ref", "relref", "param"}


def text_value(r, name, pos, named, line):
    if name in ("ref", "relref"):
        path = _arg(pos, named, "path", 0)
        return r.ctx.ref(path, line=line)
    key = _arg(pos, named, "name", 0)
    value = r.ctx.param(key)
    if value is None:
        r.ctx.warn("param: no %r in this page's front matter" % key, line=line)
        return ""
    return str(value)


def block(r, node):
    """A shortcode on lines of its own -> its HTML."""
    name, line = node["name"].lower(), node["line"]
    pos, named = parse_args(node["args"])
    if name in TEXT:
        return "<p>%s</p>" % esc(text_value(r, name, pos, named, line))
    fn = BLOCK.get(name)
    if fn is None:
        return unknown(r, node["source"], name, line)
    # a highlight's lines are code, shown as written, tabs and all; any
    # other shortcode's inner text is Markdown, read as the page is read
    inner = node.get("inner_raw") if name == "highlight" else node.get("inner")
    return fn(r, pos, named, inner, line)


def inline(r, name, args, inner, source):
    """A shortcode inside a line -> ("text", what it says) for ref, relref and
    param, ("html", its HTML) for the rest."""
    name_l = name.lower()
    line = r.ctx.line
    pos, named = parse_args(args)
    if name_l in TEXT:
        return "text", text_value(r, name_l, pos, named, line)
    fn = BLOCK.get(name_l)
    if fn is None:
        return "html", unknown(r, source, name, line)
    return "html", fn(r, pos, named, inner, line)


def unknown(r, source, name, line):
    r.ctx.warn("unknown shortcode {{< %s >}}: nothing is drawn for it" % name, line=line)
    return error_box("Unknown shortcode <code>%s</code>: the guide has none by that name, "
                     "so nothing is drawn here." % esc(source.strip()))
