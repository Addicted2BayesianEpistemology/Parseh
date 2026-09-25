#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Install Parseh on Linux or macOS, from the checkout.
#
#   ./install.sh              everything: the environment and its packages, the
#                             guide, the models the word analyzers download, then
#                             a report of what this machine has, and the readers
#   ./install.sh --check      only the report, the readers and the guide; installs nothing
#   ./install.sh --conda      make the environment with this machine's conda,
#                             not the checkout's own micromamba
#   ./install.sh --recreate   throw .runtime/env away and make it again
#   ./install.sh --json       the installing only, as JSON lines (docs/installer.md)
#   ./install.sh --align      the report also says what re-aligning a narration needs
#   ./install.sh --pdf        ... and fetches what TeX Live lacks for building a PDF
#   ./install.sh --guide      only compile the guide (html-guide/markdown/ into
#                             html-guide/site/, what the hub's guide button
#                             opens), and stop; nothing is installed
#
# Serving a built reader needs nothing but Python 3.  Rebuilding books,
# dividing Japanese and Chinese into words and the rest need the packages of
# environment.yml, and those live in one environment, ilya-frank, so the
# machine's own Python is never touched.  Where the machine has none, it is
# made in this folder, .runtime/env, with micromamba -- one program, downloaded
# into .runtime/bin -- so nothing needs installing first but curl, which Linux
# and macOS both have, and removing the folder removes all of it.  A conda
# user's `conda env create -f environment.yml` still works, and every script
# here finds that environment too (lib/env.sh).
#
# lib/runtime.py does the installing and says what it does; this script finds
# a Python to run it with -- or, on a machine with none at all (a new Mac),
# makes the environment first, in sh.
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"
ENVNAME=ilya-frank
ok=0; warn=0

say()  { printf '%s\n' "$*"; }
good() { printf '  ok    %s\n' "$*"; ok=$((ok+1)); }
bad()  { printf '  MISS  %s\n' "$*"; warn=$((warn+1)); }
skip() { printf '  --    %s\n' "$*"; }

want_align=""; want_pdf=""; check_only=""; as_json=""; pass=""; guide_only=""
for a in "$@"; do
  case "$a" in
    --guide)    guide_only=1 ;;
    --align)    want_align=1 ;;
    --pdf)      want_pdf=1 ;;
    --check)    check_only=1 ;;
    --json)     as_json=1; pass="$pass --json" ;;
    --conda)    pass="$pass --conda" ;;
    --recreate) pass="$pass --recreate" ;;
    *) echo "unknown argument: $a"; exit 2 ;;
  esac
done

# usable_python <python>: a Python 3.8 or newer that really runs -- not the stub
# a Mac without its command line tools answers `python3` with, which opens a
# dialog instead of running anything
usable_python() {
  if [ "$(uname -s)" = Darwin ] && [ "$1" = /usr/bin/python3 ] \
     && ! xcode-select -p >/dev/null 2>&1; then
    return 1
  fi
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1
}

# bootstrap_env: the environment made in sh, for a machine with no Python --
# micromamba into .runtime/bin, then .runtime/env from environment.yml
bootstrap_env() {
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)              plat=linux-64 ;;
    Linux-aarch64|Linux-arm64) plat=linux-aarch64 ;;
    Darwin-arm64)              plat=osx-arm64 ;;
    Darwin-x86_64)             plat=osx-64 ;;
    *) say "no micromamba for $(uname -s) $(uname -m): install Python 3, or conda and then ./install.sh --conda"
       exit 1 ;;
  esac
  mkdir -p .runtime/bin
  if [ ! -x .runtime/bin/micromamba ]; then
    say "downloading micromamba ($plat) ..."
    curl -fsSL -o .runtime/bin/micromamba.part \
      "https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-$plat"
    mv .runtime/bin/micromamba.part .runtime/bin/micromamba
    chmod +x .runtime/bin/micromamba
  fi
  say "making the environment in .runtime/env -- a few hundred megabytes, once ..."
  MAMBA_ROOT_PREFIX="$ROOT/.runtime/mamba" .runtime/bin/micromamba create -y \
    -r "$ROOT/.runtime/mamba" -p "$ROOT/.runtime/env" -f environment.yml
}

. "$ROOT/lib/env.sh"
parseh_env

# compile_guide: the guide's compiler is standard-library Python, so the
# environment's python3 runs it when there is one and the system's when not
compile_guide() {
  gpy="$PARSEH_PY"
  if ! usable_python "$gpy"; then gpy="$(command -v python3 || true)"; fi
  if [ -z "$gpy" ] || ! usable_python "$gpy"; then
    say "no Python 3 to compile the guide with"
    return 1
  fi
  "$gpy" html-guide/build.py
}

