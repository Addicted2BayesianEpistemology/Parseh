#!/usr/bin/env bash
# Build the README banner, light and dark, from docs/banner.tex.
#
#     cd docs && ./banner.sh
#
# XeLaTeX sets it in the toolbox's own faces and pdftocairo turns every glyph
# into a path, so the finished SVG needs no font on the machine that reads it.
# That is not a nicety: GitHub shows this to people who have neither nastaliq
# nor Devanagari, and text-as-text would come out as boxes.
#
# WHY pdftocairo AND NOT dvisvgm, which is the obvious tool and which this
# script tried first.  Both of dvisvgm's routes are wrong here, each in
# silence:
#
#   dvisvgm --pdf    drops every Devanagari glyph, no warning: a gap in the
#                    row where Hindi should be.
#   dvisvgm <.xdv>   keeps them and loses the POSITIONS: every line lands on
#                    the same point, the banner a pile of type in the corner,
#                    and again nothing said.
#
# The PDF XeLaTeX writes is right in both respects and pdftocairo -svg
# converts it whole.  So: PDF, then cairo.  The counts printed at the end are
# how you would notice either of those coming back.
#
# It also prints the language row back, read off the typeset page with
# pdftotext.  Once the glyphs are outlines the SVG says nothing about what it
# says, and the row being quietly one language short is exactly what happened
# twice before this file existed.
set -euo pipefail
cd "$(dirname "$0")"

for tool in xelatex pdftocairo; do
  command -v "$tool" >/dev/null || { echo "banner: $tool is not on PATH" >&2; exit 1; }
done

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

build () {                      # build <name> <extra TeX>
  local name="$1" pre="$2" i
  # Twice: eso-pic needs no second pass to find the page corner, but geometry
  # and the .aux do, and one run leaves the banner differing from the next
  # build of the same source for no visible reason.
  for i in 1 2; do
    xelatex -interaction=nonstopmode -halt-on-error \
            -output-directory="$work" -jobname="$name" \
            "$pre\\input{banner.tex}" >"$work/$name.out" 2>&1 || {
      echo "banner: xelatex failed; the last of its log:" >&2
      tail -25 "$work/$name.out" >&2
      exit 1
    }
  done
  # A face the machine has not got does not stop XeLaTeX: it substitutes and
  # says so in the log, and the banner comes out in the wrong hand with
  # nothing to show for it.  So the substitution is the error here.
  if grep -qE "does not contain|cannot be found|Missing character" "$work/$name.out"; then
    echo "banner: a font is missing, or a character is not in the face asked for it:" >&2
    grep -m5 -E "does not contain|cannot be found|Missing character" "$work/$name.out" >&2
    exit 1
  fi
  pdftocairo -svg "$work/$name.pdf" "banner-$name.svg"
}

build light ''
build dark  '\def\BannerDark{1}'

echo "  the languages, as the page carries them:"
# [[:space:]] and not ^$: the page ends with a form feed on a line of its own,
# which is not an empty line and would be the one printed
pdftotext "$work/light.pdf" - 2>/dev/null \
  | grep -v '^[[:space:]]*$' | tail -1 | sed 's/^/    /'

python3 - <<'PY'
import io, re, sys

# the attributes come out double-quoted from cairo and single-quoted from
# dvisvgm; read either, so a banner rebuilt with another tool still reports
Q = r'[\x27\x22]'
bad = False
for name in ("light", "dark"):
    p = "banner-%s.svg" % name
    s = io.open(p, encoding="utf-8").read()
    m = re.search(r"width=%s([\d.]+)\w*%s height=%s([\d.]+)" % (Q, Q, Q), s)
    uses, texts = s.count("<use "), s.count("<text")
    print("  %-18s %.2f x %.2f pt, %d glyphs, %d text elements"
          % (p, float(m.group(1)), float(m.group(2)), uses, texts))
    # A <text> element renders in whatever face the reader happens to have,
    # which for nastaliq and Devanagari is usually none at all.
    if texts:
        print("  ^ text was left as text: it will not render on a machine "
              "without the face", file=sys.stderr)
        bad = True
sys.exit(1 if bad else 0)
PY
