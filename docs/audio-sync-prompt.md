# Prompt for Claude Code — audio-synced HTML companion to the Buf-e Kur reading edition

> Fill in the audio path on line 1 of "Inputs" before sending. Everything else is already specific to this project.

---

I have a Persian reading edition of Sadeq Hedayat's *Buf-e Kur* built with LuaLaTeX, in the Ilya Frank style. I also have the audiobook narration. I want a browser-based companion where clicking any chunk of Persian plays exactly that fragment of the narration.

## Hard constraints — read these before anything else

1. **The existing PDF pipeline is not to be touched.** `build.sh`, the book's `main.tex`, `lib/frank-preamble.tex` and `lib/lang/fa.tex`, `assemble.py`, `extract.py`, and every macro definition stay exactly as they are. The only permitted modification to `ch1.tex` / `ch2*.tex` is the insertion of **whole-line LaTeX comments**, which the compiler discards.
2. **No duplicate authoring.** The `.tex` files are the single source of truth. The HTML is *generated* from them. There must be no second copy of the Persian, the transliteration, the vocabulary or the translation anywhere. When I add a new batch of paragraphs to a `.tex` file, re-running one command must produce both the PDF (unchanged pipeline) and the updated HTML.
3. **Timestamps live inside the `.tex` as comments**, so text and timing travel together in one file and diff together in git.
4. **The `.tex` is the only authority on what the text says.** I am also giving you a machine transcript of the audio. It contains errors and is *not* a source of text — it is a time index and nothing else. Never write a word of it into the reader, never use it to "correct" the `.tex`, never let a mismatch between the two be resolved in the transcript's favour. The only thing you take from it is *when* things are said.

## Inputs

- Audio:  a single audio file in the book's audiobook directory (the path `book.json` gives as `audio`)
- Transcript: beside it (the path `book.json` gives as `transcript`) — machine-generated from the audio, with timestamps. Inspect it and tell me whether it carries **word-level** or only **segment-level** times, since that changes what you can do with it.
- Text: `ch1.tex`, `ch2.tex`, `ch2b.tex`, `ch2c.tex`, `ch2d.tex` — ~1,800 `\ch` chunks across 377 `frank` environments, the new ones (when we will move on in the new paragraphs) will also have to work with this method.
- the book's `main.tex` gives the chapter order via its `\input` lines; it inputs `lib/frank-preamble.tex`, which defines every macro you need to interpret (and `lib/lang/fa.tex`, which sets what is Persian's: the two labels a `\vb` prints, the harakat filter)

Note that the `.tex` currently covers only chapter 1 and the first 40 paragraphs of chapter 2, while the audio and transcript cover the whole novel. The reference text is a **subsequence** of the recording, not a parallel copy of it — so find where it sits inside the transcript by local alignment. Do not assume the two start together or end together.

## What the source looks like

Each paragraph is a `frank` environment preceded by `\parnum{۱.۱}`. Inside it, chunks are:

```
\ch{colour}{persian, vocalised}{transliteration}{vocabulary}{english}
\chp{colour}{persian}                      % a chunk needing no gloss
```

The first argument of both is the chunk's colour — `\Cred`, `\Cblue`, `\Corange`, `\Cgreen`, or empty — the reader's own mark, and nothing you need to read; the Persian is always the **second** argument (5 arguments for `\ch`, 2 for `\chp`).

The vocabulary field admits only these macros — `\dw`, `\vb`, `\bw`, `\pw`, `\textit`, `\emph`, `\nobreak` (the allowlist is in `assemble.py`). That is the entire surface your parser has to handle. Their signatures are in `lib/frank-preamble.tex`; read it rather than guessing — `\vb`, for one, prints its second and third form only when that form is not empty, and `lib/texparse.py` already reads every one of them exactly as the PDF prints it.

The book gives each passage four times, and the Persian is written only once, in the `\ch` chunks — passes 3 and 4 are rebuilt from the same tokens with the harakat filtered out (codepoints U+064B–U+0652, see `frank_strip` in `lib/lang/fa.tex`). **Your HTML must derive its passes the same way, from the same chunks.** Never re-typeset text a second time.

---

## Stage 1 — Timestamp comments

Write `timestamp.py`, which aligns audio to text and edits the `ch*.tex` files in place, inserting comment lines.

**Format — the comment goes on its own line, immediately above the `\ch` it describes:**

```
% @par 1.1 118.42 141.07
\begin{frank}
% @t 118.42 121.06 0.97
\ch{}{دَر زِندِگی}{dar zendegi}{...}{in life}
```

Use a **full-line** comment, never a trailing one. A `%` at the end of a line of LaTeX swallows the following newline and the inter-token space with it; a line that *begins* with `%` is consumed whole and can have no effect on output whatsoever. This distinction is the entire reason the PDF stays safe.

Also write a sidecar `timings.json` keyed by a hash of the chunk's Persian text. The `.tex` comments are the readable copy; the sidecar means that if `assemble.py` ever regenerates a batch file from its JSON and wipes the comments, re-running `timestamp.py` restores them without re-aligning. Make the script idempotent: running it twice changes nothing, and it skips chunks that already carry a `% @t` line unless given `--force`.

**Alignment method.** The transcript is a noisy observation of the audio; the `.tex` is the true text. Use the transcript to find *where in the recording* each passage lives, then get precise boundaries from the true text.

