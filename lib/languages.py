#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The languages Parseh teaches -- one registry, read everywhere.

    from languages import get, LANGS, DEFAULT, by_folder, detect_from_path
    L = get("ja")
    L.name, L.native, L.folder, L.dir, L.rtl        # Japanese, 日本語, japanese, ltr, False
    L.has_script("漢字")                             # True: a run of the target script
    L.run_re                                        # compiled: maximal runs of the target script
    L.strip("دَر")                                  # marks off (harakat for fa/ar; identity for ja/it)
    L.to_latin_digits("۳.۱۲") / L.to_native_digits("3.12")
    L.reading                                       # True when the language has a kana-like reading
    L.passes                                        # the reading editions' passes, in order
    L.vb_labels                                     # the two labels a \vb gloss prints
    L.vb_forms                                      # what its three forms are, in words
    L.vb_video_bare                                 # a video's \vb line without the marks (ar)
    L.as_json()                                     # what a page embeds for its script

    from languages import gloss, GLOSS_CODES, DEFAULT_GLOSS
    G = gloss("it")                                 # what the glosses are WRITTEN in
    G.name, G.dir, G.babel, G.taught                # Italian, ltr, italian, True

The table itself is lib/languages.json, beside this file: names, folders,
scripts, digits, fonts, TeX names, passes, Anki note-type ids.  Nothing else
in the toolbox holds a list of languages; adding one means adding an entry
there (docs/languages.md says what each field does and what else a new
language needs).

The target-language text is stored under the key `fa` in every data format
(video chunks, Anki cards, the .tex chunks read by texparse) -- the name is
from the days the toolbox knew Persian alone, and it is kept because every
tool and every stored file uses it.  Read it as "the foreign text".  Its
opposite number, the meaning, is stored under `en` for the same historical
reason and is read as "the gloss": which language the gloss is actually
WRITTEN in is `gloss()` below, and it is a per-book, per-video choice.

