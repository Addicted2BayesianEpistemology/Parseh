---
title: Exercises in the editor
weight: 6
description: The Exercises ▾ menu — Add exercise… and its form, ✎ Edit in the preview, Generate with LLM…, Load from a deck….
---

An exercise is a block of the document's Markdown, from an
`:::exercise <type>` line to a closing `:::` — twelve kinds of activity
and three kinds of flashcard, answered on the document's page and studied
in the exercise decks. You can type one by hand (the syntax of every kind
is in [Writing exercises](../dialect-exercises/_index.md)), but the
editor's **Exercises ▾** menu writes them for you, reads them back, and
brings them in from elsewhere:

- **Add exercise…** — a form for a new exercise of any kind.
- **Generate with LLM…** — a prompt that asks a language model to add
  exercises to this page.
- **Load from a deck…** — an exercise out of one of your exercise decks.

The menu closes as soon as you pick an entry.

## Add exercise…

**Add exercise…** opens a grid of the activities a learner can be given,
each with a line saying what it is:

| Entry | Type |
|---|---|
| **Fill in blanks** | `fill-blanks` |
| **Order sentences** | `order-sentences` |
| **Construct a sentence** | `construct-sentence` |
| **Match translations** | `match-translations` |
| **Match opposites** | `match-opposites` |
| **Match definitions** | `match-definitions` |
| **Yes / No questions** | `yes-no` |
| **True / False questions** | `true-false` |
| **Choose one answer** | `single-choice` |
| **Choose all correct answers** | `choose-all` |
| **Identify the incorrect part** | `incorrect-part` |
| **Odd one out** | `odd-one-out` |
| **Embedded vocabulary flashcard** | `flashcard`, `card-type: vocab` |
| **Embedded opposites flashcard** | `flashcard`, `card-type: opposites` |
| **Embedded Jolly flashcard** | `flashcard`, `card-type: jolly` |

Pick one, and the form for that kind opens. You never have to know the
Markdown it writes: the form asks for what the learner will see.

### The form

The form is in sections, from the top:

