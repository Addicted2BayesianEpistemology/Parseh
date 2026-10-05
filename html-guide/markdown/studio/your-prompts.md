---
title: Your own prompts
linkTitle: Your prompts
weight: 3
description: The prompts you write for a chatbot — added to Parseh's or in place of them — kept on this computer, chosen at every button that copies a prompt, exported and imported as files.
---

Wherever Parseh hands you a prompt to paste into a chatbot, the words are
Parseh's own, written for that job. You can keep prompts of your own beside
them: a rule you always want (*never gloss proper names*, *prefer British
spellings*), or a whole prompt written your way. Each has a name, is kept on
this computer, is offered wherever it makes sense, and is used when you
choose it at the button that copies the prompt. **Parseh's own prompts are
never changed or deleted by any of this**: yours stand beside them, and
choosing Parseh's again is one click.

A prompt is only text that you copy and carry to a chatbot yourself: writing
one, or choosing it, runs no model and sends nothing. Your prompts change what
you copy, and nothing else.

## Where there is a prompt

Every place that hands out a prompt has its own list of yours:

| The prompt for | Where you copy it |
|---|---|
| a new document | [the LLM prompt page](llm-prompt.md) |
| exercises for a page | **Exercises ▾ → Generate with LLM…** in the editor ([Exercises in the editor](editor-exercises.md#generate-with-llm)) |
| a video from its transcript | the add page ([Adding a video](../videos/adding-a-video.md)) |
| a transcript, tidied | **or with an LLM…** in the add page's subtitle editor ([Mending the transcript first](../videos/mending-the-transcript.md#or-with-an-llm)) |
| a stretch of a video | **gloss with an LLM** in the player ([Glossing with an LLM](../videos/glossing-with-an-llm.md)) |
| a stretch of a book | **gloss with an LLM** in the reader ([Glossing with an LLM](../books/glossing-with-an-llm.md)) |
| one sentence | **Ask LLM** in the sources sidebar ([Ask LLM](../books/unglossed.md#ask-llm)) |
| a book made by an agent | the make-a-book page ([Adding a book](../books/adding.md)) |

A prompt you wrote for one of these is offered only there: a prompt for a
stretch of a video does not appear at the button for a stretch of a book.

## Writing one: the menu beside the button

Every button that copies a prompt has a menu in front of it, **prompt:
Parseh's ▾**, and three small buttons: **new**, **edit** and **delete**. The
menu lists Parseh's own prompt for that place and yours, and the one chosen
is the one the button copies; the size said under the button is its size. On
the add page, where the prompt is prepared before there is a button to copy
it with, the menu is above **Prepare the prompt**, with the choices that
belong to it. A place where the computer has no prompts of yours to offer
(it does not answer) has no menu, and the prompt is Parseh's own.

- **new.** Opens an editor under the buttons (in the exercise dialog, at the
  top of what scrolls): a **name**, **what it is** (*added after Parseh's
  instructions*, the default, or *in place of Parseh's instructions*, which
  begins as a copy of Parseh's own words), **which language** (every one, or
  one) and the **text**. Under the text it lists the names Parseh fills in,
  each a button that puts it where the cursor is, and shows, greyed, what
  stays Parseh's.
- **save.** Keeps it, chooses it, and from then on the button copies it. A
  name Parseh does not fill in, or a name that another prompt of yours has for
  the place, is refused in words, and nothing is kept.
- **edit.** Opens the prompt chosen as it was saved. **save** keeps the
  changes; **save as…** asks for a name and keeps what is written as a new
  prompt, leaving the first as it was. The button copies the prompt as it was
  last saved, and the editor says when what you typed is not saved yet.
- **delete.** Asks first, in the row (*delete "name"? it cannot be got back*),
  and then Parseh's own is chosen again. **edit** and **delete** are off while
  Parseh's own is chosen: it is never changed or deleted from here.
- **close.** Leaves the editor, and asks before it throws away what you
  changed. **Esc** does the same, and leaves what is round the editor (the
  transcript being mended, the sidebar) as it was.

The menu remembers on this device which prompt was used last, for each place;
one that has gone, or is for another language than the page's, is Parseh's own
again. The prompts are yours on every device that is let in; what each device
has chosen is its own.

A prompt in place of Parseh's whose starting words Parseh has changed since
says so under the buttons: *Parseh's prompt changed since you started from
it.* **see what changed** shows the lines, what Parseh added marked **+** and
what it took away marked **-**; **mine stands** says that yours stands as it is,
and the note goes. If another device deletes the prompt you have chosen, the
row says it is gone and Parseh's own is chosen.

## Two kinds

- **Added to Parseh's.** What a new prompt is. Your text goes *after*
  Parseh's instructions, so Parseh's rules all still stand and yours say
  what to do besides: *Never gloss proper names.* *Prefer British spellings
  in the meanings.* *Explain the grammar of each phrase in one line, in
  `note`.*
- **In place of Parseh's.** Your text is the instructions, and Parseh's are
  left out. A new prompt of this kind **starts as a copy of Parseh's own
  instructions**, so you never write from a blank page: change what you
  want and keep the rest.

## What stays Parseh's

Whatever you write, two things come after it, and they are Parseh's and
locked:

- **the answer contract**: the shape the answer has to have, and how to send
  it (one fenced block, the JSON keys, several messages, the later block
  wins, a file or a fence);
- **the data**: the captions, the chunks, the page, the question.

That is what lets Parseh check and file the answer, however you asked for it:
*an answer to your prompt lands exactly as an answer to Parseh's own*. The
editor shows both greyed under your text, so you see what goes with it, and
the data is said in one line (*then the stretch of the video, as one JSON
document*) rather than filled with a real one.

Two places have no contract, because nothing there is read back by Parseh:
**Ask LLM** and **a book made by an agent**. In those the whole text may be
yours.

## Placeholders

A prompt may name things Parseh fills in when it is copied. A name is written
between double braces, and the editor lists, for the place you are writing
for, every name it may use and what it stands for. The ones every place has:

| Written | Filled in with |
|---|---|
| `{{LANGUAGE}}` | the language's name, in English (*Persian*) |
| `{{LANGUAGE_NATIVE}}` | its name in itself |
| `{{LANGUAGE_CODE}}` | its code (*fa*) |
| `{{TR_LABEL}}` | what its transliteration is called (*transliteration*, *pinyin*, *rōmaji*), or *IPA* where the prompt asks for it |

A place that asks for a transliteration (the studio's two, a video or a book
from scratch, a stretch of either) also has `{{TR_SCHEME}}`, the scheme it is
written in (*IPA*, or *the usual rōmaji scheme for Japanese*); the places that
write or read a book's or a video's own text have `{{MARKS_RULE}}`, what is
asked of the short vowels in Persian and Arabic (*write the short vowels in
`fa`*, or *leave `fa` as it is*), and nothing in a language that has none.

Where a gloss language is involved (the video and book prompts, and Ask
LLM) there are also the language the meanings are written in
(`{{GLOSS_LANGUAGE}}`, `{{GLOSS_CODE}}`), and each place has names of its own
(a stretch has `{{FIELD_LIST}}` and `{{UNITS}}`; a video from its transcript
has `{{TR_RULE}}`; the tidy has `{{MARKS}}`). A name Parseh does not fill in
for that place is **refused when you save**, in words that name it: `{{NOPE}}`
*is not something Parseh fills in for this prompt. It fills in: …*

A part of a prompt may be kept for one kind of place only, between
`{{?video}}` and `{{/video}}` (or `book`, `studio`), and the prompts that
begin as a copy of Parseh's carry such blocks: leave them as they are and the
prompt still fits both the book and the video. The two choices beside the copy
button have blocks of their own: `{{?ipa}}…{{/ipa}}` is kept while the
transliteration is asked for in IPA and `{{?classic}}…{{/classic}}` while it is in
the language's usual scheme; `{{?marks}}…{{/marks}}` while the short vowels are to
be written and `{{?nomarks}}…{{/nomarks}}` while the text is left as it is (neither
in a language without short vowels). The editor says which a place can use. A double brace that is none of
these cannot be part of your text; write it with a space between the braces.

## For every language, or for one

A prompt is for every language unless you mark it for one, and then it is
offered only there: your rule for Persian is not at the button for a video in
Italian. A prompt marked for a language is refused, in words, if asked for
another.

## Its name

A name is a few words on one line, at most 60 characters, and each place has
one prompt of that name (upper and lower case count the same). The line every
copied prompt opens with says which prompt made it:

```text
Parseh prompt · video-region · fa → en · <the version> · no marks · custom: British spellings
```

so an answer can always be traced to the words that asked for it. What the
choices beside the copy button came to stands before the name (*IPA*, *marks*,
*no marks*), because the name is your own text and goes last.

## Keeping up with Parseh

A prompt **in place of** Parseh's remembers which of Parseh's prompts, and
which version of its words, it began from. When Parseh's own has changed
since (a new Parseh, better words), the prompt says so, and its editor shows
what changed: a line by line difference, what Parseh added and what it took
away. You can bring the changes into your text, or say that yours stands as
it is, and the note goes.

A prompt **added to** Parseh's never says it: Parseh's instructions come
first each time, as they are now.

## Where they are kept

In `config/prompts.json`, on the computer Parseh runs on, so **they follow you
to every device that is let in**: what you write on the computer is at the
button on your phone, and the other way round. Updating Parseh keeps them,
as it keeps your settings ([Updating Parseh](../getting-started/updating.md#what-it-keeps)).
An older Parseh does not read the file and ignores it. They are not in a
book's or a library's backup: export the ones you would hate to lose.

## Export and import

Each prompt is exported as a file of its own, and any Parseh reads it back.
On **Settings → Your prompts**, **Export** beside a prompt downloads it
(`British-spellings.parseh-prompt.json`), and **Import a prompt…** takes one.
An import **never writes over** a prompt: one whose name you already have for
that place is kept as *British spellings (2)*, and the page says so. A file
that is not a prompt Parseh reads is refused in words and nothing is kept: a
file that is not a prompt at all, one made by a newer Parseh, one that names
what Parseh does not fill in.

## Settings → Your prompts

**Settings → Your prompts** lists every prompt of yours by the place it is for,
each with what it is (added or in place of, for which language, how long,
when it changed) and its words, folded until you ask to read them. From
there you export one, delete one (asked in the row, never at once) or import
one. **Any device that has been let in** may do all of it, from a phone as
from the computer: what a prompt says is text you copy, and decides nothing
Parseh runs.

Making and editing a prompt is not done there but at the button that copies
the prompt, in the **prompt: Parseh's ▾** menu beside it: it lists Parseh's
prompt for that place and yours, and **new**, **edit**, **save**, **save as…**
and **delete** work on yours. What you choose there is what the button copies,
and the menu remembers on this device which you used last.

## The studio's old custom prompt

Before a0.4.2 the studio kept **one** custom prompt, a file in its library
(`_prompt.md`). The first time a0.4.2 starts, it moves into your prompts as
**my studio prompt (from before a0.4.2)**, for the studio's prompt, in place of
Parseh's; the file is taken out of the library, and it is moved once and
never again. It is a prompt like the others: rename it, edit it, export it or
delete it. Nothing chooses it for you: it is in the menu of the studio's
prompt page under that name. It has none of the boxes' blocks, so it is copied
whole and the boxes are greyed (see [the LLM prompt page](llm-prompt.md#your-own-prompt)).
