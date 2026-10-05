# SPDX-License-Identifier: GPL-3.0-or-later
"""Who made Parseh, and where to find him: his name and his two addresses,
kept ONCE.

THE OWNER ASKED FOR THESE (TO-DO §15.17, 2026-09-25; the places were decided
with him on 2026-09-28): his name and links to his GitHub and to his website,
in a few places and no more --

  * two links, and only the two, at the foot of the hub (the browser layout
    and the mobile one), of the guide (every page, and its front page, which
    is written by hand) and of the Settings hub;
  * his name beside "the author", and the same two links, on the Licences
    page (lib/notices.py) and in the README's License section, where the
    copyright line is "Copyright (c) 2026 Bruno Ursino".
  * his name and the two links on the installation's About settings page.

NEVER in what a person makes or keeps: a book's reader, a document, a deck, a
card, a printed page, an exported page.  tests/test_author.py holds that.

LINKS ONLY.  Nothing is fetched from either address -- no icon, no picture,
no font, no script -- so a page that carries them is drawn the same offline.
A link is followed only when it is clicked, in a tab of its own, and
`noreferrer` keeps a Parseh reached by a LAN or VPN address from telling
either site where it lives.

STANDARD LIBRARY ONLY, AND NO OTHER PARSEH MODULE: the guide's compiler
(html-guide/engine) imports this file and must run with nothing else, and a
guide exported with `build.py --export` carries a copy of it in
engine/vendor/ (html-guide/engine/manifest.py MODULE_FILES).
"""
import html

NAME = "Bruno Ursino"

# The ACCOUNT Parseh lives under, not the repository: lib/updater.py's REPO is
# "<this account>/Parseh", and tests/test_author.py holds the two together.
GITHUB_URL = "https://github.com/Addicted2BayesianEpistemology"
SITE_URL = "https://imbrunoursino.net/"

# What a link SAYS.  The two words are all a foot shows; what a screen reader
# announces and a hover shows is the label, which names the person.  The label
# always CONTAINS the words the link shows (WCAG 2.5.3, label in name), so a
# person who speaks to the page and says what they see hits the right link.
GITHUB_TEXT = "GitHub"
SITE_TEXT = "imbrunoursino.net"
GITHUB_LABEL = NAME + " on " + GITHUB_TEXT
SITE_LABEL = SITE_TEXT + ", " + NAME + "'s website"

# the year of the copyright line: the year of the first release
YEAR = 2026

# the separator every place uses between the two links, as the mobile hub's
# licence line uses it between its own two phrases
SEP = " &middot; "


def link(url, text, label):
    """One link: opens in a tab of its own, tells the site nothing about where
    it was followed from, and carries `label` for a screen reader and for a
    hover.  No script, no icon, nothing to fetch."""
    return ('<a href="%s" target="_blank" rel="noopener noreferrer" aria-label="%s" '
            'title="%s">%s</a>'
            % (html.escape(url, quote=True), html.escape(label, quote=True),
               html.escape(label, quote=True), html.escape(text)))


def github_link():
    return link(GITHUB_URL, GITHUB_TEXT, GITHUB_LABEL)


def site_link():
    return link(SITE_URL, SITE_TEXT, SITE_LABEL)


def links():
    """The two links, side by side -- the whole of a foot's signature:
    GitHub · imbrunoursino.net"""
    return github_link() + SEP + site_link()


def row():
    """The same two links as the items of a flex row (the mobile hub's last
    line), the dot between them an item of its own and hidden from a screen
    reader, which reads two links and no punctuation."""
    return github_link() + '<span aria-hidden="true">&middot;</span>' + site_link()


def copyright_line():
    """The copyright line the Licences page and the README carry, in HTML."""
    return "Copyright &copy; %d %s" % (YEAR, html.escape(NAME))


def notice(app):
    """The Licences page's line: the copyright, who holds it and where he is."""
    return "%s, the author of %s &mdash; %s" % (copyright_line(), html.escape(app), links())