*Normalise both sides into a comparable token stream* (this is where most of the accuracy comes from). Strip harakat (U+064B–U+0652 — they are pedagogical and won't appear in a transcript), normalise ZWNJ (U+200C) so that می‌خورد, می خورد and میخورد collapse to one form, fold Arabic yeh ي→ی and kaf ك→ک, unify ه/ة, drop ezafe marks, convert Persian and Arabic digits to a common form, strip punctuation, collapse whitespace.

*Match fuzzily, never exactly.* Persian ASR errors are systematic: dropped or invented ZWNJ, colloquial spellings where the narrator reads a literary form, unwritten ezafe, split and merged compounds, homophone confusions, plus the usual hallucinated repetitions in silence and occasional dropped stretches. So compare tokens by edit distance (`rapidfuzz`) rather than equality, and use monotonic sequence alignment — Needleman–Wunsch, or `difflib.SequenceMatcher` with a custom equality — so the mapping can never run backwards.

*Anchor and interpolate.* Long and rare words make the best anchors; short function words make the worst, so weight them accordingly. Take timings from confidently matched anchors and interpolate linearly across unmatched gaps, weighting by character count. A boundary that came from an anchor and one that came from interpolation are not equally trustworthy — record which, and let it drive the confidence score.

*Work paragraph-first.* The 377 `\parnum` paragraphs are 377 independent anchor points; locate each paragraph in the transcript first, then place chunks within that paragraph's span. This contains any error to one paragraph instead of letting drift propagate down a chapter.

*Then refine on the true text.* Once the transcript has told you a passage lives at roughly 118–141 s, run a real forced aligner — `ctc-forced-aligner` (MMS) handles Persian well — over just that window using the **`.tex` text, not the transcript text**. The transcript gets you to the right few seconds cheaply and robustly; forced alignment on the true text gives boundaries you can actually cut on. If this stage proves unreliable, say so and fall back to transcript-derived boundaries, but tell me which chunks came from which path.

*Sanity-check everything the transcript tells you.* Reject non-monotonic timestamps. Flag any chunk whose implied speaking rate is outside a plausible band for Persian narration, whose duration is under ~0.3 s, or which sits in a paragraph whose token match rate is poor. A transcript that hallucinated a loop will otherwise produce confident nonsense.

Finally, snap every boundary to the nearest silence via `ffmpeg silencedetect` within a short window, then pad ~120 ms before and ~200 ms after; clean fragment playback depends on this more than on raw alignment precision.

**Then verify the PDF is untouched:** build the PDF before and after inserting comments, run `pdftotext` on both, and confirm the extracted text is byte-identical. Show me that check passing. If it doesn't, stop and tell me.

## Stage 2 — `tex2html.py`

Parses the same `ch*.tex` files, with their `% @t` comments, and emits the reader. Chapter order comes from the `\input` lines in the book's `main.tex`. No configuration file listing chapters — that would be a second source of truth.

**Mirror the book's four passes**, all from the same chunk data:

1. Whole paragraph, vocalised, no glosses — the reader's own attempt
2. The chunks, Persian right, gloss left, each chunk clickable
3. Whole paragraph, naskh, harakat stripped
4. Whole paragraph, nastaliq

Audio is reachable from every pass: in pass 2 a chunk plays itself; in passes 1, 3 and 4 clicking anywhere plays the chunk containing that word; `\parnum` plays the whole paragraph.

**Right-to-left is the part that will bite you.** The `.tex` preamble documents the traps and the HTML has the same ones: an English gloss sitting inside an RTL run needs isolation (`<bdi>`, or `unicode-bidi: isolate`) exactly as `\babelsublr{\mbox{…}}` does in LaTeX, or two Persian words separated by a space will merge into one run and come out reversed. Set `lang="fa" dir="rtl"` on Persian, `lang="en" dir="ltr"` on gloss. Preserve ZWNJ. Test that a paragraph with mixed content renders in the right order before building all 377.

**Fonts:** Vazirmatn for naskh, Noto Nastaliq Urdu for nastaliq — the same two the PDF uses. Copy the woff2 files next to the HTML and load them with `@font-face`. No CDN, no network at runtime. Nastaliq needs generous line-height, as `\SzNast` does at 15/36.

**Behaviour:** click to play chunk · loop a chunk for drilling · continuous play with the active chunk highlighted and auto-scrolled · speed 0.5×–1.5× · toggle each pass on and off · per-chapter timing offset nudge to correct drift · keyboard (space, ← →, R loop, G glosses) · position, speed and offset in `localStorage` · dark mode · readable on a phone. Vanilla JS, inline CSS, no framework, no build step. Audio referenced as a local sibling file, not embedded.

A chunk with no `% @t` renders normally but is visibly marked as having no audio. Never play an approximate fragment.

## Stage 3 — `review.html`

Lists every chunk below a confidence threshold, plays it, lets me nudge start/end with arrow keys, and writes corrections back into the `.tex` comments and the sidecar. Alignment will get some of this wrong and I need to fix it by ear, not by editing JSON.

Show, beside each flagged chunk, **the true text from the `.tex` and the transcript words that landed in its window**, so I can see at a glance whether the mapping is sane or whether the transcript went astray there. Mark clearly which is which — the transcript is displayed as diagnostic evidence, never as text to read. Show also whether each boundary came from an anchor, from interpolation, or from forced-alignment refinement.

## Deliverables

- `timestamp.py`, `tex2html.py`, `review.html`, and `build-html.sh` (one command, mirroring `build.sh`)
- `timings.json` sidecar
- `reader/` output plus a README of how to re-run
- A report: confidence distribution, chunks needing review, the pdftotext before/after check, and per-paragraph transcript match rates — low match rate is the signal that either the audio diverges from this edition or the transcript failed in that stretch, and I want to see it rather than have it quietly interpolated over