- **Instructions** (every kind but a flashcard): **Prompt shown to the
  learner**, with the usual instruction of that kind as its placeholder,
  and **Writing direction of the activity** — **Automatic**, **Use Persian
  direction** (the document's target), **Right to left** or **Left to
  right**.
- **The activity itself**, in the words of its kind:
  - *Fill in blanks*: **Sentence and blanks**, built from pieces —
    **+ Add sentence text** for the words that stay visible,
    **+ Add blank** for a gap and the block that belongs in it — and
    **Extra movable blocks (optional distractors)**, with
    **+ Add distractor**.
  - *Order sentences* and *Construct a sentence*: the sentences, or the
    words or chunks, **in the correct order**, one per row, with
    **+ Add sentence** or **+ Add word or chunk**. A sentence to construct
    also has **Direction of the answer (including wrapped lines)** and
    **Reverse order**, which turns the whole list round — the quick fix for
    a right-to-left sentence typed in the wrong order.
  - *The three matchings*: **Pairs**, two fields each, with
    **+ Add pair**; for translations and definitions, **What the learner
    sees on the left**.
  - *Yes / No* and *True / False*: **Questions and answers** or
    **Statements and answers**, each with its **Correct answer**.
  - *The choices*: **Answer choices** (or **Sentence segments**), each
    with **Correct answer** ticked on the right ones — exactly one, except
    for *Choose all correct answers* — or **This is the incorrect
    segment**.
  - *A flashcard*: **Card content** — for a vocabulary card the word, its
    reading, its transliteration, its meaning, an example, notes, a source,
    or a custom front and back; for an opposites card the word and its
    opposite with their readings and transliterations; for a Jolly card the
    four fields, primary and secondary, of each side, which take any
    Markdown of the dialect over several lines. Each text field has
    **Text appearance**: its **Text size (%)**, from 50 to 250, and its
    **Color treatment** — **Primary text**, **Subdued**, **Muted**,
    **Accent color** or **Custom color**. **Which side appears first**
    turns the card round.

  Every row has **↑** and **↓** to move it and **Delete** to take it away.
- **Pictures (optional)** and **Recordings (optional)** (every kind but a
  flashcard): **Picture with the question** and **Recording with the
  question**, shown between the prompt and the activity, and **Picture
  shown after the answer** and **Recording played after the answer**, kept
  back until the exercise has been answered, right or wrong. Each has
  **Upload…**, which stores the file in the document and fills in its path,
  and a fold — **Size and position**, or **Size, position and clip** —
  with **Width (% of the column)** and **Where it sits**, and for a
  recording **Play from** and **Play to**.
- **Explanation after checking (optional)**: one shown when the answer is
  correct, one when it is not. With only the first filled in, it is shown
  either way.
- **Preview**: the exercise as the editor's preview will draw it, solved,
  redrawn as you type.

A flashcard's picture and recording fields have **Upload…** too, and a
recording field a **▶** to hear it. A Jolly field has **Image…** and
**Recording…**, which upload a file and put its line into the field at the
cursor.

Every text box of the form has its own **⇤ RTL** / **⇥ LTR** button: the
box starts the way its text is written, and the button turns it for typing
— a Persian answer inside an English exercise, say. It changes only how
that box is edited, never the exercise. **∑ Maths…** at the foot of the form
opens [the maths sheet](editor.md#maths) and writes the formula, in the
line, into the field you were last in.

**Insert exercise** checks the form — a blank with no block, a choice with
no right answer, a row half filled are each said in a message, and the
form stays open — then puts the exercise in at the cursor, on lines of its
own. **Cancel**, **✕** or Escape closes the form and writes nothing.

> **Save the document before uploading.** Pictures and recordings go into
> the document's own folders, so **Upload…**, **Image…** and
> **Recording…** need it saved once.

### Paste markdown…

Under the grid, **Paste markdown…** takes an exercise copied as Markdown —
**copy markdown** on a book's or a video's card sheet gives one, and so
does any `:::exercise` block copied out of another document — and opens it
in the form as a new exercise, to be looked over before **Insert
exercise**. Paste it into the box and press **Open in the form** (or
Ctrl+Enter); **Back** returns to the grid. Pressing Ctrl+V on the grid
itself does all of it at once. Words around the block are left out; a text
with no exercise, or more than one, is refused with a line saying so. In a
saved document, the recordings and pictures the block names come in from
the clip tray before the form opens, so its preview plays them.

## ✎ Edit, in the preview

Every exercise in the preview has **✎ Edit** in its head. It reopens that
exact block in the same form, filled in, and **Save exercise** puts the
changed block back where it was — one step you can undo. An exercise the
form cannot show (a kind it does not know) says so instead, and stays
yours to edit in the source.

## Generate with LLM… {#generate-with-llm}

**Generate with LLM…** prepares a prompt that asks a language model to add
practice activities to this page. **The page itself is always included** —
the editor's text as it is now, saved or not. Under that, the dialog lists
your Anki decks (the ones the toolbox builds for you; see the
[cards and Anki section](../cards-and-anki/_index.md)), each with its
language and its number of cards: tick some, and their words — with
readings, transliterations and meanings — go into the prompt as vocabulary
the learner already knows, for the model to use where it helps. None is
needed: *No Anki decks installed — the prompt works without them.*

**Copy complete prompt** puts on the clipboard, in one piece: the
instructions for writing exercises, the whole description of the dialect
(your custom prompt, if you saved one on the
[LLM prompt page](llm-prompt.md), and the target language's conventions),
the known vocabulary, and the page. The line beside the button says how
many known words went in.

Paste it to your model. It answers with the whole page, exercises added,
in one Markdown block: copy that block, select all the text in the editor,
paste it in place, look it over in the preview and **Save** — or undo, if
you do not like it.

## Load from a deck… {#load-from-a-deck}

**Load from a deck…** is the other direction of a document page's
**+ Deck**: it takes an exercise out of one of your exercise decks and puts
it in this page. The dialog lists the decks of the page's language — only
those, since a deck holds one language — and, under the chosen deck, every
exercise in it, headed by its kind and showing its opening words; one the
deck reports as broken is marked, and still offered, since a document is
where it is easiest to mend. Click one and press **Insert**.

The exercise goes in at the cursor exactly as the deck has it, and what it
needs comes with it:

- **its pictures and recordings** are copied into this document's own
  `images/` and `audio/` — a file whose name is taken there by a different
  file is stored as `name-2.png`, and the block that goes in names it so;
- **the footnotes it calls** are placed among the document's own, in
  reading order, and one whose name the document already uses for another
  note is renamed (`n1-2`) in the block and in its definition, so neither
  note is lost.

The deck is left exactly as it was. The document must have been saved once,
since the files go into its folder. With no deck in the page's language
the dialog says *No Persian deck yet — make one with “+ Deck” on a page*.

The entry is there only when the exercise decks can be reached from this
page: always in the studio's own library, and in a note beside a book or a
video when the decks know that book or video.
