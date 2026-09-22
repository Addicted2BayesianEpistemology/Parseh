# The mobile mode — the design

Parseh has two interfaces. The **browser** one is every page as it has always
been, with everything that makes and changes content on it. The **mobile** one
is a second set of pages made to be *read* on a phone: streamlined, a single
column, big targets for a finger, and **no editing controls at all**. It is for
looking at what is there — reading a book, watching a video, reading a note,
studying a deck — and never for writing it.

The mode is a choice, made with the **Browser | Mobile** switch in the hub's top
bar (and in the bar of every mobile page), and it holds across every page and
every reload until it is switched back. It is being built one interface at a
time. Today the hub, the books (their shelf and every book's reader) and the
exercise decks have their mobile layouts; the videos and the studio's notes do
not yet, so their doors still open the browser pages: **a page without a mobile
version always falls back to its browser version.**

A phone is held **sideways** as often as upright — more, to read — so every
mobile layout is made for both: from 600px wide the columns widen and go two
to a row, the reader's controls take one line, and studying puts its buttons
in a column down the right edge (*A phone held sideways*, below). And the
mobile interface can be **installed as an app**, from the phone's browser: an
icon on the home screen that opens it on the whole screen, with no address bar
(*Parseh as an app*, below).

## What it is not

**It is not the phone adjustments the pages already make.** Those follow the
width of the screen, in either mode, and nothing about the mobile mode changes
them. They stay exactly as they are:

* the bar that gets out of the way on a scroll under 560px (`bars()` in
  `lib/parseh.js`, `body.barhidden`), and the reader's and the studio's bars
  put away by hand (`body.chrome-off`) — in the mobile mode the same `bars()`
  follows the scroll at every width, and only the mobile pages' own sheets
  answer it there (a phone held sideways is wider than 560px); a browser page
  opened in the mobile mode still hides its bar under 560px only;
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

A page that is **only** a mobile version, at an address of its own (`/m/books/`),
names the page it stands for in `<body data-browser-page="/books/">`: switched to
the browser mode — there, or in another tab — it goes to that page
(`location.replace`), since it has nothing of its own to show in that mode. Only
on a switch: opened in the browser mode (a link kept from a phone), it opens as it
is and says, in a line only that mode shows, where its browser page is. Nothing
goes the other way — a browser page may hold somebody's unsaved work.

### Reading the mode where `parseh.js` is not loaded

The studio's and the exercises' pages (`markdown/app/templates/*`, `app.js`,
`decks.js`) do not load `parseh.js`. The exercise decks' pages have a mobile
layout, so they read the mode the way `parseh.js` does, the stored value first
and the cookie when there is none — in their `<head>`, before anything is drawn
(`deckroutes.MODE_SCRIPT`, which every deck template takes as `{{MODE_SCRIPT}}`),
and `decks.js` keeps the switch from there on (`bindMode`: stored, mirrored in the
cookie, drawn, and followed when another tab changes it). The studio's own pages
need nothing yet. In JavaScript, the reading is:

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
  { match: /^\/(index\.html)?$/, to: '/' },
  // the book library is a static page: its mobile version is one of its own
  { match: /^\/books\/(index\.html)?$/, to: '/m/books/' },
  // a book's reader is its own mobile version (the layer, below)
  { match: /^(\/books\/(?:[^\/]+\/){1,2}reader\/)(index\.html)?$/, to: '$1' },
  // the exercise decks: each page carries both layouts
  { match: /^\/exercises\/(.*)$/, to: '/exercises/$1' }
];
```

`match` is a regular expression over the whole path (anchored, and not `g`);
`to` is handed to `String.replace`, so it may say `$1` for part of the match —
`{ match: /^\/youtube\/v\/([^/]+)\/$/, to: '/m/v/$1/' }` — or be a function. The
query and the fragment are carried over. `route(url)` answers the mobile address
when the mode is mobile and a row matches a same-origin `url`, and `url` itself
otherwise: **the browser page is always the fallback.** A page that is its own
mobile version is registered too, mapped onto itself: the registry is the list of
what has a mobile version, and says so of every page that has one.

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

1. **Write it.** In one of three ways, whichever the browser page allows:
   - at an address of its own, as the book shelf is (`/m/books/`, `lib/mobile.py`
     — served like any other page, added to `serve.py`'s routes, and naming its
     browser page in `data-browser-page`): the way for a page written as a file
     on disk, which a layout added to it would not reach until it is written
     again;
   - as a second layout of the same page, the way the hub and the exercise decks
     are: its browser elements marked `data-layout="browser"`, its mobile ones
     `data-layout="mobile"`, and the sheet (`lib/mobile.css`, or the studio's
     `static/mobile.css`) shows one or the other by `<html data-mode>`;
   - as a layer over a page BUILT for its content, the way a book's reader is: a
     script and a sheet in `lib/` that `parseh.js` loads into the page, so every
     page built before the mobile interface gets it without being built again.
     The layer lays the page's own controls out for a phone and hides what edits
     — it moves, copies and rewrites none of them — and refuses the gestures that
     would write.
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
7. **Test it where it is drawn.** `tests/mobile_mode.mjs` drives the hub, and
   `tests/mobile_pages.mjs` the book shelf, the readers, the decks and the app,
   in a headless Chromium as a touch phone held upright (390x844 and 360x740)
   and sideways (844x390) and with a mouse, and measures what is on the
   screen; a new page gets the same: that its
   layout is the one shown, that nothing on it edits, that its links route,
   that the switch back to browser restores the browser page.
   `tests/test_mobile_mode.py` and `tests/test_mobile_pages.py` read the markup
   and the sheets: every rule in `lib/mobile.css` hangs off a mobile class
   (`m-…`, `html.m-reader`) or `[data-layout=…]`, and every rule in the studio's
   `static/mobile.css` off `html[data-mode=mobile]`, so neither can reach a
   browser page.

## The pages

| Browser page | Mobile version |
|---|---|
| the hub, `/` | **done**: the same page, its mobile layout — the four doors (books, videos, the studio's notes, the exercises) with their counts, two to a row from 600px, the language chips in one row that scrolls sideways and always shows the picked one (with a mouse, in rows that wrap), the guide, and the door to installing the mobile interface as an app (not drawn inside the app) |
| the book library, `/books/` | **done**: the shelf, `/m/books/` — below |
| a book's reader | **done**: the same page, its mobile layer — below |
| the videos, `/youtube/`, a channel, and the player | to come: the index, and the player with its transcript and glosses |
| the studio's library, `/studio/`, and a document, `/studio/doc/<id>` | to come: the notes to read |
| the exercise decks, `/exercises/`, a deck, studying it and cramming it | **done**: each page, its mobile layout — below |
| the guide, `/guide/` | to come, if it needs more than it has |

### The book shelf, `/m/books/`

`lib/mobile.py` writes it on every request from the shelf itself — the browser
library is a static file (`lib/make_index.py`) written when a book is built or
put on the shelf, so a layout added to it would reach nobody's library until the
next build. The mobile bar (home, "Books", the switch, the theme); the chips, in
one row that scrolls sideways (wrapping for a mouse), filtering the books by
language; and each book as the library's card says it — its title and author in
the book's own face and direction, the Latin line, the blurb in three lines, the
chapters, whether it is narrated and how much is timed — the whole card a link to
its reader, at least 96px high, two to a row from 600px (a language's heading
the whole width). A book whose reader has never been built opens
nothing, and says it is built in the browser interface. A book read on this
phone says how far ("read on · 40%", and a line along the card's foot): the
reader keeps its place in the browser under `bk_pos:` and its address
(`lib/tex2html.py`, `save()`), and the shelf reads it, never writes it, and links
the address the place was kept under. Nothing that manages the shelf is on it:
no delete, no build, no bundle in or out, no backup, no stop.

### A book's reader: the mobile layer

A reader is built for its book, and `lib/parseh.js` — which every reader loads,
however old — puts `html.m-reader` on it and loads `lib/mobile.css` and
`lib/mobilereader.js` beside itself, the way it loads `lib/activity.js`. In the
mobile mode:

* **The header is laid out again, for a thumb.** Its rows stop being boxes
  (`display: contents`), so each control is an item of the header, placed by
  `order`. The first line is the way out and what a reader reaches for: the
  hub, the shelf, ☰ the contents, Aa the text size, and ⋯ — five 48px
  targets, which fit a 320px phone. A narrated book adds the recording: ↺ ▶ ↻
  and where it is (0:12 / 3:40). Upright, those four take a line of their own
  under the first (a `.m-rbreak` the layer adds ends the first line there);
  from 600px wide — a phone held sideways — all of it is one line.
  ⋯ opens the rest under it, a group to a line, each with a line saying what
  it is: *Passes* (the pass buttons, gloss, hover), *Listening* (continuous,
  loop and its gap, stop at a change, the speed — with the word the select
  does not say —, how far ↺ and ↻ move, listen and its follow and scroll,
  the seek), *Looking a word up* (the dictionary and its definitions, where a
  dictionary is installed), *This page* (the theme, putting the bars away, the
  switch). A group with nothing this book offers has no line. Open, the
  controls scroll inside the header, never taller than the screen.
* **↺ and ↻ move the recording** back and on by so many seconds: ten, until
  the *Listening* group's "skip by … seconds" field says otherwise — any whole
  number from 1 to 600, kept for every book in this browser as `bk_skip`,
  beside the reader's gap and rate (a number that is none keeps the one
  before). The reader plays by subparagraph, so the move takes the reading
  place with it: the subparagraph the recording lands in becomes the place —
  the mark, the place kept for next time, and where the playing stops — found
  as the reader's own *follow* finds it (`subAtTime`). In *listen* there is no
  reading place, and only the fold ahead is worked out again. All of that is
  the reader's own state, the top-level bindings of its script, which every
  classic script on the page shares; a reader built before one of them
  existed has the recording moved, and follows as it can. Paused, it stays
  paused. A book with no narration has neither button nor field.
* **The header gets out of the way at every width**: down, it goes; the
  smallest move up brings it back (parseh.js `bars()`, which the mobile mode
  runs whatever the width). It holds still while ⋯ is open, and through the
  scroll a skip makes to the new reading place, so ↺ and ↻ stay under the
  thumb for a second press (`<body data-bars-held>`).
* **Only what reads is there.** The sheet names the controls that stay; every
  other one — book info, the builds, the narration, folding, the timings, the
  download, the dictionary setup, stop, and whatever a later reader adds that
  nobody has named — is not on a phone at all. Neither are the page's other
  writing doors: the pencil over a chunk, the gloss cloud's *card* and *edit*,
  a seam's *+* for a note and the note viewer's *edit*, the naming of chapters
  and sections in the contents, and every sheet they open. A sheet left open
  in the browser mode is hidden, not closed, so going back finds it as it was.
* **The gestures that write are refused**, in the capture phase before the
  reader's own listeners hear them: a modifier-click on a word (a card) and E
  (the chunk's editor). A plain click, a tap and a shift-click (a copy) are the
  reader's as they always were.
* **Reading is untouched**: the passes, the glosses and the gloss cloud (a tap
  opens it in hover mode), the narration in step, the contents, the notes
  between two lines (the viewer opens the studio's page — its browser layout,
  until the studio has a mobile one), looking a word up, taking a character
  apart, the Aa panel, the reading place.

The page is marked `data-mobile-page`, so its links route: the shelf's ▤ goes to
`/m/books/`. Going back to the browser mode leaves the page exactly as the reader
built it: every rule is a mobile-mode rule, what the layer adds is
`data-layout="mobile"`, and nothing of the reader's own was moved.

### The exercise decks, `/exercises/`

Each of the four pages — the decks, a deck, studying it, cramming it — carries
both layouts (`markdown/app/templates/*`), its head says which to draw
(`deckroutes.MODE_SCRIPT`), `decks.js` keeps the switch and the theme, and
`markdown/app/static/mobile.css` lays the mobile one out in the studio's own
colour tokens, so paper, dark and sepia carry over. The mobile bar has the way
home, the way up (the decks, the deck), the switch and the theme.

* **The decks**: the chips in one row, filtering the decks; each deck with what
  is due in it and its two doors, *Study* and *Open*, the whole width (two decks
  to a row from 600px). No import, backup, restore, new deck or stop; no ⋯ on a
  deck (export, delete).
* **A deck**: its name, its language, what is in it and what is due; *Study now*
  and *Cram all* — every exercise of the deck, crammed, the scheduling as it
  was. Then **its exercises, to pick the ones to cram**: the browser layout's
  own list, filters (the text, the type, the state, the tag) and ways to pick
  (all, the ones shown, by tag — a dialog with the deck's tags —, none), each
  exercise with a box a finger can hit (drawn by the sheet: 24px inside 48),
  and a tap on the rest of it showing it solved, as a click does in the browser.
  While anything is picked a *Cram N exercises* button floats at the foot of the
  screen (`#m-cram`, the bulk bar's own *Cram* is at the list's top). That is
  a cram plan — a tag, the lapsed ones, the ones a word is in — and nothing in
  it edits: the bulk bar's copy, move, tags, *Set to new* and delete, and every
  exercise's own buttons, are the browser layout's. A deck with nothing due
  says cramming leaves the scheduling alone; an empty one says exercises are
  added in the browser interface, and draws no list. No rename, add, export,
  options or delete.
* **Studying**: the exercise has the screen — **no bar over it**; the deck's
  name and what is left are one line, with ‹ back to the deck at its start. What
  to do next is one box (`.dk-answerbar` in `study.html`, around the actions and
  the ratings; nothing in the browser layout) and the answering button is always
  in the same place in it: *Check* or *Show answer*, and, the answer back,
  **Next** where it was — rating the exercise as the answer says (Good when it
  was right or a card was turned, Again when it was wrong: its label says which,
  and when the exercise comes back) — so the exercises go by at a tap in one
  spot, with the four ratings beside it for any other. Held upright the box is a
  bar fixed at the foot of the screen (Skip and the answer; the ratings come in
  over them); held sideways, or on anything wider than it is tall from 600px, it
  is a column down the right edge — Skip at the top, the ratings two by two, the
  answer at the foot, where a thumb holding the phone rests — and the exercise
  has the whole height beside it. The answers, blocks, blanks and arrows inside
  an exercise are 48px. **A blank, and a matching exercise's place, are
  filled the other way round** (app.js, `bindExercises`, which asks `<html
  data-mode>` at each tap): a tap on the place opens a cloud — a copy of what
  the bank holds now, hung under the sentence or the list of rows (or right
  under the place, when their end is far below it) inside the exercise,
  which takes it along when it is redrawn — and a tap on a word puts it there
  by the same `moveItem` a drop uses, so what the place held goes back to the
  bank and checking is unchanged; a filled place's cloud can empty it. The
  bank stays, to show what is left, and is not picked up or dragged in this
  mode; an empty match's place says *tap to choose*. (An ordering exercise
  has no places: its blocks move by their arrows, in either layout.) No *Edit* (correcting an exercise is the browser
  layout's), no key hints, no stop.
* **Cramming**: the same box, the same place — *Skip* beside *Check* then
  *Next exercise*, *Show answer* then *Wrong* and *Correct* — in the mobile
  layout's words; and the end's two lists, what was answered wrong at least
  once and what was skipped, each entry 48px, opening the exercise solved.

On the decks and a deck the bar gets out of the way on the way down at every
width, as the toolbox's own mobile pages' does (`decks.js`, `bindBarFollow`,
from 560px up; `app.js` does it below).

The theme button is the toolbox's ◐, cycling `parseh_theme`; the studio's pages
follow that preference until a theme is picked in the studio's own panel, so
pressing ◐ lets such a pick go and the studio follows the toolbox again.

These stay browser pages only, with no mobile version planned, because what
they are for is making or administering something: adding a book or a video
(`/books/add/`, `/youtube/add/`), the studio's editor, new document and LLM
prompt pages, the Anki sync (`/anki/sync/`), the clip tray (`/clips/`) and the
dictionary setup (`/lookup/`). A link to one of them from a mobile page still
opens it — in its browser version.

## A phone held sideways

What a phone held sideways lacks is height — 320 to 430px of it, against 640 to
930px of width — so the mobile layouts spend width to save height. Two
thresholds do it, both in the sheets:

* **From 600px wide** (a phone sideways, a tablet, a desktop in the mobile
  mode): the column widens to 880px (`--m-col`), and what was one under
  another goes two to a row — the hub's doors, the shelf's books (a language's
  heading the whole width), the decks, a deck's *Study now* and *Cram all*,
  its filters and ways to pick. The reader's header is one line, the
  recording's controls in it.
* **Sideways and 600px wide** (`(orientation: landscape) and (min-width:
  600px)`): studying and cramming put their buttons in a column down the right
  edge instead of a bar at the foot. A desktop in the mobile mode is sideways
  too, and gets the column.
* **Sideways and short** (`(orientation: landscape) and (max-height: 500px)`):
  the lines under a page's name that only say what the page is go, and the
  hub's brand is smaller.

And every mobile page's bar goes on the way down at every width (above). The
phone adjustments of the browser pages are untouched: they still answer only
under 560px.

## Parseh as an app

Installed from a phone's browser, the mobile interface is an app: an icon on
the home screen, opening on the whole screen, with no address bar and no
browser around the page. A browser installs a site when the site describes
itself, has a service worker, and is served over https with a certificate the
phone trusts. Here:

* **The manifest**, `/manifest.webmanifest` (`mobile.manifest()`): the name, the
  icons, `start_url` `/?mode=mobile` — the app opens on the mobile hub, in the
  mobile mode; `lib/parseh.js` sets the mode from the address and gives the
  address back without it (`history.replaceState`) before anything is painted
  — the scope `/` (the whole toolbox is the app), `display` `fullscreen` (on
  Android the phone's own bars go too; where that is not offered, an app's
  window, `standalone`), any orientation.
* **The icons**, `lib/icons/`: پ in white in the toolbox's own Noto Nastaliq Urdu
  on the accent, `#be3455` — 192 and 512 in a circle (`any`), 512 filling the
  square with the letter inside the middle 80% (`maskable`: the launcher cuts
  its own shape), and Apple's 180. `lib/icons/make.mjs` drew them (headless
  Chromium, a canvas, the letter's ink box in the middle: a nastaliq line box
  hangs the letter low), and is kept to make them again; it is not served.
* **The tags**, `mobile.app_head()`: the manifest's link, Apple's icon, the
  bars' colour for a light and a dark phone, and Apple's names for "an app".
  The hub, the shelf and the install page carry them; the decks' templates do
  too (`{{APP_HEAD}}`, `deckroutes.APP_HEAD`, held equal to `app_head()` by
  `tests/test_mobile_pages.py`); `lib/parseh.js` adds them to a page that has
  none — every book's reader, built without them. No favicon: a page keeps its
  own.
* **The service worker**, `lib/sw.js`, served at `/sw.js` so that its scope is
  the whole site, and registered by `lib/parseh.js` and the decks' `decks.js`
  while the mode is mobile (on every page, which costs nothing). **It is not a
  cache of the toolbox**: Parseh is a server on somebody's own computer, and
  every page, book and recording comes from there, fresh, as without it. It
  answers page loads only (navigations, `GET`), and only when the network
  fails does it answer anything itself: the offline page, `/m/offline/`
  (`mobile.offline_page()`: "Parseh cannot be reached", and *Try again* — a
  page that stands alone, no stylesheet or script from anywhere), which it
  keeps when it is installed. A recording and its ranges, a picture, an upload,
  every call of an API goes by untouched. A new `VERSION` in it keeps the
  offline page again and lets the old copy go.
* **Installing**, `/m/install/` (`mobile.install_page()`), from the mobile hub's
  *As an app* door (not drawn inside the app: `display-mode`). It says, live,
  where this phone stands — in the app already; a browser that installs nothing;
  a certificate not trusted yet (the service worker is refused over it); ready —
  and gives the two steps: trusting the certificate, and installing (an
  *Install Parseh* button while Chrome offers one, and the menu's *Install app*,
  or Safari's *Add to Home Screen*). In the mobile mode `lib/parseh.js` keeps
  Chrome's offer (`beforeinstallprompt`) for the page's own
  `[data-parseh-install]` buttons, `Parseh.app.prompt()`, rather than a bar of
  the browser's over whatever is being read.
* **The certificate.** A browser tab goes on after one warning about a
  certificate nobody vouches for; an app does not. So `serve.py` (`make_cert`)
  makes two: **an authority of the machine's own** (`.tls/ca.pem`, its key
  `ca-key.pem`), made once and never again — what a phone is told to trust,
  once, from the install page (`/m/install/parseh-ca.crt`, the authority's
  certificate in DER as `application/x-x509-ca-cert`, which an iPhone offers to
  install as a profile and an Android phone saves for *Settings* → *Install a
  certificate* → *CA certificate*) — and **the server's**, signed by it for
  every name and address the machine has, for 825 days (the most an iPhone
  accepts), with the server-authentication use Apple requires, made again
  when it nears its end or when `serve.sh cert` asks: a phone that trusts the
  authority trusts each one, and nothing is installed again. **The authority
  can vouch for this machine and nothing else**: its name constraints permit
  only `localhost`, the machine's own name, `.local` and tailnet (`.ts.net`)
  names, and the private and Tailscale address ranges (127/8, 10/8,
  172.16/12, 192.168/16, 100.64/10) — so it is good for nothing on the
  internet, were its key ever copied off the machine; the server's certificate
  names nothing outside them. A certificate made before the authority (one
  self-signed, `O=Parseh`) is replaced by the pair once, at the next start —
  each browser warns once more, as it did about the old one; **one put in
  `.tls/` by hand** — Tailscale's (`tailscale cert`), Let's Encrypt's — is used
  as it is and never touched, and the install page then has no authority to
  hand over (a phone trusts those already). Over plain http there is no app,
  except from the computer itself at `localhost`.

`tests/test_mobile_pages.py` holds the manifest, the icons' sizes, the tags on
every page, the worker's rules, the install page and the certificate — the
authority and the server's, their constraints and lifetimes, renewal, the
migration, a hand-placed one left alone, and a real TLS server handing over the
authority to a client that trusts nothing else. `tests/mobile_pages.mjs` (its
part *app*) drives it: the app's address, Chromium's own verdict that the pages
are installable (`Page.getInstallabilityErrors`: nothing but the test's
incognito profile), the worker taking the pages over, the install page, and —
the server stopped — the page that says so.