if [ -n "$guide_only" ]; then
  compile_guide
  exit $?
fi

if [ -z "$check_only" ]; then
  if ! usable_python "$PARSEH_PY"; then
    bootstrap_env
    parseh_env
  fi
  [ -n "$as_json" ] || say "== installing =="
  # $pass is a list of flags, split on purpose
  if ! "$PARSEH_PY" lib/runtime.py install --no-readers $pass; then
    [ -z "$as_json" ] || exit 1
    bad "the installation did not finish -- the lines above say why"
  fi
  [ -z "$as_json" ] || exit 0
  parseh_env                 # a new environment's python3 first from here on
  say ""
fi

say "== required to serve the reader =="
if command -v python3 >/dev/null 2>&1; then
  good "python3 ($(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))'))"
else
  bad "python3 — install it, nothing here works without it"; exit 1
fi

# The web fonts travel with the reader as woff2, so a bare server needs no
# fonts for Persian or Arabic; which files that means is the registry's
# business (lib/languages.json, fonts.web_files), not this script's.
webfonts="$(python3 -c 'import sys; sys.path.insert(0, "lib"); import languages
print(" ".join(sorted(set(f for L in languages.LANGS.values() for f in L.fonts.get("web_files") or []))))')"
missing_fonts=""
for f in $webfonts; do
  [ -f "lib/fonts/$f" ] || missing_fonts="$missing_fonts $f"
done
if [ -z "$missing_fonts" ]; then
  good "bundled web fonts ($webfonts)"
else
  bad "lib/fonts/ lacks$missing_fonts — copy them from a working checkout"
fi

# The books: books/<language>/<slug>/, and -- the layout before languages --
# books/<slug>/ itself; lib/books.py knows both, so the list comes from it
# (one line per book: dir, language, name, whether it is legacy).  A
# narration is optional, and each book says in its book.json where its own is.
booklist="$(mktemp)"
trap 'rm -f "$booklist"' EXIT
python3 -c 'import sys; sys.path.insert(0, "lib"); import books
for b in books.all_books():
    print("\t".join([b.dir, b.rel_from_books(), b.lang.name,
                     "legacy" if b.folder is None else ("misfiled" if b.folder != b.lang.folder else "")]))' > "$booklist"
if [ ! -s "$booklist" ]; then
  skip "no book under books/ yet (books/<language>/<slug>/ with a book.json is all it takes)"
fi
booklangs=""
tab="$(printf '\t')"
while IFS="$tab" read -r bdir brel bname bnote; do
  case "$bnote" in
    legacy)   bad "$brel lies directly under books/ — it reads as Persian; move it to books/persian/$brel" ;;
    misfiled) bad "$brel is filed under the wrong language folder for a $bname book (see book.json)" ;;
    *)        good "book $brel ($bname)" ;;
  esac
  booklangs="$booklangs|$bname|"
  for key in audio transcript; do
    f="$(python3 -c "import json,os,sys;v=json.load(open(sys.argv[1])).get(sys.argv[2]);print(os.path.normpath(os.path.join(os.path.dirname(sys.argv[1]),v)) if v else '')" "$bdir/book.json" "$key")"
    [ -n "$f" ] || continue
    [ -f "$f" ] && good "$f ($(du -h "$f" | cut -f1))" \
                || bad "$f — $brel declares it; copy it there, or use the picker in the page"
  done
  [ -f "$bdir/timings.json" ] && good "$brel/timings.json (the alignment)" \
                              || skip "$brel/timings.json (no narration aligned yet)"
done < "$booklist"

# The CJK languages are the ones whose faces are not bundled (a CJK font is
# tens of megabytes, and there are two of them): when there is content in
# one, the machine must have its font, or the reader and the player fall back
# to whatever the browser finds.  Which languages those are is the registry's
# answer (tex.script) and not a list here, and fontconfig knows each of them
# by the registry's own code.  The list carries code:folder and not the name,
# those two being the fields that are certainly one word apiece; the name is
# asked for inside the loop, where a space in it costs nothing.
cjk="$(python3 -c 'import sys; sys.path.insert(0, "lib"); import languages
print(" ".join("%s:%s" % (L.code, L.folder)
               for L in languages.LANGS.values() if L.tex.get("script") == "CJK"))')"
cjk_have=""; cjk_missing=""
for row in $cjk; do
  ccode="${row%%:*}"; cfolder="${row#*:}"
  cname="$(python3 -c 'import sys; sys.path.insert(0, "lib"); import languages
