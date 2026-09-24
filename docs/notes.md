# Notes — how one is shown, and how fast

A **note** is a markdown document in the seam between two lines of a book, or
between two captions of a video. It is written with the studio's editor and
kept in the content's own `markdown/` directory; the reader and the player
draw a small **mark** in the seam, and clicking it opens the note over the
page in a frame.

The promise the guide makes about a note is that it *is* a studio page: the
same renderer, the same marks, the same colours, the same typography. That
promise is what everything below is arranged around.

This file is about the three things decided with the owner on 2026-09-23
(`TO-DO.md` §0): a folded run of paragraphs must not swallow its notes, a note
must open fast, and **a note must travel with the book or the video it sits
in** when that is kept on a phone.

## A folded run shows the notes it is hiding

A run of paragraphs can be folded away (`lib/reading.py`, kept with the book):
the text is not drawn, a **fold bar** stands in its place, and reading and
narration walk past it.

The seams are drawn *inside* the paragraph they belong to, so folding a run
took its notes off the page with it — and nothing said so. A reader could
fold a chapter and never learn that six notes had gone with it.

So the bar carries them. Under its button it draws **a row of the marks of
every note inside the run**: the first three, and then `+N more`, which opens
the rest where it stands. The row goes when the run is opened, because every
one of those notes is standing in its own seam again by then (it is a CSS
rule, `.foldbar.open .fnotes`, not a second piece of state).

**Which notes those are is found by walking the page**, not by comparing
anchors a second time. Every mark carries the note it was made for
(`noteButton`, `b.noteRecord`); a bar asks which marks are inside the
paragraphs *it* hid, so what it shows is exactly what was hidden — no more,
and nothing that was never there. A note whose anchor names a seam the book
has not got is nobody's run's, and it stays adrift at the end of the book as
it always did.

It is repainted wherever the marks and the bars are: at the end of
`paintNotes` and at the end of `applyFold`, and it always walks the whole
document rather than the scope `applyFold` was given, because a run can begin
in one chapter and end in another and the chapter that arrives second must
fill a bar standing in the first.

Both are in `lib/tex2html.py` (`foldNoteRow`, `paintFoldNotes`).

## A note opens fast

### The bare note page

`GET <mount>/note/<id>` (`markdown/app/server.py`, `page_note`) is the note
and nothing else: the rendered document on the studio's sheet, no editor, no
scripts of the studio's. `templates/note.html`.

The document page — `<mount>/doc/<id>` — is what a mark used to open, and it
costs about 1.3 MB **every time**: `app.css`, `app.js`, `exform.js`,
`mode.js`, `keep.js`, `explain.js`, `activity.js`, the MathJax loader, all of
it answered `no-store` or `no-cache` because a page somebody may be editing
must never come back stale. A note is read a dozen times in a session and
written on almost never, so it pays that price a dozen times for an editor
nobody opened.

What the bare page carries instead:

* **one stylesheet**, `static/sheet.css` — the faces, the palette and the
  LaTeX-styled sheet, split out of `app.css` so that both pages are the same
  document in the same colours and neither can drift from the other;
* **the language tokens**, `static/langs.css`;
* **an inline head script** that reads the studio's own typography preference
  (theme, text size, column width, leading, justification) out of
  `localStorage` and applies it. Inline because it costs no request, and
  there because a note that opened white under a reader working in the dark
  would only *look* like the studio's page. It writes nothing;
* **an inline foot script**, two things long: Escape posts `close-note` up to
  the page that framed it, and *open in the studio* posts `open-note-full`
  instead of navigating the frame (a navigation inside a frame lands on the
  joint session history, so a note opened in full would cost a press of Back
  before the book underneath moved). Out of a frame the header link is an
  ordinary link and does the ordinary thing;
* **MathJax, only where the note has maths.** `class="math` in the render is
  the test.

Its header carries the note's title and **open in the studio**, which is the
whole document page — the editor, the glosses, the downloads.

### A note that holds an exercise never gets the bare page

An exercise with no script is a box that cannot be answered, checked or
copied, and showing one would look like a broken note. `page_note` counts the
exercises **off the render** (`htmlgen.render_document`'s `exercises`, which
is the number of boxes that were actually drawn — a malformed block is still
a box) and answers with a redirect to the document page. Nothing inert is
ever shown.

The reader and the player remember which ids redirected, so a second click on
such a note goes straight to the full page without the extra hop.

### The notes within a screen, read before they are wanted

The reader and the player watch every mark with an `IntersectionObserver`
(`rootMargin: 600px`), the same bargain the chapters already make, and fetch
the bare page of one that comes near. It is held as **text** and put into the
frame with `srcdoc`, rather than left to the browser's cache, because the
studio answers `no-cache` and a revalidation over a tunnel is the very wait
this removes.

Three rules:

* **capped** (12): a textbook has hundreds of notes and a reader walking it
  must not carry them all; the one held longest goes first;
* **never while a note is open**: the note being read is what the connection
  is for. Anything that came near meanwhile waits and goes when it closes;
* **the open one is forgotten when it closes**: the editor is reached through
  that very frame, so the copy in hand is the only one that can have gone
  stale.

### One address for the studio's own files