Standard library only: this is imported by the server, which has nothing
else.
"""
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.realpath(__file__))
REGISTRY = os.path.join(HERE, "languages.json")
DEFAULT = "fa"          # the toolbox's first language: what undeclared content is


class Lang:
    def __init__(self, code, d):
        self.code = code
        self.name = d["name"]
        self.native = d.get("native") or d["name"]
        # ISO 639-3, because the corpora are keyed by it and Parseh is
        # keyed by 639-1.  For Persian the two differ by more than
        # length: `pes` is Western Persian and `fas` the macrolanguage,
        # and only the first has an export to download.
        self.iso3 = d.get("iso3") or ""
        self.folder = d["folder"]
        self.tag = d.get("tag") or d["folder"]
        self.dir = d.get("dir", "ltr")
        self.script = d.get("script", "latin")
        self.chars = d.get("chars")                 # regex ranges, or None (Latin script)
        # WHAT THE READING IS WRITTEN IN, where the language has one at all.
        # `chars` is the whole script -- for Japanese that is kana AND kanji
        # -- so it cannot tell a reading from the text it is the reading OF.
        # にほんご is a reading of 日本語 and 日本語 is not.
        self.reading_chars = d.get("reading_chars")
        self.word_sep = d.get("word_sep", " ")
        self.digits = d.get("digits") or "0123456789"
        self.strip_range = d.get("strip")           # regex ranges of marks the bare pass drops
        self.reading = bool(d.get("reading"))
        self.vertical = bool(d.get("vertical"))
        # WHETHER A CHUNK IS DIVIDED INTO WORDS, each with its own reading
        # (lib/wordline.py): kana over a Japanese word, pinyin over a Chinese
        # one.  A language that writes spaces has its words already.
        self.words = bool(d.get("words"))
        self.require_tr = bool(d.get("require_tr", True))
        self.translit_label = d.get("translit_label") or "transliteration"
        self.reading_label = d.get("reading_label")
        self.vocal_label = d.get("vocal_label") or "the sentence"
        self.bare_label = d.get("bare_label")
        # the two words a gloss prints before \vb's second and third forms
        # (fa pres./past, ar impf./masdar, ja stem/-te).  The same pair
        # lib/lang/<code>.tex sets as \FrankVbPres / \FrankVbPast, so the
        # reader and the PDF of one book label the same forms; the Persian
        # labels stand in for an entry written before the field existed.
        self.vb_labels = list(d.get("vb_labels") or ["pres.", "past"])[:2]
        # WHAT THE THREE FORMS ARE, in words -- fa infinitive / present stem /
        # past stem, zh verb / A了B / A不B.  The labels above are what the page
        # prints and are two abbreviations by design; the chunk editor also
        # has to tell whoever types a \vb what goes in each of the seven
        # slots, and it used to build that out of the labels -- "infinitive,
        # pres. stem, past stem" -- which told a Turkish annotator "stem
        # stem, aor. stem" and a Chinese one to give an infinitive Chinese
        # does not have.  Three strings, always: a row written
        # before the field existed reads as the neutral names below rather
        # than as Persian's, which would be a claim about its grammar.
        forms = [str(x) for x in (d.get("vb_forms") or []) if str(x).strip()]
        self.vb_forms = forms[:3] if len(forms) >= 3 else \
            ["dictionary form", "second form", "third form"]
        # A VIDEO'S VERB LINE WITHOUT THE MARKS, where the language's videos
        # are written without them: an Arabic caption is unvowelled and
        # docs/lang/ar.md's video line is `أراد arāda (IV) · impf. يريد
        # yurīdu · …`, while the dictionary's forms, and a book's \vb, carry
        # every haraka.  lib/verbs takes `strip` off the video's forms when
        # this is true; false, the default, leaves them as the book has them.
        self.vb_video_bare = bool(d.get("vb_video_bare", False))
        self.fonts = dict(d.get("fonts") or {})
        self.tex = dict(d.get("tex") or {})
        self.passes = [dict(p) for p in d.get("passes") or []]
        self.anki = dict(d.get("anki") or {})
        self.duration_units = list(d.get("duration_units") or [])
        self.chapter_words = list(d.get("chapter_words") or [])
        self.re_chars = re.compile("[%s]" % self.chars) if self.chars else None
        self.re_reading = (re.compile("^[%s\\s]+$" % self.reading_chars)
                           if self.reading_chars else None)
        if self.chars:
            if self.word_sep:
                self.run_re = re.compile(
                    "[%s]+(?:%s[%s]+)*" % (self.chars, re.escape(self.word_sep), self.chars))
            else:
                self.run_re = re.compile("[%s]+" % self.chars)
        else:
            self.run_re = None
        self._strip_re = re.compile("[%s]" % self.strip_range) if self.strip_range else None
        self._to_latin = str.maketrans(self.digits, "0123456789") \
            if self.digits != "0123456789" else None
        self._to_native = str.maketrans("0123456789", self.digits) \
            if self.digits != "0123456789" else None

    # --- script -----------------------------------------------------------
    @property
    def rtl(self):
        return self.dir == "rtl"

    @property
    def spaced(self):
        """Words are separated by spaces (Persian, Arabic, Italian); Japanese
        has no word separator, so a chunk is one word for every tool."""
        return bool(self.word_sep)

    @property
    def alt_pass(self):
        """The 'alt' pass, when the language has one: nastaliq for Persian,
        vertical for Japanese; None otherwise."""
        for p in self.passes:
            if p.get("key") == "alt":
                return p
        return None

    @property
    def pass_keys(self):
        return [p["key"] for p in self.passes]

    def has_script(self, s):
        """True when the text carries at least one character of the target
        script.  Always False for a Latin-script language: its text cannot
        be told from the prose around it, so it is marked, never detected."""
        return bool(self.re_chars and s and self.re_chars.search(s))

    def is_reading(self, s):
        """Is this written in what this language's READING is written in?

        A language with no reading, or one that has not said what its reading
        looks like, answers False to everything: there is nothing to check
        against, and guessing would refuse good answers.
        """
        return bool(self.re_reading and s and self.re_reading.match(s.strip()))

    def strip(self, s):
        """The bare form: the marks the vowelled pass carries taken off
        (harakat for Persian and Arabic).  Identity for the others."""
        return self._strip_re.sub("", s) if self._strip_re else s

    def to_latin_digits(self, s):
        return s.translate(self._to_latin) if self._to_latin else s

    def to_native_digits(self, s):
        return str(s).translate(self._to_native) if self._to_native else str(s)

    def split_words(self, s):
        """The words of a chunk, for the tools that count or address them.
        Japanese has no separator, so the chunk is its own single word."""
        if not self.spaced:
            return [s] if s else []
        return s.split()

    def css_font(self, alt=False):
        if alt:
            return self.fonts.get("css_alt") or self.fonts.get("css_main") or "serif"
        return self.fonts.get("css_main") or "serif"

    def html_attrs(self):
        return ' lang="%s" dir="%s"' % (self.code, self.dir)

    def as_json(self):
        """The record a page embeds for its script: everything the browser
        may need, the compiled regexes as their source strings."""
        return {"code": self.code, "name": self.name, "native": self.native,
                "folder": self.folder, "tag": self.tag, "dir": self.dir,
                "script": self.script, "chars": self.chars,
                "reading_chars": self.reading_chars,
                "word_sep": self.word_sep, "digits": self.digits,
                "iso3": self.iso3,
                "strip": self.strip_range, "reading": self.reading,
                "vertical": self.vertical, "words": self.words,
                "require_tr": self.require_tr,
                "translit_label": self.translit_label,
                "reading_label": self.reading_label,
                "vocal_label": self.vocal_label, "bare_label": self.bare_label,
                "vb_labels": self.vb_labels, "vb_forms": self.vb_forms,
                "fonts": {"css_main": self.css_font(), "css_alt": self.fonts.get("css_alt"),
                          "alt_key": self.fonts.get("alt_key"),
                          "alt_line_height": self.fonts.get("alt_line_height")},
                "passes": self.passes, "anki": self.anki}

    def __repr__(self):
        return "<Lang %s %s>" % (self.code, self.name)


def _load():
    with open(REGISTRY, encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for code, d in raw.items():
        if code.startswith("_") or not isinstance(d, dict):
            continue
        out[code] = Lang(code, d)
    if DEFAULT not in out:
        raise SystemExit("lib/languages.json has no entry for the default language %r" % DEFAULT)
    return out


LANGS = _load()
CODES = list(LANGS)
FOLDERS = {L.folder: L.code for L in LANGS.values()}


def get(code, default=None):
    """The language with this code.  Unknown -> the default when one is
    given, else KeyError: a misspelled code must not quietly become
    Persian in a tool that writes files."""
    code = (code or "").strip().lower()
    if code in LANGS:
        return LANGS[code]
    if default is not None:
        return LANGS[default] if isinstance(default, str) else default
    raise KeyError("unknown language %r (known: %s)" % (code, ", ".join(CODES)))


def get_or_default(code):
    """The language with this code, or the toolbox's default -- for content
    written before languages were declared, which is all Persian."""
    return get(code, DEFAULT)


def by_folder(folder):
    """The language whose folder this is ("persian" -> fa), or None."""
    code = FOLDERS.get((folder or "").strip().lower())
    return LANGS[code] if code else None


def detect_from_path(path):
    """The language a path sits under: the nearest component that is a
    language folder (books/japanese/<slug>, videos/persian/<id>,
    library/arabic/<id>).  None when no component is one."""
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    for p in reversed(parts):
        L = by_folder(p)
        if L:
            return L
    return None


# ------------------------------------------------------------------ the gloss
# A book or a video declares TWO languages: the one it TEACHES (`language`, a
# registry code) and the one its glosses are WRITTEN IN (`gloss`).  They are
# different questions -- an Italian learning English wants the meanings in
# Italian -- and the studio has asked them apart since it had a front matter
# (`target:` and `lang:`, docs/languages.md section 5).  This is that same
# answer, for the two doors that used to assume English.
#
# ABSENT MEANS ENGLISH.  Everything written before the field existed is
# glossed in English and says nothing, so no file has to be migrated and
# nothing that is in the toolbox today changes meaning.
DEFAULT_GLOSS = "en"

# A gloss language is PROSE, not a subject: somebody may gloss Persian in
# Spanish, and nobody studies Spanish here.  So what may be written in is the
# registry's languages PLUS the prose-only codes below -- the same set the
# studio accepts for `lang:`, because it is the same question at the other
# door and one document must not be sayable there and unsayable here.
#
# WHY THE TABLE IS HERE AND NOT READ OUT OF THE STUDIO'S COPY.  The studio's
# is `texgen._HYPHEN_PROSE`, and it answers the other half of the question --
# what TeX calls the patterns, and how few letters may be left on a line.
# Two things stop lib/ reading it.  It sits inside the studio, and importing
# it pulls the whole studio in behind it (the reason draft.slugify is written
# out a third time), and lib/ is what the server imports, so it may depend on
# nothing but the standard library and itself.
# And the dependency already runs the other way: texgen.py imports THIS file,
# and for a code the registry teaches its table holds None and takes the name
# from `tex.hyphen` -- so this is the end both doors can already reach, and
# the same deferral covers the codes when somebody comes to write it.
#
# A prose language cannot be a registry entry instead.  An entry there is a
# language somebody STUDIES: a folder under books/, a script, digits, fonts,
# passes, Anki note types, lib/lang/<code>.tex and docs/lang/<code>.md, every
# one of them checked by `newlang.py --check`.  Spanish has none of that and
# needs none -- it is a language the toolbox WRITES IN, not one it teaches --
# and inventing the rest of an entry to hold two strings would put a books/
# directory and a pair of Anki model ids in the way of a gloss.  Nothing here
# is a second list of the languages taught, either: a language the registry
# holds is not repeated below, and where a gloss code is one of them the
# registry names it, gives its direction and says what babel calls it.
# `_glosses()` takes the registry first and only then these, so a row here
# for a language that has since been TAUGHT is dead weight that says the
# opposite of this paragraph -- Spanish sat here until it became a language
# of its own, and was removed the day it did.
#
# Every row is left to right, and lib/frank-preamble.tex says so out loud:
# a gloss code the registry does not carry is taken there as Latin-script and
# LTR, because guessing otherwise would set a page backwards without a word.
# An RTL prose language added here is that file's business as well as this
# one's -- which is why the direction is a column and not an assumption.
#
# code -> (name, native name, what babel calls it, direction)
_PROSE = {
    "pt": ("Portuguese", "português", "portuguese", "ltr"),
    "nl": ("Dutch", "Nederlands", "dutch", "ltr"),
    "ca": ("Catalan", "català", "catalan", "ltr"),
    "ro": ("Romanian", "română", "romanian", "ltr"),
    "pl": ("Polish", "polski", "polish", "ltr"),
    "ru": ("Russian", "русский", "russian", "ltr"),
    # the two spellings of English that hyphenate differently: babel's
    # `english` is the American set, so a book glossed for British readers
    # has to be able to say so
    "en-gb": ("British English", "British English", "british", "ltr"),
    "en-us": ("American English", "American English", "USenglish", "ltr"),
}

# The ISO 639-2 spellings, resolved to the two-letter code: a writer told to
# give "the ISO code" sometimes gives three letters, and the studio's table
# has taken both for as long as it has existed.
_GLOSS_ALIAS = {"eng": "en", "ita": "it", "fra": "fr", "deu": "de", "spa": "es"}


class Gloss:
    """The language a book's or a video's glosses are written in.

    Deliberately not a `Lang`: a Lang has a folder, a script, digits, fonts
    and note types, and handing one back for Spanish would be a promise this
    toolbox cannot keep.  What a gloss needs is what a page and a preamble
    ask of it -- what to call it, which way it runs, what babel calls it --
    and `lang` when it happens to be a language the toolbox also teaches.
    """

    def __init__(self, code, name, native, babel, direction, lang=None):
        self.code = code
        self.name = name
        self.native = native or name
        self.babel = babel
        self.dir = direction
        self.lang = lang                # the Lang, when the toolbox teaches it too

    @property
    def rtl(self):
        return self.dir == "rtl"

    @property
    def taught(self):
        """True when the gloss language is also one of the eight: an English
        edition glossed in Persian has a registry record to draw a font from,
        a Spanish one has not (the roman sets it, as it sets every gloss)."""
        return self.lang is not None

    def html_attrs(self):
        return ' lang="%s" dir="%s"' % (self.code, self.dir)

    def as_json(self):
        """What a page embeds beside the target language's record: enough to
        label the gloss row and set a card's lang and dir."""
        return {"code": self.code, "name": self.name, "native": self.native,
                "dir": self.dir, "babel": self.babel, "taught": self.taught}

    def __repr__(self):
        return "<Gloss %s %s>" % (self.code, self.name)


