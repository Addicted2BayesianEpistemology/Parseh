# Estimating by the sound — lib/wavealign.py

"Estimate the rest" (key E in the timeline editor) lays a fresh guess over
every piece after the line in hand. *By the text* spreads them in proportion
to how much text each has. *By the sound* hands the same pieces, and the
picture of the sound of the same stretch, to `lib/wavealign.py`, which lays
the text through that picture. This document is the description of how it
does it: the stages, the cost it minimises, what it costs to run, which of
its numbers matter, and what was measured. `lib/wavealign_lab.py` is its
bench — the made-up recordings, the measures, the drawing — and
`tests/test_wavealign.py` holds it to all of it; both are in the source code
only, and a release carries neither.

---

## 0. What it cannot do — read this first

**The only input is a waveform envelope**: one loudness per bucket of time,
the picture an audio editor draws — the peak of every 10 ms of a book's
narration, every 50 ms of a YouTube video's `waveform.json`. It says how loud
the sound was and when it went quiet. **It does not say what was said.**
Nothing here can know that a stretch of the envelope *is* a particular word,
and nothing tries: there is no audio, no spectrum, no speech recogniser, no
phoneme model, no pronunciation dictionary, and there never will be — that is
the owner's constraint, and the reason the thing runs anywhere NumPy does.

So what comes out is **not acoustic forced alignment** and must never be
presented as if it were. It is the globally most plausible *monotonic
segmentation* of the transcript through time, given

    transcript structure + duration priors + waveform activity + pause structure

The question asked is never "which stretch sounds like this word?" — that is
impossible with this data — but "among all monotonic ways to spread this text
through time, which is most consistent with where the sound is, where it
pauses, how long the words are, where the punctuation is, and a speaking rate
that changes smoothly?". Where the sound pauses the answer is usually right
to a few hundredths of a second; inside continuous speech, between two words
nothing in the envelope separates, it is an informed interpolation, and it
says so.

**Confidence is structural timing confidence**: how firmly the envelope pins
a boundary where it was put — never a probability that a word was recognised.
0.9 is a boundary on a clear pause, 0.5 one mostly placed by the duration
prior, 0.2 one only proportional allocation put there; an envelope that shows
nothing gives 0.1 everywhere — and then the answer is the proportional one
over the words' weights, nothing more (§3).

---

## 1. The two doors

```python
align_transcript_to_waveform(waveform, duration_seconds, transcript,
                             sample_times=None, options=None, tokenize=None)
    -> AlignmentResult(words=[WordAlignment(word, start, end, confidence,
                                            start_min, start_max, end_min, end_max)],
                       speech_regions=[(start, end)], pauses=[Pause(...)],
                       global_confidence, diagnostics, candidates)

estimate_pieces(envelope, duration, texts, kind="span", *, sample_times=None,
                options=None, tokenize=None) -> dict
```

The first is the owner's specification's API, for anything; the second is
the one Parseh calls (`serve.py`, both estimate doors), and it runs **the
same engine**: the pieces' texts are aligned as one transcript whose piece
boundaries are breaks of their own strength, and the pieces are read off the
words (§4). The contract of `estimate_pieces` — the shape of its answer and
every invariant — is in the job's CONTRACT; in short: all times from the
start of the stretch, `pieces[0].t0 == 0.0` exactly, every piece at least
`min(0.4 s, duration / pieces / 2)` long, a video's captions end to end with
the last ending at `duration`, a book's pieces joined in the gap between them
or split across a pause of at least `split_gap` (0.5 s) with `pad` (0.1 s,
never more than a third of the gap) either side, the trailing silence left to
nobody, the same question giving byte-identical answers, and `ValueError`
only for no pieces or a duration that is not a positive number — or that is
shorter than a microsecond (`MIN_DURATION`: below it the pieces' floor and
the projection's own slack no longer fit inside the stretch, so no answer
could keep its times in order and in `[0, duration]`; the doors refuse
anything under a tenth of a second, and the page never asks under 0.4 s).
Garbage in the envelope — NaN, inf, negatives, strings, integers too long
for a float, nothing at all — is survived, never raised on; so is a
tokenizer that breaks, however it breaks (§2).

`WordAlignment` satisfies `0 <= start < end <= duration` and
`word[i].end <= word[i+1].start` **exactly**: the times are the candidates'
own numbers, so no tolerance is needed; a caller comparing after its own
arithmetic may allow 1e-9 s. A gap between two words is a silence left to
nobody.

Every number the aligner uses is a field of `AlignmentOptions`, with a
comment saying what it is; §7 says which matter.

---

## 2. The transcript

**Tokens.** `tokenize(text) -> Sequence[str]` is a callback; the default
splits on whitespace and, inside a whitespace word, cuts a run of a script
written without spaces into single characters, each with the marks that
follow it. Which scripts those are is decided by the Unicode Script property
(the ranges of `Scripts.txt`: Han, Hiragana, Katakana, Bopomofo, Thai, Lao,
Tibetan, Myanmar, Khmer, Yi, the Tai scripts, Balinese, Javanese) and never
by a language code or a word list — so Japanese and Chinese are read a
character at a time, a Latin word inside Japanese stays whole, and Korean,
which writes spaces, keeps its words. Punctuation stays on the token it
follows; an opening bracket or quote (Unicode `Ps`, `Pi`) on the token it
opens; a token that is punctuation alone joins its neighbour, because nobody
says it. A tokenizer that breaks is replaced by the default — whether it
raises when called, returns something that is not a list, is a generator
that raises halfway, or hands back a token that cannot be made a string.

**Character counts** are letters and digits (Unicode `L*`, `N*`): no
punctuation, no symbols, **no combining marks** — a vowelled Persian or
Arabic word weighs exactly what the bare one does (the harakat write vowels
the bare letters leave unwritten; they do not make the word longer to say,
and the test proves the alignment byte-identical with and without them).
**Devanagari's dependent vowel signs are the one exception, and they count
as a character each**: unlike harakat they are always written and always
spoken — `कि` is two sounds where `क` is one — so they carry length the way a
Latin vowel letter does. The rule is by the Unicode Name (`… VOWEL SIGN …`),
so it covers the other Indic and South-East Asian scripts the same way;
virama, nukta, anusvara and candrabindu do not count. Katakana's prolonged
sound mark is a letter (`Lm`) and counts — it is a mora. The Arabic
**tatweel** (U+0640, kashida) is filed as a letter too, but it is only ink
that stretches a word across the line: it does not count, the same case as
the harakat.

**Duration weight.** `weight = max(min_weight, prior(chars))`, the prior
being `chars ** alpha` (default, `alpha` 0.8), `chars`, `sqrt(chars)` or
`constant + per_char * chars` (`duration_prior`). A character of a script
without spaces weighs `continua_weight` (2) letters: a kana is a mora, a Han
character a syllable. An empty or punctuation-only piece gets a stand-in of
half a word, so it still gets a slice.

**Breaks.** The punctuation after each token, classed by Unicode alone:
general category `P*` says it is punctuation, the Name says which kind — a
name with FULL STOP, QUESTION MARK, EXCLAMATION MARK, ELLIPSIS, DANDA or
INTERROBANG ends a sentence (`. ! ? … 。 ！ ？ ؟ ۔ । ॥`), COLON (which
SEMICOLON contains) is a colon (`; : ؛ ； ：`), COMMA a comma (`, ، 、 ，`,
and a dash); INVERTED marks, quotes, brackets and hyphens break nothing.
Repeated punctuation (`?!?!`, `...`, a closing quote after a full stop)
counts as its strongest mark. A **paragraph is what a blank line ends**, and
in `estimate_pieces` each **piece boundary is a break of its own**: a book's
(`piece_strength_span`, 0.9) about as strong as a sentence end, a caption's
(`piece_strength_point`, 0.5) weaker, since captions are cut anywhere.

**Pause priors.** Each break carries the probability that a reader pauses
there — plain word 0.04, comma 0.45, colon 0.55, sentence 0.85, paragraph
0.95 (`pause_prob_word`, `break_strength`) — and, for the weak ones, **how
long a pause there is apt to be** (`pause_length`: a plain word 0.12 s, a
comma 0.25, a colon 0.35): beyond 0.3 s a pause of `g` seconds is
`exp(-min((g - 0.3) / length, 1.5))` as likely there. So a whole second of
silence hardly belongs after a comma, and seldom after a plain word — the
owner's "strong waveform pauses over proportional timing assumptions", as a
likelihood rather than a rule. The **cap** (`pause_length_cap`, 1.5 nats)
is the owner's "ordinary word + huge pause → small penalty": uncapped, a
breath of a second after a plain word cost some nine nats, and the DP would
rather drag a sentence end onto the hesitation, or read the words around it
at an absurd pace, than admit a reader stopped for breath. Capped, it costs
at most `-log(p_word)` and 1.5 nats more (§8). **A sentence end and a paragraph have no
such limit**: what follows them may be a breath, a page turned, the silence
between two chapters. The first design gave them 0.6 and 1.2 s; on real
speech, where the pause between paragraphs runs to two seconds and more,
that charged the very pauses that mark sentence ends, and drove the ends
elsewhere (§8).

**A text nobody punctuated.** Forty words and more with no mark between
them — no comma, no full stop, no blank line (`bare_min_tokens`) — is what
a punctuated text almost never is: an auto-caption as the recogniser wrote it
(YouTube leaves Persian and Arabic ones bare, and tidying is a button, not
automatic), lyrics, subtitles in a script whose captions carry no full
stop. Its sentences end all the same, unmarked, and its captions end where a
line filled up, not where the voice stopped. So in such a text **a plain
word may be followed by a pause as long as a sentence end's** (no length
limit), and **a caption's end is a plain word's end** (its prior is not
raised to `piece_strength_point`, and the calibration treats it as one). A
book's piece end is the book's own cut and stays one. It changes nothing in
a punctuated text — no Kokoro stretch is bare (§8) — and it took a thousand
words of made-up auto-captions from worse than by the text to better (§6).

---

## 3. The stages

```
WaveformPreprocessor → ActivityEstimator → PauseDetector → BoundaryCandidateGenerator
   → TranscriptAnalyzer → InitialDurationModel (+ calibration) → HierarchicalAligner
   → DynamicProgrammingAligner → BoundaryRefiner → ConfidenceEstimator → AlignmentResult
```

Each is a class of its own in `lib/wavealign.py`.

**WaveformPreprocessor.** Garbage out (NaN and inf are holes, negatives are
magnitudes written signed), then onto a uniform grid of `frame_rate` (100)
frames a second whatever the source's resolution: peak per frame when the
envelope is finer, linear between samples when coarser, `sample_times`
honoured when given (unsorted, uneven, partly outside the stretch). Then the
**compressed domain**: 20·log10, a median filter (30 ms, one-frame spikes
out) and a Gaussian (20 ms) — both in seconds, never in samples — and a
**robust normalisation** by percentiles (5th and 99th, in dB), never by the
maximum, which one click would decide. The dB domain is what makes a 20 Hz
peak picture and a 100 Hz RMS one comparable: the depth of a pause is a
ratio, not a difference. The dynamic range between the percentiles is the
**evidence**: under 6 dB the envelope is believed not at all, over 18 dB
fully, in between in proportion — every term that listens to the envelope is
scaled by it. **With no evidence at all** (a flat line, a muted or silent
recording, a picture with no range left in it) nothing else runs: the answer
is the proportional one over the words' weights, at a confidence of 0.1.
Left to the DP, the rate-aware beam still reshaped the pieces on the
durations alone, with no pause to hold them, and landed them worse than the
proportion it started from (1.4 s of piece error against 0.7 by the text, on
ten flat made-up cases). A picture that is only noise, with some range
left, is believed as far as its range says.

