# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.manifest -- the files the guide takes from Parseh, named once.

Read by studio.py (where to import from), export.py (what to snapshot into
engine/vendor/) and fingerprint.py (what a compile depends on).  Plain data
and nothing imported, so the Parseh server can ask what the guide depends on
without loading the studio's renderer into its own process.
"""

# the modules the engine imports, by their path in Parseh
MODULE_FILES = ("lib/languages.py", "lib/languages.json",
                "markdown/exlex/mdparser.py", "markdown/exlex/texgen.py",
                "markdown/app/htmlgen.py")
# the licences the fonts travel with (lib/fonts/): copied into
# site/_parseh/fonts/ beside the fonts themselves
FONT_LICENCES = ("OFL.txt", "GUST-FONT-LICENSE.txt", "README.md")
# what a compiled page loads at run time, copied into site/_parseh/
RUNTIME_FILES = ("markdown/app/static/app.js", "markdown/app/static/app.css",
                 "lib/mathjax.js", "lib/mathjax.css",
                 "lib/mathjax/tex-svg.js", "lib/mathjax/LICENSE",
                 "lib/mathjax/README.md") + tuple("lib/fonts/" + n for n in FONT_LICENCES)
# where the toolbox keeps the fonts the studio's sheet names
FONT_DIRS = ("lib/fonts", "markdown/exlex/assets/fonts", "markdown/app/static/fonts")
# the directory under site/ the runtime files are copied to
RUNTIME_DIR = "_parseh"