print(languages.get(sys.argv[1]).name)' "$ccode")"
  chas=""
  case "|$booklangs|" in *"|$cname|"*) chas=1 ;; esac
  for d in "books/$cfolder"/*/ "youtube/videos/$cfolder"/*/; do
    [ -d "$d" ] && chas=1
  done
  # the face the registry asks for by name, which is the one the PDF needs;
  # any other font covering the language only saves the browser, so the two
  # are reported apart rather than as one yes.
  cface="$(python3 -c 'import sys; sys.path.insert(0, "lib"); import languages
print(languages.get(sys.argv[1]).tex.get("main") or "")' "$ccode")"
  if [ -z "$chas" ]; then
    skip "$cname font (no $cname book or video yet)"
  elif ! command -v fc-list >/dev/null 2>&1; then
    skip "$cname font check (no fc-list; macOS ships CJK faces of its own, which the pages use)"
  elif [ -n "$cface" ] && [ -n "$(fc-list "$cface" family 2>/dev/null | head -1)" ]; then
    cjk_have="$cjk_have $cname"
    good "$cface is installed (what a $cname page is set in)"
  elif [ -n "$(fc-list :lang=$ccode 2>/dev/null | head -1)" ]; then
    cjk_missing="$cjk_missing $cname"
    bad "no $cface — a $cname page falls back to another face the machine has, and its PDF cannot build:  sudo apt install fonts-noto-cjk"
  else
    cjk_missing="$cjk_missing $cname"
    bad "no $cname font — Debian/Ubuntu: sudo apt install fonts-noto-cjk;  Fedora: sudo dnf install google-noto-serif-cjk-fonts;  macOS: brew install --cask font-noto-serif-cjk"
  fi
done

say ""
say "== the environment (everything that rebuilds) =="
if [ -n "$PARSEH_PREFIX" ]; then
  good "the '$ENVNAME' environment ($PARSEH_PREFIX)"
else
  bad "no '$ENVNAME' environment — ./install.sh makes one (./install.sh --conda: with your conda)"
fi
# every package environment.yml lists and every program it carries, as
# lib/runtime.py names them, asked of the environment's python3 (lib/env.sh
# put it first on the PATH)
envreport="$(python3 -c 'import sys; sys.path.insert(0, "lib"); import runtime
st = runtime.status()
for p in st["packages"]:
    print(("ok " if p["have"] else "miss ") + "%s — %s" % (p["name"], p["what"]))
for t in st["tools"][:len(runtime.ENV_TOOLS)]:
    print(("ok " if t["path"] else "miss ") + "%s — %s" % (t["program"], t["what"]))' 2>/dev/null || true)"
while IFS= read -r line; do
  case "$line" in
    ok\ *)   good "${line#ok }" ;;
    miss\ *) bad "${line#miss } — ./install.sh adds it" ;;
  esac
done <<ENVREPORT
$envreport
ENVREPORT

say ""
say "== optional: rebuilding the PDF =="
if command -v lualatex >/dev/null 2>&1; then
  good "lualatex ($(lualatex --version | head -1 | cut -c1-40))"
  if [ -n "$want_pdf" ] && command -v tlmgr >/dev/null 2>&1; then
    # a minimal TeX Live (TinyTeX) has none of these
    # (extsizes: the studio's large print, its 14, 17 and 20 pt classes;
    # pgf: TikZ, which draws a flashcard's round frame on paper)
    for pkg in luatexbase fancyhdr environ etoolbox geometry xcolor fontspec babel-english tex-gyre hyperref bookmark microtype enumitem needspace titlesec booktabs graphics extsizes pgf; do
      tlmgr info --only-installed "$pkg" >/dev/null 2>&1 \
        && good "tex: $pkg" || { bad "tex: $pkg"; tlmgr install "$pkg" || true; }
    done
    # The hyphenation patterns, one package per language that has any.  Which
    # languages those are is the registry's answer (tex.hyphen, null for the
    # scripts that do not hyphenate) and TeX Live names each package after the
    # language in English, so what follows is a rule and not a list: the
    # seventh hyphenating language is checked the day it is added.
    #
    # Nothing about a missing one is loud.  \babelprovide[import=de] still
    # brings the locale, the quotation marks and the case pairs, and only the
    # patterns are absent, so babel writes "Hyphen rules for 'ngerman' set to
    # \l@english" once into the .log and then breaks the whole book at English
    # points -- Fre-und-schaft for Freund-schaft, print-emps for prin-temps,
    # faleg-name for fa-le-gna-me -- in a PDF that compiles clean and looks
    # right to anyone who cannot read it.
    #
    # Installed is not the same as reachable, which is why the second check is
    # here: the patterns arrive through language.dat, and a stale copy of that
    # file earlier in the kpse path shadows the one tlmgr generates, leaving
    # tlmgr saying yes while babel still falls back to English.
    hyphs="$(python3 -c 'import sys; sys.path.insert(0, "lib"); import languages
