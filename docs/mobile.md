# The mobile mode — the design

Parseh has two interfaces. The **browser** one is every page as it has always
been, with everything that makes and changes content on it. The **mobile** one
is a second set of pages made to be *read* on a phone: streamlined, a single
column, big targets for a finger, and **no editing controls at all**. It is for
looking at what is there — reading a book, watching a video, reading a note,
studying a deck — and never for writing it.

The mode is a choice, made with the **Browser | Mobile** switch in the hub's top
bar, and it holds across every page and every reload until it is switched back.
It is being built one interface at a time. Today the hub has its mobile layout
and nothing else does, so every other door still opens its browser page: **a page
without a mobile version always falls back to its browser version.**

## What it is not

**It is not the phone adjustments the pages already make.** Those follow the
width of the screen, in either mode, and nothing about the mobile mode changes
them. They stay exactly as they are:

* the bar that gets out of the way on a scroll under 560px (`bars()` in
  `lib/parseh.js`, `body.barhidden`), and the reader's and the studio's bars
  put away by hand (`body.chrome-off`);
* the layouts under 560px, 620px, 720px and 820px in `lib/parseh.css`, the
  reader, the player, the card kit, the timeline and the studio;
* a tap that opens a gloss on a screen that claims a hover it never delivers,
  and the studio's drag handles that are off on a coarse pointer.

A mobile page is free to use the same classes (the mobile hub's bar is a
`.parseh-bar`, so it hides on a phone scroll like every other one), but nothing
in the mobile mode restates or undoes them.

**It is not a lock.** Nothing is refused in the mobile mode. A browser page
reached by typing its address, or from a bookmark, opens and works as it always
does, editing and all. The mobile pages simply do not *show* the controls that
edit; the server never checks the mode before doing what it is asked.

## How the mode is stored

* **`localStorage` `parseh_mode`**: `browser` or `mobile`. Nothing stored means
  `browser`. This is the one that decides.
* **A cookie of the same name**, `parseh_mode=mobile|browser; Path=/;
  SameSite=Lax; Max-Age=31536000` — a year, for the whole site. It mirrors the
  stored value so that the server, and the pages that do not load
  `lib/parseh.js`, can read the mode too. It is not `Secure`, because `serve.py`
  can speak plain http (`--http`, or a Windows machine without OpenSSL). Every
  page that loads `parseh.js` rewrites it whenever it disagrees with
  `localStorage`, so the two never differ for longer than one page load. When
  `localStorage` holds nothing — blocked, or never written on this origin — the
  cookie answers.
* **`<html data-mode="browser|mobile">`**, set by `parseh.js` as soon as it is
  parsed. The script is in `<head>`, as it is for the theme, so a page's
  stylesheet has switched layouts before the first paint and never flashes the
  other one. Another tab follows a switch made in this one (the `storage`
  event), and so does a page brought back by the back button.

`Parseh.mode` is the API, in `lib/parseh.js`:

| | |
|---|---|
| `get()` | `'browser'` or `'mobile'` |
| `set(m)` | store `m` (anything else is ignored), write the cookie, apply it |
| `isMobile()` | `get() === 'mobile'` |
| `route(url)` | where a link to `url` leads in this mode (below) |
| `onChange(fn)` | `fn(mode)` after every change of the mode on this page; returns a function that takes `fn` off again |
| `apply()` | put the stored mode on the page again |
| `pages` | the registry of mobile versions (below) |
| `KEY` | `'parseh_mode'` |

The switch itself is any pair of buttons with `data-parseh-mode="browser"` and
`data-parseh-mode="mobile"`, wrapped in a `.parseh-mode` group: `parseh.js` wires
them wherever they are, and `serve.mode_switch()` writes them. The pressed half
is drawn from `<html data-mode>`, not from `aria-pressed` (which the script keeps
up to date for a screen reader), so it is right from the first paint.

A bar that carries the switch stays one row on a phone, as the hub's bar was
before it: under 560px the browser hub's bar drops *the hub* and the word after
the stop button's ⏻, and under 420px the name beside the home glyph, and draws
the switch a little tighter (`lib/parseh.css`); the mobile bar drops the name
beside its home glyph under 360px (`lib/mobile.css`). The words are hidden from
the eye only (each sits in a `.word` span), so a screen reader still reads them.

### Reading the mode where `parseh.js` is not loaded

The studio's and the exercises' pages (`markdown/app/templates/*`, `app.js`,
`decks.js`) do not load `parseh.js`. They need nothing today; a mobile version of
one of them reads the mode the same way `parseh.js` does, the stored value first
and the cookie when there is none:

```js
function parsehMode() {
  try {
    var m = localStorage.getItem('parseh_mode');
    if (m === 'browser' || m === 'mobile') return m;
  } catch (e) {}
  var c = /(?:^|;\s*)parseh_mode=(browser|mobile)(?:;|$)/.exec(document.cookie || '');
  return c ? c[1] : 'browser';
}
```