**ActivityEstimator.** Not voice activity detection, which an envelope
cannot support: an energy estimate. Otsu's split of the level histogram gives
a noise level and a speech level; the **hysteresis** thresholds are fractions
of the way between them (`low_frac` 0.3, `high_frac` 0.5) — a run becomes
active where it reaches the high one and stays active until below the low
one, so the decision does not chatter. Bursts under 40 ms are clicks; gaps
under the shortest pause are closed; runs merged over gaps under 0.35 s are
the **speech regions**. A soft activity likelihood (a logistic around the
thresholds) is integrated once, so the mean activity of any interval is two
lookups.

**PauseDetector.** A **pause** is a run below the low threshold, and it keeps
**both edges** — where the sound stopped and where it began again — because
the word before ends at one and the word after starts at the other, and the
silence between belongs to neither. Its strength grows with depth (towards
the noise floor), length (`1 - exp(-d / 0.12 s)`) and contrast with the
quarter second either side; its *anchor* evidence is the strength ramped in
from 0.08 s to 0.3 s of length, so a stop closure inside a word is not
mistaken for a pause — and from further still where the envelope's own
dips run longer (the dip length, below). Classes: short (< 0.25 s), phrase
(< 0.6 s), long.
Leading and trailing silences are pauses of their own role. A **valley** is a
prominent local minimum inside speech (prominence against the 120 ms either
side, flat bottoms taken at their middle, a parabola for sub-frame position),
graded weak or possible word boundary — a place a boundary might go, never
assumed to be one.

**BoundaryCandidateGenerator.** Where a boundary may go: every inner pause as
one **object with two edges** (L = the end of the word before, R = the start
of the word after), and points (L = R) at valleys, the edges of speech, the
proportional estimate, the refiner's finds, and a **fallback grid** (80 ms,
or a sixth of a word) so an envelope with no valleys at all still leaves the
DP somewhere to go. Nothing is left inside a pause but its own edges; points
closer than 15 ms are merged by priority. Each candidate's boundary cost is
the level there times one minus its strength — low in a pause or a deep
valley, high in loud sound, **never a reward**, so no boundary is drawn to a
pause for its own sake (whether a pause suits the text there is the pause
prior's say). The sentence level asks for a sparser set (a 0.5 s grid, only
the stronger valleys); a transcript far shorter than its sound keeps only
its strongest valleys, thirty a word — **and only its surest pauses, thirty
a word too**: two captions left before the end of a two-hour video are four
words for a stretch of thousands of pauses, and with every one of them a
candidate the word pass's cost matrix grew as their number squared.

**InitialDurationModel and calibration.** The global rate is text weight per
second of **speech** — the speech regions between the first and the last
sound, the silences left out — and every word's expected duration follows
from it. The proportional first guess lays the words over speech time only,
so a long silence stays unassigned from the start. Then the two things
learnt from the recording before aligning it.

*How long a dip is here* (`_dip_length`). Under a bed of music or room noise
the quiet between two syllables sinks to the level of the bed, and the
envelope shows a "pause" at every stop consonant — hundreds of them, as deep
as the real ones and only shorter. By loudness they cannot be told apart; by
length and by number they can: the text says about how many pauses a reader
makes (the sum of its pause priors), and nobody pauses at every syllable. So
the length of the silence ranked `dip_rank` (2) times that many, plus four,
is taken as the length a dip may reach in this recording, and a pause is
judged against it: its anchor evidence ramps in from there rather than from
0.08 s, and the dips count as speaking time for the rate. In a clean
recording that length is under 0.08 s and nothing changes; under the
Kokoro bench's music bed and its 12 dB room noise it was 0.07–0.12 s at 100
values a second (at 20 a second the 50 ms buckets mostly swallow the dips
already). When it was found, the Hindi captions under music were off by
7–15 s without it: the envelope showed 493 pauses in 260 s, against 169 for
the same speech without the bed, the reader seemed to pause everywhere, and
the global rate came out 29 % too fast. With the pace model of today (below)
the loss is smaller — undoing it costs Hindi 0.03 s (§8) — but the dips are
still not pauses.

