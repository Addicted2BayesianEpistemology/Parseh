#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The "add a book" page: three ways in, and only one of them on screen.

A book is not a paste-the-answer job.  It is days of work, paragraph by
paragraph.  There are three ways to begin one, and they need almost
disjoint facts -- which is why the page asks WHICH FIRST and then shows
that one alone:

  1. by hand, here.  A chapter is pasted and POSTed to /books/__empty,
     which drafts the whole book with the text divided and every gloss
     blank, marks it a draft, and the reader (which has its own editor)
     is where it is filled in.  It needs the book's facts and a chapter,
     and none of the four fields the outside folder needs.

  2. onto a book already here.  POST <book>/__append, addressed by the
     book's own path so no slug ever travels in a body.  Its body is
     three keys -- text, how, chapter -- and NOT ONE of the identity
     fields: the language, the gloss and the title are the book's
     already, read from its book.json.

  3. outside, with an LLM, in a folder of its own that holds the tools
     and one finished edition to learn from.  Nothing here is posted:
     the page hands back three things to copy -- the shell that sets the
     folder up, the prompt that sets the work going the way the first
     edition was made, and the shell that brings the result back.  This
     is the one way that needs a terminal, and the card says so before
     anybody has filled in a field.

What used to be a single fifteen-field block above three mutually
exclusive actions, with the mapping stated only in prose, is now
structure: the ten identity fields are built ONCE, in #ident, and MOVED
(appendChild, never cloned -- a clone would fork the values, the
listeners and the saved draft) into whichever way needs them.  The
reference edition, the original file, its pages and the working folder
render in way 3 alone, inside a labelled box that says so.

