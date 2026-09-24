# The player as committed at 0519a1f

`player.html`, `player.js` and `style.css` here are `youtube/lib/`'s three
files exactly as commit `0519a1f` ("ability to deselect shown in explorer of
exercises", 2026-09-22) holds them:

    git show 0519a1f:youtube/lib/player.html > tests/fixtures/player_base/player.html
    git show 0519a1f:youtube/lib/player.js   > tests/fixtures/player_base/player.js
    git show 0519a1f:youtube/lib/style.css   > tests/fixtures/player_base/style.css

Parseh's own, under its licence (`GPL-3.0-or-later`, `LICENSE` at the top).

## What they are for

`tests/player_words.mjs` holds today's player to them: a chunk without a word
line must be drawn byte for byte as this player drew it, and its cloud said as
this player said it. That is a comparison with a player that STAYS PUT, which
is why it is a copy and not a git revision:

- the revision it used to name, `7a02e64` (the player before words), went in
  the squash of 2026-09-21, and a revision git cannot show stopped the suite
  before its first check;
- `HEAD`, which took its place, is the working tree itself the moment the work
  is committed -- both builds then ran the same code, every comparison
  compared a render with itself, and a regression committed while the suite
  was red or skipped became the base.

`PLAYER_BASE=<revision>` still takes the base from git instead
(`PLAYER_BASE=HEAD` shows what uncommitted work has changed).

## Changing them

Only by hand, in a commit that says why: a deliberate change to how an
unglossed or unworded chunk is drawn is a change to this base. Nothing
refreshes them, and no run writes them. The page is served as it is: its
`__YTFRANK__`, `__BASE__`, `__LANG__` and `__LANG_DIR__` are filled in by the
suite, and what it loads from `/lib/` is today's.