*The reader's pause habits* (`_calibrate`). The text expects so many pauses
(the sum of its priors); the envelope shows so many (plain pauses counted
whole). A reader who pauses at half the commas and sentence ends the priors
assume would otherwise have every sentence read straight on charged
`-log(1 - p)`, and the alignment would chase the few pauses there are at the
price of absurd rates. So the priors are fitted to the reader — with **two
counts, not one** (`calibrate_mode = "split"`): the **long** pauses (0.25 s
and more) against the strong breaks (sentence ends, a book's piece ends),
the rest against the weak ones (commas, plain words, a caption's cut). Each
group is shifted in its log-odds until its count agrees (the order within
it kept; four pauses' worth of doubt, so a short text is not refitted on one
pause more or less); the strong breaks are never made likelier than the
text says, and a reader who pauses more than the weak breaks allow has the
plain words' prior raised. A reader who stops at every full stop and runs
over the commas, and one who hardly stops anywhere, show about the same
total and want opposite priors; the length of the pauses tells them apart.
The first design scaled every prior by one factor (`calibrate_mode =
"scale"`), which for the first kind of reader — Kokoro in every language,
and most narrators — brought a sentence end's prior down to about 0.5,
where a sentence end with a pause and one without cost the same, and the
sentence ends stopped pinning anything (§8).

**Its known cost: the fast reader.** "Long" is 0.25 s and more
(`phrase_pause_s`). A reader whose sentence pauses are all shorter than that
— a brisk narrator, 0.10–0.22 s at every full stop — shows the split fit no
long pause at all, so it lowers every sentence end's prior (0.85 to about
0.3–0.4) while the commas keep theirs: **a sentence end then ranks at or
below a comma**, against the order the priors are given in. On such made-up
readers (six seeds, 160 words) that costs the books 0.096 s of piece error
against 0.054 with no calibration, and the captions 0.175 against 0.105 — by
the sound still beats by the text eightfold there. The cures tried were
worse: a pass forcing the order back (isotonic) regresses the "loose
lengths" captions 0.28 → 0.50 s and "no pauses" 0.15 → 0.24 s, since the
lowering, not the order, is what costs; no calibration regresses the
readers it exists for (hesitations 0.61 → 0.94 s, "no pauses" 0.15 → 0.30);
counting the longest pauses as "long" by rank helps the fast reader only
partly and regresses "no pauses" to 0.30. The bench keeps the case in view
("fast reader", §6).

**HierarchicalAligner.** Two levels. **Units** come from the text alone:
sentences, and pieces where a piece boundary is as strong as a sentence's (a
book's); a sentence longer than 10 s of expected speech is split at its
strongest inner break; short units are merged forward but never across a
sentence end. A caption cut in mid-sentence is *not* a unit boundary — made
one, it turned every sentence into loose fragments with rates of their own
and a boundary between them free to wander (the captions scenario went from
0.81 s to 0.08 s of piece error when that stopped). The units are aligned
first, over the sparse candidates, by the **rate-aware beam** (below); the
words are then aligned in a band around them (1.5 s plus a quarter of the
unit's length, at most a minute), **at the rate each unit was found to be
read at** (drawn towards the smooth rate curve as far as the unit is too
short to be sure). A transcript of four words or fewer, or with fewer than
two units, is aligned word by word in one go — and so is **a text with
nothing to cut it at**: no sentence mark, no paragraph and no book piece end
anywhere in the stretch. Its units could only be made up, split at a
caption's end or in the middle of the words, and the beam would pin those
made-up boundaries while every real pause had to fall inside them: on
made-up auto-captions that was 1.5–6 times worse than by the text, and
worse the longer the text. The words alone, in their wide band (some forty
words either side), are not.

A still coarser level of minute-long chunks, which the first design had, was
**measured and dropped**: with hundreds of sentence pauses that look alike a
chunk can only follow durations, it landed tens of seconds off (11 s mean
word error on a 17-minute recording against 0.07 s without it), and the
sentences were then aligned in the wrong place. The sequence of sentence
lengths against the sequence of inter-pause intervals is a fingerprint; it
is what pins a long recording down, and only the sentence level sees it.

**DynamicProgrammingAligner.** The monotonic DP over boundary objects:
boundary `b_i` is the start of token `i` and the end of token `i-1`; token
`i` occupies `[R[b_i], L[b_{i+1}]]`; `DP[i][j]` is the best cost of the
first `i` tokens with token `i-1` ending at candidate `j`, with back-pointers,
and the path is the global optimum — never a greedy word-by-word placement.
The cost of token (or unit) `i` from candidate `k` to candidate `j`, every
term in **nats** (a negative log-likelihood or something scaled like one, so
a weight of 1 means "as the model says" and the terms weigh against each
other by what they claim):

| term | what it is | weight |
|---|---|---|
| duration | `½((log d − log e) / σ)²` against the global rate (σ 0.45) — log-normal, so a long word is not punished for being long | `w_duration` (× `global_share` 0.3 once a local rate exists) |
| local rate | the same against the rate of the unit the word is in (σ 0.35) | `w_rate` |
| rate smoothness | the same against the rate of the neighbouring 1.5 s | `w_smooth` 0.3 |
| boundary | the candidate's boundary cost (§ above) | `w_boundary` |
| activity | `(share of the word the envelope calls quiet)²` — soft: low energy is not certain silence | `w_activity` 2 × evidence |
| pause / punctuation | `−log(a·p·exp(−min((g−0.3)/len, 1.5)) + (1−a)(1−p))`: the boundary is a pause with probability `a` (the envelope), the text expects one with probability `p` (the punctuation) for pauses of about `len` seconds — a longer one dearer, by 1.5 nats at most (`pause_length_cap`) | `w_pause` |
| anchor | a Poisson count of the pause mass the unit swallows against the pauses its inner breaks expect (a word: almost none; a sentence with two commas: about one), charged only for an **excess**; a pause longer than 0.3 s counts as more than one | `w_anchor` |
| unassigned sound | activity left before the first word or after the last | `w_unassigned` 1.5 × evidence |

The **duration limits** are hard: a word lasts at least a fifth of its
expected length and at most five times it or its expected length plus 0.6 s,
whichever is longer (the 0.6 s shrinking to a few words' worth of the
recording when the text is far too long for it); a unit at least about a
third of its expected speech time and at most some four times it, plus a
few seconds. The DP is **banded** (Sakoe-Chiba, around the level above)
and **duration-limited**, and every step is vectorised with NumPy over the
band of `j` and the predecessors `k` the limits allow. A path pressed against
the band's edge is solved again in a band 2.5 times as wide (twice at most);
if nothing fits, once more with the limits loosened fourfold — never
unbounded, which would cost words × candidates² — and if still nothing, the
proportional answer with a confidence of 0.1. Three guards stand before
that. **Fewer candidates than boundaries** (a stretch silent but for its two
ends: nothing but a pause's own edges is left inside a pause) is no band at
all, and the level is skipped — it used to run the bands into negative
indices and raise `IndexError`. **A wider band that loses the answer** keeps
the narrower one's: for the plain DP a wider band holds every path of the
narrower, but the beam's pruning can lose them all where a long silence
leaves one state to cross it, and throwing the edge-touching answer away
dropped the whole sentence level (an hour with a half-hour silence: 10 s and
no sentence level, against 1.2 s with it). **Far more words than any voice
says in the time** — over 20 a second (`max_words_per_s`), where the densest
real speech measured is 6.5 (Chinese and Japanese characters) — is the
proportional answer at once: no envelope resolves boundaries that close,
and the DP took minutes and gigabytes, growing as the words squared, to get
there.

For the **units**, the speaking **pace** is in the state: `solve_rated`. A
unit's own rate (its expected length over its length in speech time) is the
pace plus that unit's own scatter — its words' lengths, a number read out, a
line of dialogue — and the pace itself moves slowly. So each unit costs two
**Huber** terms (a Gaussian core, linear tails, so that a real change and an
odd sentence each cost in proportion to their size): its own rate against
the pace (spread `σ_rate²/words + rate_unit_sigma²/sentences`, 0.10 a
sentence), and the pace's move from the unit before (spread `rate_drift`,
0.08, per root second of the time between them, at least 0.03), pulled back
towards the global rate as far as that time makes the pace forget (an
Ornstein-Uhlenbeck chain, 120 s). Or, rarely, the pace **jumps** to the
unit's own rate, for a fixed `rate_jump_nats` (3) and a nat per unit of
log-rate: a new chapter, a new day at the microphone, a speed set by hand
(the pace doubling halfway: 1.36 s of word error before the rate was in the
state at all, 0.07 s with it). The best pace for each transition is found
exactly — the two terms have a single minimum between the pace before and
the unit's own rate, at their corners or between them (`_pace_step`) — and
kept on a grid of log-paces (±1.1, step 0.05); the global rate is the prior
of the first unit's pace only (σ 0.35).

Keeping the scatter out of the pace was the largest single gain on real
speech (§8). With the unit's own rate as the state, as first designed,
every sentence's scatter became a step of the pace, the steps added up to a
random walk free to wander anywhere, and a path that read a minute of text a
third too fast and the next minute a third too slow cost next to nothing —
the commonest way left to land ten seconds off.

The states (candidate, pace) are searched as a **beam that is local in
time** (`_prune`), so the work follows the ambiguity, not the length of the
recording, and hours of sentences are aligned in one pass with no coarser
level to go wrong first. Local, because states that stand at different times
are not comparable by their cost so far: one that has read the text too fast
stands early, has swallowed less sound and fewer pauses, and looks cheap —
until the end, where the sound it left over is charged all at once. The
first design's beam compared every state with the best of all (8 nats
behind it, 400 states at most) and pushed the right ones out for good: on
real speech whole stretches came out 20–45 s early, with the last 40 s of
sound left to nobody. Now each state is measured against the best within
2 s of it (8 nats, `rate_beam`; and only loosely, 40 nats, against the best
of all), each candidate keeps its best three paces, and the cap of 200 is
shared out over the windows — the best of every window first, then the
second best — so it buys different places in time rather than many paces at
one place. The first boundary is pruned the same way: kept whole, the first
unit was expanded from every candidate of a band minutes wide, and on a long
stretch with few pieces that one step was gigabytes (three captions over
four hours: 2.4 GB, now 0.4).

With `marginals`, the word DP also runs **backward**: `F + B` is the
min-marginal of every (boundary, candidate) — the cost of the best path
forced through it — whence the confidence margin and the uncertainty
interval (§ below).

**BoundaryRefiner** — coarse to fine. Round every boundary the word pass
chose, the finer curve (median only, no Gaussian) is searched for its lowest
point in a window of 0.35 s (or three words' worth, when words are absurdly
short), in the whole window and in each half; those become candidates, the
rate is re-estimated from the words (per unit, and over the neighbouring
1.5 s for the smoothness term), and the DP runs again in a band of the
window's width around the last path — **never widened**: a refinement that
wanted to go further would be the word level overruling the rate-aware level
above it, which knows better (in one pace-doubling case, letting it widen gave 0.80 s of word error
against 0.09 s). Two passes; the last one takes the marginals. No
boundary ever moves on its own, so monotonicity is never at risk.

**ConfidenceEstimator.** Each boundary's confidence is a weighted mean of
six things:

| weight | factor |
|---|---|
| 0.30 | the strength of the pause or valley it sits on (a grid point has none) — nearness to a strong silence is carried here, since a boundary on a pause sits on its very edge |
| 0.25 | the margin between the best segmentation and the best one that puts it more than 0.1 s elsewhere (from the min-marginals; the sentence level's across its whole band) |
| 0.15 | how narrow the interval of near-optimal positions is |
| 0.15 | how far it moves when the parameters are shaken: a second DP with every word's duration prior raised to the power 1.19 (whichever prior is in force: for the default `chars ** 0.8` about `chars ** 0.95`), the pause weight ×0.7, the duration spread ×1.25, the boundary weight ×1.3 — and whether its sentence could move |
| 0.10 | whether the coarse and the fine pass agree |
| 0.05 | how well the length of the words beside it fits the pace around them (the duration prior against the waveform) |

`0.05 + 0.9 × (the mean)`, the whole scaled by `0.4 + 0.6 × evidence`. **A
factor that could not be measured counts as a half**, never as the best it
could have been: when the refinement finds no way through, the coarse path
stands and its margins, interval and stability are taken from the coarse
pass in the same narrow band (`diagnostics["refine_failed"]`), and the
agreement of a coarse and a fine pass, with no fine pass, is a half — left
at their defaults, the case with the fewest checks came out the surest
(0.37 → 0.56). A word's confidence is the mean of its two boundaries'; the
global one the mean of the inner boundaries'. **Uncertainty**: `start_min..start_max` and
`end_min..end_max` span every candidate whose min-marginal is within 1 nat
of the best, so a boundary with many similarly good positions gets a wide
interval — measured: a boundary on a pause has a narrower one than a
boundary inside speech. The interval cannot exceed the refinement window;
`diagnostics["uncertainty_clipped"]` counts the boundaries it reached.

On real speech (§8, TUNE, the piece starts of all 7,050 evaluations) the
confidence ranks the errors as it should, if gently:

| confidence | share of starts | off by more than 0.5 s | mean error |
|---|---|---|---|
| 0.8 and above | 32 % | 1.2 % | 0.119 s |
| 0.6–0.8 | 28 % | 2.5 % | 0.136 s |
| 0.4–0.6 | 31 % | 4.0 % | 0.167 s |
| 0.2–0.4 | 9 % | 7.3 % | 0.223 s |
| below 0.2 | 0.3 % | 11 % | 0.372 s |

**Silence** is kept four ways: leading and trailing silence are left out of
the first and last words (and in `estimate_pieces` the leading silence
belongs to the first piece, the trailing to nobody); an inner pause is a gap
object, so a 2-second silence is `A.end = 10.2, B.start = 12.1`, never a
word stretched across it; `result.pauses` gives every pause the envelope
showed with its class by sound and its role in the alignment (leading,
trailing, inter-word, phrase, sentence, paragraph, within-word).

---

## 4. From words to pieces (`estimate_pieces`)

The pieces' tokens are aligned as words, and each boundary between piece
`i` and `i+1` is read from the last word of one and the first of the next:
a gap of at least `split_gap` is **split** (`t1 = end + pad`,
`t0 = start − pad`, the pad never more than a third of the gap; for a
caption, which has one number, `start − min(pad, gap/2)`), a shorter one is
**joined** at the quietest point of the gap (its middle when it has none).
The first piece starts at 0.0 — the line in hand, whose leading silence it
keeps. A book's last piece ends at its last word's end plus the pad; a
caption's at the end of the stretch. Where a piece would be shorter than
`min(0.4 s, duration / pieces / 2)` the numbers are projected onto the
constraints by least squares (pool-adjacent-violators) — touched only when
something violates them. Each piece carries the confidence of its start
boundary (the first: 1.0), the uncertainty interval of its start, and
`speech`, its first word's start and last word's end. `anchored` counts the
boundaries that sit in a pause the envelope shows — the number the timeline
tells the owner.

---

## 5. What it costs to run

Let `N` be the words, `M` the candidates (a few per word: pauses, valleys,
the 80 ms grid — about five per word in speech), `B` the band in candidates
(about 2 × (1.5 s + ¼ of the unit) of candidates at the word pass, 2 × 0.35 s
in refinement), `K` the predecessors a word's duration limits allow (a
fraction of a second of candidates), `U` the units (sentences, about N / 10),
`S` the beam's states (≤ 200) and `T` the transitions a unit's limits allow.

- **Time**: preprocessing, activity and detection are O(frames). The unit
  beam is O(U · S · T): a unit's own cost is computed once for each
  (candidate it may start at, candidate it may end at) — not once per pace
  — the pace step is a closed form, the best way into every (candidate,
  pace) a scatter-minimum, and the local pruning a sort of the survivors,
  O(S log S). The word
  pass and each refinement are O(N · B · K), vectorised over B × K per word;
  the backward pass the same. Nothing is O(N · M²) — the relaxed fallback is
  still banded. So the whole is **linear in the words** at a fixed pace.
- **Memory**: the frames, the candidates, and per word the back-pointers of
  the band (O(N · B)) and, in the pass that takes the marginals, the step
  costs (O(N · B · K) float32); the beam keeps (candidate, pace, parent) per
  surviving state per unit (O(U · S)).

Measured on this machine (NumPy, one thread; the load of other work on it is
given, because it doubles the times), at 100 values a second unless marked:

| case | words | pieces | envelope | `estimate_pieces` | error of the piece starts | contract |
|---|---|---|---|---|---|---|
| made-up, an hour | 10,000 | 581 | 4,211 s | 3.8 s | 0.002 s (by the text 8.6 s) | ≤ 10 s |
| made-up, four hours | 40,000 | 2,402 | 17,045 s | 15.8 s | 0.004 s (by the text 23.4 s) | ≤ 60 s |
| **real speech, an hour** | 11,896 | 531 | 3,810 s | **6.4 s** | 0.111 s (by the text 92 s) | ≤ 10 s |
| **real speech, four hours** | 45,724 | 2,009 | 14,478 s | **24.8 s** | 0.138 s (by the text 155 s) | ≤ 60 s |
| real speech, four hours at 20 a second | 45,724 | 2,009 | 14,478 s | 23.1 s | 0.157 s | ≤ 60 s |

"Real speech" is the Kokoro bench's TUNE books (§8) laid end to end in all
their languages, with their heard truth; its "words" count every Japanese
and Chinese character as the tokenizer does. The times above were taken
with the machine nearly idle (load 1–8). With other agents loading it to
35–47, the same real hour took 13.8 s and the four hours 61.2 s — over the
contract; at a load of 20, 7.4–8.4 s and about 40 s.

**Memory**: the four real hours peak at 276 MB of allocations inside
`estimate_pieces` (tracemalloc), and the process grows by 145 MB over the
envelope and texts it was handed — well under the contract's 1 GB.

**Where the time goes** in the real hour (idle): the sentence beam 1.5 s,
its backward run for the margins 1.0 s (a beam of 100 states, not 200: it
only has to see the alternatives near the path), the word pass 2.6 s (a
band retry once — see `_solve`), refinement 0.6 s, the perturbed pass
0.5 s, the rest a fifth of a second. The made-up hour: 1.1, 0.7, 0.9, 0.5,
0.4 s.

**Against the aligner as first written**, on the same real speech: an hour
in 13.5 s with a mean error of 519 s, four hours in 59.1 s with 3,165 s —
lost within minutes, because its beam dropped the right paths (§8). The
made-up hour, which it aligned well, took it 3.6–4.2 s.

**The worst envelopes for memory**, as a review found them, and the process's
peak (maxrss; "allocations" where what NumPy and Python allocated was
measured instead, with tracemalloc) before and after its fixes — every one
inside the doors' limits (twelve hours, twenty thousand pieces):

| case | before | after | what fixed it |
|---|---|---|---|
| four hours of short bursts, 40,000 words in 1,800 pieces | 2.5 GB | 443 MB | the first boundary of the sentence beam pruned (§3) |
| the same, a pause every 0.6 s with syllables in the bursts | 4.8 GB | 451 MB | the same |
| three captions over four hours (20 a second) | 2.4 GB (allocations) | 0.4 GB (allocations) | the same |
| two captions over two hours | 356 MB (allocations) | 93 MB (allocations) | pauses budgeted like valleys (§3) |
| 4,000 one-word pieces in a minute | 21 s, 0.9 GB | 0.5 s | more than 20 words a second: the proportional answer |
| a stretch of a billionth of a second | 14 GB (MemoryError) | refused | every window no wider than the grid; `MIN_DURATION` |
| twelve hours of short bursts, 150,000 words in 2,000 pieces | 9.3 GB | 1.3 GB | the first boundary pruned; back-pointers in 32 bits |

The last is over the contract's gigabyte, which is for four hours: the
memory left is linear in the words (the back-pointers of every word's band,
about 9 kB a word on that envelope), and twelve hours is the door's ceiling.
Those pathological four hours still take 90–112 s here (the word pass
widens its band twice); real speech takes 25 s (above). The doors run one
estimate at a time, refuse a second at once rather than queue it, and
answer a `MemoryError` in words (`serve.py`, `ESTIMATE_SLOTS`).

```
python3 lib/wavealign_lab.py bench --quick --long 4
```

---

## 6. What was measured

On made-up recordings (`lib/wavealign_lab.py`): words whose lengths follow
their letters with a log-normal scatter, syllable-like bumps within words,
dips between words of a random depth (and between syllables, sometimes deeper
than between words — a stop inside a word), pauses at commas and sentence
ends and paragraphs with given probabilities and lengths, an occasional
hesitation where the text has no mark, a pace that wanders (an
Ornstein-Uhlenbeck process, ±12 %) or jumps, a noise floor that drifts,
clicks, leading and trailing silence, read as Parseh reads a recording — the
peak (or the RMS) of each bucket of a fine signal, at any rate. The truth is
where each word's sound starts and ends. Words are measured by the absolute
error of every start and end; pieces by the distance of each piece boundary
from the silence between the last word of one piece and the first of the next
(zero anywhere inside it — every point there is a right cut). "by the text"
is `lib/timeline.js` spreadRest to the letter (NFD, the same marks stripped,
whitespace out, UTF-16 length, 0.4 s floor, the last ending at the end); for
words, the same rule with no floor. Three seeds of 120 words each unless the
name says otherwise (the long cases are in §5). "hesitations" pauses 0.6–1.5 s
after 6 % of the plain words; "fast reader" pauses 0.10–0.22 s at sentence
ends and never at a comma; the "bare" cases are captions with their
punctuation and paragraphs taken out, the sound unchanged (an untidied
auto-caption). `python3 lib/wavealign_lab.py bench --quick`:

```

WORDS (seconds; % within)
scenario               mean median    p90  sent.  <50ms   <100   <250
---------------------------------------------------------------------
clean          new    0.070  0.017  0.231  0.006   69.6   77.2   92.4
               text   0.943  0.833  1.870  0.928    3.6    6.4   19.9
no pauses      new    0.188  0.154  0.481  0.142   34.7   42.4   71.0
               text   0.992  1.114  1.861  0.996    4.2    5.8   20.1
noisy          new    0.079  0.020  0.254  0.010   69.4   74.6   90.7
               text   0.943  0.833  1.870  0.928    3.6    6.4   19.9
loose lengths  new    0.479  0.208  1.417  0.267   32.9   40.3   61.7
               text   1.449  1.338  2.763  1.518    1.8    2.9    7.9
rate jump      new    0.088  0.020  0.278  0.041   69.4   76.5   88.9
               text   2.396  2.097  4.514  2.281    0.6    1.3    3.6
20 Hz          new    0.086  0.045  0.219  0.036   56.4   74.4   93.5
               text   0.943  0.833  1.870  0.928    3.6    6.4   19.9
5 Hz           new    0.172  0.141  0.356  0.161   17.9   36.5   78.3
               text   0.943  0.833  1.870  0.928    3.6    6.4   19.9
rms            new    0.070  0.017  0.238  0.009   68.5   76.7   92.1
               text   0.943  0.833  1.870  0.928    3.6    6.4   19.9
persian        new    0.076  0.015  0.232  0.005   67.6   75.8   91.4
               text   1.056  1.070  1.900  1.060    4.6    8.2   19.3
chinese        new    0.175  0.018  0.390  0.130   61.1   67.2   85.6
               text   1.560  1.295  3.031  1.584    0.9    2.6    6.4
captions       new    0.070  0.017  0.231  0.006   69.6   77.2   92.4
               text   0.943  0.833  1.870  0.928    3.6    6.4   19.9
hesitations    new    0.125  0.021  0.324  0.076   62.8   69.9   85.7
               text   1.150  0.900  2.446  1.084    2.6    4.4   12.8
fast reader    new    0.177  0.098  0.482  0.141   43.8   51.4   74.0
               text   1.029  0.969  2.006  1.041    2.6    4.7   13.6
bare en        new    1.489  0.858  4.064  1.583   23.8   26.3   33.7
               text   2.100  1.695  4.346  2.068    1.5    2.9    6.2
bare zh        new    2.002  1.976  3.619  2.083    5.2    5.7    8.2
               text   1.569  1.406  3.162  1.633    2.1    3.2    9.2
bare fa        new    1.205  0.913  2.803  1.325   13.9   15.6   21.3
               text   2.395  2.325  4.535  2.455    1.9    3.4   10.6
bare en 1000   new    2.116  1.698  4.692  2.181   12.8   14.0   18.7
               text   2.536  1.938  5.505  2.541    1.7    3.3    8.3
bare zh 1000   new    1.899  1.685  3.887  2.022    5.5    6.0    9.1
               text   3.133  3.002  6.127  3.120    0.9    1.9    4.7
bare fa 1000   new    1.604  1.161  3.831  1.758   17.7   19.8   26.9
               text   3.554  3.362  6.665  3.583    1.3    2.7    6.6

PIECES (distance from the true silence between pieces)
scenario               mean median    p90  sent.  <50ms   <100   <250
---------------------------------------------------------------------
clean          new    0.000  0.000  0.000  0.000  100.0  100.0  100.0
               text   0.472  0.403  0.942  0.472   39.4   39.4   51.7
no pauses      new    0.077  0.000  0.255  0.077   80.9   80.9   80.9
               text   0.746  0.586  1.452  0.746   23.3   28.8   38.1
noisy          new    0.000  0.000  0.000  0.000  100.0  100.0  100.0
               text   0.534  0.360  1.081  0.534   27.8   27.8   43.7
loose lengths  new    0.142  0.000  0.562  0.142   92.5   92.5   92.5
               text   1.070  0.940  2.187  1.070   17.3   17.3   26.2
rate jump      new    0.020  0.000  0.000  0.020   97.0   97.0   97.0
               text   1.962  1.675  3.878  1.962    0.0    0.0    0.0
20 Hz          new    0.000  0.000  0.000  0.000  100.0  100.0  100.0
               text   0.472  0.403  0.942  0.472   39.4   39.4   51.7
5 Hz           new    0.003  0.000  0.003  0.003   96.7  100.0  100.0
               text   0.472  0.403  0.942  0.472   39.4   39.4   51.7
rms            new    0.000  0.000  0.000  0.000  100.0  100.0  100.0
               text   0.472  0.403  0.942  0.472   39.4   39.4   51.7
persian        new    0.000  0.000  0.000  0.000  100.0  100.0  100.0
               text   0.608  0.531  1.292  0.608   40.0   40.0   48.9
chinese        new    0.088  0.000  0.000  0.088   97.0   97.0   97.0
               text   1.188  1.028  2.503  1.188   17.7   20.5   23.2
captions       new    0.071  0.014  0.235  0.000   70.1   78.2   91.7
               text   0.966  0.794  1.868  0.439    5.3    7.9   21.6
hesitations    new    0.000  0.000  0.000  0.000  100.0  100.0  100.0
               text   0.595  0.184  1.421  0.595   35.7   35.7   42.4
fast reader    new    0.035  0.000  0.101  0.035   84.9   84.9   95.8
               text   0.660  0.585  1.300  0.660   17.0   20.7   33.7
bare en        new    1.508  0.795  3.963  0.822   22.3   23.3   31.2
               text   2.059  1.624  4.364  1.436    1.8    2.9    6.7
bare zh        new    2.043  2.088  3.537  2.037    6.9    7.8    7.8
               text   1.560  1.352  3.109  1.305    1.0    2.0    9.6
bare fa        new    1.263  0.959  2.930  1.335   11.6   12.5   19.0
               text   2.367  2.388  4.379  2.591    1.9    1.9    8.4
bare en 1000   new    2.087  1.670  4.716  1.582   12.1   13.5   17.7
               text   2.486  1.863  5.426  1.782    3.9    5.3    8.7
bare zh 1000   new    1.862  1.628  3.966  1.352    5.6    5.8    7.5
               text   3.115  2.908  6.119  2.754    1.7    1.7    4.7
bare fa 1000   new    1.549  1.052  3.811  1.752   18.6   20.3   27.4
               text   3.498  3.403  6.552  3.631    1.7    4.0    6.5
```

Every 120-word case aligns in about a tenth of a second, the Chinese one
(260 characters) in a fifth. Against the first version of these tables (the
algorithm as first written, before the real-speech bench): the words are as
good or better everywhere but in "no pauses" (0.158 → 0.188 s) and
"chinese" (0.136 → 0.175 s), and the pieces better or equal everywhere but
in "no pauses" (0.058 → 0.077 s) and "chinese" (0 → 0.088 s: one seed of
three, where the path through a mis-placed sentence is cheaper than the
truth by a nat — a near tie in a made-up case with few pauses). "loose
lengths" gained the most (pieces 0.515 → 0.142 s), then "captions" (0.118
→ 0.071 s) and "20 Hz" (0.023 → 0). The review's cap on the length of a
pause after a plain word (§2) cost "rate jump" one boundary of one seed
(words 0.068 → 0.088 s, pieces 0 → 0.020 s) and changed nothing else here.

