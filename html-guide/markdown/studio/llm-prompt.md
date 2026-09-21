---
title: The LLM prompt page
linkTitle: LLM prompt
weight: 3
description: The text that makes a language model answer in the studio's dialect, with the target language chosen and your question added.
---

A language model knows Markdown but not the studio's dialect: it does not
know that `## کتاب | ketâb | …` is a lemma heading, that a sentence of
the target language goes in `[…]{tl}`, or that a gloss's translation is
written in italics so that the glossary can find where it ends. The
**LLM prompt** page, `/studio/prompt` — the library's **LLM prompt**
button — holds the text that teaches it all that, ready to copy in front of
your question. The model then answers with a document the studio reads as
it is, typeset and verified.

## The workflow

The page says it in one line under the prompt:

1. **Copy prompt + question**.
2. Ask your LLM: paste the lot into one message.
3. Download the `.md` file it writes.
4. Back in the library, **Upload .md / .zip**.
5. Read it typeset, tag it, build the verified PDF.

A model that answers in the chat instead of writing a file is no problem:
copy its whole reply and use **Paste LLM answer** on the library, which
takes the document out of its code fence. See
[Bringing documents in and out](documents-in-and-out.md).

## The page

- **target language** is a menu in the prompt's head: the language the
  document will be *about*. It starts on the language the toolbox is set
  to. The prompt itself is the same for every language; what the menu
  changes is what is copied with it: a first line stating the target
  (*target: fa — this document is about Persian: write `target: fa` in the
  front matter*) and, under the prompt, that language's own conventions —
  its transliteration scheme, its reading rule, what to hyphenate — so they
  reach the model too.
- **The prompt box** shows the prompt and the conventions under it. Its
  badge says whether this is the **default** prompt (the one that ships
  with Parseh) or your **custom** one, and for which language.
- **Copy prompt only** copies the target line, the prompt and the
  conventions — for when you write the question in the chat yourself.
- **Your question** is the box under the prompt, for what you want to know:
  *the Persian words for hot and cold: uses, registers, opposites,
  compounds.*
- **Copy prompt + question** copies the target line, the prompt, the
  conventions and your question, in that order, ready to paste as one
  message. It needs a question: without one it says *Write your question
  first*. The line beside it says how many characters were copied.

The prompt is written in no particular prose language: it tells the model
to answer in the language of your question, so a question asked in Italian
gets a document written in Italian about Persian. It also tells the model
that the dialect's features are tools and not tasks — a document uses the
few it needs, never colours a word to show that it can, and never
describes its own markup — and that pictures, recordings, videos and links
to other documents are yours to add: a model never writes one, and keeps
the ones a document it is asked to revise already has.

## Your own prompt

- **Edit prompt** makes the prompt box editable. It shows the prompt
  alone, without the language's conventions, which belong to the language
  and are added again when you copy.
- **Save custom prompt** keeps your version: from then on it is the prompt
  this page shows and copies, for every language, and the badge says
  **custom**. **Cancel** leaves editing without saving.
- **Reset to default** throws your version away, after asking, and goes
  back to the prompt that ships with Parseh.

The custom prompt is a file in the library (`_prompt.md`), so it travels in
the library's **Backup**. It is also what the editor's **Exercises ▾ →
Generate with LLM…** sends as the description of the dialect: see
[Exercises in the editor](editor-exercises.md#generate-with-llm).
