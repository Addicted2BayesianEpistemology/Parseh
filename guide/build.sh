#!/bin/sh
# Build this manual.
#
#   ./build.sh          compile the guide and refresh the copy in the root
#
# LuaLaTeX, because the example words of the four languages need HarfBuzz
# shaping (Persian and Arabic for the joining, Japanese for the CJK face and
# babel's own line breaking between characters), and because the bundled
# fonts live in ../lib/fonts (which is what OSFONTDIR is for -- same trick
# the books' build.sh uses).  Japanese is set in the system's Noto Serif CJK
# JP, which OSFONTDIR also covers through /usr/share/fonts.
set -e
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
OSFONTDIR="$ROOT/lib/fonts:/usr/share/fonts:/usr/local/share/fonts:$HOME/.local/share/fonts"
export OSFONTDIR

# Until the .aux and .toc stop changing (they are git-ignored, so a fresh
# clone starts without them).  Two passes are not enough here: the second
# typesets the table of contents from the first pass's page numbers, taken
# before the contents pages themselves existed, so every entry comes out two
# pages early; the third pass is the one that reads the settled numbers.
# Bounded, as latexmk bounds it, in case something never settles.
stamp() { cat user-guide.aux user-guide.toc 2>/dev/null | cksum; }
before=""
for pass in 1 2 3 4 5; do
  lualatex -interaction=nonstopmode user-guide.tex >/dev/null 2>&1 || true
  after="$(stamp)"
  [ "$after" = "$before" ] && break
  before="$after"
done

if [ ! -f user-guide.pdf ]; then
  echo "FAILED -- see guide/user-guide.log"
  exit 1
fi
# A LaTeX error under nonstopmode still leaves a PDF behind, with the
# offending piece silently dropped -- a mistyped macro in an example word
# would vanish from the manual and nobody would know.  So any '!' line in
# the log is a failed build, as it is for the books.
if grep -q '^!' user-guide.log; then
  echo "FAILED -- errors in guide/user-guide.log:"
  grep -n -A2 '^!' user-guide.log | head -30
  exit 1
fi
cp user-guide.pdf "$ROOT/HOW TO USE THIS TOOLBOX.pdf"
echo "guide/user-guide.pdf"
echo "$ROOT/HOW TO USE THIS TOOLBOX.pdf"