def _glosses():
    """Every code a gloss may be written in: the registry's eight, each named
    by the registry, then the prose-only ones.  Registry first, so a prose
    row written for a code the registry teaches would be passed over rather
    than allowed to rename it -- there is one name for Italian on screen and
    it is the one the chip row shows."""
    out = {}
    for L in LANGS.values():
        out[L.code] = Gloss(L.code, L.name, L.native,
                            L.tex.get("babel") or L.code, L.dir, L)
    for code, (name, native, babel, direction) in _PROSE.items():
        if code not in out:
            out[code] = Gloss(code, name, native, babel, direction)
    return out


GLOSSES = _glosses()
GLOSS_CODES = list(GLOSSES)


def gloss(code=None):
    """The gloss language of a book or a video: THE function that answers it.

    Nothing said -> English, which is what every book and video written
    before the field existed means (docs/languages.md section 3).  An unknown
    code raises KeyError, exactly as `get` does and for the same reason: a
    tool that WRITES files must not gloss in a guessed language, and a typo
    quietly becoming English is the very thing the field exists to stop.
    Callers that must show the thing anyway ask `gloss_or_default` and report
    the code separately (books.Book.gloss_problem).
    """
    # A value that is not a string at all -- a number or a list in a
    # hand-edited book.json, a JSON body arriving at a route -- is spelled
    # out rather than tripped over: it is an unknown gloss language and a
    # sentence to read, never a traceback out of a request.  That is
    # check_annotations.lang_code's rule, one door earlier and for the same
    # field.
    if code is not None and not isinstance(code, str):
        code = str(code)
    key = (code or "").strip().lower().replace("_", "-")
    if not key:
        return GLOSSES[DEFAULT_GLOSS]
    key = _GLOSS_ALIAS.get(key, key)
    if key in GLOSSES:
        return GLOSSES[key]
    raise KeyError("unknown gloss language %r (a gloss may be written in: %s)"
                   % (code, ", ".join(GLOSS_CODES)))