**These are made-up recordings.** Real speech is harder in ways a generator
only imitates — coarticulation, breaths, a reader's own habits, room noise.
§8 is the measure on real speech, and it is the one the defaults were set
on. The owner's own recordings are **not** a benchmark: none of their cuts
is trustworthy.

**Where it is weak** (made-up sound). A transcript whose word lengths
poorly follow their letters ("loose lengths"): inside continuous speech the
text is then a poor guide and the envelope rarely a better one. A reader who
seldom pauses ("no pauses"): the sentence level has little to hold on to.
**A text nobody punctuated** ("bare"): with no sentence to pin, only the
words' lengths and the pauses are left, and a long stretch drifts — 1.2–2.1 s
of piece error. That is better than by the text in English and Persian at
300 words and in all three at 1,000, but still worse in 300 characters of
Chinese (2.0 s against 1.6), where a character is a poor measure of time.
Before the review it was 1.5–6 times worse than by the text everywhere,
growing with the length (the sentence level built from made-up units, a
plain word's long pause charged in full, a caption's end taken for a likely
pause). Tidying such captions first gives them their full stops, and then
they are the "captions" case. **A reader who hesitates for breath** after
plain words, a second at a time, longer than the sentence pauses: with six
such pauses in a hundred words (ten seeds each of 80 to 400 words) the
pieces are off by 0.2–2.4 s by the sound against 0.8–3.0 by the text — the
long pauses are where the sentence ends look likeliest. And the **fast reader** of §3's calibration.
And near ties: where the envelope shows few pauses, two segmentations can
differ by a nat or less, and which one wins turns on the rate model's
numbers — the sensitivity table below shows cliffs of that kind on these
made-up cases (none of them on real speech, §8). The integration test
`WithTheRealAligner.test_a_book_by_the_real_aligner` (six words, a second
of silence, four words) was reported to put the silence after the comma;
simulated here (tone to 1 s, silence to 2 s, tone to 3 s, the stretch from
0.25 to 3.5 s) both the first and the present defaults put the boundary in
the silence (1.11 / 1.89 s). That test itself belongs to the integration
and was not run here.

