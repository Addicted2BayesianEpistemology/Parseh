# The prompt kit

`lib/promptkit.py` assembles every copyable prompt Parseh hands to a chatbot.
It writes the prompt, and the relevant feature checks and files the answer.
Browser ASR review also offers an explicit API route through the separate LLM
adapter. This page is for whoever changes a copyable prompt.

## A surface, and its three parts

A **surface** is one place a prompt comes from. Each has ONE readable template
file, and the file is the whole prompt.

| surface | template | assembled by |
|---|---|---|
| `studio-doc` | `markdown/exlex/PROMPT.md` (after its first `---`) | `markdown/app/server.py` `studio_prompt` |
| `studio-exercises` | `markdown/exlex/EXERCISES_PROMPT.md` | `server.py` `exercise_prompt` |
| `video-new` | `youtube/docs/chat-prompt.md` + `conventions.md` | `ytpages.assembled_chat`, `assembled_full` |
| `video-region`, `book-region` | `docs/region-prompt.md` | `glossregion.assembled` |
| `book-new` | `docs/new-book-prompt.md` | the page (in the browser); `newbook.conventions` |
| `transcript-tidy` | `PROMPT` in `youtube/lib/tidy.py` | `tidy.assembled` |
| `ask` | `lib/llm.js` | the browser |
| `asr-suspect`, `asr-full`, `asr-workspace` | `docs/asr-*-prompt.md` | `asrexternal.assembled` |

Every prompt has three parts, in this order:

1. the **instructions**: how to do the job. Parseh's, or a person's own;
2. the **answer contract**: the shape of the answer and how to send it (one
   fence, the JSON, several messages, the later block wins, file or fence).
   Always Parseh's, for every prompt whose answer Parseh reads back;
3. the **data**: captions, chunks, page, question. Always Parseh's, last.

In a template, `{{?contract}}…{{/contract}}` and `{{?data}}…{{/data}}` mark the
second and third part; everything else is the instructions. A mark sits against
its words on the side its whitespace belongs to, so taking the marks out gives
the file as it was (`promptkit.flat`). A contract may be several blocks, and a
sentence may be split from its paragraph: the kit joins the blocks with a blank line.

## Blocks and placeholders

`{{?flag}}…{{/flag}}` is kept where the flag is true. `{{NAME}}` is filled from
what the caller gives; `placeholders(surface)` lists the names with a line each
(the editor of a person's own prompt shows it). Both are the same everywhere:
templates, the language files, a person's instructions.

- **A resolved prompt never carries `{{`**: the kit refuses one that does, and a
  block whose flag nobody gave, in words (`PromptError`). It is a bug.
- **`verbatim`** values and the **data** are never looked into: a caption or a
  title may say `{{`. Parseh's own text put in by hand (`lead`, `extras`) is
  looked into with `promptkit.check(text, surface)`, which is `assemble`'s test.
- Flags of every text of a surface: `book`, `video`, `studio`, `region`, `new`
  (`surface_flags`), beside those the assembler gives (`keep`, `regloss`, …).

## The language's conventions, cut per prompt

`docs/lang/<code>.md` is read only through `language_text(surface, lang)`. One
table, `promptkit.SECTIONS`, says which section goes to which kind of prompt
(the studio's, a region's, a from-scratch prompt's); a section nobody lists goes
everywhere. Inside The text field the studio takes the note that names the
studio's `{tl}` mark, wherever it stands, and a region takes its first
paragraph. Mark what belongs to one surface with `{{?book}}`, `{{?video}}`,
`{{?studio}}`, `{{?region}}` or `{{?new}}`; the kit resolves them. A word to whoever
maintains the file ("no speaker has reviewed this example yet") goes in
`{{?note}}…{{/note}}`: that flag is never true, so no prompt carries it.

## The version line

Every prompt opens with `Parseh prompt · video-region · fa → en · a0.4.2`, then
`· re-gloss` or `· per field` for a mode and `· custom: <name>` for a person's
own. The version is read from `lib/version.py` when the line is made, never
written in a template.

## For a person's own instructions

`assemble(surface, lang, gloss, instructions=text, …)` puts the person's text in
place of Parseh's; the contract and the data come after it and are Parseh's.
`parts(surface)`, `instructions(surface)` and `contract(surface)` give a
template's raw parts. A person's text may not carry the marks of the parts.

## Adding a surface

1. Write its template, marking the contract and the data.
2. Name it in `SURFACES` and `TEMPLATES` (or `register()` a template held in code),
   add its placeholders to `_PLACEHOLDERS`, and its row to `LAYOUT`/`KIND` if it
   takes the language's conventions.
3. Write its assembler: build the values, call `assemble`, return the `Assembled`.
4. Teach `lib/promptlab.py` `build` to make one, and add its row to `SIZES`
   and to `MEASURED` in `tests/test_prompts.py` when using a measured fixture
   budget. The three ASR surfaces use the explicit UTF-8 prompt limit and
   bounded batches instead.

## The lab and the tests

`python3 lib/promptlab.py <surface> <language> [--mode regloss] [--sizes]`
prints a prompt as a chatbot receives it and the sizes of its parts.
`tests/test_prompts.py` builds every surface in every language (and one added
by `newlang.py`) with it and runs the table `CHECKS`. A size is one row of
`SIZES`: change the measured number and its budget together, on purpose. A row
marked `PENDING("D")` or `PENDING("E")` is skipped with its reason and fails the
day it passes everywhere, so the lane that made it true takes the mark off.
