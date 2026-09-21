# clips/

The clip tray: the recordings cut out of a book's narration or a film on
this machine, or recorded from a YouTube video playing in its tab, and the
frames captured from a video, while a card is being made. Everything here
except this file is personal and is not committed.

    <name>          a recording (mp3, m4a, ... -- whatever ffmpeg writes best
                    here) or a picture (png, jpg)
    <name>.json     where it came from: language, label, text, the book or
                    video and the seconds it was cut at

A name is `<word>-<6 hex>.<ext>`, unique across the toolbox, so
`audio/<name>` or `images/<name>` pasted into a studio document, an exercise
deck's Add exercise (its "Paste markdown…"), or sent with an Anki card names
this one file. Each of them copies the file in from here when it first sees
the name, so emptying the tray breaks nothing already made: only a card
copied as markdown and not pasted yet still needs its clips.

The tray has a page of its own, reached from the hub (`/clips/`): every clip
plays or shows there, ✕ deletes one, and "Empty the tray" deletes them all.
A studio document's Recordings… deletes a recording of the tray with its ✕
too. The store itself is `lib/clips.py`; the server answers for it under
`/clips/`.