---

## 7. Which parameters matter

Each parameter at a lower and a higher value, everything else at its
default, over six made-up scenarios (clean, no pauses, noisy, 20 Hz, rate
jump, loose lengths), three seeds each; the mean word error and the mean piece
error, and their change from the defaults
(`python3 lib/wavealign_lab.py sensitivity --seeds 3`):

| parameter | default | value | words (s) | pieces (s) | Δ words | Δ pieces |
|---|---|---|---|---|---|---|
| (all defaults) | | | 0.165 | 0.040 | | |
| `w_pause` | 1.0 | 0.5 | 0.228 | 0.107 | +0.063 | +0.067 |
| `w_pause` | 1.0 | 2.0 | 0.169 | 0.041 | +0.004 | +0.001 |
| `w_anchor` | 1.0 | 0.5 | 0.164 | 0.040 | -0.001 | +0.000 |
| `w_anchor` | 1.0 | 2.0 | 0.186 | 0.072 | +0.020 | +0.032 |
| `w_boundary` | 1.0 | 0.5 | 0.166 | 0.041 | +0.001 | +0.001 |
| `w_boundary` | 1.0 | 2.0 | 0.168 | 0.041 | +0.003 | +0.001 |
| `w_activity` | 2.0 | 1.0 | 0.166 | 0.040 | +0.001 | +0.000 |
| `w_activity` | 2.0 | 4.0 | 0.160 | 0.040 | -0.005 | +0.000 |
| `w_duration` | 1.0 | 0.5 | 0.164 | 0.040 | -0.001 | +0.000 |
| `w_duration` | 1.0 | 2.0 | 0.166 | 0.040 | +0.001 | +0.000 |
| `w_rate` | 1.0 | 0.5 | 0.161 | 0.039 | -0.004 | -0.001 |
| `w_rate` | 1.0 | 2.0 | 0.166 | 0.041 | +0.001 | +0.001 |
| `w_rate_step` | 1.0 | 0.5 | 0.183 | 0.108 | +0.018 | +0.068 |
| `w_rate_step` | 1.0 | 2.0 | 0.244 | 0.113 | +0.079 | +0.073 |
| `w_unassigned` | 1.5 | 0.75 | 0.165 | 0.040 | +0.000 | +0.000 |
| `w_unassigned` | 1.5 | 3.0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `sigma_duration` | 0.45 | 0.3 | 0.167 | 0.041 | +0.002 | +0.001 |
| `sigma_duration` | 0.45 | 0.7 | 0.164 | 0.040 | -0.001 | +0.000 |
| `sigma_rate` | 0.35 | 0.25 | 0.211 | 0.104 | +0.046 | +0.064 |
| `sigma_rate` | 0.35 | 0.5 | 0.383 | 0.229 | +0.218 | +0.189 |
| `alpha` | 0.8 | 0.6 | 0.216 | 0.104 | +0.051 | +0.064 |
| `alpha` | 0.8 | 1.0 | 0.164 | 0.036 | -0.001 | -0.004 |
| `pause_prob_word` | 0.04 | 0.02 | 0.165 | 0.040 | +0.000 | +0.000 |
| `pause_prob_word` | 0.04 | 0.08 | 0.164 | 0.040 | -0.001 | +0.000 |
| `anchor_full_s` | 0.3 | 0.2 | 0.180 | 0.070 | +0.015 | +0.030 |
| `anchor_full_s` | 0.3 | 0.45 | 0.154 | 0.033 | -0.011 | -0.007 |
| `calibrate_pauses` | True | False | 0.160 | 0.038 | -0.006 | -0.002 |
| `rate_state` | True | False | 0.397 | 0.264 | +0.232 | +0.224 |
| `low_frac` | 0.3 | 0.2 | 0.168 | 0.043 | +0.003 | +0.003 |
| `low_frac` | 0.3 | 0.4 | 0.167 | 0.040 | +0.002 | +0.000 |
| `high_frac` | 0.5 | 0.4 | 0.163 | 0.040 | -0.002 | +0.000 |
| `high_frac` | 0.5 | 0.65 | 0.166 | 0.042 | +0.001 | +0.002 |
| `min_pause_s` | 0.06 | 0.04 | 0.166 | 0.042 | +0.001 | +0.002 |
| `min_pause_s` | 0.06 | 0.12 | 0.165 | 0.040 | +0.000 | +0.001 |
| `smooth_s` | 0.02 | 0.01 | 0.173 | 0.048 | +0.008 | +0.008 |
| `smooth_s` | 0.02 | 0.04 | 0.170 | 0.040 | +0.005 | +0.000 |
| `refine_passes` | 1 | 3 | 0.165 | 0.040 | +0.000 | +0.000 |
| `rate_beam` | 8.0 | 5.0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `rate_beam` | 8.0 | 12.0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `rate_latent` | True | False | 0.208 | 0.102 | +0.043 | +0.062 |
| `rate_jump_nats` | 3.0 | 1.5 | 0.209 | 0.102 | +0.044 | +0.062 |
| `rate_jump_nats` | 3.0 | 6.0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `rate_unit_sigma` | 0.1 | 0.08 | 0.166 | 0.042 | +0.001 | +0.002 |
| `rate_unit_sigma` | 0.1 | 0.15 | 0.426 | 0.291 | +0.261 | +0.251 |
| `dip_rank` | 2.0 | 0.0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `dip_rank` | 2.0 | 4.0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `calibrate_mode` | split | scale | 0.167 | 0.040 | +0.002 | +0.000 |
| `rate_per_candidate` | 3 | 0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `rate_per_candidate` | 3 | 8 | 0.165 | 0.040 | +0.000 | +0.000 |
| `rate_beam_window_s` | 2.0 | one beam | 0.165 | 0.040 | +0.000 | +0.000 |
| `rate_beam_window_s` | 2.0 | 1.0 | 0.165 | 0.040 | +0.000 | +0.000 |
| `pause_length_cap` | 1.5 | 0.75 | 0.165 | 0.040 | +0.000 | +0.000 |
| `pause_length_cap` | 1.5 | inf | 0.162 | 0.037 | -0.003 | -0.003 |

What it says, largest first:

- **The pace in the sentence level's state (`rate_state`) matters most**:
  without it (a sentence level with a global rate only) the word error more
  than doubles, and the pieces lose 0.22 s. Keeping each unit's scatter out
  of the pace (`rate_latent`) is next (words +0.04 s, pieces +0.06 s
  without it), then the price of a jump (`rate_jump_nats` at 1.5: jumps
  come too cheap, and the pace chases the scatter).
- **Cliffs.** Three numbers of the pace model have a cliff on this made-up
  sound: the spread of a unit's own scatter (`rate_unit_sigma` 0.15: +0.26
  s), the words' spread against the local rate (`sigma_rate` 0.5: +0.22 s)
  and the weight of the pace's steps (`w_rate_step`). Each cliff is one or
  two of the eighteen cases (a "rate jump" or a "no pauses" seed) tipping
  from one segmentation to another that differs from it by a nat or less.
  On real speech the same changes move the mean by less than a hundredth
  of a second (§8), which is why the defaults were not pushed further on
  the strength of these.
- **The pause terms (`w_pause`, `w_anchor`, `anchor_full_s`)**: halving the
  pause prior's weight costs 0.06–0.07 s of words and of pieces; doubling
  the anchor weight 0.02–0.03 s, doubling the pause weight next to nothing.
  The length at which a pause counts in full trades a little both ways.
- **The cap on a plain word's pause length (`pause_length_cap`)** moves
  these six readers by 0.003 s at most — uncapped is that much better, the
  one "rate jump" seed of §6 — because none of them hesitates for long. It
  is there for the reader who does (§6: up to 0.17 s of piece error), and
  it costs real speech 0.0007 s (§8).
- **The duration prior's exponent (`alpha`)** at 0.6 costs 0.05 s here; on
  real speech (§8) it is flat.
- **Hardly anything else moves**: the activity, global-duration and
  unassigned-sound weights, the duration spread, the thresholds, the
  smoothing, the beam's width, its locality and its share per candidate
  (made-up recordings are short: the beam never fills), the dip length
  (there is no bed of music here), the form of the calibration, the number
  of refinement passes (so the default is one). (Measured again after the
  review's fixes: the defaults moved 0.162 → 0.165 s of words and 0.037 →
  0.040 of pieces, all of it the one "rate jump" seed; no other row moved by
  more than 0.04 s, and the two that moved most, `w_pause` 2.0 and `w_rate`
  0.5, were +0.03 and are now harmless.)

---

## 8. Real speech: the Kokoro bench

§6 and §7 are made-up sound. The defaults were set on real speech with
known timing, and this is the measure that counts.

**What the truth was.** Speech rendered by **Kokoro** (an open
text-to-speech model the owner trusts; espeak-ng, trusted much less, was
never used to tune) from 44 original texts written for the purpose —
stories, dialogue, letters, lists, numbers written out, and every kind of
punctuation each language uses (`、。！？「」`, `，。：；`, `।`, `«» ¿ ¡ —`)
— in **seven languages: English, Spanish, French, Italian, Hindi, Japanese
and Chinese**, and a little Brazilian Portuguese (marked `pt*`, counted in
its own rows only). 40 recordings, 185 minutes, 23 voices — without the
Portuguese, 36 recordings, 182 minutes, 21 voices. Each text is cut
two ways: as a book's pieces (one to four whole sentences, `span`) and as
captions (5–14 words, or 8–25 characters in Japanese and Chinese, cut in
mid-sentence too, `point`). Each piece's true start and end are Kokoro's
own durations, **corrected at every pause from the clean sound itself** to
the millisecond (Kokoro spends a pause partly inside the phoneme before it,
so its durations put a piece's end 0.1–0.7 s after the sound stops; inside
continuous speech its durations stand). The pace changes (0.80–1.25 ×, with
177 abrupt changes at paragraph breaks), silences of known length separate
paragraphs and texts, each recording has its own loudness, and every one is
heard **five ways**: clean, room noise at 25 dB and at 12 dB signal-to-noise,
a slow drift of loudness, and a soft bed of music. The envelopes are
Parseh's own: `audiofile.envelope` at 100 a second, as a book's door makes
it, and the 20-a-second picture a YouTube video records, sliced as
`serve.py` slices it.

**What it cannot tell.** A synthesizer does not hesitate, lose its place,
breathe audibly, cough, turn a page, laugh, or read in a room with a door
and a dog; its pauses are regular; its pace changes only where it was told
to; and its "speaker" reads every text as written. A human narrator does
all of that — and none of it is in this bench. Nor are Persian, Arabic,
German or Turkish (Kokoro has no voice for them; they are covered only by
the made-up sound of §6). So these numbers are what to expect from a clean,
fluent reader; a human one, in a real room, will be worse, by an amount no
one has measured yet — `wavealign_lab.py bench-audio` (§9) is there for
whoever has a recording whose cuts they trust.

