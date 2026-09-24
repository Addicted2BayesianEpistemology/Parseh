## [a0.3.0] - 2026-09-23
### Added
- Videos and Markdown for mobile
- Settings, from the hub, with Network as its first page: who may reach
  Parseh, the port, and a certificate of your own — no terminal, and a change
  takes effect at once
- A phone on the Wi-Fi is let in once with a pairing code shown on the computer
- Notes open at once, on the studio's sheet without the editor, and the reader
  fetches the ones near you before you ask
- A book kept on an Android phone comes by Android's own download: it goes
  on with the page closed, shows in the notification with its own Cancel,
  and the button says "— you can leave this page". The text comes first and
  the recordings after it, so the book opens as soon as its text is in. On
  the iPad and in Firefox, which have no such download, a book is kept as 
  later described.
- What is kept on this phone is checked file by file, against a checksum the
  computer sends: a download cut off is unticked and says so
- A kept deck brings its exercises, their pictures and their recordings, so
  cramming works with the computer away
- Delete a gloss: one button in the chunk sheet and in the player's ✎ form
  empties the whole gloss and keeps the text, the colour and the word line;
  undo delete puts it back while the page is open
- Gloss a stretch with an LLM, in books and in videos: pick the stretch, copy
  the prompt, paste the answer back. Only chunks nobody has glossed are
  filled, whole or not at all; a gloss already there is never changed, and
  Parseh decides that when you paste, not the LLM. Re-gloss (asked twice)
  and filling the empty boxes of chunks that have a gloss are two
  checkboxes; the second asks for every empty box, a vocabulary line left
  empty on purpose (a word already given) included
- HTML export of markdown and crammed decks

### Removed
- The "draft" flag of books and videos, and its tags and marks in the
  library, the reader, the player and on the phone. A leftover
  `"draft": true` in a book.json or video.json is ignored

## [a0.2.0] - 2026-09-22
### Added
- PWA mobile version
- Book and Exercises for mobile
- Cram mode shows which exercises were more difficult at the end of a session