def gloss_or_default(code):
    """The gloss language, or English when the code is one this toolbox
    cannot set -- for a reader that has to render the book regardless."""
    try:
        return gloss(code)
    except KeyError:
        return GLOSSES[DEFAULT_GLOSS]


_ALL_NATIVE = "".join(L.digits for L in LANGS.values() if L.digits != "0123456789")
_ALL_TO_LATIN = str.maketrans(
    _ALL_NATIVE, "".join("0123456789" for L in LANGS.values() if L.digits != "0123456789"))


def any_to_latin_digits(s):
    """Every language's digits -> Latin, for a tool that reads a label before
    it knows which language wrote it (\\parnum{۳.۱}, \\parnum{٣.١})."""
    return s.translate(_ALL_TO_LATIN)


# ------------------------------------------------------------------ case
# Unicode's locale-blind lower-casing spells the small form of Turkish's
# dotted capital İ (U+0130) as "i" + U+0307 -- two characters nobody types
# and nothing else matches.  Python and every browser do this, so any tool
# that lower-cases target text (a slug, a search key, a sort key) breaks on
# the commonest capital letter in Turkish unless it goes through here.
_LOWER = str.maketrans({"İ": "i"})              # İ -> i, no stray dot
_FOLD = str.maketrans({"İ": "i", "ı": "i", "̇": ""})