**The scenario is the user's.** The boundaries are right up to a line; the
user presses E. So every stretch starts at a piece's true start and runs
over M = 3, 10, 30 or 100 pieces or all the rest, to the true end of the
last; the estimator is handed the texts, the stretch's length and its
envelope; each answer is rounded to a hundredth as the page and the door
round it. Measured: the error of every piece start but the first (the line
in hand). **gap** counts a start anywhere inside the pause before its piece
as right — where a hand would cut. Two things to know when reading: after a
pause, the contract puts a start `pad` (0.1 s) before the sound, so about
0.1 s is the floor of *mean* for those starts while *gap* shows 0; and by
the text never hears, so its numbers are the same in every condition and
rate. "sound wins" is the share of stretches whose mean error by the sound
is below by the text's.

**The split.** TUNE is the first voice of each language reading texts 1, 3
and 5 (and 7 in English); HOLDOUT the other voices (one to four a language)
reading texts 2, 4 and 6 (and 8 in English); Portuguese 1 against 2. French
has one voice, so its halves differ by text only. Everything
was tuned on TUNE, and HOLDOUT was only ever run to report (`sha256` of
`lib/wavealign.py` recorded with each result): once on the code before the
review below — through the bench's evaluator, and once more on the
identical code only to split the same numbers by rate, which came out the
same to the last digit — and once on the **final code, on 2026-09-24**,
after which no parameter was changed. The HOLDOUT tables below are that
final run's.

### What was wrong, and why

Each fault was found the same way: for a stretch that went wrong, the cost
of the path the aligner chose was set against the cost of a path forced
through the truth. A chosen path cheaper than the truth is the model's
fault; a truth cheaper than the path found is the search's. In the order
they were found, with the mean start error on TUNE (all 7,050 evaluations
unless marked):

