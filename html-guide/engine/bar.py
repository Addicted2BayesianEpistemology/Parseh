# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.bar -- the bar of the guide as it is PUBLISHED: the website's own.

The guide a person reads at https://parseh.io/guide is part of Parseh's site,
and says so: at the top of every page, the bar the site's own pages wear --
the Parseh logo and name (a link to the site's front page), Guide, Examples
and Downloads, and the flag -- with "Guide" marked as where one is.

ONLY THE LAYOUT `build.py --pages` ASSEMBLES HAS IT.  The committed
html-guide/site/ ships in every install and is read from the computer, often
with no network: it has none, and neither has a guide exported into somebody's
own project (build.py says when the bar is Parseh's to wear).  The switch is
`Site(bar_home=...)`, which site.py reads when it draws a page, and
`put_on_the_front_page()` for the hand-written html-guide/index.html, which
is copied, not compiled: no second set of pages.

THIS BLOCK IS THE TWIN OF THE SITE'S BAR, AND IS SHARED WITH IT.  The site
(the repository parseh-io/parseh-io.github.io: the `<header class="bar alone">`
of every page, and the `.bar` block of assets/site.css) draws the bar that
this one copies, to the eye: 56 px high and 44 under 520 px of width, where
the name goes; the accent with the text on it; the Persian letter in a circle
of the text's colour; the same three links, the flag.  The class names are
this block's own (`ps-`), the colours are the guide's tokens -- `--accent`
and `--accent-fg`, which are the site's `--accent` and `--on` -- with the
site's own as their fallback, so that in the guide's three themes the bar is
the guide's, and the website could paste HEAD_CSS and bar() as they are.
Edit the two together.

WHERE THEY DIFFER, ON PURPOSE:
  * the NAME is the site's too: TeX Gyre Chorus, the face the site sets it in,
    which travels with Parseh (lib/fonts/texgyrechorus-mediumitalic.otf, the
    GUST Font License like Pagella and Heros) and is copied into the PUBLISHED
    layout alone, beside the guide's other fonts (site.py, `_runtime`); the
    rule that names it is FONT_FACE below, written with the page's own
    relative address, and the guide fetches nothing from another folder of
    the domain.
  * the bar SCROLLS AWAY, the site's sticks: the guide has a header of its
    own that sticks, and on a phone nothing of Parseh's is to stay fixed over
    the text.
  * the flag is a button that does nothing here, as on the site ("more
    languages later").

WHAT IT FETCHES: nothing from another host.  The letter is drawn in Noto
Nastaliq Urdu, which the guide's stylesheet loads from the published site
itself (site/_parseh/fonts/), and the name in Chorus, from the same folder; the
flag is inline; it works with scripts off.  The
few lines of script only keep one number up to date, how much of the bar is
still in view, because three boxes of the guide's own chrome are sized to
the window and must not run under it.
"""

FRONT = "index.html"

# the faces the bar names that the guide's own stylesheet does not: copied into
# site/_parseh/fonts/ of the published layout, from lib/fonts/ (site.py)
FONT_FILES = ("texgyrechorus-mediumitalic.otf",)
# the site's own rule (assets/site.css), with the address of the file as the page
# that carries it reaches it: `%s` is the way to site/_parseh/fonts/ ("../_parseh/fonts/")
FONT_FACE = ("@font-face{font-family:'TeX Gyre Chorus';"
             "src:url(%stexgyrechorus-mediumitalic.otf) format('opentype');font-display:swap}\n")

# THE BAR'S RULES (the site's, with the guide's tokens).  The bar is above
# the guide's header; the guide's chrome measures itself from --g-top, the
# header's height.  What stands above the header (--ps-bar high, and still in
# view while the page is near its top) matters to three boxes only: the
# contents column on a wide window (its height is the window's, less the
# header and the part of the bar in view), the drawer that is the contents on
# a phone, and the dimming behind it -- ps-bar-seen, kept by the script.
HEAD_CSS = """\
:root{--ps-bar:56px}
.ps-bar{display:flex;align-items:center;gap:6px;height:var(--ps-bar);
  padding:0 max(14px,env(safe-area-inset-right)) 0 max(14px,env(safe-area-inset-left));
  background:var(--accent,#be3455);color:var(--accent-fg,var(--on,#fff))}
.ps-home{display:inline-flex;align-items:center;gap:10px;margin-right:auto;
  color:inherit;text-decoration:none}
.ps-glyph{font-family:'Noto Nastaliq Urdu',serif;font-size:15px;line-height:1;
  width:34px;height:34px;border-radius:50%;background:var(--accent-fg,#fff);color:var(--accent,#be3455);
  display:inline-flex;align-items:center;justify-content:center;flex:none}
/* a nastaliq line box is far taller than the letter: lift the ink to the middle */
.ps-glyph i{font-style:normal;display:block;transform:translateY(-.62em)}
.ps-name{font-family:'TeX Gyre Chorus','Apple Chancery',cursive;font-size:27px;line-height:1}
.ps-nav{display:flex;align-items:center;gap:2px;flex-wrap:nowrap;white-space:nowrap}
.ps-nav a{color:inherit;text-decoration:none;font:550 15px/1.5 var(--g-sans,system-ui,sans-serif);
  padding:8px 12px;border-radius:999px}
.ps-nav a:hover,.ps-nav a[aria-current]{background:rgba(127,127,127,.3);
  background:color-mix(in srgb,currentColor 16%,transparent)}
.ps-lang{width:34px;height:34px;margin:0 0 0 8px;padding:0;border-radius:50%;
  border:2px solid currentColor;background:none;overflow:hidden;cursor:default;flex:none}
.ps-lang svg{display:block;width:100%;height:100%}
.ps-bar a:focus-visible,.ps-bar button:focus-visible{outline:2px solid currentColor;outline-offset:2px}
/* the guide's own chrome, under the bar */
.g-layout{min-height:calc(100vh - var(--g-top) - var(--ps-bar))}
@media (min-width:901px){
  .g-side{height:calc(100vh - var(--g-top) - var(--ps-bar-seen,0px))}
}
@media (max-width:900px){
  .g-side,html[data-side=closed] .g-side{top:calc(var(--g-top) + var(--ps-bar-seen,0px))}
  html.g-drawer .g-backdrop{inset:calc(var(--g-top) + var(--ps-bar-seen,0px)) 0 0 0}
}
@media (max-width:520px){
  :root{--ps-bar:44px}
  .ps-bar{gap:2px;padding:0 max(10px,env(safe-area-inset-right)) 0 max(10px,env(safe-area-inset-left))}
  .ps-name{display:none}
  .ps-glyph{width:28px;height:28px;font-size:12.5px}
  .ps-nav{gap:0}
  .ps-nav a{padding:5px 8px;font-size:14px}
  .ps-lang{width:26px;height:26px;margin-left:4px;border-width:1.5px}
}
@media print{.ps-bar{display:none}}
"""

# THE BAR'S MARKUP.  `%(home)s` is the site's front page, `%(examples)s` and
# `%(downloads)s` its pages, `%(guide)s` the guide's own front page (a
# relative address, so that the bar leads to the guide it is on, wherever
# that is served), each already written for the page.
BAR = """\
<header class="ps-bar" data-parseh-bar>
  <a class="ps-home" href="%(home)s" aria-label="Parseh, the front page"><span class="ps-glyph" lang="fa" aria-hidden="true"><i>پ</i></span><span class="ps-name">Parseh</span></a>
  <nav class="ps-nav" aria-label="Parseh">
    <a href="%(guide)s" aria-current="true">Guide</a>
    <a href="%(examples)s">Examples</a>
    <a href="%(downloads)s">Downloads</a>
  </nav>
  <button class="ps-lang" type="button" aria-label="Language: English" title="English (more languages later)"><svg viewBox="0 0 60 30" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><clipPath id="ps-uk"><path d="M30,15h30v15zv15h-30zh-30v-15zv-15h30z"/></clipPath><path d="M0,0v30h60v-30z" fill="#012169"/><path d="M0,0 60,30M60,0 0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 60,30M60,0 0,30" clip-path="url(#ps-uk)" stroke="#c8102e" stroke-width="4"/><path d="M30,0v30M0,15h60" stroke="#fff" stroke-width="10"/><path d="M30,0v30M0,15h60" stroke="#c8102e" stroke-width="6"/></svg></button>
</header>
<script id="ps-bar-js">(function(){var b=document.querySelector(".ps-bar"),r=document.documentElement;if(!b)return;
function f(){r.style.setProperty("--ps-bar-seen",Math.max(0,Math.round(b.getBoundingClientRect().bottom))+"px")}
addEventListener("scroll",f,{passive:true});addEventListener("resize",f);f()})();</script>
"""


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def head_css(fonts):
    """What goes in <head>, after the guide's own stylesheet (the rules that
    meet the guide's are written to win by coming last).  FONTS is the way from
    the page to site/_parseh/fonts/, with its closing slash."""
    return '<style id="ps-bar-css">\n%s%s</style>\n' % (FONT_FACE % fonts, HEAD_CSS)


def bar(home, up):
    """The bar for a page whose front of the guide is UP ("", "../", "../../"):
    HOME is the site's front page (project.WEBSITE_URL), with a closing slash."""
    return BAR % {"home": esc(home), "examples": esc(home + "examples/"),
                  "downloads": esc(home + "downloads/"), "guide": esc(up + FRONT)}


def put_on_the_front_page(text, home):
    """The hand-written front page, with the bar on it: the rules before
    </head>, the bar before the guide's own header.  Refuses a page that is
    not shaped as expected (a front page that changed must be looked at).  The
    front page stands above site/, so its fonts are at site/_parseh/fonts/."""
    for needle in ("</head>", '<header class="g-top">'):
        if text.count(needle) != 1:
            raise ValueError("html-guide/index.html has %d of %r, expected one: the bar "
                             "cannot be placed (engine/bar.py)" % (text.count(needle), needle))
    return (text.replace("</head>", head_css("site/_parseh/fonts/") + "</head>")
                .replace('<header class="g-top">', bar(home, "") + '<header class="g-top">'))