def lower(s):
    """str.lower() without the combining dot Unicode leaves behind: the
    lower case of İ is i, and the trailing U+0307 is an artefact of the
    default rule, not a letter anyone writes.  Loses nothing -- ı stays ı
    -- so a stored tag or title keeps its own spelling.  NFC first, so a
    decomposed İ (I + U+0307, which is what a Mac filename hands over) is
    the same letter as a typed one."""
    return unicodedata.normalize("NFC", s or "").translate(_LOWER).lower()


def fold(s):
    """The comparison form: `lower`, plus the dotted and dotless i folded
    together (İ I i ı all become i) and any stray combining dot dropped.

    For matching only -- a search box, a filter key, a slug, an alignment
    token -- never for anything displayed or stored as the user wrote it.
    A Turk types "iyi" for a heading that opens "İyi", and a keyboard
    without ı types "isik" for "ışık"; folding matches too generously,
    which for a filter is the harmless direction.  Every other language is
    untouched: none of them uses ı or İ, so their text folds to exactly
    what it always lower-cased to.  The dot is dropped after NFC has had
    its chance to compose it, so a transliteration's ṡ keeps its own."""
    return unicodedata.normalize("NFC", s or "").translate(_FOLD).lower()


# The same fold, as JavaScript, for the pages that filter text in the
# browser and must agree character for character with what a tool wrote
# into them (the reading edition's contents panel).  Kept beside `fold`
# because the two have to be read together to stay the same function.
FOLD_JS = ("s => (s || '').normalize('NFC')"
           ".replace(/[\\u0130\\u0131]/g, 'i')"
           ".replace(/\\u0307/g, '').toLowerCase()")