print(" ".join("%s=hyphen-%s" % (L.tex["hyphen"], L.name.lower())
               for L in languages.LANGS.values() if L.tex.get("hyphen")))')"
    for pair in $hyphs; do
      hname="${pair%%=*}"; pkg="${pair#*=}"
      tlmgr info --only-installed "$pkg" >/dev/null 2>&1 \
        || { bad "tex: $pkg"; tlmgr install "$pkg" || true; }
      langdat="$(kpsewhich language.dat 2>/dev/null || true)"
      if [ -n "$langdat" ] && grep -q "^$hname " "$langdat" 2>/dev/null; then
        good "tex: $pkg (babel's '$hname' patterns)"
      else
        bad "tex: '$hname' is in no language.dat, so its books break at ENGLISH points — run:  tlmgr generate language && fmtutil-sys --all"
      fi
    done
  else
    skip "TeX package check (pass --pdf)"
  fi
  # LuaLaTeX needs real ttf/otf, which the woff2 are not; build.sh points
  # OSFONTDIR at these, so nothing is installed system-wide
  if [ -f lib/fonts/Vazirmatn-Regular.ttf ] && [ -f lib/fonts/NotoNastaliqUrdu-Regular.ttf ] \
     && [ -f lib/fonts/NotoNaskhArabic-Regular.ttf ]; then
    good "lib/fonts/*.ttf (what LuaLaTeX reads)"
  else
    bad "lib/fonts/*.ttf — building them from the woff2"
    python3 - <<'PY' || echo "     could not build them; conda activate ilya-frank and retry"
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
f = TTFont("lib/fonts/Vazirmatn.woff2")           # variable: pin each weight
for wght, style in ((400, "Regular"), (700, "Bold")):
    g = instancer.instantiateVariableFont(TTFont("lib/fonts/Vazirmatn.woff2"),
                                          {"wght": wght}, updateFontNames=True)
    g.flavor = None; g.save("lib/fonts/Vazirmatn-%s.ttf" % style)
n = TTFont("lib/fonts/NotoNastaliqUrdu.woff2")
n.flavor = None; n.save("lib/fonts/NotoNastaliqUrdu-Regular.ttf")
# the Arabic naskh's woff2 is the regular weight; the bold ships as a ttf
a = TTFont("lib/fonts/NotoNaskhArabic.woff2")
a.flavor = None; a.save("lib/fonts/NotoNaskhArabic-Regular.ttf")
print("     built lib/fonts/*.ttf")
PY
  fi
  # a CJK book is set in the face the registry names (Noto Serif CJK JP for
  # Japanese, CJK SC for Chinese); LuaLaTeX finds it through the system,
  # never through lib/fonts/.  The search happened above; this only says what
  # it costs here.
  if [ -n "$cjk_missing" ]; then
    bad "no font for:$cjk_missing (fonts-noto-cjk) — those books' PDFs cannot build"
  elif [ -n "$cjk_have" ]; then
    good "a CJK font for LuaLaTeX ($(echo $cjk_have))"
  fi
else
  skip "lualatex (only needed to rebuild the PDF)"
fi

say ""
say "== optional: re-running the alignment, cutting a card's recording =="
command -v ffmpeg    >/dev/null 2>&1 && good "ffmpeg"    || bad "ffmpeg (silence snapping will be skipped; a card's recording is recorded in the browser instead of cut)"
command -v pdftotext >/dev/null 2>&1 && good "pdftotext" || bad "pdftotext (poppler-utils; only for re-extracting the source)"
[ -n "$want_align" ] && say "  (run:  python3 lib/timestamp.py --book <slug>)"

say ""
say "== optional: reading a book nobody has glossed yet =="
# None of the three is required, and none is installed by this script: a
# toolbox without them is exactly the toolbox it has always been, and the
# switch simply does not appear.  They are reported because a dictionary
# built months ago and forgotten is the kind of thing you want told.
if python3 - <<'PY' 2>/dev/null
import sys
sys.path.insert(0, "lib")
import languages, lookup
have = [L.code for L in languages.LANGS.values() if lookup.available(L.code)]
sys.exit(0 if have else 1)
PY
then
  say "  ok    a dictionary for: $(python3 -c 'import sys;sys.path.insert(0,"lib");import languages,lookup;print(" ".join(L.code for L in languages.LANGS.values() if lookup.available(L.code)))')"
  ok=$((ok+1))