The server reads the cookie (`http.cookies.SimpleCookie(self.headers.get("Cookie",
""))`, then `.get("parseh_mode")`). It may use it to pick a default or to write a
page's mobile layout at the page's own address. It must never use it to redirect
a browser address somewhere else or to refuse a request.

## Links: the registry and the fallback

`MOBILE_PAGES`, in `lib/parseh.js` (`Parseh.mode.pages`), lists the pages that
have a mobile version:

```js
var MOBILE_PAGES = [
  // the hub is its own mobile version: the one page carries both layouts
  { match: /^\/(index\.html)?$/, to: '/' }
  // { match: /^\/books\/$/, to: '/m/books/' } -- as each one is written
];
```

`match` is a regular expression over the whole path (anchored, and not `g`);
`to` is handed to `String.replace`, so it may say `$1` for part of the match —
`{ match: /^\/youtube\/v\/([^/]+)\/$/, to: '/m/v/$1/' }` — or be a function. The
query and the fragment are carried over. `route(url)` answers the mobile address
when the mode is mobile and a row matches a same-origin `url`, and `url` itself
otherwise: **the browser page is always the fallback.**

On a **mobile page** — one whose `<body>` carries `data-mobile-page` — every link
followed in the mobile mode goes where `route()` says. The link's `href` is
rewritten in the capture phase, before the browser acts on the click, rather than
the click being cancelled and the page moved by hand: so a ctrl- or cmd-click
into a new tab, a middle click, a long press's *open in new tab* and a
`target=_blank` all get the mobile address too. The address the page was written
with is kept in `data-parseh-href` and put back when the mode goes back to
browser. Two kinds of link are never routed: a download (`download`), and a link
marked `data-no-route` — for a mobile page that deliberately offers its browser
version.

## Adding a mobile page

1. **Write it.** Either at an address of its own (`/m/books/`, say — served like
   any other page, and added to `serve.py`'s routes), or as a second layout of the
   same page, the way the hub is: its browser elements marked
   `data-layout="browser"`, its mobile ones `data-layout="mobile"`, and
   `lib/mobile.css` shows one or the other by `<html data-mode>`.
2. **Mark it and load the shared files.** `<body data-mobile-page>`, and in
   `<head>` `/lib/parseh.css`, `/lib/langs.css`, `/lib/mobile.css`, then
   `/lib/parseh.js`. A new shared file goes into `serve.py`'s `STATIC_FILES`, or
   it is a 404.
3. **Register it** in `MOBILE_PAGES`. From then on every link to its browser
   address, on every mobile page, lands on it in the mobile mode.
4. **Show nothing that edits.** What a reader or a learner does stays: read,
   play, look a word up, open a gloss, answer a due card. What makes or changes
   content does not appear: edit, add, delete, build, upload, download a bundle,
   sync, the clip tray, the dictionary setup, stop the server. When in doubt, it
   is not on the mobile page; the browser page still has it.
5. **Design for a phone first.** One column, `--m-col` wide on anything larger
   and centred there; every target at least 48px; colours only from
   `parseh.css`'s tokens, so light, dark and sepia all follow (check the three).
   Nothing only a swipe can reach, either: the mobile mode is also opened on a
   desktop, where a mouse cannot swipe a row sideways and a wheel over it
   scrolls the page — the hub's chip row wraps under
   `(hover:hover) and (pointer:fine)` for that reason.
6. **Every language.** Right-to-left Persian and Arabic, the Latin languages,
   Japanese and Chinese (vertical text where the browser page has it), Hindi in
   Devanagari: the registry's tokens (`langs.css`, `data-lang`) give each its
   face and direction, as on the browser pages.
7. **Test it where it is drawn.** `tests/mobile_mode.mjs` drives the hub in a
   headless Chromium at 390x844 as a touch phone and at 1280x800 with a mouse,
   and measures what is on the screen; a new page gets the same: that its
   layout is the one shown, that nothing on it edits, that its links route,
   that the switch back to browser restores the browser page.

## The pages

| Browser page | Mobile version |
|---|---|
| the hub, `/` | **done**: the same page, its mobile layout — the four doors (books, videos, the studio's notes, the exercises) with their counts, the language chips in one row that scrolls sideways and always shows the picked one (with a mouse, in rows that wrap), the guide |
| the book library, `/books/`, and a book's reader | to come: the shelf, and the reader as a reader only |
| the videos, `/youtube/`, a channel, and the player | to come: the index, and the player with its transcript and glosses |
| the studio's library, `/studio/`, and a document, `/studio/doc/<id>` | to come: the notes to read |
| the exercise decks, `/exercises/`, a deck, and studying it | to come: the decks and studying what is due |
| the guide, `/guide/` | to come, if it needs more than it has |

These stay browser pages only, with no mobile version planned, because what
they are for is making or administering something: adding a book or a video
(`/books/add/`, `/youtube/add/`), the studio's editor, new document and LLM
prompt pages, the Anki sync (`/anki/sync/`), the clip tray (`/clips/`) and the
dictionary setup (`/lookup/`). A link to one of them from a mobile page still
opens it — in its browser version.