def digit_class():
    """A regex character class matching a digit of any known language."""
    return "0-9" + _ALL_NATIVE


def chips(counts=None):
    """[{code, name, native, folder, count}] for an index page's language
    row, in registry order.  `counts` maps code -> number of items."""
    counts = counts or {}
    return [{"code": L.code, "name": L.name, "native": L.native,
             "folder": L.folder, "dir": L.dir, "count": int(counts.get(L.code, 0))}
            for L in LANGS.values()]


if __name__ == "__main__":
    for L in LANGS.values():
        print("%-3s %-9s %-9s %s  digits=%s  passes=%s%s%s"
              % (L.code, L.name, L.folder, L.dir, L.digits, "/".join(L.pass_keys),
                 "  reading" if L.reading else "", "  vertical" if L.vertical else ""))
    print("glosses may be written in: %s" % ", ".join(GLOSS_CODES))


# ---------------------------------------------------------------- the pages
def css():
    """The per-language CSS tokens every page links (served as /lib/langs.css
    by the Parseh server and as static/langs.css by the studio alone).

    An element that carries data-lang="<code>" gets --tl-font (the main face),
    --tl-alt (the alternate face, or the main one again), --tl-dir and
    --tl-alt-lh (the leading the alternate face wants).  The stacks come
    from the registry, so no stylesheet names a font per language.
    """
    out = ["/* generated from lib/languages.json -- do not edit */", ":root{"]
    for L in LANGS.values():
        out.append("  --tl-font-%s:%s;" % (L.code, L.css_font()))
        out.append("  --tl-alt-%s:%s;" % (L.code, L.css_font(alt=True)))
    out.append("}")
    for L in LANGS.values():
        lh = L.fonts.get("alt_line_height") or 1
        out.append("[data-lang=%s]{--tl-font:var(--tl-font-%s);--tl-alt:var(--tl-alt-%s);"
                   "--tl-dir:%s;--tl-alt-lh:%s}" % (L.code, L.code, L.code, L.dir, lh))
    return "\n".join(out) + "\n"


def write_css(path=None):
    """Write css() to lib/langs.css (or `path`), so a reader opened straight
    off the disk -- or served as a plain file -- finds the tokens beside
    parseh.css.  Idempotent: rewritten only when the text changed."""
    path = path or os.path.join(HERE, "langs.css")
    text = css()
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return path
    except OSError:
        pass
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
    return path


def chips_html(counts=None, current=None, cls="parseh-langs", selector="[data-lang]"):
    """The language row of an index page: one chip per nonempty language, with a
    count, plus 'all'.  lib/parseh.js wires the clicks (the shared
    `parseh_lang` preference, Parseh.lang) and hides every element matching
    `selector` (inside <main>, or <body> without one; the row itself never)
    whose data-lang is not the picked language.  `selector` None makes a
    row that only records the preference (an add page's default, say).
    `current` pre-selects a chip server-side (else the script does)."""
    import html as _h
    counts = counts or {}
    cur = current or "all"
    if cur not in LANGS or int(counts.get(cur, 0)) <= 0:
        cur = "all"
    total = sum(int(v) for v in counts.values())
    bits = ['<div class="%s" role="group" aria-label="language"%s>'
            % (cls, (' data-lang-filter="%s"' % _h.escape(selector, quote=True))
               if selector else "")]
    bits.append('<button type="button" class="chip%s" data-pick="all">all'
                '<span class="n">%d</span></button>' % (" on" if cur == "all" else "", total))
    for L in LANGS.values():
        n = int(counts.get(L.code, 0))
        if n <= 0:
            continue
        # data-lang gives the native name (the .native span, which the
        # stylesheets set in var(--tl-font)) its own face through langs.css;
        # parseh.js never filters a chip (anything inside .parseh-langs is
        # excluded), so the attribute cannot hide the chip itself
        bits.append('<button type="button" class="chip%s" data-pick="%s" lang="%s" '
                    'data-lang="%s" title="%s"><span class="native">%s</span>'
                    '<span class="n">%d</span></button>'
                    % (" on" if cur == L.code else "", L.code, L.code, L.code,
                       _h.escape(L.name, quote=True), _h.escape(L.native), n))
    bits.append("</div>")
    return "".join(bits)
