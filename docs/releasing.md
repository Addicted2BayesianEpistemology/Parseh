# Releasing Parseh

*The checklist a release follows, from the first test to the published zip,
and what to do when a published release turns out to be bad. Written to be
followed blindly: somebody who remembers nothing about the last release must
be able to make the next one from this page alone. Decided with the owner on
2026-09-24 and 2026-09-25.*

**Releasing is a developer's act.** Every command below is one line, typed in
a terminal (Linux or macOS) at the top of a copy of Parseh's source code — a
`git clone` of the repository, called *the checkout* here. Nobody who uses
Parseh ever runs any of them. The steps that happen in a browser are said as
the pages say them.

**What a release is.** One commit, tagged with its version exactly as
`VERSION` spells it (no `v` in front), and one zip built from it, `parseh-<version>.zip`: the program without
its tests, its demo GIFs or the repository's own files, with
`.parseh-release.json` inside — the list of every file it ships with a
checksum for each, the version, the commit, the data formats this version
writes, and what `environment.yml` asked for. An install made from the zip
keeps that list, and **Settings → Updating Parseh** reads it to update in
place. GitHub builds the zip when the tag is pushed and leaves it as a
**draft**, which only the repository's owner can see; publishing it is a
separate act, by hand.

**What a rehearsal is.** Before the version's own tag, the whole road is
tried once under a rehearsal's tag, `<version>-rc1` (`a0.3.2-rc1`, say): the
same zip, named `parseh-<version>-rc1.zip`, whose list says `<version>-rc1`,
left by GitHub as a draft marked **pre-release**. It is looked at, then
deleted with its tag. Parseh counts `<version>-rc1` as coming before
`<version>` (and `-rc2` after `-rc1`), so an install made from a rehearsal
updates forward to the release. A rehearsal may be made before the release's
day is written; the version's own tag may not. `VERSION` never says `-rc`:
it is only ever a tag's name.

## Contents