The prompt's text lives in docs/new-book-prompt.md; this file only fills
its placeholders and lays the page out.  Everything the page needs to
know about the toolbox (its path, the built books with their languages
and sizes, the books already on the shelf -- built or not, because a
name is taken either way -- and every language of the registry with its
conventions block docs/lang/<code>.md, read at request time) is embedded
as JSON, and the placeholders are filled in the browser as the form is
typed.  The language select defaults to the toolbox's shared preference
(Parseh.lang, the chip rows' choice) and picks the reference edition:
one of the same language when there is one, else the Persian one, with
the prompt saying that the method is the same and the conventions
differ.

A book declares TWO languages: the one it teaches and the one its
glosses are WRITTEN in (docs/languages.md section 3).  The second select
is that, defaulting to English -- which is what every book in the
toolbox is glossed in, and what a book.json with no "gloss" means -- and
offering both the languages the toolbox teaches and the prose languages
it can only set.  The prompt tells the annotator which one to write in,
once, at the top, because the reference edition it learns from is
glossed in English and its every example would otherwise say so.
"""
import html
import json
import os
import sys

LIB = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, LIB)
from books import all_books, ROOT                              # noqa: E402
import chunker                                                 # noqa: E402
import languages                                               # noqa: E402
import make_index                                              # noqa: E402

APP_NAME = "Parseh"
DOCS = os.path.join(ROOT, "docs")
WORK = os.path.join(ROOT, "work dir")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def references():
    """Every built book, with what the prompt says about it and the
    language it is in.  The page picks among them by language."""
    out = []
    for b in all_books():
        st = make_index.stats(b)
        if not st.get("built"):
            continue
        n_annot = 0
        if os.path.isdir(os.path.join(WORK, "annot")):
            n_annot = sum(1 for f in os.listdir(os.path.join(WORK, "annot"))
                          if f.endswith(".json"))
        has_notes = os.path.isfile(os.path.join(b.dir, "NOTES.md"))
        chapters = len(st.get("chapters", []))
        stats = ("%d chapter%s, %d paragraphs, %d subparagraphs, %d chunks%s%s"
                 % (chapters, "" if chapters == 1 else "s", st.get("paragraphs", 0),
                    st.get("subs", 0), st.get("chunks", 0),
                    ", narrated" if b.has_audio else "",
                    ", with NOTES.md" if has_notes else ""))
        # "src" is where the edition lies in this toolbox; "path" is where the
        # setup shell puts the copy -- always under its language's folder, so
        # a reference still lying directly under books/ (the layout before
        # languages) is addressed, in the prompt and the shell alike, at the
        # place it will actually be
        out.append({"slug": b.slug, "src": b.rel_from_books(),
                    "path": "%s/%s" % (b.lang.folder, os.path.basename(b.dir)),
                    "folder": b.lang.folder, "lang": b.language,
                    "lang_name": b.lang.name,
                    # what the reference's OWN glosses are written in: an
                    # edition glossed in another language is a model for the
                    # shape of a gloss and not for its wording
                    "gloss": b.gloss, "gloss_name": b.gloss_lang.name,
                    "title": b.title, "title_latin": b.title_latin,
                    "author_latin": b.author_latin, "stats": stats,
                    "has_notes": has_notes, "annot": n_annot,
                    "source_pdf": b.meta.get("source_pdf") or "",
                    "chapters": chapters, "paragraphs": st.get("paragraphs", 0)})
    # the edition with notes and its JSON is the one to learn from
    out.sort(key=lambda r: (-int(r["has_notes"]), -r["paragraphs"]))
    return out


def shelf():
    """Every book already here -- built or not -- with where it lives.

    Two jobs, and the second is why this is data and not only markup.
    The way that adds to a book needs the list to choose from, and each
    option carries the book's own language so the text box takes that
    book's face and direction rather than the identity select's.  And the
    slug field needs the names ALREADY TAKEN, so the page can say a name
    is taken before the write refuses it (draft._write refuses on a
    book.json that exists, whatever state the book is in).  references()
    cannot answer that: it holds BUILT books only, and the likeliest
    collision of all is with a draft nobody has built yet.

    The href is worked out from the DIRECTORY rather than from the slug,
    so a book from before languages (lying directly under books/) is
    addressed correctly too.
    """
    out = []
    for b in all_books():
        try:
            rel = os.path.relpath(b.dir, os.path.join(ROOT, "books"))
        except ValueError:
            continue
        rel = rel.replace(os.sep, "/")
        out.append({"path": "/books/" + rel, "rel": rel,
                    "folder": b.lang.folder, "dirname": os.path.basename(b.dir),
                    "lang": b.language, "lang_name": b.lang.name,
                    "dir": b.lang.dir,
                    "name": b.meta.get("title_latin") or b.meta.get("title") or rel})
    return out


def conventions(L):
    """docs/lang/<code>.md, the language's binding annotation conventions,
    read now rather than at import so an edit to the file reaches the next
    request.  A missing file is said to be missing, in one line, rather
    than leaving the prompt with a hole."""
    path = os.path.join(DOCS, "lang", L.code + ".md")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return ("(The conventions of %s -- docs/lang/%s.md -- are not written yet: "
            "the file is missing. Ask for them before annotating.)" % (L.name, L.code))


def lang_records():
    """One record per language of the registry, in its order, with what the
    prompt's placeholders need."""
    out = []
    for L in languages.LANGS.values():
        out.append({
            "code": L.code, "name": L.name, "native": L.native, "folder": L.folder,
            "dir": L.dir, "reading": L.reading, "words": L.words,
            "translit_label": L.translit_label,
            "digit_example": L.to_native_digits("3"),
            "label_example": L.to_native_digits("3.1"),
            # what "character for character" means for this language's text
            "strip_note": ("once the marks (harakat) are stripped from both sides"
                           if L.strip_range else
                           "-- %s carries no marks to strip, so exactly" % L.name),
            "conventions": conventions(L),
        })
    return out


def gloss_records():
    """One record per language a book's glosses may be written in.

    languages.GLOSSES is the whole answer -- the eight the toolbox teaches,
    each named by the registry, then the prose languages it can set but does
    not teach -- so nothing is listed here.  `taught` is what divides the
    select into its two groups: a language with a folder under books/ and a
    language this toolbox only writes in.
    """
    return [G.as_json() for G in languages.GLOSSES.values()]


def prompt_template():
    with open(os.path.join(DOCS, "new-book-prompt.md"), encoding="utf-8") as f:
        return f.read()


SETUP_SH = r'''#!/bin/sh
# Set up a folder for the new edition of {{TITLE_LATIN}} ({{LANG_NAME}}), beside (not inside) the toolbox.
set -e
SOFT="{{ROOT}}"                 # this toolbox
WORK="{{FOLDER}}"               # the new book's own folder
SRC="{{SOURCE_PATH}}"           # the original text of the new book (PDF, epub or txt)

mkdir -p "$WORK/books/{{LANG_FOLDER}}/{{SLUG}}/source/paras" "$WORK/books/{{LANG_FOLDER}}/{{SLUG}}/annot" \
         "$WORK/books/{{REF_FOLDER}}" "$WORK/others" "$WORK/work dir"
# the tools, the build script, the environment, the docs (with the languages' conventions)
cp -r "$SOFT/lib" "$SOFT/build.sh" "$SOFT/environment.yml" "$SOFT/docs" "$WORK/"
rm -rf "$WORK/lib/__pycache__"
# the finished edition to learn from -- its text, its notes, its batch files
cp -r "$SOFT/books/{{REF_SRC}}" "$WORK/books/{{REF_FOLDER}}/"
rm -rf "$WORK/books/{{REF_PATH}}/reader" "$WORK/books/{{REF_PATH}}/main.aux" \
       "$WORK/books/{{REF_PATH}}/main.log" "$WORK/books/{{REF_PATH}}/main.toc"
# ... and its annotation JSON, the ground truth its .tex was built from
[ -d "$SOFT/work dir/annot" ] && cp -r "$SOFT/work dir/annot" "$WORK/work dir/"
[ -d "$SOFT/work dir/src" ]   && cp -r "$SOFT/work dir/src"   "$WORK/work dir/"
# the new book's original, and its skeleton
cp "$SRC" "$WORK/others/"
cat > "$WORK/books/{{LANG_FOLDER}}/{{SLUG}}/book.json" <<'EOF'
{{BOOK_JSON}}
EOF
cat > "$WORK/books/{{LANG_FOLDER}}/{{SLUG}}/main.tex" <<'EOF'
{{MAIN_TEX}}
EOF
cat > "$WORK/PROMPT.md" <<'EOF'
{{PROMPT}}
EOF
echo "ready: $WORK"
echo "next:  cd \"$WORK\" && claude     then paste PROMPT.md (or say: read PROMPT.md and begin)"
'''

RETURN_SH = r'''#!/bin/sh
# Bring the finished edition of {{TITLE_LATIN}} back into the toolbox, and build it.
set -e
SOFT="{{ROOT}}"
WORK="{{FOLDER}}"

# the book itself -- its .tex, its sources, its annotation JSON, its notes --
# into its language's folder
mkdir -p "$SOFT/books/{{LANG_FOLDER}}"
cp -r "$WORK/books/{{LANG_FOLDER}}/{{SLUG}}" "$SOFT/books/{{LANG_FOLDER}}/"
rm -rf "$SOFT/books/{{LANG_FOLDER}}/{{SLUG}}/reader"          # the reader is rebuilt below
# the original it was made from, where book.json points
mkdir -p "$SOFT/others"
[ -f "$WORK/others/{{SOURCE_FILE}}" ] && cp "$WORK/others/{{SOURCE_FILE}}" "$SOFT/others/"

cd "$SOFT"
. lib/env.sh && parseh_env    # the ilya-frank environment, wherever it is (lib/env.sh)
./build.sh {{SLUG}}         # the PDF and the reader (minutes); ./build.sh --html for the reader alone
python3 lib/verify_book.py --help >/dev/null 2>&1 || true
FRANK_BOOK=books/{{LANG_FOLDER}}/{{SLUG}} python3 lib/verify_book.py
echo "done: open https://localhost:8765/books/  (or ./serve.sh restart if it is not running)"
'''

BOOK_JSON = '''{
  "slug": "{{SLUG}}",
  "language": "{{LANG}}",
  "gloss": "{{GLOSS}}",
  "title": "{{TITLE}}",
  "title_latin": "{{TITLE_LATIN}}",
  "title_en": "{{TITLE_EN}}",
  "author": "{{AUTHOR}}",
  "author_latin": "{{AUTHOR_LATIN}}",
  "year": "{{YEAR}}",
  "blurb": "{{BLURB}}",
  "main": "main.tex",
  "audio": null,
  "transcript": null,
  "source_pdf": "../../../others/{{SOURCE_FILE}}"{{SOURCE_PAGES}}
}'''

# \BookLang, \BookGloss and \FrankLib come before the preamble, which reads
# them; the preamble \providecommand's all three (\BookGloss as `en', which is
# what a book that says nothing means) so the reference's older main.tex still
# builds.  ../../../lib: the book sits two directories under books/.
MAIN_TEX = r'''%% {{TITLE_LATIN}} - {{AUTHOR_LATIN}} ({{LANG_NAME}}, glossed in {{GLOSS_NAME}}).  Build with:  ./build.sh {{SLUG}}
\newcommand{\BookLang}{{{LANG}}}
\newcommand{\BookGloss}{{{GLOSS}}}
\newcommand{\FrankLib}{../../../lib}
\newcommand{\BookTitle}{{{TITLE}}}
\newcommand{\BookAuthor}{{{AUTHOR}}}
\newcommand{\BookTitleLatin}{{{TITLE_LATIN_UPPER}}}
\newcommand{\BookAuthorLatin}{{{AUTHOR_LATIN}}}
\input{\FrankLib/frank-preamble.tex}
\input{\FrankLib/frank-frontmatter.tex}

% one \input per batch, added as each batch is assembled and checked:
% \input{ch1.tex}    % chapter 1, paragraphs 0-9
% \input{ch1b.tex}   % paragraphs 10-19
% ...

\end{document}'''


def page():
    refs = references()
    langs = lang_records()
    glosses = gloss_records()
    books = shelf()
    data = {"root": ROOT, "refs": refs, "langs": langs, "glosses": glosses,
            "books": books,
            "default_lang": languages.DEFAULT, "default_gloss": languages.DEFAULT_GLOSS,
            "prompt": prompt_template(),
            "setup": SETUP_SH, "ret": RETURN_SH, "book_json": BOOK_JSON,
            "main_tex": MAIN_TEX, "batch": 10}
    # The ways a draft may be cut, named once (lib/chunker.py) so this page
    # and the video's cannot come to disagree about what they offer.  All of
    # them are offered whatever is installed, and NOT disabled by what this
    # toolbox can do today: the language is chosen on this same form, so a
    # page rendered once cannot know which language the answer will be about,
    # and greying out `sense groups' because the DEFAULT language has no
    # dictionary would be wrong for every other one.  What each needs is said
    # beside the select, and a way that cannot be carried out falls back --
    # to the dictionary cut, or to one chunk per sentence -- rather than
    # failing.
    def how_opts(el_id):
        return ('<select id="%s">%s</select>'
                % (el_id, "".join('<option value="%s"%s>%s</option>'
                                  % (w, " selected" if w == chunker.DEFAULT_WAY else "",
                                     html.escape(chunker.WAY_LABEL[w]))
                                  for w in chunker.WAYS)))
    # each option carries the book's own language: the text box of the way
    # that adds to a book takes ITS face and direction, never the identity
    # select's, which is about a book that does not exist yet
    into_opts = "".join(
        '<option value="%s" data-lang="%s" data-dir="%s" data-langname="%s" data-name="%s">'
        '%s &mdash; %s</option>'
        % (esc(b["path"]), esc(b["lang"]), esc(b["dir"]), esc(b["lang_name"]), esc(b["name"]),
           esc(b["name"]), esc(b["rel"])) for b in books)
    lang_opts = "".join('<option value="%s">%s &mdash; %s</option>'
                        % (esc(L["code"]), esc(L["name"]), esc(L["native"]))
                        for L in langs)
    # two groups, because the two halves are not the same kind of thing: one
    # is a language with a folder under books/ and a conventions file, the
    # other a language this toolbox can only write and set
    gloss_opts = "".join(
        '<optgroup label="%s">%s</optgroup>'
        % (label, "".join('<option value="%s">%s &mdash; %s</option>'
                          % (esc(G["code"]), esc(G["name"]), esc(G["native"]))
                          for G in glosses if G["taught"] is taught))
        for taught, label in ((True, "taught here"), (False, "written in, not taught")))
    ref_opts = "".join('<option value="%s" data-lang="%s">%s (%s) &mdash; %s</option>'
                       % (esc(r["path"]), esc(r["lang"]), esc(r["title_latin"] or r["slug"]),
                          esc(r["lang_name"]), esc(r["stats"]))
                       for r in refs)
    # The card for "add to a book already here" is not offered when there is
    # nothing to add to.  The LANE stays in the markup whatever the shelf
    # holds -- every control it owns is read by save() and the draft restore,
    # and a missing one would take the whole script down on a toolbox with no
    # books yet, which is every first run.
    extend_hidden = "" if books else " hidden"
    return r'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Add a book &mdash; ''' + APP_NAME + r'''</title>
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/langs.css">
<link rel="stylesheet" href="/youtube/lib/style.css">
<script src="/lib/parseh.js"></script>
<style>
/* Both add pages sit at body.wizard main{max-width:820px} (youtube/lib/style.css),
   which already has its matching footer rule.  The 860px this page used to
   force was for the command blocks, and those are inside a <details> now. */
.step label{display:block;margin:10px 0 4px;font-size:13.5px;color:var(--dim)}
.step label.inline{display:flex;align-items:center;gap:8px;margin:0;flex-wrap:wrap}
.step input[type=text],.step input:not([type]),.step select,.step textarea{width:100%;font:inherit;
  font-size:14px;padding:7px 10px;border:1px solid var(--rule);border-radius:7px;
  background:var(--bg);color:var(--ink)}
.step label.inline select{width:auto}
/* the title and author fields are in the book's language: the face and the
   direction follow the select.  data-lang sits on #ident, the block that
   TRAVELS between the ways -- put it on a wrapper that stays behind and the
   fields lose their face the moment the block is moved into another lane. */
.step input[data-tl]{font-family:var(--tl-font,inherit)}
.step textarea{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;line-height:1.5;
  resize:vertical;white-space:pre}
.step .grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}
.step .grid .wide{grid-column:1/-1}
.step .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}
.step pre.cmd{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;line-height:1.55;
  background:var(--bg);border:1px solid var(--rule);border-radius:8px;padding:10px 12px;
  overflow:auto;max-height:420px;white-space:pre;color:var(--ink);margin:8px 0}
.step .why{font-size:13.5px;line-height:1.65;color:var(--dim)}
.step .why b{color:var(--ink)}
.step ol{padding-left:20px;margin:0}
.step li{font-size:13.5px;line-height:1.7;color:var(--dim);margin:2px 0}
.step code,.pathnote code,.fieldnote code{font-family:ui-monospace,Menlo,monospace;
  font-size:12px;background:var(--bg);border:1px solid var(--rule);border-radius:4px;padding:0 4px}
.step details{margin:8px 0 0}
.step summary{cursor:pointer;color:var(--dim);font-size:13.5px}
.stat{color:var(--accent);font-size:12.5px}
.stat.warn{color:var(--warn)}
/* the chapter is text in the book's language, not a command: it overrides
   the monospace the command blocks share, and wraps */
.step textarea[data-tl]{font-family:var(--tl-font,inherit);font-size:15px;
  line-height:1.8;white-space:pre-wrap}
/* the prose links wear the accent: the browser's own link colour is the one
   thing on these pages that follows neither theme's palette */
.step a,.pathnote a,footer.idx a{color:var(--accent)}
/* a refusal from a door may be several lines (the control-character one
   quotes thirty characters of context under its sentence) and must read as
   it was written */
.note.bad{white-space:pre-wrap}
.note .row{margin-top:10px}
/* .wbtn was written for a <button>; the reader link in an answer is an <a>
   wearing it, and an inline box ignores the vertical padding */
a.wbtn{display:inline-block;text-decoration:none;color:var(--accent-fg)}

/* ---------------- the chooser ----------------
   Not a <fieldset>/<legend>: a legend inside a display:grid fieldset is the
   one layout engines still disagree about, and one taken as a grid item
   steals the first card's cell -- three cards silently become two and one.
   A <p> naming the group through aria-labelledby says the same thing to a
   screen reader and lays out the same everywhere. */
.qlab{display:block;margin:0 0 10px;font:400 13px/1.3 inherit;letter-spacing:.14em;
  text-transform:uppercase;color:var(--faint)}
.paths{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 6px}
.paths.two{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:760px){.paths,.paths.two{grid-template-columns:1fr}}
.path{display:block;width:100%;text-align:start;font:inherit;cursor:pointer;
  background:var(--card);color:var(--ink);border:1px solid var(--rule);
  border-radius:12px;padding:14px 15px 12px;transition:border-color .12s,transform .12s}
.path:hover{border-color:var(--accentlt);transform:translateY(-1px)}
.path:focus-visible{outline:2px solid var(--accentlt);outline-offset:2px}
.path b{display:block;font-size:15px;font-weight:600;color:var(--ink)}
.path span{display:block;margin-top:4px;font-size:12.5px;line-height:1.5;color:var(--dim)}
.path em{display:block;margin-top:8px;font-style:normal;font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--faint)}
/* "chosen" wears the chip row's own signature, so it reads here exactly as
   it does on every language row in the toolbox (parseh.css .chip.on) */
.path[aria-checked="true"]{border-color:var(--accent);background:var(--hl)}
.path[aria-checked="true"] em{color:var(--accent)}
.pathnote{max-width:34rem;margin:0 auto;padding:26px 0;text-align:center;
  color:var(--dim);font-size:13px;line-height:1.6}
.pathnote b{color:var(--ink)}
.pathnote .also{display:block;margin-top:10px;color:var(--faint);font-size:12px}

/* ---------------- one sentence under one control ----------------
   Requirement 4: every option says what it does, where it is, in a line.
   Anything longer than a line goes behind the way's own disclosure. */
.fieldnote{display:block;margin-top:4px;font-size:12px;line-height:1.5;color:var(--faint)}
.fieldnote b{color:var(--dim)}
.fieldnote.warn{color:var(--warn)}
.fieldnote.bad{color:var(--danger)}
/* a disabled button keeps its pointer events (style.css only dims it), so
   its title can still say what is missing -- but a touch screen never shows
   a title, and there the same sentence is printed instead */
.whysmall{display:none}
@media (max-width:620px){.whysmall{display:block}}

/* ---------------- the disclosure ----------------
   The narration panel's device, in this page's tokens: one button per way,
   opening one labelled box.  What is read once and never again must not sit
   between a person and the buttons. */
.hbtn{font:inherit;font-size:13px;padding:5px 10px;border:1px solid var(--rule);
  background:transparent;color:var(--dim);border-radius:6px;cursor:pointer;margin-top:14px}
.hbtn:hover{border-color:var(--accentlt);color:var(--accent)}
.hbox{background:var(--boxbg);border:1px solid var(--rule);border-radius:10px;
  padding:10px 12px;margin-top:10px}
.hlab{color:var(--dim);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
  margin-bottom:8px}
.hbox p{font-size:12.5px;line-height:1.55;color:var(--faint);margin:0 0 8px}
.hbox p:last-child{margin-bottom:0}
.hbox p b{color:var(--dim)}
.hbox label{margin-top:6px}
</style>
</head><body class="index wizard">
<div class="parseh-bar">
  <a class="home" href="/" title="the hub"><span class="glyph">&#x67E;</span>''' + APP_NAME + r'''</a>
  <span class="where"><a href="/books/">books</a> &rsaquo; add<span id="crumb"></span></span>
  <span class="sp"></span>
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
  <button type="button" class="stop" data-parseh-stop title="stop the server">&#9211; stop</button>
</div>
<main>
  <h1 class="idx">Add a book</h1>
  <p class="sub" style="max-width:46rem">A reading edition is made paragraph by paragraph,
  with a checker after every batch &mdash; days of work, not one answer.</p>

  <p class="qlab" id="q1lab">What are you doing?</p>
  <div class="paths" id="paths" role="radiogroup" aria-labelledby="q1lab">
    <button type="button" class="path" role="radio" aria-checked="false" tabindex="0"
            data-path="new" aria-controls="lane-new">
      <b>Write it here, by hand</b>
      <span>Paste a chapter. It is cut into paragraphs and sentences with every gloss left
        blank, and the reader opens on it.</span>
      <em>needs: the book&rsquo;s facts, and a chapter</em>
    </button>
    <button type="button" class="path" role="radio" aria-checked="false" tabindex="-1"
            data-path="extend" aria-controls="lane-extend" id="card-extend"''' + extend_hidden + r'''>
      <b>Add to a book already here</b>
      <span>More text onto the end of a book on the shelf. Nothing already written is touched
        or re-cut.</span>
      <em>needs: a book, and the text</em>
    </button>
    <button type="button" class="path" role="radio" aria-checked="false" tabindex="-1"
            data-path="llm" aria-controls="lane-llm">
      <b>Let an LLM do it outside</b>
      <span>Three things to copy: a script that builds a working folder, the prompt, and a
        script that brings the finished book back.</span>
      <em>needs: the facts, the original file, a folder &mdash; and a terminal. Nothing here
        is posted.</em>
    </button>
  </div>

  <p class="pathnote" id="nopath">Three ways in. <b>By hand</b> and <b>add to a book</b> write
    to the shelf straight away; <b>outside, with an LLM</b> only hands you things to copy.
    <span class="also">Already have an exported <code>&lt;slug&gt;-book.zip</code>? Bring it
      back from <a href="/books/">the library page</a>.</span></p>

<!-- ===================== way 1: write it here, by hand ===================== -->
<div id="lane-new" hidden>
<section class="step" id="step-new-1">
  <div class="shead"><span class="num">1</span><h2>The book</h2></div>
  <div class="sbody" id="facts-new">

  <!-- THE IDENTITY BLOCK, BUILT ONCE.  choose() MOVES it (appendChild) into
       the way that needs it -- ways 1 and 3.  A move keeps every value,
       every listener and the saved draft; a clone would fork all three. -->
  <div id="ident">
  <div class="grid">
    <label>Language <select id="lang">''' + lang_opts + r'''</select>
      <span class="fieldnote">The language the book teaches &mdash; it sets the folder it is
        filed under, the fonts it is set in, and the conventions it is annotated by.</span></label>
    <label>Glosses in <select id="gloss">''' + gloss_opts + r'''</select>
      <span class="fieldnote">The language the meanings are written <b>in</b>. An Italian
        learning Persian wants them in Italian.</span>
      <span class="fieldnote" id="glossnote"></span></label>
    <label class="wide">Slug (directory name, ascii) <input id="slug" placeholder="hekayat-e-…" autocomplete="off">
      <span class="fieldnote">The directory name. Left empty it is made from the
        transliterated title.</span>
      <span class="fieldnote" id="slugprev"></span></label>
    <label>Year <input id="year" placeholder="1921" title="Printed on the title page; it is written into book.json and shown on the library card."></label>
    <label><span id="title_lbl">Title, in the language</span> <input id="title" data-tl placeholder="فارسی شکر است"></label>
    <label>Title, transliterated <input id="title_latin" placeholder="Farsi shekar ast">
      <span class="fieldnote">The ascii spelling: the slug falls back to it, and the half
        title is set from it in capitals.</span></label>
    <label><span id="title_en_lbl">Title, in English</span> <input id="title_en" placeholder="Persian is Sugar">
      <span class="fieldnote">The title as the gloss language says it, for the library
        card.</span></label>
    <label><span id="author_lbl">Author, in the language</span> <input id="author" data-tl placeholder="محمدعلی جمال‌زاده"></label>
    <label>Author, transliterated <input id="author_latin" placeholder="Mohammad-Ali Jamalzadeh"
      title="Written into book.json and set as the byline of the half title."></label>
    <label class="wide">One-sentence blurb <input id="blurb" placeholder="What the book is.">
      <span class="fieldnote">One sentence, for the library card.</span></label>
  </div>
  </div>

  </div>
</section>

<section class="step" id="step-new-2">
  <div class="shead"><span class="num">2</span><h2>The chapter</h2></div>
  <div class="sbody">
  <label><span id="text_lbl">The chapter, in the language</span> &mdash; a blank line between
    paragraphs, or one to a line
    <textarea id="chtext" data-tl rows="10" spellcheck="false"></textarea></label>
  <div class="row">
    <label class="inline">Cut the text into ''' + how_opts("how") + r'''</label>
  </div>
  <span class="fieldnote">A chunk is what a reader hovers. <b>Sense groups</b> needs this
    language&rsquo;s installed dictionary and falls back to one chunk per sentence without it
    &mdash; either way you can re-cut any chunk in the reader.</span>
  </div>
</section>

<section class="step" id="step-new-3">
  <div class="shead"><span class="num">3</span><h2>Make it</h2></div>
  <div class="sbody">
  <div class="row">
    <button type="button" class="wbtn" id="mkempty">Make the draft</button>
    <span class="stat" id="estat"></span>
  </div>
  <span class="fieldnote whysmall" id="mkwhy"></span>
  <div id="eresult" aria-live="polite" hidden></div>
  <button type="button" class="hbtn" aria-expanded="false" aria-controls="how-new">how this works</button>
  <div class="hbox" id="how-new" hidden>
    <p><b>What it writes:</b> <code>book.json</code>, <code>main.tex</code>, the chapter&rsquo;s
      <code>.tex</code>, and the source files the fidelity checks read.</p>
    <p><b>It is marked a draft</b> while you work, so the checker forgives a chunk nobody has
      glossed yet and still catches a half-written one.</p>
    <p><b>For Japanese and Chinese</b> the word line is proposed by the toolbox and left for
      you to correct; every other line is blank.</p>
    <p><b>Sense groups</b> cuts at the edges of phrases &mdash; a preposition with its noun, a
      noun with its adjectives, a verb with its auxiliaries &mdash; reading the parts of speech
      out of the language&rsquo;s dictionary.</p>
    <p><b>The reader opens at once.</b> The card on <a href="/books/">the library page</a> is
      written with it; the PDF comes with the next <code>./build.sh</code>, or the button in
      the answer above.</p>
  </div>
  </div>
</section>
</div>

<!-- ===================== way 2: add to a book already here ================= -->
<div id="lane-extend" hidden>
<section class="step" id="step-add-1">
  <div class="shead"><span class="num">1</span><h2>Which book</h2></div>
  <div class="sbody">
  <div class="row">
    <label class="inline">Add to <select id="addinto">''' + into_opts + r'''</select>
      <span class="tag" id="addlang"></span></label>
  </div>
  <span class="fieldnote">Its language, its glosses and its title are the book&rsquo;s already
    &mdash; they are not asked again.</span>
  </div>
</section>

<section class="step" id="step-add-2">
  <div class="shead"><span class="num">2</span><h2>Where it goes</h2></div>
  <div class="sbody">
  <label class="inline"><input type="radio" name="addwhere" id="addwhere_new" value="new" checked>
    A new chapter</label>
  <span class="fieldnote">Its own opening and its own line in <code>main.tex</code> &mdash;
    another story, another lesson.</span>
  <label class="inline" style="margin-top:10px"><input type="radio" name="addwhere" id="addwhere_last" value="last">
    More of the last chapter</label>
  <span class="fieldnote">Continues it, its paragraphs numbered on from the ones already there.
    This is the only thing on the page that edits a file that already exists.</span>
  </div>
</section>

<section class="step" id="step-add-3">
  <div class="shead"><span class="num">3</span><h2>The text</h2></div>
  <div class="sbody">
  <label><span id="aptext_lbl">The text</span> &mdash; a blank line between paragraphs, or one
    to a line
    <textarea id="aptext" data-tl rows="10" spellcheck="false"></textarea></label>
  <div class="row">
    <label class="inline">Cut the text into ''' + how_opts("ahow") + r'''</label>
  </div>
  <span class="fieldnote">A chunk is what a reader hovers. <b>Sense groups</b> needs this
    language&rsquo;s installed dictionary and falls back to one chunk per sentence without it
    &mdash; either way you can re-cut any chunk in the reader.</span>
  </div>
</section>

<section class="step" id="step-add-4">
  <div class="shead"><span class="num">4</span><h2>Add it</h2></div>
  <div class="sbody">
  <div class="row">
    <button type="button" class="wbtn" id="addto">Add it</button>
    <span class="stat" id="addstat"></span>
  </div>
  <span class="fieldnote whysmall" id="addwhy"></span>
  <div id="addresult" aria-live="polite" hidden></div>
  <button type="button" class="hbtn" aria-expanded="false" aria-controls="how-add">how this works</button>
  <div class="hbox" id="how-add" hidden>
    <p><b>Nothing written before is touched or re-cut</b> &mdash; the old chapters are read
      only to be numbered on from.</p>
    <p><b>More of the last chapter</b> rewrites that chapter&rsquo;s file: its
      <code>\chapend</code> moves to the end of the new text, and
      <code>source/src_chN.json</code> is merged.</p>
    <p><b>It is marked a draft</b> while you work, so the checker forgives a chunk nobody has
      glossed yet and still catches a half-written one.</p>
  </div>
  </div>
</section>
</div>

<!-- ===================== way 3: an LLM, outside ============================ -->
<div id="lane-llm" hidden>
<section class="step" id="step-llm-1">
  <div class="shead"><span class="num">1</span><h2>The book</h2></div>
  <div class="sbody" id="facts-llm">
  <!-- #ident is moved in here by choose('llm') -->
  <div class="hbox">
    <div class="hlab">only for the outside folder</div>
    <label>Learn from <select id="ref">''' + ref_opts + r'''</select>
      <span class="fieldnote">A finished edition the LLM copies its method from &mdash; its
        notes and its annotation JSON are copied into the folder beside your book.</span>
      <span class="fieldnote" id="refnote"></span></label>
    <label>The original <input id="source" placeholder="/home/you/books/the-book.pdf">
      <span class="fieldnote">PDF with a text layer, epub or txt. The script copies it into
        the folder; nothing is uploaded anywhere.</span></label>
    <label>PDF pages, first&ndash;last <input id="pages" placeholder="13-21">
      <span class="fieldnote" id="pagesnote">0-based. Leave empty for the whole file.</span></label>
    <label>Working folder <input id="folder" placeholder="~/frank-the-book">
      <span class="fieldnote" id="foldernote">Where the LLM works, outside the toolbox.</span></label>
  </div>
  </div>
</section>

<section class="step" id="step-llm-2">
  <div class="shead"><span class="num">2</span><h2>Set the folder up</h2></div>
  <div class="sbody">
  <div class="note warn" id="llmwarn" hidden></div>
  <p class="why">Run this once in a terminal.</p>
  <details><summary>the setup script</summary><pre class="cmd" id="setup"></pre></details>
  <div class="row"><button type="button" class="wbtn quiet" data-copyraw="setup">copy the setup script</button></div>
  </div>
</section>

<section class="step" id="step-llm-3">
  <div class="shead"><span class="num">3</span><h2>Set Claude Code to work</h2></div>
  <div class="sbody">
  <ol>
    <li><code>cd</code> into the folder and start <code>claude</code>.</li>
    <li>Paste the prompt (it is also in the folder as <code>PROMPT.md</code>).</li>
    <li>Between batches, look at the draft PDF (<code>./build.sh --draft chNx</code>) and read
      a paragraph or two. The tools prove fidelity; they cannot judge a gloss.</li>
  </ol>
  <details id="pshow"><summary>The prompt, as copied</summary><pre class="cmd" id="prompt"></pre></details>
  <div class="row"><button type="button" class="wbtn quiet" data-copyraw="prompt">copy the prompt</button>
    <span class="stat" id="plen"></span></div>
  </div>
</section>

<section class="step" id="step-llm-4">
  <div class="shead"><span class="num">4</span><h2>Bring it back</h2></div>
  <div class="sbody">
  <p class="why">When every chapter is closed and <code>verify_book.py</code> is clean.</p>
  <details><summary>the return script</summary><pre class="cmd" id="ret"></pre></details>
  <div class="row"><button type="button" class="wbtn quiet" data-copyraw="ret">copy the return script</button></div>
  <button type="button" class="hbtn" aria-expanded="false" aria-controls="how-llm">how this works</button>
  <div class="hbox" id="how-llm" hidden>
    <p><b>The setup script copies</b> the tools, the reference edition with its notes and its
      annotation JSON, the original, and a <code>book.json</code> and <code>main.tex</code>
      skeleton, and writes the prompt as <code>PROMPT.md</code> in the folder.</p>
    <p><b>The return script</b> copies the finished
      <code>books/&lt;language&gt;/&lt;slug&gt;/</code> in, builds the PDF and the reader, and
      runs <code>verify_book.py</code>. The book then appears on
      <a href="/books/">the library page</a>.</p>
    <p><b>Nothing on this page is posted</b> &mdash; the three scripts are yours to copy and
      run, and the LLM works outside the toolbox without seeing this software.</p>
  </div>
  </div>
</section>
</div>
</main>
<footer class="idx">
  <span id="foot-all">A book is written paragraph by paragraph: the reader is rebuilt the
  moment text lands, the PDF with the next <code>./build.sh</code>.</span>
  <span id="foot-llm" hidden>The prompt is <code>docs/new-book-prompt.md</code>, the conventions
  per language <code>docs/lang/&lt;code&gt;.md</code>; the reference&rsquo;s own account of the
  method is <code>books/&lt;reference&gt;/NOTES.md</code>. Edit any and this page follows.</span>
</footer>
<script id="data" type="application/json">''' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + r'''</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById('data').textContent);
  var $ = function (id) { return document.getElementById(id); };
  var KEY = 'bk_add_draft';
  // the fields the outside folder's templates are built from: these, and
  // only these, re-render on every keystroke
  var FIELDS = ['lang', 'gloss', 'ref', 'slug', 'year', 'title', 'title_latin', 'title_en',
                'author', 'author_latin', 'blurb', 'source', 'pages', 'folder'];
  // saved and restored, but never a reason to re-render: the two texts feed
  // no template (re-rendering a 19 KB prompt on every keystroke of a pasted
  // chapter would make typing it a chore), and the rest feed only a body.
  // `how` had no listener at all before this: choosing "sense groups" was
  // never saved and silently reverted to one chunk per sentence on reload.
  var SAVE_ONLY = ['how', 'ahow', 'addinto', 'chtext', 'aptext'];
  var LANES = {'new': 'lane-new', 'extend': 'lane-extend', 'llm': 'lane-llm'};
  var PATH = '';
  var IDENT = $('ident');
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
  // every read and write of a control is guarded: the "add to a book" card
  // is not offered on an empty shelf, and a page whose script died on a null
  // would take save(), render() and every button down with it
  function val(id, v) {
    var el = $(id);
    if (!el) return '';
    if (v !== undefined && v !== null) el.value = v;
    return el.value;
  }
  FIELDS.concat(SAVE_ONLY).forEach(function (k) { if (saved[k]) val(k, saved[k]); });
  if (saved.addwhere === 'last') { if ($('addwhere_last')) $('addwhere_last').checked = true; }
  function addWhere() {
    return ($('addwhere_last') && $('addwhere_last').checked) ? 'last' : 'new';
  }
  // the language: the draft's if there is one, else the toolbox's shared
  // preference (the chip rows' pick, Parseh.lang), else the registry's default
  if (!saved.lang) {
    var pref = (window.Parseh && Parseh.lang && Parseh.lang.get) ? Parseh.lang.get() : 'all';
    var known = D.langs.some(function (l) { return l.code === pref; });
    val('lang', known ? pref : D.default_lang);
  }
  // the gloss has no shared preference to take: it is not what you are
  // reading, it is what you write, and English is what every book in the
  // toolbox is glossed in and what a book.json with no "gloss" means
  if (!saved.gloss) val('gloss', D.default_gloss);
  function save() {
    var o = {};
    FIELDS.concat(SAVE_ONLY).forEach(function (k) { o[k] = val(k); });
    o.addwhere = addWhere();
    o.path = PATH;
    try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {}
  }
  // the toolbox's one case fold, spliced in from languages.FOLD_JS, and then
  // the ASCII that NFKD leaves: the slug the studio's store makes for the
  // same title, character for character.  A plain toLowerCase knows nothing
  // of Turkish, and a directory name is where that shows worst -- it spells
  // İ as i plus a combining dot and leaves ı and the breve of ğ un-ASCII, so
  // "Yağmurlu bir kış" came out yag-murlu-bir-k-s.
  var foldCase = ''' + languages.FOLD_JS + r''';
  function slugify(s) {
    // the hyphens are stripped and THEN it is cut to 40, exactly as
    // draft.slugify does (re.sub(...).strip("-")[:40]); cutting first would
    // leave a trailing hyphen here and not there, and the directory way 3's
    // script creates would differ from the one way 1's door creates
    return foldCase(s).normalize('NFKD').replace(/[^\x00-\x7f]/g, '')
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
  }
  function fill(tpl, m) {
    return tpl.replace(/\{\{([A-Z_]+)\}\}/g, function (_, k) { return k in m ? m[k] : '{{' + k + '}}'; });
  }
  function jsonStr(s) { return JSON.stringify(String(s)).slice(1, -1); }
  function langRec() {
    return D.langs.filter(function (l) { return l.code === val('lang'); })[0] || D.langs[0];
  }
  function glossRec() {
    return D.glosses.filter(function (g) { return g.code === val('gloss'); })[0]
      || D.glosses.filter(function (g) { return g.code === D.default_gloss; })[0];
  }
  // The reference to learn from: one of the same language when there is one,
  // else the Persian one -- the method is the same, the conventions differ
  // and the prompt says so.  Called when the language changes; a choice made
  // by hand in the select afterwards stands until the language changes again.
  function pickRef() {
    var L = langRec();
    var same = D.refs.filter(function (r) { return r.lang === L.code; });
    var fa = D.refs.filter(function (r) { return r.lang === D.default_lang; });
    var r = same[0] || fa[0] || D.refs[0];
    if (r) val('ref', r.path);
  }
  function refRec() {
    return D.refs.filter(function (r) { return r.path === val('ref'); })[0] || D.refs[0] || {};
  }
  function slugNow() {
    return slugify(val('slug') || val('title_latin') || val('title') || 'new-book') || 'new-book';
  }
  // THE NAME, BEFORE IT CAN REFUSE.  draft._write refuses a directory that
  // already holds a book.json, whatever state that book is in -- so the list
  // compared against is every book on the shelf (D.books), not the built
  // ones: the likeliest collision of all is with a draft nobody has built.
  function taken(slug, folder) {
    return D.books.some(function (b) { return b.folder === folder && b.dirname === slug; });
  }
  function slugPreview() {
    var L = langRec(), slug = slugNow(), el = $('slugprev');
    if (!el) return;
    var hit = taken(slug, L.folder);
    el.className = 'fieldnote' + (hit ? ' warn' : '');
    el.innerHTML = hit
      ? (PATH === 'llm'
          ? 'a book is already at <code>books/' + esc(L.folder) + '/' + esc(slug) +
            '/</code> &mdash; the return script would copy over it'
          : 'a book is already at <code>books/' + esc(L.folder) + '/' + esc(slug) +
            '/</code> &mdash; choose another slug')
      : 'will be created as <code>books/' + esc(L.folder) + '/' + esc(slug) + '/</code>';
  }
  // The one pairing the reading editions refuse: a right-to-left gloss of a
  // left-to-right text.  The gloss block is one paragraph in the gloss's
  // direction, and a vocabulary line of Latin entries in it comes out with
  // its entries reversed, because the punctuation between them takes the
  // paragraph's direction (lib/frank-preamble.tex says it at length, and
  // stops the build).  The other three pairings all set: it is offered where
  // it works and taken off the list where it does not, rather than left to
  // be discovered by a LaTeX error days later.
  function applyGloss() {
    var L = langRec(), G = glossRec();
    var bad = function (g) { return g.dir === 'rtl' && L.dir !== 'rtl'; };
    Array.prototype.forEach.call($('gloss').options, function (o) {
      var g = D.glosses.filter(function (x) { return x.code === o.value; })[0];
      o.disabled = !!(g && bad(g));
    });
    if (bad(G)) { val('gloss', D.default_gloss); G = glossRec(); }
    var note;
    if (G.code === L.code)
      note = 'Glossed in the language it teaches: the meanings are definitions rather than ' +
             'translations. That is this book\'s choice, not a property of ' + L.name + '.';
    else if (G.taught)
      note = L.name + ' is what the reader is learning; ' + G.name +
             ' is what the book talks to them in.';
    else
      note = 'The meanings are written in ' + G.name + ', which this toolbox sets but does ' +
             'not teach: no folder under books/, no conventions file.';
    var off = D.glosses.filter(bad).map(function (g) { return g.name; });
    if (off.length)
      note += ' ' + off.join(' and ') + ' are greyed out: a right-to-left gloss of a ' +
              'left-to-right text cannot have its vocabulary lines set in order.';
    $('glossnote').textContent = note;
    // the one field the gloss-language refactor never reached: the label
    // follows the gloss, the key in book.json stays title_en
    $('title_en_lbl').textContent = 'Title, in ' + (G.name || 'English');
  }
  function applyLang() {
    var L = langRec();
    // data-lang rides on the block that TRAVELS between the ways: langs.css
    // hands --tl-font down from it to every input[data-tl] inside, and a
    // wrapper left behind in another lane would hand down nothing
    IDENT.setAttribute('data-lang', L.code);
    $('title_lbl').textContent = 'Title, ' + L.name;
    $('author_lbl').textContent = 'Author, ' + L.name;
    // the chapter is the book's own text: its face comes from langs.css
    // through data-lang, and Persian and Arabic read the other way
    $('text_lbl').textContent = 'The chapter, in ' + L.name;
    $('chtext').setAttribute('data-lang', L.code);
    $('chtext').setAttribute('dir', L.dir);
    $('chtext').setAttribute('lang', L.code);
    ['title', 'author'].forEach(function (id) {
      $(id).setAttribute('dir', L.dir); $(id).setAttribute('lang', L.code);
      // the Persian placeholders are the reference's; another language gets none
      $(id).placeholder = (L.code === D.default_lang)
        ? (id === 'title' ? 'فارسی شکر است' : 'محمدعلی جمال‌زاده') : '';
    });
    slugPreview();
  }
  // the book chosen to add to, by its name (the transliterated title, else
  // the title), for the activity list's label of its build
  function intoName() {
    var sel = $('addinto');
    var o = sel ? sel.options[sel.selectedIndex] : null;
    return o ? (o.getAttribute('data-name') || '') : '';
  }
  // THE OTHER TEXT BOX TAKES THE BOOK'S LANGUAGE, NOT THE SELECT'S.  The
  // book being added to has its own language in its own book.json, and
  // add_to_book reads it from there: pasting Persian into a Persian book
  // while the identity select says Italian used to give a left-to-right box
  // in the wrong face.  Run on every change of the select AND after the
  // draft is restored, or a reloaded page opens with the wrong one.
  function applyInto() {
    var sel = $('addinto');
    if (!sel) return;
    var o = sel.options[sel.selectedIndex];
    var code = o ? (o.getAttribute('data-lang') || '') : '';
    var dir = o ? (o.getAttribute('data-dir') || 'ltr') : 'ltr';
    var name = o ? (o.getAttribute('data-langname') || '') : '';
    var ta = $('aptext');
    if (code) { ta.setAttribute('data-lang', code); ta.setAttribute('lang', code); }
    ta.setAttribute('dir', dir);
    $('aptext_lbl').textContent = name ? ('The text, in ' + name) : 'The text';
    $('addlang').textContent = name;
  }
  function render() {
    // only way 3 reads any of this.  It used to rebuild four artefacts and a
    // ~19 KB prompt on every keystroke of fourteen fields, in ways where
    // nothing it produces is ever looked at.
    if (PATH !== 'llm') return;
    var L = langRec();
    var G = glossRec();
    var ref = refRec();
    var slug = slugNow();
    var src = val('source').trim();
    var srcFile = src ? src.replace(/^.*[\\/]/, '') : 'the-book.pdf';
    var folder = val('folder').trim() || ('$HOME/frank-' + slug);
    folder = folder.replace(/^~(?=\/|$)/, '$HOME');
    var pages = val('pages').trim(), pageArgs = '', pagesJson = '';
    var pm = pages.match(/^(\d+)\s*[-–]\s*(\d+)$/);
    if (pm) { pageArgs = '--from ' + pm[1] + ' --to ' + pm[2];
              pagesJson = ',\n  "source_pages": [' + pm[1] + ', ' + pm[2] + ']'; }
    // the working folder has a real default and needs no gate; it is simply
    // shown, so what the script will contain is on screen before it is run
    $('foldernote').textContent = 'Where the LLM works, outside the toolbox. Defaults to ' + folder + '.';
    // a page range that is not a range was dropped in silence, and the whole
    // file was extracted instead
    $('pagesnote').className = 'fieldnote' + (pages && !pm ? ' warn' : '');
    $('pagesnote').textContent = (pages && !pm)
      ? 'the page range is ignored: write it 13-21'
      : '0-based. Leave empty for the whole file.';
    // THE ONE GATE WAY 3 HAS EVER HAD.  Only the original is checked: with
    // it empty the scripts say /path/to/the-book.pdf and the user runs that.
    // The folder is NOT gated -- its default is correct and is printed above.
    var ready = !!src;
    $('llmwarn').hidden = ready;
    if (!ready) $('llmwarn').innerHTML = '<b>Name the original first</b> &mdash; without it ' +
      'the scripts are written with <code>/path/to/the-book.pdf</code> in them.';
    Array.prototype.forEach.call(document.querySelectorAll('[data-copyraw]'), function (b) {
      b.disabled = !ready;
      b.title = ready ? '' : 'name the original file first';
    });
    var sameLang = ref.lang === L.code;
    var refNote = sameLang ? '' :
      ' The reference is in ' + (ref.lang_name || 'Persian') + ', not in ' + L.name +
      ': the method is the same and the conventions differ -- the conventions of ' + L.name +
      ' below replace every ' + (ref.lang_name || 'Persian') + '-specific rule of the notes.';
    $('refnote').textContent = ref.path ? (sameLang
      ? 'A ' + L.name + ' edition to learn from: its notes and conventions apply as they are.'
      : 'No ' + L.name + ' edition is built yet, so the reference is the ' + (ref.lang_name || 'Persian') +
        ' one: the conventions of ' + L.name + ' are in the prompt and replace its language-specific rules.')
      : 'No built edition to learn from: build one first (./build.sh) and reload.';
    // the class the note is written with follows the class it is styled by:
    // it was 'why' and is now 'fieldnote', and the warn state has to ride
    // the new one or the note silently loses its styling on the first render
    $('refnote').className = 'fieldnote' + (ref.path && sameLang ? '' : ' warn');
    var kanaRule = (L.reading
      ? ' ' + L.name + ' is a **reading language**: every glossed chunk also carries `kana`, the reading of the ' +
        'whole chunk (never a per-character alignment); `assemble.py` writes it as `\\chr` and refuses a ' +
        'chunk without it, and `check_batch.py` reports one.'
      : '') + (L.words
      ? ' ' + L.name + ' also divides every glossed chunk into **words**, and the division is required: `words` is ' +
        'one line, the words parted by spaces and each word\'s ' + (L.reading ? 'kana' : L.translit_label) +
        ' after it in parentheses, and the words joined with nothing between them must be `fa` exactly (the ' +
        '`## Words` section of the conventions below is the rule). **The machine starts the words and the ' +
        'annotator corrects them** (step 2b): the division is never written from nothing. `words` never replaces ' +
        (L.reading ? '`kana`' : '`tr`') + ', which stays the reading of the whole chunk; `assemble.py` writes a ' +
        'chunk with words as `\\' + (L.reading ? 'chrw' : 'chw') + '` and `check_batch.py` checks the line, and ' +
        'warns about a paragraph none of whose chunks has one.'
      : '');
    // and how the words start: from the machine's proposal, exactly what a
    // text pasted into a draft gets, which the annotator then corrects
    var wordsStep = L.words
      ? '\n   For ' + L.name + ' every chunk\'s words start from the machine\'s, as a text pasted into a ' +
        'draft does. As soon as a paragraph\'s chunks are cut and their ' + (L.reading ? '`kana`' : '`tr`') +
        ' written, the annotator runs, with the environment\'s Python (the analyzers are in it),\n\n' +
        '   ```bash\n   python3 lib/fill_words.py --lang ' + L.code + ' --json books/' + L.folder + '/' + slug +
        '/annot/chN_pNN.json\n   ```\n\n' +
        '   which gives every chunk without words the proposed `words` -- each word\'s reading cut from the ' +
        'chunk\'s own -- and fills a reading still blank from the words. Then the annotator reads every line ' +
        'against `## Words` and corrects, in the JSON, the division and the readings: the proposal is where the ' +
        'words start, never where they end. A chunk cut again afterwards gets its `words` deleted and the tool ' +
        'run once more.\n'
      : '';
    // What the annotator has to be told once, at the top, because everything
    // it is shown to learn from was glossed in another language.  Nothing is
    // said when the reference already glosses in this one: there the examples
    // are the model for the wording as well as for the shape.
    var glossNote = (!ref.path || ref.gloss === G.code) ? '' :
      ' The reference edition is glossed in ' + ref.gloss_name + ' and yours is not: read its ' +
      '`en` fields and its vocabulary lines for the SHAPE of a gloss, never for its wording, ' +
      'and write every one of yours in ' + G.name + '.';
    var kanaExample = (L.reading || L.words)
      ? '\nFor ' + L.name + ' every chunk has ' +
        (L.reading ? 'the reading beside the transliteration' : '') +
        (L.reading && L.words ? ', and ' : '') + (L.words ? 'its words' : '') + ':\n\n' +
        '```json\n{"fa": "…"' + (L.words ? ', "words": "…"' : '') + (L.reading ? ', "kana": "…"' : '') +
        ', "tr": "…", "voc": "…", "en": "…"}\n```\n'
      : '';
    var m = {
      ROOT: D.root, FOLDER: folder, SLUG: slug, SOURCE_PATH: src || '/path/to/' + srcFile,
      SOURCE_FILE: srcFile, PAGE_ARGS: pageArgs, SOURCE_PAGES: pagesJson,
      TITLE: val('title').trim() || '…', TITLE_LATIN: val('title_latin').trim() || slug,
      // the half title is set in capitals, and the registry's code is the
      // locale that decides which: Turkish uppercases bir to BİR and kış to
      // KIŞ.  The browser carries that rule; a table of pairs written out
      // here would be a language's own spelling kept outside the registry
      TITLE_LATIN_UPPER: (val('title_latin').trim() || slug).toLocaleUpperCase(L.code),
      TITLE_EN: val('title_en').trim(), AUTHOR: val('author').trim() || '…',
      AUTHOR_LATIN: val('author_latin').trim() || '…', YEAR: val('year').trim(),
      BLURB: jsonStr(val('blurb').trim()),
      LANG: L.code, LANG_NAME: L.name, LANG_NATIVE: L.native, LANG_FOLDER: L.folder,
      GLOSS: G.code, GLOSS_NAME: G.name, GLOSS_NATIVE: G.native, GLOSS_NOTE: glossNote,
      LANG_CONVENTIONS: L.conventions, LANG_DIGIT_EXAMPLE: L.digit_example,
      LANG_LABEL_EXAMPLE: L.label_example, STRIP_NOTE: L.strip_note,
      TR_LABEL: L.translit_label, KANA_RULE: kanaRule, KANA_EXAMPLE: kanaExample,
      WORDS_STEP: wordsStep,
      REF_SLUG: ref.slug || '', REF_PATH: ref.path || '', REF_SRC: ref.src || '',
      REF_FOLDER: ref.folder || '',
      REF_LANG_NAME: ref.lang_name || '', REF_NOTE: refNote,
      REF_STATS: ref.stats || '', BATCH: String(D.batch),
      // a reference kept with its annotation JSON is worth pointing at; one without it is not
      WORKDIR_LINES: ref.annot
        ? "work dir/annot/          the reference's annotation JSON — the ground truth its .tex was built from\n" +
          "work dir/src/            its per-chapter source lists (src_chN.json), what assemble.py indexes into\n"
        : '',
      JSON_EXAMPLES: ref.annot
        ? "Hundreds of real ones are in `work dir/annot/`; the reference's `ch*.tex` show what they become."
        : "The reference's `ch*.tex` show what they become: read a chunk there back into this shape and you have the idea."
    };
    m.BOOK_JSON = fill(D.book_json, m);
    m.MAIN_TEX = fill(D.main_tex, m);
    var prompt = fill(D.prompt, m);
    m.PROMPT = prompt;
    $('prompt').textContent = prompt;
    $('plen').textContent = prompt.length + ' characters';
    $('setup').textContent = fill(D.setup, m);
    $('ret').textContent = fill(D.ret, m);
    slugPreview();
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }

  /* ---------------- which way, and only that way ---------------- */
  var CRUMB = {'new': ' &rsaquo; by hand', 'extend': ' &rsaquo; add to a book',
               'llm': ' &rsaquo; outside, with an LLM'};
  function choose(p, push, focusIt) {
    if (!LANES[p]) p = '';                       // an unknown ?path= falls back to the chooser
    if (p === 'extend' && !D.books.length) p = '';   // nothing to add to: the chooser, not an empty select
    PATH = p;
    Object.keys(LANES).forEach(function (k) { $(LANES[k]).hidden = k !== p; });
    Array.prototype.forEach.call(document.querySelectorAll('.path'), function (b) {
      var on = b.dataset.path === p;
      b.setAttribute('aria-checked', String(on));
      b.tabIndex = on ? 0 : -1;
    });
    if (!p) {                                    // nothing chosen: the first card is the way in
      var first = document.querySelector('.path:not([hidden])');
      if (first) first.tabIndex = 0;
    }
    $('nopath').hidden = !!p;
    $('crumb').innerHTML = CRUMB[p] || '';
    $('foot-all').hidden = (p === 'llm');
    $('foot-llm').hidden = (p !== 'llm');
    // A MOVE, NEVER A CLONE.  appendChild takes the block with its values,
    // its listeners and its place in the saved draft; a clone would fork all
    // three and show up only as "my title disappeared when I switched".
    if (p === 'new') $('facts-new').appendChild(IDENT);
    if (p === 'llm') $('facts-llm').insertBefore(IDENT, $('facts-llm').firstChild);
    if (p === 'llm') render();                   // the one gated call: way 3 must not open on empty <pre>s
    ticks();
    save();
    if (push) {
      try { history.replaceState(null, '', '/books/add/' + (p ? '?path=' + p : '')); } catch (e) {}
    }
    // the keyboard lands inside the way without the page moving; never on a
    // restore or a deep link, where the caret would jump into a textarea
    // before the cards have been read
    if (focusIt && p) {
      var el = $(LANES[p]).querySelector('input,select,textarea,button');
      if (el) el.focus({preventScroll: true});
    }
  }
  Array.prototype.forEach.call(document.querySelectorAll('.path'), function (b) {
    b.addEventListener('click', function () { choose(b.dataset.path, true, true); });
    b.addEventListener('keydown', function (e) {
      var keys = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1};
      if (!(e.key in keys)) return;
      e.preventDefault();
      var all = Array.prototype.filter.call(document.querySelectorAll('.path'),
                  function (x) { return !x.hidden; });
      var i = all.indexOf(b);
      var next = all[(i + keys[e.key] + all.length) % all.length];
      next.focus();
      choose(next.dataset.path, true, false);
    });
  });
  // a step's number becomes a ticked circle when what it asks for is there:
  // progress said by the control itself, which is what numbered instructions
  // are for (style.css .step.ok .num)
  function tick(id, ok) { var el = $(id); if (el) el.classList.toggle('ok', !!ok); }
  function ticks() {
    tick('step-new-1', !!val('title').trim());
    tick('step-new-2', !!val('chtext').trim());
    tick('step-add-1', !!val('addinto'));
    tick('step-add-3', !!val('aptext').trim());
    tick('step-llm-1', !!(val('title').trim() && val('source').trim()));
    gate();
  }
  // a button that cannot act says why, in its title -- and, where no title is
  // ever shown, in a line under it.  style.css dims a disabled .wbtn and
  // leaves its pointer events alone, so the tooltip is readable.
  function gate() {
    var why = !val('title').trim() ? 'the title comes first'
            : !val('chtext').trim() ? 'paste the chapter first' : '';
    $('mkempty').disabled = !!why;
    $('mkempty').title = why;
    $('mkwhy').textContent = why;
    var awhy = !val('addinto') ? 'there is no book here to add to yet'
             : !val('aptext').trim() ? 'paste the text first' : '';
    if ($('addto')) {
      $('addto').disabled = !!awhy;
      $('addto').title = awhy;
      $('addwhy').textContent = awhy;
    }
  }

  /* ---------------- the answers the doors give ---------------- */
  // The PDF is the one thing a writing way leaves undone, and this page has
  // never offered the button for it though parseh.js has exported it all
  // along: the library page and the reader both build from one.  `name` is
  // the book's name as the server names the build on the activity list, so
  // the pill says it from the click on.
  function buildRow(folder, slug, name) {
    return '<div class="row"><button type="button" class="wbtn quiet" data-buildnow="/books/' +
      esc(folder) + '/' + esc(slug) + '/__build" data-book="' + esc(name || '') +
      '">build the PDF now</button><span class="stat" data-buildsay></span></div>';
  }
  function wireBuild(res) {
    var b = res.querySelector('[data-buildnow]');
    if (!b) return;
    var say = res.querySelector('[data-buildsay]');
    b.onclick = function () {
      Parseh.buildBook(b.getAttribute('data-buildnow'), 'the PDF', {
        book: b.getAttribute('data-book') || '', button: b,
        say: function (msg, err) {
          say.textContent = msg;
          say.className = 'stat' + (err ? ' warn' : '');
        }
      });
    };
  }
  // The two doors' shared tail: the library card and the PDF are written by
  // other programs, and when one of them fails the book is still on disk.
  // Both keys came back before this and were dropped on the floor.
  function afterWrote(j) {
    var h = '';
    if (j.reader && !j.reader.ok)
      h += '<div class="note bad"><b>The reader was not built &mdash; the book is on disk, ' +
        'the page to read it is not:</b> ' + esc(j.reader.error || 'tex2html failed') + '</div>';
    if (j.library && !j.library.ok)
      h += '<div class="note warn"><b>The book is written, but the library page was not ' +
        'rewritten</b> &mdash; it will appear after the next build. ' +
        esc(j.library.error || '') + '</div>';
    return h;
  }
  // on the activity list while the server writes the book and builds its
  // reader (lib/activity.js, through parseh.js)
  function working(label) {
    return Parseh.working ? Parseh.working(label)
      : {url: function (u) { return u; }, end: function () {}};
  }
  // Every other button on this page copies something for you to run; these
  // two write the book itself, so what they say back is the endpoint's own
  // sentence -- a title that leaves no ascii for a directory name, a slug
  // already taken, a paragraph LaTeX cannot set -- never "failed".
  $('mkempty').onclick = function () {
    var text = val('chtext');
    if (!val('title').trim()) { Parseh.toast('the title comes first', true); $('title').focus(); return; }
    if (!text.trim()) { Parseh.toast('paste the chapter first', true); $('chtext').focus(); return; }
    var res = $('eresult'); res.hidden = true;
    $('estat').textContent = 'drafting…'; $('mkempty').disabled = true;
    var act = working('Writing the book ' + val('title').trim());
    fetch(act.url('/books/__empty'), {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({lang: val('lang'), gloss: val('gloss'),
        text: text, slug: val('slug').trim(),
        title: val('title').trim(), title_latin: val('title_latin').trim(),
        title_en: val('title_en').trim(), author: val('author').trim(),
        author_latin: val('author_latin').trim(), year: val('year').trim(),
        blurb: val('blurb').trim(), how: val('how')})})
      .then(function (r) { return r.json(); })
      .then(function (j) {
        act.end(!!j.ok);
        $('mkempty').disabled = false; $('estat').textContent = ''; res.hidden = false;
        gate();
        if (!j.ok) {
          res.innerHTML = '<div class="note bad"><b>' + esc(j.error || 'failed') + '</b></div>';
          res.scrollIntoView({behavior: 'smooth', block: 'nearest'});
          return;
        }
        var href = '/books/' + j.folder + '/' + j.slug + '/reader/';
        var h = '<div class="note good"><b>Drafted.</b> ' + j.paragraphs + ' paragraphs, ' +
          j.sentences + ' sentences, ' + j.chunks + ' blank chunks, in <code>books/' +
          esc(j.folder) + '/' + esc(j.slug) + '/</code>. <a href="' + esc(href) +
          '"><b>Open the reader &rarr;</b></a>' +
          // the name draft.py gave it: the transliterated title, else the slug
          buildRow(j.folder, j.slug, val('title_latin').trim() || j.slug) + '</div>';
        h += afterWrote(j);
        res.innerHTML = h;
        wireBuild(res);
        res.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        // where the glossing is actually done; the library page lists it at
        // once, and the PDF waits for the button above or the next build
        if (!j.reader || j.reader.ok) location.href = href;
      })
      .catch(function (e) { act.end(false); $('mkempty').disabled = false; $('estat').textContent = '';
        gate(); Parseh.toast(String(e), true); });
  };
  // Onto a book that is already here.  It posts to the BOOK's own address --
  // the select carries it -- so no slug travels in a body and the route
  // resolves it exactly as __delete does.
  if ($('addto')) $('addto').onclick = function () {
    var text = val('aptext'), into = val('addinto');
    if (!into) { Parseh.toast('there is no book here to add to yet', true); return; }
    if (!text.trim()) { Parseh.toast('paste the text first', true); $('aptext').focus(); return; }
    var res = $('addresult'); res.hidden = true;
    $('addstat').textContent = 'adding…'; $('addto').disabled = true;
    var act = working('Adding text to the book');
    fetch(act.url(into + '/__append'), {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text, how: val('ahow'), chapter: addWhere()})})
      .then(function (r) { return r.json(); })
      .then(function (j) {
        act.end(!!j.ok);
        $('addto').disabled = false; $('addstat').textContent = ''; res.hidden = false;
        gate();
        if (!j.ok) {
          res.innerHTML = '<div class="note bad"><b>' + esc(j.error || 'failed') + '</b></div>';
          res.scrollIntoView({behavior: 'smooth', block: 'nearest'});
          return;
        }
        var href = into + '/reader/';
        var parts = into.replace(/^\/books\//, '').split('/');
        var h = '<div class="note good"><b>Added.</b> ' + j.paragraphs + ' paragraphs, ' +
          j.sentences + ' sentences, ' + j.chunks + ' blank chunks, ' +
          (j.where === 'new' ? 'as chapter ' : 'onto the end of chapter ') + j.chapter + '.' +
          (j.pdf_stale ? '<span class="fieldnote">the PDF is out of date until the next build</span>' : '') +
          '<div class="row">' +
          '<a class="wbtn" href="' + esc(href) + '">Open the reader &rarr;</a>' +
          '<button type="button" class="wbtn quiet" id="addmore">Add another chapter</button>' +
          '</div>' +
          (parts.length >= 2 ? buildRow(parts[0], parts[1], intoName()) : '') +
          '</div>';
        h += afterWrote(j);
        res.innerHTML = h;
        wireBuild(res);
        // NO REDIRECT HERE, deliberately.  This way's rhythm is repeated
        // appends, and jumping to the reader broke it every time -- and hid
        // the counts, which were only ever seen when something failed.  The
        // reader is one click away.
        var again = $('addmore');
        if (again) again.onclick = function () {
          val('aptext', ''); save(); ticks(); $('aptext').focus();
          res.hidden = true;
        };
        res.scrollIntoView({behavior: 'smooth', block: 'nearest'});
      })
      .catch(function (e) { act.end(false); $('addto').disabled = false; $('addstat').textContent = '';
        gate(); Parseh.toast(String(e), true); });
  };

  /* ---------------- wiring ---------------- */
  FIELDS.forEach(function (k) {
    var el = $(k);
    if (!el) return;
    el.addEventListener('input', function () { save(); ticks(); render(); });
    el.addEventListener('change', function () { save(); ticks(); render(); });
  });
  SAVE_ONLY.forEach(function (k) {
    var el = $(k);
    if (!el) return;
    el.addEventListener('input', function () { save(); ticks(); });
    el.addEventListener('change', function () { save(); ticks(); });
  });
  ['addwhere_new', 'addwhere_last'].forEach(function (k) {
    var el = $(k);
    if (el) el.addEventListener('change', function () { save(); });
  });
  if ($('addinto')) $('addinto').addEventListener('change', function () { applyInto(); });
  $('lang').addEventListener('change', function () {
    applyLang(); applyGloss(); pickRef(); save(); ticks(); render(); });
  $('gloss').addEventListener('change', function () { applyGloss(); save(); render(); });
  Array.prototype.forEach.call(document.querySelectorAll('.hbtn'), function (b) {
    b.onclick = function () {
      var box = $(b.getAttribute('aria-controls'));
      var open = box.hidden;
      box.hidden = !open;
      b.setAttribute('aria-expanded', String(open));
    };
  });
  // RAW, not collapsed.  Parseh.copy squeezes every run of whitespace to one
  // space, which is right for a word and destroys a shell script: both setup
  // scripts carry heredocs and the prompt is ~15,000 characters of Markdown,
  // and all three arrived as a single unrunnable line.  The second argument
  // asks for the text exactly as it stands, and keeps the toast and the
  // execCommand fallback that a private clipboard call would have lost.
  Array.prototype.forEach.call(document.querySelectorAll('[data-copyraw]'), function (b) {
    b.onclick = function () {
      var el = $(b.dataset.copyraw);
      // a <pre> here and a <textarea> on the video page: read whichever the
      // element actually keeps its text in
      Parseh.copy(('value' in el) ? el.value : el.textContent, true);
    };
  });

  // THE ORDER MATTERS, now that render() is gated.  The draft is restored,
  // the language and the gloss are applied, the reference is picked -- and
  // only then is a way chosen, which performs the single gated render.  Turn
  // these around and a way-3 visitor's first prompt is built against
  // whichever reference happened to be first in a notes-first sort.
  applyLang();
  applyGloss();
  if (!saved.ref) pickRef();
  applyInto();
  var want = (location.search.match(/[?&]path=([a-z]+)/) || [])[1] || saved.path || '';
  choose(want, false, false);
})();
</script>
</body></html>
'''