else
  skip "no dictionary in dict/ — the lookup is not offered"
  say "        get one:    open Settings, Reading help once the server is running,"
  say "                    and press Get it beside your language — three clicks,"
  say "                    no account, nothing to sign up for"
  say "                    or  python3 lib/getdict.py <code>   (fa, hi, zh, ...)"
fi
if python3 -c 'import sys;sys.path.insert(0,"lib");import corpus;sys.exit(0 if corpus.installed() else 1)' 2>/dev/null; then
  say "  ok    sentences somebody translated: $(python3 -c 'import sys;sys.path.insert(0,"lib");import corpus;print(" ".join("%s-%s" % p for p in corpus.installed()))')"
  ok=$((ok+1))
else
  skip "no parallel corpus — the panel lists senses but shows no example sentence"
  say "        get one:    Settings, Reading help, or  python3 lib/getcorpus.py <code>"
fi
if python3 -c 'import sys;sys.path.insert(0,"lib");import getmt;sys.exit(0 if getmt.installed() else 1)' 2>/dev/null; then
  say "  ok    a translation model in the page: $(python3 -c 'import sys;sys.path.insert(0,"lib");import getmt;print(" ".join("%s-%s" % p for p in getmt.installed()))')"
  ok=$((ok+1))
else
  skip "no translation model — the reader cannot translate a line for you"
  say "        get one:    Settings, Reading help, or  python3 lib/getmt.py <from> <to>"
  say "                    about 20 MB a pair, and it runs in the page itself"
fi
if python3 -c 'import sys;sys.path.insert(0,"lib");import getsyn;sys.exit(0 if getsyn.installed() else 1)' 2>/dev/null; then
  say "  ok    a synonym table for the machine's reading (mt/synonyms.en.json)"
  ok=$((ok+1))
else
  skip "no synonym table — a mark still comes from the word itself, never a synonym of it"
  say "        get one:    Settings, Reading help, or  python3 lib/getsyn.py"
  say "                    about a megabyte, from WordNet (Princeton University)"
fi
say ""
say "== optional: dividing Japanese and Chinese into words =="
# The analyzers are Python packages of the conda environment, not files in the
# checkout.  Without them a new chunk simply gets no word line, which is always
# legal, and the word strip in the reader divides it by hand (lib/words.py).
for wlang in ja zh; do
  if python3 -c "import sys;sys.path.insert(0,'lib');import segmenter;sys.exit(0 if segmenter.available('$wlang') else 1)" 2>/dev/null; then
    good "words cut by machine for $wlang ($(python3 -c "import sys;sys.path.insert(0,'lib');import segmenter;print(segmenter.about('$wlang')['analyzer'])"))"
  else
    skip "no word analyzer for $wlang in $(command -v python3) — its chunks are divided by hand"
    say "        get it:     ./install.sh"
  fi
done
if python3 -c 'import spacy_pkuseg' 2>/dev/null; then
  # the models pkuseg downloads for itself: the words, and their parts of
  # speech, without which a Chinese clause is cut at its punctuation alone
  for mrow in $(python3 -c 'import sys; sys.path.insert(0, "lib"); import segmenter
print(" ".join("%s:%d" % (m["name"], m["have"]) for m in segmenter.models("zh")))'); do
    if [ "${mrow#*:}" = 1 ]; then
      good "pkuseg's ${mrow%%:*} model, for Chinese (${PKUSEG_HOME:-$HOME/.pkuseg})"
    else
      skip "pkuseg's ${mrow%%:*} model is not downloaded — Chinese is cut and read less well without it"
      say "        fetch it:   python3 lib/words.py --fetch zh   (./install.sh does)"
    fi
  done
fi
say ""
say "== building the readers =="
./build.sh --html
if [ -n "$check_only" ]; then
  # without --check lib/runtime.py compiled it, as its `guide` step
  say ""
  say "== compiling the guide =="
  compile_guide || bad "the guide did not compile -- the lines above say why"
fi

say ""
say "$ok checks passed, $warn missing."
say ""
say "Start it with:   ./serve.sh          (background, survives the terminal)"
say "             or:   python3 serve.py   (foreground, Ctrl-C to stop)"
say "It binds every interface, so any device on your Tailscale network can open"
say "the address it prints.  Use --local to keep it to this machine."