- [What the machines check, and what they do not](#what-the-machines-check-and-what-they-do-not)
- [Before you start](#before-you-start)
- [The known-red baseline](#the-known-red-baseline)
- [The checklist](#the-checklist)
  1. [The suites](#1-the-suites)
  2. [The version](#2-the-version)
  3. [The guide, compiled](#3-the-guide-compiled)
  4. [The rehearsal's commit, and its build](#4-the-rehearsals-commit-and-its-build)
  5. [The rehearsal, on Parseh-test](#5-the-rehearsal-on-parseh-test)
  6. [The rehearsal, on GitHub](#6-the-rehearsal-on-github)
  7. [The day, and the release commit](#7-the-day-and-the-release-commit)
  8. [Tag and push: GitHub's draft](#8-tag-and-push-githubs-draft)
  9. [The draft is what you built](#9-the-draft-is-what-you-built)
  10. [The canary, Parseh-mine](#10-the-canary-parseh-mine)
  11. [Publish](#11-publish)
  12. [Afterwards](#12-afterwards)
- [When a draft is wrong](#when-a-draft-is-wrong)
- [When a published release is bad](#when-a-published-release-is-bad)
- [The first managed release](#the-first-managed-release)

## What the machines check, and what they do not

A step a machine enforces is a step nobody can forget. These are enforced:

| Who | Refuses |
|---|---|
| `lib/release.py check`, run by GitHub before it builds anything | a tag, `VERSION`, `CHANGELOG.md`'s newest heading and What's new's newest heading (`html-guide/markdown/reference/whats-new.md`) that do not all name the same version; a tag that is neither a version nor a rehearsal of one (`-rc1`, `-rc2` …: not `-rc0`, `-rc01`, `-RC1` or `-beta`); an empty newest section. For a **version's own tag**, also: a changelog heading that still says `unreleased`, a What's new heading that still says `not yet released`, and the two giving different days. A **rehearsal's tag** passes with both still undated. GitHub then makes no draft, and the run is red. |
| `lib/release.py guide`, run by GitHub before it builds anything | a compiled guide (`html-guide/site/`, which ships as committed) that is not what the guide's sources compile to — a page, a picture, the guide's engine or the studio's renderer changed after the last compile — or whose last compile had errors, or that is missing. GitHub then makes no draft. |
| `lib/release.py build`, locally and on GitHub | a release missing a folder Parseh writes into or a file it cannot do without; a `.bat` without CRLF line endings; a launcher that lost its executable bit; anything personal or any content (`.tls/`, a file in `config/`, `books/`, `dict/` and the rest other than a `.gitkeep` or a `README.md`); `tests/` or a GIF in `docs/`; a symbolic link. `--tag` refuses a tag that is not `VERSION`'s own or a rehearsal of it. It writes no zip then. |
| the release workflow (`.github/workflows/release.yml`) | building over a release that is already published: a published release is never replaced. An earlier **draft** of the same tag is replaced. It marks a rehearsal's draft **pre-release** and a version's draft not. It runs **no test suite**. |
| `tests/test_html_guide.py` | a guide page *What changed, version by version* whose `## ` headings are not the changelog's versions, in its order, with its days. |
| `tests/test_version.py` | a `VERSION` that is not one line holding a version (never a rehearsal's name); a version written by hand anywhere in the code; a `README.md` that names a version (it links to the newest release instead, so it never goes stale); a kind of file Parseh keeps without a data-format number in `lib/version.py`. |
| `tests/test_release.py` | an `export-ignore` list in `.gitattributes`, a `/dist/` rule in `.gitignore`, or a release workflow that drifted from what this page relies on (its steps and their order — check, guide, build, notes, pre-release or not, the draft — and no test suite in it) — and the builder's own refusals, each driven in a scratch repository. |

**Not enforced — this page is the only guard:** that the suites were run
and are no redder than the baseline (GitHub runs none: they need a browser
and the whole toolchain, which are on your computer); the rehearsals; the
canary; publishing; everything under *Afterwards*.

## Before you start

- **The checkout**, on `main`, up to date with GitHub (`git pull`), with
  the right to push to it.
- **Parseh's environment** on the terminal's path, so that `python3` is the
  environment's and `deno` is there. From the checkout:

  ```bash
  export PATH="$(dirname "$(python3 lib/runtime.py python)"):$PATH" PARSEH_PYTHON="$(python3 lib/runtime.py python)"
  ```

- **A Chromium** for the browser suites, named by `CHROME_BIN`. The one
  Playwright downloaded does:

  ```bash
  export CHROME_BIN="$(ls -d ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome | tail -1)"
  ```

  (Any Chrome or Chromium the system has does as well:
  `export CHROME_BIN=/usr/bin/chromium`, say.)
- **A temporary folder with room.** The browser suites write big
  temporary files — a 200 MB download the phone is made to keep, a
  browser profile per suite — into `TMPDIR`. Where `/tmp` is a memory disk
  (a *tmpfs*) that is filling up, they fail in ways that look like faults
  of Parseh: `tests/mobile_pages.mjs`'s background step *j* failed every
  time with `/tmp` 79% full, and passed every time on the main disk. Point
  it at the main disk:

  ```bash
  mkdir -p ~/.cache/parseh-tests-tmp && export TMPDIR=~/.cache/parseh-tests-tmp
  ```

- **Two installs of Parseh besides the checkout**, each made from a release's
  zip, never a git checkout. This page calls them by the names the owner
  keeps them under, as folders beside the checkout:
  - **Parseh-test** — where the update is **rehearsed** before anything is
    published: it runs the previous release, holds things to lose, and is
    updated with the zip you built. It answers on its own port, **7655**,
    so it can run beside the other. Nothing in it matters; it is there to be
    broken.
  - **Parseh-mine** — the Parseh actually used, with the real books, decks
    and dictionaries. It is **never updated by hand and never from a file you
    built**: only from the zip GitHub built, through **Settings → Updating
    Parseh**, exactly as every other person's is. It is the canary for the
    public road: what goes wrong there would have gone wrong for everybody.
- **No phone, no tablet.** Nothing here needs one. The promise a phone
  depends on (the app takes the new version, says so in a line, and keeps
  everything it kept) is held by `tests/mobile_pages.mjs`, whose `update`
  part runs in step 1.
- **A few hours.** The browser suites alone take about an hour and a half.

## The known-red baseline

Some suites are red before any release work starts. They must be known
**first**, so that a red suite in step 1 can be told apart: one on this list
is old breakage, anything else is new, and new breakage stops the release.

Measured on 2026-09-25, on the finished a0.3.2 tree before its commit, one
suite at a time, with `TMPDIR` on the main disk:

| Suite | State | How it fails |
|---|---|---|
| unit — `python3 -m unittest discover -s tests -p "test_*.py"` | green | `Ran 1739 tests … OK (skipped=12)` |
| `python3 tests/smoke.py` | green | `1838 passed, 0 failed, 21 skipped` |
| `tests/decomposition.mjs` | **red** | `TimeoutError: locator.click: Timeout 7000ms exceeded` waiting for `.test-extra [data-character="想"]`: the mode bar's *Choose a kanji in the text.* (with `#novid` and `#captimes`) covers it — `tests/decomposition.mjs:119` |
| `tests/exercises.mjs` | **red** | `page.evaluate: Error: a line of chunks points its arrows along the line` — `tests/exercises.mjs:91`. A second red hides behind it: the mocked editor page never shows `.ex-edit` (a 30 s timeout). Mending the first will not turn it green. |
| `tests/studio_narrow.mjs` | **red** | `FAIL: from 280 to 1440 px the editor never scrolls sideways …`: at 730 and 740 px the page is 741 px wide and `ins-br` is off screen; its parts b and c never run |
| the other 39 `tests/*.mjs` | green | `tests/activity.mjs` among them only on a second run, alone: see *Flaky* below |

The three reds are old: they failed the same way on a0.3.0, before this
version's work began (measured again on 2026-09-24).

**Flaky, not broken.** These have failed now and then and passed when the
suite was run again alone. They depend on timing — a browser that is slow
to start, a download caught halfway, a toast waited for twenty seconds —
and on the machine being otherwise quiet. Rerun the suite once, **alone**,
before calling any of them new breakage; a step that fails again alone is
breakage:

- `tests/mobile_pages.mjs`, its background part: step *i2* (*a Save the
  browser refuses frees nothing*: the *REFUSED* toast within 20 s), step
  *j* (*the computer killed with … bytes come … got -1 want 200000000*:
  almost always a `TMPDIR` without room, see [Before you
  start](#before-you-start)), and *the rec download could not be caught
  halfway: []*;
- `tests/reach.mjs`, its `slow` part: *a write on a slow computer was
  refused as away: {"failed":"Failed to fetch"…}*;
- `tests/activity.mjs`, at 1280×800: *the hub's pill steps aside while
  the panel is in sight* (the hub is a tab behind another, and the page
  learns that its panel is in sight a moment after the check looks);
- `tests/studio_audio.mjs`: *the pasted clip plays*;
- `tests/studio_starter_media.mjs`: *timed out: the editor draws the new
  picture*;
- any suite that stops with *Target page, context or browser has been
  closed*: Chromium itself crashed (`coredumpctl list chrome` shows it).

**Taking it again.** When this table is older than the last release, or you
do not trust it, measure it again before changing anything: on the last
release's own commit, so that nothing of the new work is in it. Put that
commit beside the checkout, run everything there as step 1 says, and remove
it afterwards:

```bash
git worktree add ../parseh-baseline <last release's tag>
```

```bash
git worktree remove --force ../parseh-baseline
```

Then write the new table here, with its date, and commit it with the
release.

## The checklist

Replace `<version>` everywhere with the version being released, as `VERSION`
spells it (`cat VERSION`), and `<previous>` with the last published release.
`<version>-rc1` is the first rehearsal; a second one, after a fault, is
`<version>-rc2`, and so on — a rehearsal's name is never used twice.

### 1. The suites

Run every suite on the tree you mean to release, **one at a time** — two at
once in one checkout break each other — and compare with the baseline.
`TMPDIR` must be set as [Before you start](#before-you-start) says.

1. The unit tests, then the library page they rewrite put back:

   ```bash
   python3 -m unittest discover -s tests -p "test_*.py"; python3 lib/make_index.py
   ```

   They fail by themselves if they changed anything in `config/`.
2. The smoke test:

   ```bash
   python3 tests/smoke.py
   ```

3. Every browser suite, one after another, each log kept (about an hour
   and a half):

   ```bash
   mkdir -p ../parseh-suites && : > ../parseh-suites/results.txt && for t in tests/*.mjs; do n=$(basename "$t" .mjs); NO_COLOR=1 timeout 900 deno run --allow-all "$t" > "../parseh-suites/$n.log" 2>&1; echo "$n $?" | tee -a ../parseh-suites/results.txt; done
   ```

   Then the red ones, each with the end of its log:

   ```bash
   for n in $(grep -v ' 0$' ../parseh-suites/results.txt | cut -d' ' -f1); do echo "== $n"; tail -8 "../parseh-suites/$n.log"; done
   ```

4. Every red suite must be in the baseline, failing the same way. A flaky
   step: rerun that suite alone (`deno run --allow-all tests/<name>.mjs`).
   Anything else is new breakage: **stop, mend it, and begin again at 1.**
5. Remove `../parseh-suites` when done.

### 2. The version

`VERSION` names the version being made from the day its work begins
(step 12 opens the next one), so it should already be right. Three files,
and only these, say the version, and until step 7 two of them still say it
is not released:

1. **`VERSION`** — one line, the version: check it with `cat VERSION`.
2. **`CHANGELOG.md`** — its newest heading, `## [<version>] - unreleased`.
   Read the section under it once more: it becomes the release's notes,
   word for word, and it is written for the people who use Parseh — what
   they will see, not how it was built. KEEP IT SHORT (the owner,
   2026-09-25): one line per group of work, the length of a commit's
   title, about ten lines for a version (more only for a big one), no
   details — those belong in What's new. A thing changed again before the
   release is said ONCE, as it now is, never as the first try and then its
   correction.
3. **`html-guide/markdown/reference/whats-new.md`** — its newest heading,
   `## <version> — not yet released`. Its sections say the same news as the
   changelog, for a reader, with links into the guide.

Then hold the three together — the tests must end `OK`, and `check` must
say `Agreed: <version>-rc1 rehearses <version> …`:

```bash
python3 -m unittest tests/test_version.py tests/test_html_guide.py; python3 lib/release.py check <version>-rc1
```

`check` here reads the working tree; GitHub runs the same check on the
tagged commit and makes nothing while they disagree.

### 3. The guide, compiled

The compiled guide, `html-guide/site/`, ships in the zip and is what GitHub
Pages publishes, so it is committed with the Markdown it comes from:

```bash
python3 html-guide/build.py
```

It must end `0 warnings, 0 errors`. When it names files *kept from the site
that was there*, look at each: one this computer cannot make (a font, a PDF)
is rightly kept, but a picture no page shows any more is a leftover — delete
it from `html-guide/site/`. Then ask the question GitHub will ask; it must
say `In step`:

```bash
python3 lib/release.py guide
```

Compile again after **any** later change to a guide page, a picture in it,
the guide's engine (`html-guide/engine/`) or the studio's renderer: each of
them puts the compiled guide out of step, and GitHub refuses the tag.

### 4. The rehearsal's commit, and its build

A release is built from a commit, never from the working tree.

1. Commit everything the release is — the changes, `VERSION`,
   `CHANGELOG.md`, `whats-new.md`, `html-guide/site/` — and nothing else.
   `git status --short` must then print nothing that belongs in the
   release. **Do not push.**
2. Build the rehearsal, exactly as GitHub will:

   ```bash
   python3 lib/release.py build --tag <version>-rc1
   ```

   It writes `dist/parseh-<version>-rc1.zip`, its `.sha256` and its list of
   files, `dist/parseh-<version>-rc1.manifest.json`, and says how many
   files, how big, from which commit, and *A rehearsal of <version>*. Under
   **NOT IN THIS BUILD** it names every file changed or new and not
   committed: each one must be something you meant to leave out. When it
   refuses, it says why; mend that, commit, and build again.
3. What GitHub will see is the commit, not your working tree (a stray file
   under `html-guide/markdown/` that is neither committed nor ignored
   counts on your computer and not there), so ask again of the commit —
   both must agree:

   ```bash
   python3 lib/release.py check <version>-rc1 --ref HEAD; python3 lib/release.py guide --ref HEAD
   ```

A fault found in steps 5 and 6 costs nothing: mend it, commit, and rehearse
again from step 3 under the next name, `<version>-rc2`.

### 5. The rehearsal, on Parseh-test

Your own steps, by hand, in the browser, at `https://localhost:7655/` —
never scripted. The point is to go through what somebody updating will go
through, and to prove that what is theirs survives it.

1. **Parseh-test runs `<previous>`, as released.** The hub's foot says
   which version it is. If it is anything else, put `<previous>` back:
   download `parseh-<previous>.zip` from its page on
   [GitHub's releases](https://github.com/Addicted2BayesianEpistemology/Parseh/releases),
   then **Settings → Updating Parseh → A zip of your own**, choose it, and
   press the button (**Go back to…** or **Install … again**).
2. **It has something to lose**, and something new since last time:
   - a book **with its narration** — from Parseh-mine, its reader's download
     *all of it*, then **Bring a book back** on Parseh-test's books;
   - a video, the same way (**⤓** in the player, **Bring a video back**);
   - an exercise deck **with answers in its schedule** — answer two or three
     exercises now, so that some are new;
   - a dictionary — **Settings → Reading help**, the Persian dictionary is
     21 MB;
   - a changed setting — the theme, and the port (7655) on
     **Settings → Network**.
3. **Fingerprint what is yours**, in Parseh-test's folder (the readers, the
   library page and the phone's checksums are left out: an update rebuilds
   the first two and the server rewrites the others as it pleases):

   ```bash
   find books youtube/videos youtube/anki markdown/library exercises clips dict corpus mt components config .tls -type f -not -path '*/reader/*' -not -name index.html -not -name .reader-key -not -name digests.json -not -name wheres.json -not -name updates.json -print0 2>/dev/null | sort -z | xargs -0 sha256sum > ../parseh-test-before.txt
   ```

4. **Update to the rehearsal.** **Settings → Updating Parseh → A zip of
   your own**, choose `dist/parseh-<version>-rc1.zip` from the checkout.
   Before pressing anything, read **Ready to install**:
   - it says **↑ newer**, `<previous>` → `<version>-rc1`;
   - *Changed by hand since they were installed* lists nothing — the guide's
     compiled pages are listed apart, and are expected;
   - the environment line says what it will add, if `environment.yml`
     changed, and nothing otherwise;
   - no *What may not survive going back* (that is only for going back).

   Press **Update to <version>-rc1**, then **Yes**. The page shows each
   step and comes back by itself.
5. **Check what survived.** **The last update** stands at the top and says
   what was written and deleted. **Settings → Updating Parseh** says
   `<version>-rc1`; the hub's foot says `<version>` (it reads `VERSION`,
   which never says `-rc`). Then:
   - the fingerprint again, and compare — **no line may differ**:

     ```bash
     find books youtube/videos youtube/anki markdown/library exercises clips dict corpus mt components config .tls -type f -not -path '*/reader/*' -not -name index.html -not -name .reader-key -not -name digests.json -not -name wheres.json -not -name updates.json -print0 2>/dev/null | sort -z | xargs -0 sha256sum > ../parseh-test-after.txt; diff ../parseh-test-before.txt ../parseh-test-after.txt && echo "all yours, untouched"
     ```

   - the book opens and its narration plays in step;
   - the deck opens, and the exercises you answered are not *new* any
     more;
   - a word looked up in the book answers from the dictionary;
   - the theme is the one you set, and **Settings → Network** still says
     port 7655 and lists every device you let in;
   - the browser did not warn about the certificate again.
6. **Go back.** Take the fingerprint again first, into
   `../parseh-test-before.txt` as in 5.3 — opening the book moved its
   reading place in `config/prefs.json`. Then choose
   `parseh-<previous>.zip` the same way: the page says
   **↓ older — going back**, and the button **Go back to <previous>**. If
   this version raised a data format, it also says *What may not survive
   going back*, names it, and keeps the button off until you tick *I
   understand*: that is expected exactly when this version's changelog says
   it changed how something is stored, and a fault otherwise. Go back, and
   compare the fingerprint as in 5.5, before opening anything: no line may
   differ.
7. **Forward again, then the same version twice.** Choose
   `dist/parseh-<version>-rc1.zip` (↑ newer), update, and compare the
   fingerprint; then choose it once more: the page says **= the same
   version** and **Install <version>-rc1 again**, which is accepted, not
   refused as up to date. Install it, and compare a last time.

Parseh-test is left on `<version>-rc1`: the release itself will be ↑ newer
to it.

### 6. The rehearsal, on GitHub

The whole road GitHub takes — check, guide, build, notes, the draft — tried
once before it counts. Pushing a tag shows nobody anything but the tag and
its commit.

1. Tag the rehearsal's commit and push **the tag alone** — not `main`,
   which would publish the guide on GitHub Pages with its undated page:

   ```bash
   git tag -a <version>-rc1 -m "Parseh <version>, rehearsal 1"
   ```

   ```bash
   git push origin <version>-rc1
   ```

2. On GitHub, **Actions → release**: the run for `<version>-rc1` must end
   green (a few minutes). A red run says in its failing step why, and made
   no draft: see [When a draft is wrong](#when-a-draft-is-wrong).
3. On GitHub, **Releases**: at the top, **Parseh <version>-rc1**, marked
   **Draft** and **Pre-release** — visible to you, signed in, and to nobody
   else. Its assets are `parseh-<version>-rc1.zip` and its `.sha256` (and
   GitHub's own *Source code* archives, which are not the release). Its
   notes are the changelog's `<version>` section.
4. Download both assets in the browser, then — this must print `OK`, then
   say **They agree**:

   ```bash
   cd ~/Downloads && sha256sum -c parseh-<version>-rc1.zip.sha256; cd -
   ```

   ```bash
   python3 lib/release.py compare dist/parseh-<version>-rc1.zip ~/Downloads/parseh-<version>-rc1.zip
   ```

5. **Delete the rehearsal**, draft and tag. On the draft's page,
   **Delete** (the bin), and confirm. Then the tag, on GitHub and here:

   ```bash
   git push --delete origin <version>-rc1; git tag -d <version>-rc1
   ```

   Delete the two downloads as well.

### 7. The day, and the release commit

1. **Date both headings, the same day** — the day you will publish:
   - `CHANGELOG.md`: `## [<version>] - unreleased` becomes
     `## [<version>] - 2026-09-25` (year, month, day);
   - `whats-new.md`: `## <version> — not yet released` becomes
     `## <version> — 25 September 2026` (the way the guide writes a day, no
     leading zero).
2. **Compile the guide again** — dating What's new put it out of step:

   ```bash
   python3 html-guide/build.py
   ```

3. Hold them together, commit, and ask of the commit what GitHub will ask —
   the tests end `OK`, `check` says `Agreed: … released on the same day`,
   and `guide` says `In step`:

   ```bash
   python3 -m unittest tests/test_version.py tests/test_html_guide.py
   ```

   ```bash
   git commit -am "<version>: the day it is released" && python3 lib/release.py check <version> --ref HEAD && python3 lib/release.py guide --ref HEAD
   ```

   `check` names each heading it refuses, with its file and line, and says
   how the other day is spelt; mend it, compile, and commit again.
4. **Build the release** as GitHub will, for step 9's comparison:

   ```bash
   python3 lib/release.py build
   ```

   Then compare it with the rehearsal, which proves that nothing but the
   day changed since it was rehearsed:

   ```bash
   python3 lib/release.py compare dist/parseh-<version>-rc1.zip dist/parseh-<version>.zip
   ```

   It says **They DISAGREE** — on the version, the commit, and these five
   files only: `CHANGELOG.md`, `html-guide/markdown/reference/whats-new.md`,
   and the three the compile rewrote for it, `html-guide/site/build.json`,
   `html-guide/site/reference/whats-new.html` and
   `html-guide/site/search-index.js`. Any other file named is a change that
   was never rehearsed: rehearse again (step 3, `-rc2`).

If the release slips to another day, change both dates, compile, and commit
before you tag.

### 8. Tag and push: GitHub's draft

1. Tag the release commit and push it, with `main`:

   ```bash
   git tag -a <version> -m "Parseh <version>"
   ```

   ```bash
   git push origin main <version>
   ```

   Pushing `main` also publishes the compiled guide on GitHub Pages, dated
   pages and all, within minutes; publish the draft the same day.
2. On GitHub, **Actions → release**: the run for `<version>` must end
   green (a few minutes). A red run says in its failing step why —
   usually `check`, naming what disagrees — and made no draft: see
   [When a draft is wrong](#when-a-draft-is-wrong).
3. On GitHub, **Releases**: at the top, **Parseh <version>**, marked
   **Draft** and **not** pre-release — visible to you, signed in, and to
   nobody else. Its assets are `parseh-<version>.zip` and
   `parseh-<version>.zip.sha256` (and GitHub's own *Source code* archives,
   which are not the release and never get a checksum). Its notes are the
   changelog's section.

### 9. The draft is what you built

1. On the draft's page, download **`parseh-<version>.zip`** and
   **`parseh-<version>.zip.sha256`** in the browser (you are signed in, so
   the draft's assets download like any file).
2. The zip is whole — this must print `OK`:

   ```bash
   cd ~/Downloads && sha256sum -c parseh-<version>.zip.sha256; cd -
   ```

3. It is what you built:

   ```bash
   python3 lib/release.py compare dist/parseh-<version>.zip ~/Downloads/parseh-<version>.zip
   ```

   It must say **They agree** — the same version, the same commit, every
   file with the same checksum and mode. It says as well whether the two
   zips are the same file byte for byte; when they are not, the files in
   them still are, which is what counts (two computers' compressors may
   pack the same bytes differently). **They DISAGREE** means the draft is
   not what you built: [When a draft is wrong](#when-a-draft-is-wrong).

### 10. The canary, Parseh-mine

Your own step, by hand, in the browser: the update everybody will make, on
the Parseh you use, from the zip GitHub built — the last proof before
anyone else is exposed.

1. On Parseh-mine, **Settings → Updating Parseh → A zip of your own**, and
   choose the draft's zip you downloaded in step 9 — **not** the one in
   `dist/`. (*Check now* cannot see a draft: GitHub shows a draft to nobody
   until it is published, the updater included.)
2. Read **Ready to install** as in step 5.4: ↑ newer, nothing changed by
   hand but the guide's compiled pages, the environment line.
3. **Update to <version>**, **Yes**, and wait for the page to come back.
4. Then use it for a few minutes as on any day: a book and its narration, a
   video, a deck, a word looked up, the page you last worked on. The hub's
   foot says `<version>`.

If anything is wrong, stop here: nothing is public yet. Go back on
Parseh-mine (choose `parseh-<previous>.zip`, **Go back to <previous>**),
then [When a draft is wrong](#when-a-draft-is-wrong).

### 11. Publish

The moment the world sees it.

1. On GitHub, **Releases**, the draft, **Edit** (the pencil).
2. Leave the notes as they are — they are the changelog's; a change to them
   is a change to `CHANGELOG.md` and a new draft.
3. **Set as a pre-release**: unticked, as the workflow left it (the
   version's own `a` says alpha, and the updater's *Check now* never sees a
   pre-release). **Set as the latest release**: ticked.
4. **Publish release**.

From now on this release is somebody's download: it is never replaced, and
its tag never moves. GitHub's workflow refuses to build over it.

### 12. Afterwards

1. **The public road.** On Parseh-mine, **Settings → Updating Parseh →
   Check now**: it must name `<version>` as the newest release, *the
   version this Parseh already is*. On Parseh-test, go back to `<previous>`
   with its zip, then **Check now**, **Download** and **Update to
   <version>**: the whole road a user takes, checksum included. (Parseh-test
   then runs `<version>`, ready for the next rehearsal.)
2. **The releases page, signed out** (a private window): the release is
   there, with the zip and its `.sha256`, and no rehearsal.
3. **Pages is current.** GitHub, **Actions**: the *pages build and
   deployment* run for your push is green. Then
   `https://addicted2bayesianepistemology.github.io/Parseh/html-guide/site/reference/whats-new.html`
   shows `<version>` with its day.
4. **README.md** needs nothing: it names no version and links to the newest
   release (a test holds it so).
5. **The baseline.** If step 1 found the reds different from the table
   above — one mended, a new known one accepted — write the new table, with
   its date.
6. **Open the next version.** Decide its number (the next `a0.x.y`; it can
   be renamed while it is unreleased), then, in one commit:
   - `VERSION` — the next version;
   - `CHANGELOG.md` — a new heading at the very top,
     `## [<next>] - unreleased`;
   - `whats-new.md` — a new heading above the others,
     `## <next> — not yet released`;
   - the guide compiled again (`python3 html-guide/build.py`): the new
     heading changed What's new.

   `python3 -m unittest tests/test_version.py tests/test_html_guide.py`
   must be `OK`. Commit, push.
7. **Clear up**: `dist/` (ignored by git, and made again at will), the two
   fingerprints `../parseh-test-*.txt`, and the downloads.
8. **An announcement**, if this version is one to announce, is a piece of
   work of its own, not a step of this list.

## When a draft is wrong

Nothing of a draft is public but its tag (and the commits it points at), so
a draft is cheap to replace.

**A rehearsal's draft** (`<version>-rc1`) is never mended in place: delete
it and its tag (step 6.5), mend on `main`, commit, and rehearse again under
the next name, `<version>-rc2`, from step 3.

**The version's own draft**: mend, commit, and move the tag onto the new
commit. The workflow runs again and its draft replaces the old one.

1. Mend it on `main`, commit, build (step 7.4) and, if the mend is more
   than a word of the notes, rehearse it (steps 5 and 6, the next `-rcN`).
2. Move the tag, and push it over the old one:

   ```bash
   git tag -f -a <version> -m "Parseh <version>"
   ```

   ```bash
   git push origin main && git push --force origin <version>
   ```

3. Go on from step 8.2.

**When the run is red at *The tag, VERSION, the changelog and What's new
agree*** (`check`): the step's log names each thing that disagrees — a tag
that is not `VERSION`'s, a heading still `unreleased` or *not yet
released*, two headings on different days (with the line, and the day
spelt as the other file spells it). Mend them as step 7.1 says, compile
the guide, commit, and move the tag as above.

**When the run is red at *The compiled guide is in step with its
sources*** (`guide`): the log says *Not in step*, and why — the compiled
guide is not what the commit's pages compile to (a page, a picture, the
guide's engine or the studio's renderer changed after the last compile),
its last compile had errors, or there is none. Compile it
(`python3 html-guide/build.py`, `0 errors`), commit `html-guide/site/`,
check that `python3 lib/release.py guide --ref HEAD` now says `In step`,
and move the tag as above.

**To start again from nothing**, delete the draft (its page, **Delete**) and
the tag, then begin again at step 8:

```bash
git push --delete origin <version>; git tag -d <version>
```

**To run the workflow again without a new commit**: GitHub, **Actions →
release → Run workflow**, and type the tag. Should a run for a tag that has
only a draft stop at *Never over a published release*, delete the draft by
hand and run it again.

## When a published release is bad

A published release has been downloaded by somebody: it is **never
replaced, never deleted, and its tag never moves** — two different
Parsehs under one number would be worse than the fault. There are three
answers, and a bad fault takes all three, in this order:

1. **Withdraw it, so that nobody new gets it.** On GitHub, the release,
   **Edit**, tick **Set as a pre-release**, **Update release**. The page
   stays, for those who have it, but GitHub's *latest release* is
   `<previous>` again, so **Check now** stops offering the bad one to
   everybody. At the top of its notes (editing the notes of a published
   release is allowed; its files are not), say what is wrong and what to
   do: *Do not install this version: … If you have, go back: Settings →
   Updating Parseh, choose the zip of <previous>.*
2. **Tell people to go back.** Going back is the updater's own road:
   **Settings → Updating Parseh → A zip of your own**, `<previous>`'s zip
   from its release page, **Go back to <previous>**. Somebody who has the
   bad version and presses **Check now** is shown `<previous>` as *OLDER
   than this Parseh*, with the same button. If the bad version raised a
   data format, going back asks them to tick *I understand* and keeps a copy
   of their small files first; say so in the notes.
3. **Supersede it.** Mend the fault and release the next version by this
   whole checklist, from step 1, as quickly as care allows. Once it is
   published, **Check now** offers it to everybody, the ones on the bad
   version included.

A fault that loses data or stops Parseh starting calls for all three at
once. A fault that only looks wrong calls for the third alone.

## The first managed release

a0.3.2 is the first version released this way: every Parseh before it has
no `.parseh-release.json`, and **Settings → Updating Parseh** refuses such an
install, saying to install afresh from a release. So, that once:

- **The baseline** is the table above, taken on the a0.3.2 tree itself;
  there is no earlier tag to take it on.
- **Parseh-test** is made fresh from the rehearsal's local build —
  unpacked from `dist/parseh-<version>-rc1.zip` into a new folder,
  installed with its installer, started with `./serve.sh 7655` (then the
  port set to 7655 on **Settings → Network**). With no previous release to
  come from or go back to, 5.1 is that fresh install, and 5.4 to 5.7 go up
  to a throwaway *next* version built in a scratch clone and back down
  again (to `dist/parseh-<version>-rc1.zip`):

  ```bash
  git clone -q . ../parseh-next && cd ../parseh-next && echo <next> > VERSION && git commit -qam "throwaway <next>" && python3 lib/release.py build --out ../parseh-next-dist; cd -
  ```

  That clone is never pushed; delete `../parseh-next` and
  `../parseh-next-dist` after the rehearsal.
- **Parseh-mine** is moved into a fresh install made from the draft's zip,
  by hand, as the guide's *Updating Parseh → Moving into a fresh install,
  once* describes, in place of step 10's update — then checked as step
  10.4 says.
- **12.1's second half** (going back to `<previous>`, then the public road)
  waits for the second release.
