# The prompt kit

`lib/promptkit.py` assembles every prompt Parseh hands to a chatbot. Parseh
runs no model and sends nothing: it writes the prompt, and checks and files the
answer. This page is for whoever changes a prompt.

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

## Your own prompts

`lib/prompts.py` keeps the prompts a person wrote, in `config/prompts.json`
(`STORE_FORMAT`; a prompt is exported as a file in `EXPORT_FORMAT`; both have a
row in `lib/version.py` `FORMATS`). Parseh's own prompts are not in it, so no
route can delete or overwrite one. A prompt has an `id` (what a route is given,
never the name), a `name` (one per place, ignoring case), a `surface`, a `kind`,
its `text`, `languages` (`[]` for every language, or one code) and, for the kind
`replace`, `based_on`: the surface, the version and the text of Parseh's
instructions it began from.

| kind | the kit is handed | a new one begins as |
|---|---|---|
| `added` (the default) | Parseh's raw instructions, then the person's text | empty |
| `replace` | the person's text alone | a copy of Parseh's raw instructions |

Either way the contract and the data are Parseh's, after the text. For `ask` and
`book-new` nothing is read back, so nothing is locked (`parseh(surface)["locked"]`
is false) and the whole text may be the person's; `ask`'s words are held in
`prompts.ASK` (the page builds its prompt in JavaScript) and a test holds them to
`lib/llm.js`. A text is checked when it is saved (`check_text`): a placeholder the
kit does not publish for that place (`known_names`), a block it does not know, the
marks of a part, a double brace that is none of these: refused in words, with the
kit's own dry run as the last word.

### What the code calls

```python
chosen = prompts.resolve(surface, prompt_id, lang)       # None: Parseh's own
promptkit.assemble(surface, lang, gloss, ...,
                   instructions=chosen and chosen.instructions,
                   custom=chosen and chosen.name)          # the version line ends `· custom: <name>`
```

`resolve` refuses in words an id that is gone (`prompts.NotFound`, status 404) and
one for another place or another language (`prompts.PromptsError`, status 400).
`Chosen` is `(id, name, kind, text, instructions)`: `instructions` is what the kit is
handed, `text` the person's own words alone, `kind` what Lane G needs (an `added`
prompt travels in a skill's short request, a `replace` cannot).
`prompts.instructions_for(surface, id, lang)` is the same for a caller that wants
the string alone; for `book-new` it is the whole prompt as the page fills it.

The doors take `prompt=<id>` in their body: `POST /youtube/api/region/prompt` and
`<book>/__region/prompt` (the id goes to `glossregion.book_prompt` and
`video_prompt`, which resolve it against the stretch's language), `/youtube/api/prepare`
(`ytpages.assembled_full`), `/youtube/api/transcript` with `prompt` an id where
`true` is Parseh's own (`tidy.assembled`). The answer then carries
`custom: {id, name, kind}`. **Not wired yet, by design (Lane F2):** the studio's
`GET /api/prompt` and `POST /api/exercise-prompt`, `ask` (`lib/llm.js`, which already
takes `instructions`, `instructionsKind` and `custom`) and the make-a-book page. A
`studio-doc` prompt of kind `added` goes after the boxes: hand the kit
`chosen.instructions` with the box flags, or `chosen.text` as an extra; a `replace`
one takes the boxes only if its text carries the `{{?id}}` markers, which
`prompts.markers(chosen.text)` lists. Where the kit refuses a prompt of yours at the
door (it named something Parseh no longer fills in), say it with
`prompts.unmade(chosen, error)`: the kit's words speak of a bug in a template, which a
person's prompt is not.

### The API the row's menu calls

One module answers for both route layers: `prompts.api(what, body)` returns
`(status, answer)`. In the toolbox the routes are `POST /settings/api/prompts/<what>`
(listed in `lib/settingspage.py` `ROUTES`, no risk: any device let in); the studio
run on its own has the same names at `/api/prompts/<what>`
(`markdown/app/server.py`), and inside the toolbox at `/studio/api/prompts/<what>`;
all three are one store. Every writing route is refused from another site
(`lib/crosssite.py`).

| `what` | body | answer |
|---|---|---|
| `list` | `{surface, lang?}` | `prompts`: those the place offers (for the language or for every one), without their text: `id name surface kind languages size updated stale` |
| `get` | `{id}` | `prompt` (with `text`) and `verdict` |
| `parseh` | `{surface}` | Parseh's raw `text`, its `version`, `locked`, the `contract` (raw, to show greyed under the text), `data` (one line saying what follows), the `placeholders` `[[NAME, meaning]]`, the `blocks` a text may use (`{{?name}}…{{/name}}`) and the place's `label` |
| `save` | `{id?, surface, name, kind, text, languages?}` | `prompt` and `verdict`; with `id` it changes that prompt (its surface stays) |
| `uptodate` | `{id}` | "mine stands on Parseh's as it is now": records the current version, `prompt` and `verdict` |
| `delete` | `{id}` | `{ok}` |
| `import` | `{data}` (an exported file's text) | `prompt`, and `renamed_from` when the name was taken |
| `state` | `{}` | every prompt, the places and the languages: what Settings draws |

`GET .../export?id=<id>` downloads the file. Every refusal is `{ok: false, error}`
in words, with 400 (404 for an id that is gone). `verdict` is `null` for a prompt
that is added, `{known, stale, was, now, diff}` for one in place of Parseh's;
`diff` is a line diff of what changed in Parseh's own since, `[{op: "+" | "-" | " ",
text} | {op: "…", skipped: n}]`, and `known` is false where nothing was recorded of
what it began from (the studio's old prompt, from before a0.4.2). `stale` is on
every listed prompt too, so a menu can say it without asking for the diff.

The placeholders the page fills for `ask` are the kit's four and `{{GLOSS_LANGUAGE}}`
and `{{GLOSS_CODE}}` (`prompts.EXTRA`: the kit publishes a name only for the prompts
it fills itself, and its tests pin that).

### The studio's old prompt

The custom prompt the studio kept as `markdown/library/_prompt.md` moves into the store
once, at the first start (`store.move_prompt`, from `server.migrate_library`), as
"my studio prompt (from before a0.4.2)", surface `studio-doc`, kind `replace`, with no
record of what it began from. The store's marker (`moved`) makes it once and only once:
the file's return, written by an older Parseh, is never moved again. The studio's old
single-prompt routes (`GET/PUT/DELETE /api/prompt`) keep working on that prompt.

## Adding a surface

1. Write its template, marking the contract and the data.
2. Name it in `SURFACES` and `TEMPLATES` (or `register()` a template held in code),
   add its placeholders to `_PLACEHOLDERS`, and its row to `LAYOUT`/`KIND` if it
   takes the language's conventions.
3. Write its assembler: build the values, call `assemble`, return the `Assembled`.
4. Teach `lib/promptlab.py` `build` to make one, and add its row to `SIZES`
   and to `MEASURED` in `tests/test_prompts.py`.

## The lab and the tests

`python3 lib/promptlab.py <surface> <language> [--mode regloss] [--sizes]`
prints a prompt as a chatbot receives it and the sizes of its parts.
`tests/test_prompts.py` builds every surface in every language (and one added
by `newlang.py`) with it and runs the table `CHECKS`. A size is one row of
`SIZES`: change the measured number and its budget together, on purpose. A row
marked `PENDING("D")` or `PENDING("E")` is skipped with its reason and fails the
day it passes everywhere, so the lane that made it true takes the mark off.