| | mean | |
|---|---|---|
| the aligner as first written | 4.31 s | median 0.15 s, but p90 15.7 s: whole stretches lost |
| **1. the beam, local in time** | 1.44 s (clean + music) | a search failure: a path reading the text too fast looks cheap until the end and pushed the right paths out of a global beam — stretches 20–45 s early, the last 40 s of sound left to nobody (§3) |
| **2. the dip length** | 0.26 s (clean + music); 0.28 s (all) | under music the dips between syllables became hundreds of "pauses"; the global rate came out 29 % fast (§3) |
| 3. the reader's pause habits by length (`split`) | 0.28 s (0.28 before) | one factor for every prior had brought a sentence end's prior to ~0.5, where a pause there and none cost the same; the split fit keeps it where the reader keeps it. It did not move real speech; it kept the made-up reader who hardly pauses right (§3), until step 5 made the calibration matter little either way (below) |
| **4. no length limit after a sentence end** | 0.22 s | paragraph gaps of 1–2.5 s were charged as too long for a sentence end, so sentence ends went looking for shorter pauses elsewhere (§2) |
| **5. the pace, not the unit's rate, in the state** | 0.15 s | with each sentence's scatter taken for a step of the pace, the pace was a random walk and a stretch read a third too fast then a third too slow cost nothing (§3) |
| 6. the spreads set where made-up and real speech agree, the beam made faster | **0.149 s** | `rate_unit_sigma` 0.12 → 0.10 and `rate_drift` 0.04 → 0.08 (§7's cliffs moved away from the defaults; real speech unchanged within 0.005 s), 200 states instead of 400, the unit cost shared across paces, the pace step in closed form |
| 7. the review's fixes (below) | **0.150 s** | 0.1492 → 0.1499: the cap on a plain word's pause length; everything else a guard real speech never reaches |

### What a review changed

A review of the finished aligner — made-up cases built to break it, a fuzzer,
and a second look at every claim here — found faults Kokoro could not show,
because it never reaches them: a text with no punctuation at all, a reader
who hesitates, an envelope with nothing in it, stretches at the doors'
limits. What was done, and what it cost on TUNE (all 7,050 evaluations,
the mean start error before → after, `evaluate.py --set tune --estimator
sound`):

- **A plain word's long pause capped** at 1.5 nats (`pause_length_cap`, §2):
  the one change that moves real speech, and by little — everything 0.1492 →
  0.1499 s, books 0.1291 → 0.1299, captions 0.1603 → 0.1608; Italian 0.155
  → 0.160 and French 0.174 → 0.176 pay for it, English and Spanish gain a
  little. On made-up readers who hesitate a second at a time it is worth up
  to 0.17 s of piece error (§6); removing the length term altogether instead
  cost Kokoro 0.006 s.
- **A text nobody punctuated** (§2, §3): no sentence level, a plain word's
  pause unlimited, a caption's end no likelier a pause than a word's — no
  Kokoro stretch is bare, and only the five of its 705 stretches with no
  sentence end in them (three captions each) lost their sentence level: M = 3
  moved 0.1349 → 0.1350 s.
- **No evidence, no DP** (§3): the proportional answer, where the beam had
  been worse than it (Kokoro always has evidence).
- **Guards at the limits**: fewer candidates than boundaries (an
  `IndexError` before), a wider band that loses the beam, over 20 words a
  second, the first beam boundary pruned, pauses budgeted like valleys, a
  microsecond's floor, every window no wider than the grid, numbers too big
  for a float, a broken tokenizer, two ends a hair past the stretch. The
  review ran the full bench with the pruning alone: unchanged to every
  printed digit.
- **The confidence**: a factor it could not measure counts as a half (§3),
  and its stability test shakes whichever duration prior is in force.
- **The fast reader** (§3) was measured and left: the cures were worse.

### The result

TUNE (7,050 evaluations — 705 stretches × 5 conditions × 2 rates; seconds):

| group | starts | text mean | sound mean | median | p90 | ≤0.25 s | ≤0.5 s | ≤1 s | gap | sound wins |
|---|---|---|---|---|---|---|---|---|---|---|
| **everything** | 131400 | 2.408 | **0.149** | 0.108 | 0.248 | 90.2 % | 97.0 % | 98.9 % | 0.057 | 97.5 % |
| en | 32200 | 2.953 | **0.143** | 0.107 | 0.258 | 89.6 % | 97.3 % | 99.5 % | 0.061 | 99.8 % |
| es | 18020 | 1.428 | **0.119** | 0.106 | 0.184 | 94.8 % | 98.9 % | 99.7 % | 0.034 | 94.9 % |
| fr | 16940 | 2.243 | **0.174** | 0.115 | 0.304 | 86.3 % | 95.3 % | 98.2 % | 0.068 | 98.6 % |
| hi | 17500 | 3.346 | **0.119** | 0.107 | 0.156 | 96.2 % | 99.5 % | 99.7 % | 0.021 | 98.9 % |
| it | 14780 | 1.886 | **0.155** | 0.104 | 0.266 | 89.2 % | 97.0 % | 97.9 % | 0.065 | 95.6 % |
| ja | 16300 | 1.606 | **0.151** | 0.111 | 0.318 | 85.0 % | 96.6 % | 99.7 % | 0.071 | 96.9 % |
| pt* | 2100 | 0.316 | **0.106** | 0.091 | 0.204 | 93.8 % | 100.0 % | 100.0 % | 0.049 | 90.0 % |
| zh | 15660 | 2.870 | **0.197** | 0.107 | 0.256 | 89.8 % | 93.4 % | 96.5 % | 0.076 | 97.3 % |
| M = 3 | 3360 | 0.557 | **0.135** | 0.107 | 0.228 | 91.7 % | 97.9 % | 99.5 % | 0.043 | 91.4 % |
| M = 10 | 15120 | 1.197 | **0.144** | 0.108 | 0.224 | 92.0 % | 97.5 % | 99.0 % | 0.047 | 99.2 % |
| M = 30 | 43790 | 2.346 | **0.150** | 0.109 | 0.232 | 91.3 % | 97.2 % | 98.7 % | 0.049 | 100.0 % |
| M = 100 | 11880 | 3.864 | **0.145** | 0.107 | 0.304 | 86.6 % | 96.8 % | 99.8 % | 0.078 | 100.0 % |
| M = all | 57250 | 2.581 | **0.152** | 0.108 | 0.259 | 89.6 % | 96.7 % | 98.8 % | 0.061 | 99.5 % |
| point | 84980 | 2.281 | **0.160** | 0.107 | 0.309 | 86.5 % | 95.8 % | 98.7 % | 0.081 | 97.0 % |
| span | 46420 | 2.640 | **0.129** | 0.110 | 0.158 | 96.9 % | 99.0 % | 99.2 % | 0.012 | 98.1 % |
| clean | 26280 | 2.408 | **0.160** | 0.112 | 0.246 | 90.1 % | 96.5 % | 98.5 % | 0.060 | 97.5 % |
| room25 | 26280 | 2.408 | **0.147** | 0.107 | 0.238 | 91.0 % | 97.4 % | 99.0 % | 0.054 | 97.4 % |
| room12 | 26280 | 2.408 | **0.146** | 0.103 | 0.272 | 88.6 % | 96.5 % | 99.0 % | 0.060 | 97.0 % |
| drift | 26280 | 2.408 | **0.155** | 0.111 | 0.235 | 90.6 % | 96.9 % | 98.7 % | 0.056 | 97.8 % |
| music | 26280 | 2.408 | **0.139** | 0.105 | 0.242 | 90.6 % | 97.5 % | 99.2 % | 0.053 | 97.8 % |
| 100 Hz | 65700 | 2.408 | **0.138** | 0.101 | 0.240 | 90.5 % | 97.1 % | 99.0 % | 0.055 | 97.7 % |
| 20 Hz | 65700 | 2.408 | **0.161** | 0.126 | 0.253 | 89.8 % | 96.9 % | 98.8 % | 0.058 | 97.3 % |

After the review's fixes, TUNE's rows here moved by less than a hundredth
of a second (most: Italian captions 0.160 → 0.167, French books 0.137 →
0.141; English and Spanish captions gained 0.001; everything 0.149 → 0.150,
p90 0.248 → 0.248, within 0.25 s 90.2 → 90.1 %). HOLDOUT below is the
FINAL code's: run once on 2026-09-24, after the review's fixes, on
`lib/wavealign.py` as it stands (`sha256` 56c93777…), and nothing was tuned
after it. The run before the review had everything at 0.151 s, and no row
of the two differs by more than 0.005 s (Japanese 0.192 → 0.196, Japanese
books 0.176 → 0.181, room noise at 12 dB 0.200 → 0.202).

HOLDOUT, the final code, 2026-09-24 (10,510 evaluations — 1,051 stretches
× 5 × 2):

| group | starts | text mean | sound mean | median | p90 | ≤0.25 s | ≤0.5 s | ≤1 s | gap | sound wins |
|---|---|---|---|---|---|---|---|---|---|---|
| **everything** | 205220 | 1.697 | **0.152** | 0.105 | 0.284 | 87.8 % | 97.0 % | 99.3 % | 0.078 | 96.9 % |
| en | 90150 | 2.109 | **0.131** | 0.103 | 0.259 | 89.4 % | 97.7 % | 99.9 % | 0.066 | 99.1 % |
| es | 14730 | 1.256 | **0.128** | 0.104 | 0.258 | 89.6 % | 98.9 % | 100.0 % | 0.060 | 97.6 % |
| fr | 12460 | 1.347 | **0.170** | 0.114 | 0.365 | 80.7 % | 95.7 % | 99.4 % | 0.105 | 95.2 % |
| hi | 24190 | 1.348 | **0.120** | 0.103 | 0.215 | 92.9 % | 99.3 % | 99.9 % | 0.034 | 98.4 % |
| it | 11660 | 1.653 | **0.133** | 0.106 | 0.257 | 89.6 % | 98.1 % | 99.9 % | 0.074 | 97.4 % |
| ja | 27160 | 1.538 | **0.196** | 0.113 | 0.369 | 79.2 % | 93.9 % | 98.7 % | 0.107 | 93.2 % |
| pt* | 2120 | 0.676 | **0.167** | 0.097 | 0.237 | 90.2 % | 93.8 % | 96.5 % | 0.070 | 91.8 % |
| zh | 24870 | 1.172 | **0.221** | 0.099 | 0.284 | 88.3 % | 94.3 % | 96.1 % | 0.132 | 95.1 % |
| M = 3 | 5280 | 0.544 | **0.129** | 0.105 | 0.224 | 91.7 % | 98.7 % | 99.8 % | 0.044 | 90.0 % |
| M = 10 | 23760 | 1.025 | **0.144** | 0.105 | 0.242 | 90.4 % | 97.6 % | 99.3 % | 0.055 | 99.3 % |
| M = 30 | 51620 | 1.315 | **0.157** | 0.106 | 0.290 | 87.2 % | 96.8 % | 99.1 % | 0.082 | 99.2 % |
| M = 100 | 35640 | 2.167 | **0.133** | 0.101 | 0.283 | 88.1 % | 97.4 % | 99.9 % | 0.079 | 100.0 % |
| M = all | 88920 | 1.978 | **0.159** | 0.106 | 0.294 | 87.2 % | 96.6 % | 99.1 % | 0.084 | 99.4 % |
| point | 162090 | 1.650 | **0.153** | 0.104 | 0.313 | 85.7 % | 96.5 % | 99.3 % | 0.092 | 95.8 % |
| span | 43130 | 1.873 | **0.146** | 0.107 | 0.180 | 95.7 % | 98.8 % | 99.0 % | 0.027 | 98.6 % |
| clean | 41044 | 1.697 | **0.138** | 0.108 | 0.253 | 89.8 % | 97.9 % | 99.6 % | 0.064 | 97.8 % |
| room25 | 41044 | 1.697 | **0.138** | 0.103 | 0.276 | 88.4 % | 97.5 % | 99.6 % | 0.067 | 97.1 % |
| room12 | 41044 | 1.697 | **0.202** | 0.104 | 0.353 | 84.0 % | 94.2 % | 98.0 % | 0.123 | 95.2 % |
| drift | 41044 | 1.697 | **0.137** | 0.107 | 0.252 | 89.8 % | 98.1 % | 99.6 % | 0.064 | 97.7 % |
| music | 41044 | 1.697 | **0.143** | 0.102 | 0.294 | 87.3 % | 97.1 % | 99.6 % | 0.073 | 96.6 % |
| 100 Hz | 102610 | 1.697 | **0.151** | 0.098 | 0.277 | 88.2 % | 96.7 % | 99.2 % | 0.083 | 96.8 % |
| 20 Hz | 102610 | 1.697 | **0.153** | 0.118 | 0.288 | 87.5 % | 97.3 % | 99.3 % | 0.073 | 97.0 % |

By language and kind (TUNE, then HOLDOUT on the final code):

| group | starts | text mean | sound mean | median | p90 | ≤0.25 s | ≤0.5 s | ≤1 s | gap | sound wins |
|---|---|---|---|---|---|---|---|---|---|---|
| en point | 24870 | 3.307 | **0.143** | 0.106 | 0.294 | 87.3 % | 96.9 % | 99.8 % | 0.076 | 99.8 % |
| en span | 7330 | 1.753 | **0.143** | 0.110 | 0.154 | 97.3 % | 98.6 % | 98.7 % | 0.010 | 99.8 % |
| es point | 10440 | 1.301 | **0.122** | 0.102 | 0.206 | 93.2 % | 98.2 % | 99.6 % | 0.057 | 95.4 % |
| es span | 7580 | 1.602 | **0.116** | 0.109 | 0.161 | 96.9 % | 99.8 % | 99.8 % | 0.003 | 94.4 % |
| fr point | 9200 | 1.719 | **0.205** | 0.111 | 0.389 | 77.9 % | 92.4 % | 97.2 % | 0.115 | 97.3 % |
| fr span | 7740 | 2.867 | **0.137** | 0.118 | 0.172 | 96.4 % | 98.8 % | 99.3 % | 0.011 | 100.0 % |
| hi point | 9960 | 2.395 | **0.119** | 0.101 | 0.195 | 93.7 % | 99.3 % | 99.6 % | 0.033 | 98.1 % |
| hi span | 7540 | 4.603 | **0.118** | 0.111 | 0.148 | 99.5 % | 99.8 % | 99.8 % | 0.005 | 99.6 % |
| it point | 10090 | 1.729 | **0.160** | 0.103 | 0.274 | 87.9 % | 96.4 % | 97.4 % | 0.081 | 95.4 % |
| it span | 4690 | 2.223 | **0.145** | 0.105 | 0.188 | 92.0 % | 98.2 % | 98.9 % | 0.032 | 95.9 % |
| ja point | 11200 | 1.705 | **0.176** | 0.123 | 0.386 | 79.1 % | 95.1 % | 99.6 % | 0.103 | 96.7 % |
| ja span | 5100 | 1.388 | **0.097** | 0.099 | 0.144 | 98.2 % | 99.9 % | 99.9 % | 0.003 | 97.1 % |
| pt* point | 1940 | 0.301 | **0.105** | 0.086 | 0.221 | 93.3 % | 99.9 % | 100.0 % | 0.053 | 91.0 % |
| pt* span | 160 | 0.498 | **0.114** | 0.114 | 0.144 | 100.0 % | 100.0 % | 100.0 % | 0.003 | 85.7 % |
| zh point | 9220 | 2.365 | **0.233** | 0.105 | 0.487 | 85.2 % | 90.4 % | 95.4 % | 0.110 | 95.2 % |
| zh span | 6440 | 3.593 | **0.147** | 0.109 | 0.164 | 96.3 % | 97.8 % | 98.0 % | 0.027 | 99.6 % |

| group | starts | text mean | sound mean | median | p90 | ≤0.25 s | ≤0.5 s | ≤1 s | gap | sound wins |
|---|---|---|---|---|---|---|---|---|---|---|
| en point | 74640 | 2.091 | **0.133** | 0.101 | 0.284 | 88.0 % | 97.2 % | 99.9 % | 0.079 | 99.2 % |
| en span | 15510 | 2.196 | **0.120** | 0.110 | 0.190 | 96.5 % | 100.0 % | 100.0 % | 0.005 | 98.9 % |
| es point | 11660 | 1.274 | **0.131** | 0.104 | 0.269 | 88.3 % | 98.6 % | 100.0 % | 0.074 | 96.9 % |
| es span | 3070 | 1.186 | **0.118** | 0.103 | 0.157 | 94.2 % | 100.0 % | 100.0 % | 0.006 | 98.6 % |
| fr point | 9670 | 1.262 | **0.177** | 0.111 | 0.395 | 76.6 % | 95.2 % | 99.5 % | 0.126 | 93.8 % |
| fr span | 2790 | 1.641 | **0.147** | 0.120 | 0.173 | 95.2 % | 97.4 % | 99.1 % | 0.034 | 97.2 % |
| hi point | 18470 | 1.144 | **0.119** | 0.096 | 0.225 | 91.6 % | 99.1 % | 99.9 % | 0.045 | 97.2 % |
| hi span | 5720 | 2.006 | **0.125** | 0.114 | 0.192 | 97.0 % | 100.0 % | 100.0 % | 0.000 | 100.0 % |
| it point | 8920 | 1.659 | **0.138** | 0.107 | 0.274 | 87.7 % | 97.5 % | 99.9 % | 0.096 | 95.6 % |
| it span | 2740 | 1.633 | **0.117** | 0.103 | 0.199 | 95.8 % | 100.0 % | 100.0 % | 0.001 | 99.7 % |
| ja point | 20500 | 1.444 | **0.201** | 0.131 | 0.392 | 74.1 % | 93.2 % | 99.3 % | 0.121 | 91.6 % |
| ja span | 6660 | 1.827 | **0.181** | 0.102 | 0.144 | 94.7 % | 96.3 % | 97.0 % | 0.065 | 96.7 % |
| pt* point | 1620 | 0.777 | **0.162** | 0.085 | 0.362 | 89.1 % | 93.8 % | 96.7 % | 0.076 | 97.3 % |
| pt* span | 500 | 0.351 | **0.182** | 0.113 | 0.216 | 93.8 % | 93.8 % | 95.8 % | 0.050 | 80.7 % |
| zh point | 18230 | 1.029 | **0.225** | 0.097 | 0.338 | 86.1 % | 93.4 % | 95.8 % | 0.150 | 92.7 % |
| zh span | 6640 | 1.564 | **0.212** | 0.100 | 0.158 | 94.7 % | 96.7 % | 96.9 % | 0.083 | 98.2 % |

**Against Kokoro's own durations** instead of the heard truth
(`evaluate.py --truth model`, the same final code, the same day): everything
0.174 s by the sound against 1.703 by the text (median 0.135, p90 0.296,
86.3 % within 0.25 s, 96.4 % of stretches won); captions 0.169, books 0.192.
The difference is all at the pauses, where the two truths part: a start run
straight into from the speech before it scores the same against either
(0.153 s), a start after a pause 0.195 s instead of 0.150, and a book's end
0.375 s instead of 0.137 — Kokoro's durations put an end 0.1–0.7 s after
the sound stops, and the aligner puts it where the sound stops, as the
heard truth has it.

By rate — the mean start error by the text / by the sound, and the sound's
share within 0.25 s (TUNE, split from the same evaluations as its tables
above; then HOLDOUT as it was run BEFORE the review — the final code's
HOLDOUT was run once and not split again: its two rows by rate are the foot
of its table above, 0.151 s at 100 a second and 0.153 at 20):

| group | 100 Hz: text / sound (sound ≤0.25 s) | 20 Hz: text / sound (sound ≤0.25 s) |
|---|---|---|
| everything | 2.408 / 0.138 (91%) | 2.408 / 0.161 (90%) |
| en | 2.953 / 0.130 (90%) | 2.953 / 0.156 (89%) |
| es | 1.428 / 0.113 (95%) | 1.428 / 0.125 (94%) |
| fr | 2.243 / 0.149 (88%) | 2.243 / 0.199 (85%) |
| hi | 3.346 / 0.109 (96%) | 3.346 / 0.128 (97%) |
| it | 1.886 / 0.144 (89%) | 1.886 / 0.166 (90%) |
| ja | 1.606 / 0.149 (85%) | 1.606 / 0.154 (85%) |
| pt* | 0.316 / 0.099 (94%) | 0.316 / 0.112 (94%) |
| zh | 2.870 / 0.186 (90%) | 2.870 / 0.209 (89%) |
| M = 3 | 0.557 / 0.125 (91%) | 0.557 / 0.145 (92%) |
| M = 10 | 1.197 / 0.130 (92%) | 1.197 / 0.159 (92%) |
| M = 30 | 2.346 / 0.135 (92%) | 2.346 / 0.164 (91%) |
| M = 100 | 3.864 / 0.134 (87%) | 3.864 / 0.156 (86%) |
| M = all | 2.581 / 0.144 (90%) | 2.581 / 0.160 (89%) |
| point | 2.281 / 0.152 (87%) | 2.281 / 0.169 (86%) |
| span | 2.640 / 0.112 (98%) | 2.640 / 0.146 (96%) |
| clean | 2.408 / 0.138 (92%) | 2.408 / 0.183 (88%) |
| drift | 2.408 / 0.133 (93%) | 2.408 / 0.176 (89%) |
| music | 2.408 / 0.134 (90%) | 2.408 / 0.143 (91%) |
| room12 | 2.408 / 0.151 (87%) | 2.408 / 0.141 (90%) |
| room25 | 2.408 / 0.133 (91%) | 2.408 / 0.160 (91%) |

| group | 100 Hz: text / sound (sound ≤0.25 s) | 20 Hz: text / sound (sound ≤0.25 s) |
|---|---|---|
| everything | 1.697 / 0.149 (88%) | 1.697 / 0.152 (88%) |
| en | 2.109 / 0.123 (90%) | 2.109 / 0.138 (89%) |
| es | 1.256 / 0.123 (89%) | 1.256 / 0.133 (90%) |
| fr | 1.347 / 0.158 (82%) | 1.347 / 0.182 (79%) |
| hi | 1.348 / 0.112 (94%) | 1.348 / 0.128 (92%) |
| it | 1.653 / 0.127 (89%) | 1.653 / 0.139 (90%) |
| ja | 1.538 / 0.204 (79%) | 1.538 / 0.180 (81%) |
| pt* | 0.676 / 0.198 (88%) | 0.676 / 0.136 (93%) |
| zh | 1.172 / 0.242 (89%) | 1.172 / 0.200 (88%) |
| M = 3 | 0.544 / 0.123 (91%) | 0.544 / 0.136 (92%) |
| M = 10 | 1.025 / 0.142 (90%) | 1.025 / 0.143 (91%) |
| M = 30 | 1.315 / 0.159 (88%) | 1.315 / 0.154 (87%) |
| M = 100 | 2.167 / 0.127 (89%) | 2.167 / 0.139 (87%) |
| M = all | 1.978 / 0.156 (88%) | 1.978 / 0.160 (87%) |
| point | 1.650 / 0.150 (86%) | 1.650 / 0.155 (85%) |
| span | 1.873 / 0.146 (96%) | 1.873 / 0.143 (96%) |
| clean | 1.697 / 0.121 (92%) | 1.697 / 0.155 (88%) |
| drift | 1.697 / 0.117 (92%) | 1.697 / 0.156 (88%) |
| music | 1.697 / 0.136 (87%) | 1.697 / 0.148 (88%) |
| room12 | 1.697 / 0.239 (83%) | 1.697 / 0.161 (86%) |
| room25 | 1.697 / 0.133 (88%) | 1.697 / 0.142 (89%) |

**Every language improves**, on both halves, on every kind, in every
condition and at both rates: the mean start error by the sound is 0.10–0.23
s against 0.3–4.6 s by the text, and within 0.25 s for 74–100 % of starts
against 3–60 %. HOLDOUT on the final code (0.152 s) confirms TUNE (0.149 s;
0.150 after the review): nothing was fitted to the voices or texts tuned on.

**Where by the sound is weaker — plainly:**

- **Short stretches.** With M = 3 the text is already close (0.54–0.56 s),
  and by the sound loses 9–10 % of such stretches — by 0.12 s on average
  (p90 0.25 s, once 1.5 s). At M = 10 it loses under 1 %, beyond that none.
- **Captions (`point`) more than books.** A caption cut in mid-sentence has
  no pause to sit in. The starts that run straight on from the speech before
  them have a mean of 0.15 s, a p90 of 0.33–0.36 s and 81–83 % within 0.25
  s; the starts after a pause 0.15 s, 0.16–0.20 s and 93–95 %.
- **Japanese and Chinese captions** are the weakest groups: 0.18–0.23 s mean,
  p90 0.34–0.49 s, 5–10 % of starts off by more than half a second. A
  character is a poor measure of time (a kana is a mora, a Han character a
  syllable, and a caption of 8–25 of them is cut wherever the line ends), so
  the text's lengths guide less and a boundary between two pauses may go to
  the wrong one.
- **20 a second** is a little worse than 100 (TUNE 0.161 against 0.138 s; the
  median 0.126 against 0.101, the envelope's own resolution) — on HOLDOUT
  about the same (0.153 / 0.151; the median 0.118 / 0.098).
- **Room noise at 12 dB** on HOLDOUT (0.202 s, 95.2 % of stretches won;
  0.137–0.143 in the other conditions), worst at 100 a second (0.239 s,
  83 % within 0.25 s, in the split by rate made before the review): the
  noise fills the short pauses.
- **Portuguese books** (`pt*`, one short recording a half): won 81–86 % of
  stretches; its text estimate is already good (0.35–0.50 s).
- **What this bench cannot show**, measured on made-up sound instead (§6):
  a text with **no punctuation at all** — an auto-caption as YouTube leaves
  it — where a long stretch drifts by one to two seconds, still worse than
  by the text in short Chinese stretches (tidying the captions first gives
  them their full stops); a reader who **hesitates for breath** between
  plain words, whose long pauses look like sentence ends; a **fast reader**
  whose sentence pauses are all under a quarter of a second, for whom the
  calibration ranks a sentence end below a comma (§3); and an envelope with
  **nothing in it** (a muted or silent recording), where the answer is by
  the text's proportion over the words' weights, and says so with a
  confidence of 0.1.

**Which numbers matter on real speech** — each change from the defaults
alone, on TUNE's clean, music and 12 dB conditions at both rates (4,230
evaluations; defaults 0.148 s):

| change | mean | Δ | where it shows most |
|---|---|---|---|
| (the defaults) | 0.148 | | |
| the unit's own rate in the state again (`rate_latent` off) | 0.221 | +0.073 | it 0.328, fr 0.313, hi 0.258 |
| sentence ends' pauses limited again (0.6 s / 1.2 s) | 0.206 | +0.058 | zh 0.399, ja 0.345 |
| `rate_drift` 0.16 | 0.188 | +0.040 | it 0.265, zh 0.255 |
| `swallow_length` 0.5 (a long pause inside a unit counts less) | 0.168 | +0.020 | zh 0.262, ja 0.223 |
| `w_pause` 0.5 | 0.167 | +0.019 | ja 0.207, it 0.200 |
| one factor for every pause prior (`calibrate_mode` "scale") | 0.157 | +0.009 | fr 0.207, it 0.197 |
| no dip length (`dip_rank` 0) | 0.155 | +0.007 | hi 0.149 (0.121) |
| `w_anchor` 0.5 | 0.155 | +0.007 | ja 0.198 |
| `alpha` 0.6 | 0.156 | +0.008 | fr 0.179 |
| `rate_drift` 0.04 (the first value) | 0.154 | +0.006 | ja 0.171 |
| `rate_jump_nats` 1.5 | 0.153 | +0.005 | ja 0.176 |
| `w_pause` 2.0 | 0.153 | +0.005 | zh 0.244 — en 0.132, it 0.142 better |
| `anchor_full_s` 0.45 / 0.2 | 0.153 / 0.151 | +0.005 / +0.003 | |
| `w_anchor` 2.0 | 0.152 | +0.004 | |
| `rate_unit_sigma` 0.15 | 0.151 | +0.003 | zh 0.202 |
| `alpha` 1.0 | 0.150 | +0.002 | |
| `rate_beam_states` 150 | 0.149 | +0.001 | |
| `rate_jump_nats` 6, `rate_revert_s` 30, `dip_rank` 1.2 | 0.147–0.148 | 0 | |
| the beam global again, one pace a candidate, or both | 0.148 | 0 | |
| no calibration of the pause priors at all | **0.145** | −0.003 | zh 0.190 worse, fr 0.152 and it 0.150 better |
| a plain word's long pause capped at 1.5 nats (`pause_length_cap`, the default since the review) | 0.149 | +0.001 | captions 0.162 |
| no length limit after a plain word at all (`pause_length["word"]` ∞) | 0.154 | +0.006 | captions 0.170 |

What it says:

- **The pace model and the sentence ends' pause lengths are what matter**
  (+0.07 and +0.06 s undone), then the pace's wander (`rate_drift`, which
  has an optimum between 0.04 and 0.16) and the pause terms.