A note lives under its book's prefix (`/books/<slug>/notes/…`). Its *links* —
its edit page, its media, the deck it copies an exercise into — belong there.
Its **files** do not: one stylesheet, one script, one MathJax, the same bytes
whichever book asked for them. Written under each book's own prefix they were
a separate download, and a separate cache entry, per book.

So `render_template` gives templates two prefixes: `{{BASE}}`, this mount, and
`{{STUDIO}}`, the studio itself. The bare note page links the studio's.

And MathJax is now the one thing these routes cache. It is two megabytes of
checkout that change only when the checkout does, and it was being fetched
afresh on every open of a note with a formula; `serve_math_js` and its two
neighbours grant it a day, which is the exemption `serve.py` already grants
`/lib/mathjax/` for the rest of the toolbox. A MathJax file that is *not*
there still gets the ordinary 404, which is never kept.

### `static/sheet.css` and `static/app.css`

Two files to write in, one address to ask for. `sheet.css` is the sheet;
`app.css` is the chrome around it. `GET <mount>/static/app.css` answers with
**both, sheet first** (`serve_app_css`), rather than `app.css` naming the
other with an `@import` — so every page and every cache that ever asked for
that address goes on getting the whole sheet under the one name it already
knows: a deck page, a document kept on a phone, the guide's own examples.

Anything that reads `markdown/app/static/app.css` **off the disk** must now
read `sheet.css` beside it.

## A note kept on a phone

The owner, on the same day: *"the keep button in books and videos should also
keep the notes rendered in bare page way"*. Until then `lib/offline.py` never
walked a `markdown/` folder, so *Keep on this phone* kept a book's text and
its recordings and left its notes on the computer — and a note is exactly the
thing a reader wants on a train, being the one part of the page that is his
own writing.

Everything below is one answer, `GET <book>/__offline` and `GET
/youtube/v/<id>/__offline`, and the sheet `lib/keep.js` draws from it. The
keeping side of it is in [mobile.md](mobile.md#the-notes-come-with-the-book-or-the-video-2026-09-23-second-block);
what belongs here is what it means for a *note*.

### One tick, and what is behind it

The notes of a thing are a **group**: one row on the keep sheet — *its notes ·
34 · about 280 kB* — carrying every note's page, the pictures inside those
notes, and the seams' list. One row rather than thirty-four, because nobody
wants to tick notes one at a time; a row rather than nothing, because nobody
wants a third of a megabyte kept without being asked. The pictures go with
the notes and the **recordings do not**: they are a row of their own beside
the narrations, since a recording in a note is as heavy as any other.

*About*, and the word is in the answer. A note's page is the same wrapper
every time plus this note's own text, so the measure is the wrapper — read off
`templates/note.html` and `templates/doc.html`, so that editing either moves
the number — plus its `source.md` on the disk. Rendering every note to weigh
it would mean paying the cost of reading a book to answer a question about
keeping one.

### The marks are kept, and they are a door

A note is reached from its mark and from nowhere else, and the marks come from
`GET <mount>/api/marks`. Kept as a plain file it would be a list frozen at the
moment of keeping; kept as a **door** (`lib/sw.js` `isDoor`, which is every
address under an `api/`) the computer is asked first and the kept copy answers
only when it cannot be reached. So a note written at the desk this morning is
in the seam the moment the phone is home, with nothing kept again — and the
book's own version has moved as well, so the out-of-date bar offers the rest
of it in one tap.

`lib/tex2html.py` and `youtube/lib/player.js` both keep whatever marks they
were last given rather than emptying the seams when the fetch fails: they were
true when they were read, and a book whose notes vanish as the train enters a
tunnel is the failure this is all here to prevent. An empty list from a server
that *did* answer is the truth, and empties them.

### An exercise is answerable away from the desk

A note that holds an exercise is kept as its **document page**, the one the
bare address redirects to, because the bare page carries none of the studio's
scripts and an unanswerable box is the one thing this page refuses to show.
That is also why the studio's own files — `app.js`, `exform.js`, the sheet,
the thirteen faces, and MathJax where a note has a formula — are named at the
studio's canonical address from the document page too, as the bare note page
already named its two: they go in the **shared** cache and are paid once for
the phone, not once for every book on the shelf.

The faces are worth a line of their own. They are named only inside `url()`
calls in `sheet.css`, and a stylesheet's `url()` is not a link anything but a
browser can see — so nothing kept them, and a kept document rendered in
whatever face the phone happened to have. They are read off
`markdown/app/static/fonts/` rather than written into a list, because a face
added to the sheet is added to that directory and would otherwise be forgotten.

### Who looks, and why it is not `lib/`

Which notes there are, what each one renders to, and whether that render holds
an exercise or a formula are the studio's own knowledge (`store.list_docs`,
`htmlgen.render_document`) — and `lib/` must not import the studio, because a
book's reader, a bundle and the launcher all lean on `lib/` and none of them
has a studio to lean on. Teaching `lib/offline.py` the store's layout by hand
would be a second copy of somebody else's truth, waiting to drift. `serve.py`
stands on both sides of that line, so `serve.py` looks: `notes_to_keep` hands
over `[{id, updated, dir, exercises, maths}]` and `offline.notes_group` turns
it into addresses, sizes and stamps.

The exercise question is asked of the **render** and not of the markdown, for
the same reason `page_note` asks it there: only the render knows what a block
became, and a malformed exercise block is still an exercise box. Getting it
wrong would keep a bare page for a note the server will not serve bare.
