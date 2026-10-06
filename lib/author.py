# SPDX-License-Identifier: GPL-3.0-or-later
"""Who made Parseh, and where to find him: his name and his two addresses,
kept ONCE.

THE OWNER ASKED FOR THESE (TO-DO §15.17, 2026-09-25; the places were decided
with him on 2026-09-28): his name and links to his GitHub and to his website,
in a few places and no more --

  * two links, and only the two, at the foot of the hub (the browser layout
    and the mobile one), of the guide (every page, and its front page, which
    is written by hand) and of the Settings hub: the FOOT;
  * his name beside "the author", and the same two links, on the Licences
    page (lib/notices.py) and in the README's License section, where the
    copyright line is "Copyright (c) 2026 Bruno Ursino": the AUTHOR LINE.
  * his name and the two links on the installation's About settings page.

THE FOOT'S GITHUB IS THE PROJECT'S, THE AUTHOR LINE'S IS THE PERSON'S (the
owner, 2026-10-06).  Both say "GitHub" and both are followed by his website,
but the word at a foot leads to Parseh's repository -- the address the page
is handed (lib/project.py's GITHUB_URL, which this file may not import) --
and a screen reader and a hover say "Parseh on GitHub"; beside his name, on
the Licences page, in About and in the README, it leads to his own profile
(GITHUB_URL below) and says "Bruno Ursino on GitHub".  The foot is made by
foot_links() and foot_row(), the author line by links() and notice().

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
engine/vendor/ (html-guide/engine/manifest.py MODULE_FILES), and of
lib/project.py, which is where the compiler reads the address it hands to
foot_links().
"""
import html

NAME = "Bruno Ursino"

# The PERSON's GitHub profile, not the project's repository: the address of the
# author line (the Licences page, About, the README), where his name stands beside
# it.  The project lives in an organisation (lib/project.py, since a0.4.4) and he
# stays where he is, so this is a person's address and that one an organisation's:
# tests/test_author.py holds the two apart.  A FOOT does not use this one: it is
# handed the project's (foot_links).
GITHUB_URL = "https://github.com/Addicted2BayesianEpistemology"
SITE_URL = "https://imbrunoursino.net/"

# What a link SAYS.  The two words are all a foot shows; what a screen reader
# announces and a hover shows is the label, which says whose the address is: the
# person's, or -- at a foot, the first link -- the project's (project_link).  The
# label always CONTAINS the words the link shows (WCAG 2.5.3, label in name), so a
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
    """HIS GitHub: the profile, said as his -- the author line's."""
    return link(GITHUB_URL, GITHUB_TEXT, GITHUB_LABEL)


def project_link(url, name):
    """THE PROJECT'S GitHub, the foot's first link: the word is the same, the
    address is the repository's -- handed in, because this file may import no
    other Parseh module (lib/project.py's GITHUB_URL and NAME) -- and a screen
    reader and a hover say "Parseh on GitHub"."""
    return link(url, GITHUB_TEXT, name + " on " + GITHUB_TEXT)


def site_link():
    return link(SITE_URL, SITE_TEXT, SITE_LABEL)


def links():
    """HIS two links, side by side -- the author line's: GitHub · imbrunoursino.net,
    the first his profile (the Licences page, About).  A foot is foot_links()."""
    return github_link() + SEP + site_link()


def foot_links(project_url, project_name):
    """A FOOT's two links, side by side -- the whole of its signature:
    GitHub · imbrunoursino.net, the first the project's repository (the hub's
    browser layout, the Settings hub, every page of the guide and its front page)."""
    return project_link(project_url, project_name) + SEP + site_link()


def foot_row(project_url, project_name):
    """A foot's two links as the items of a flex row, the dot between them an item
    of its own and hidden from a screen reader, which reads two links and no
    punctuation: the mobile hub's last line."""
    return project_link(project_url, project_name) + '<span aria-hidden="true">&middot;</span>' + site_link()


def copyright_line():
    """The copyright line the Licences page and the README carry, in HTML."""
    return "Copyright &copy; %d %s" % (YEAR, html.escape(NAME))


def notice(app):
    """The Licences page's line: the copyright, who holds it and where he is."""
    return "%s, the author of %s &mdash; %s" % (copyright_line(), html.escape(app), links())