- **Now that the pace is modelled, the beam's locality no longer moves the
  mean** on this bench: it was the first fix, when a path read too fast was
  cheap, and it stays because the failure it prevents is one of search, not
  of the model — a model that is right can still be searched wrongly.
- **Calibrating the pause priors no longer helps anything measured**: 0.003
  s better without it on Kokoro (it helps Chinese, hurts French and
  Italian), and on the made-up reader who hardly pauses 0.011 s better
  without it too (six seeds; before the pace model it was what rescued that
  reader). Kokoro pauses at every sentence end, as the priors assume, and
  hesitates nowhere. The made-up bench now has the readers it is for: one
  who hesitates between plain words loses 0.3 s of piece error without it
  (0.61 → 0.94), and so do the "no pauses" and "loose lengths" readers; the
  fast reader gains without it (§3). It is kept, in its split form; whether
  it earns its place on a human voice is for a real recording to say
  (`bench-audio`, §9). The old one-factor form is worse (+0.009 s).
- **The duration prior's exponent (`alpha`) is flat on real speech**
  (0.6–1.0 within 0.008 s), in every language; so is almost everything else.

---

## 9. The bench

```
python3 lib/wavealign_lab.py demo                   # the WORD / START / END / CONFIDENCE table
python3 lib/wavealign_lab.py bench                  # every scenario, new against by the text
python3 lib/wavealign_lab.py bench --quick --long 4 # without the hour; time four hours
python3 lib/wavealign_lab.py plot OUT.svg --scenario "no pauses" --start 10 --end 30
python3 lib/wavealign_lab.py sensitivity            # §7
python3 lib/wavealign_lab.py bench-audio SOUND TRUTH.json   # a real recording (below)
python3 -m unittest tests/test_wavealign.py -v
```

**`bench-audio`: any recording whose cuts someone trusts.** It is handed a
sound file (anything ffmpeg reads) and a JSON of its pieces with their true
times — `[{"text": …, "t0": …, "t1": …}, …]`, or `{"pieces": [...], "kind":
"span" | "point"}`; `start`/`end` are read as `t0`/`t1`, and a caption needs
no `t1` — and it measures by the text against by the sound exactly as §8
does: stretches of 3, 10, 30 pieces and all the rest (`--sizes`), twelve of
each spread over the recording (`--per-size`), each starting at a piece's
true start and ending at the true end of its last, the picture of the sound
cut from Parseh's own envelope of the file at a thousand a second — a
book's 100 a second and a video's recorded 20 (`--rate`) — and each answer
rounded as the page and the door round it. With `--wave waveform.json` a
video's recorded picture is used instead of a sound file (give `-` for the
sound). It prints the table by rate and size (mean, median, p90, the share
within 0.1 / 0.25 / 0.5 / 1 s, the gap measure, how often the sound wins)
and writes the numbers with `--json`. Nothing in it knows of a shelf: it
reads only the two files it is given, and a shelf's own `timings.json` is
not a truth to hand it — the owner's cuts are not trustworthy.

The Kokoro bench itself (its texts, the rendering, the heard truth and the
evaluator) lives outside the repository, with the job's scratch files; its
figures are those of §8.

`plot_alignment()` draws one alignment as an SVG with no dependency — the
normalised level curve, the two thresholds, the speech regions, the pauses
(shaded by strength), the candidates (coloured by kind, as tall as their
strength), every word with its label, a bar of its confidence and the
uncertainty of its start, and the truth beneath when it is known — and a PNG
beside it when matplotlib is there (it is not needed).
