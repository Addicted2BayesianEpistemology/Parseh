#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""CHANGELOG.md, read: its versions, newest first, their dates and what each
one says (TO-DO §16.2).

    import changelog
    for s in changelog.read():        # newest first, as the file has them
        s.version, s.date, s.released, s.body, s.line
    changelog.top()                   # the newest section: the one being made
    changelog.find("a0.3.1").body     # the notes a release is cut with
    changelog.said("2026-09-24")      # "24 September 2026", as the guide writes it
    heads, before = changelog.guide_page()   # the guide's "What's new": its
                                             # versions and days, and "Before ..."

ONE READER.  Three things read the changelog and must read it alike: the
release check (the tag, VERSION and the top heading agree, and that heading
is not "unreleased"), the notes a release is published with (the section of
its version, word for word), and the guide's test that "What's new" has the
same versions in the same order with the same dates.  Each asks this module,
so a heading one of them accepts is a heading all of them accept -- and the
guide's page is read here too (whats_new(), at the foot), since the release
check holds the tagged version's day on it as well.

THE HEADINGS ARE THE CONTRACT.  A section opens on a line spelt exactly

    ## [a0.3.1] - 2026-09-24          released, on that day
    ## [a0.4.0] - unreleased          still being made: only ever the top one

and runs to the next such line; its `###` headings (Added, Changed, Removed,
Fixed) and bullets are its body, which nothing here reads into.  Anything
before the first section is a preamble and ignored.  EVERY OTHER LINE THAT
BEGINS "## " IS REFUSED, and so is a version lib/version.py cannot parse or a
rehearsal's name (a0.3.2-rc1: a tag, whose notes are a0.3.2's), a
date that is not a day of the calendar, a version twice, a version out of
order (each must be earlier than the one above it, by version.compare) and a
date later than the one above it.  Refusing is the point: a heading spelt a
little wrong would otherwise be read as no heading at all, and its version
would quietly vanish from every check at once -- the very mistake these
checks exist to catch.
"""
import datetime
import os
import re
import sys
from collections import namedtuple

HERE = os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import version  # noqa: E402

ROOT = version.ROOT
FILE = "CHANGELOG.md"
UNRELEASED = "unreleased"
HEADING = re.compile(r"## \[(?P<version>[^\]\s]+)\] - (?P<date>\d{4}-\d{2}-\d{2}|%s)" % UNRELEASED)
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

# version: as the heading spells it; date: "YYYY-MM-DD", or None while the
# version is unreleased; released: whether it has a date; body: the text under
# the heading, blank lines at its ends taken off; line: the heading's line
# number, counted from 1
Section = namedtuple("Section", "version date released body line")


class ChangelogError(ValueError):
    """The changelog says something this reader will not guess at."""


def _held(v, where, n):
    """A heading's version, held to lib/version.py: spelt as one, and not a
    rehearsal's name -- a rehearsal (a0.3.2-rc1) is a tag the version it
    rehearses is tried out under, and has no section of its own: its notes
    are that version's."""
    try:
        version.parse(v)
    except ValueError as e:
        raise ChangelogError("%s:%d: %s" % (where, n, e)) from None
    if version.rc(v) is not None:
        raise ChangelogError("%s:%d: %s is a rehearsal's name, and a rehearsal has no section "
                             "of its own: it is %s's" % (where, n, v, version.base(v)))


def parse(text, where=FILE):
    """The text of a changelog -> [Section, ...], newest first.  Raises
    ChangelogError, naming the line, for everything the docstring above
    refuses."""
    sections, head, body = [], None, []

    def close():
        if head is not None:
            v, d, n = head
            while body and not body[-1].strip():
                body.pop()
            while body and not body[0].strip():
                body.pop(0)
            sections.append(Section(v, d, d is not None, "\n".join(body), n))

    for n, raw in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        line = raw.rstrip()
        if not line.startswith("## "):
            if head is not None:
                body.append(raw.rstrip("\r"))
            continue
        m = HEADING.fullmatch(line)
        if not m:
            raise ChangelogError("%s:%d: %r is not a version's heading, which is spelt "
                                 "'## [a0.3.1] - 2026-09-24' or '## [a0.4.0] - %s'"
                                 % (where, n, line, UNRELEASED))
        v, d = m.group("version"), m.group("date")
        _held(v, where, n)
        if d == UNRELEASED:
            d = None
        else:
            try:
                datetime.date.fromisoformat(d)
            except ValueError:
                raise ChangelogError("%s:%d: %s is not a day of the calendar" % (where, n, d)) from None
        close()
        head, body = (v, d, n), []
        if len(sections):
            above = sections[-1]
            if d is None:
                raise ChangelogError("%s:%d: %s is unreleased below %s: only the top section "
                                     "may be unreleased" % (where, n, v, above.version))
            if any(s.version == v for s in sections):
                raise ChangelogError("%s:%d: %s has a section already" % (where, n, v))
            if version.compare(v, above.version) >= 0:
                raise ChangelogError("%s:%d: %s is below %s but not earlier than it: the "
                                     "newest version comes first" % (where, n, v, above.version))
            if above.date is not None and d > above.date:
                raise ChangelogError("%s:%d: %s is dated %s, after %s above it (%s)"
                                     % (where, n, v, d, above.version, above.date))
    close()
    if not sections:
        raise ChangelogError("%s has no version's heading at all" % where)
    return sections


def read(root=ROOT):
    """The changelog of the tree at `root` -> [Section, ...], newest first."""
    path = os.path.join(root, FILE)
    with open(path, encoding="utf-8") as f:
        return parse(f.read(), where=path)


def top(root=ROOT):
    """The newest section: the version being made, or the last one released."""
    return read(root)[0]


def find(v, root=ROOT):
    """The section of version `v` -> Section.  KeyError when there is none."""
    for s in read(root):
        if s.version == v:
            return s
    raise KeyError("%s has no section for %s" % (FILE, v))


def said(date):
    """"2026-09-24" -> "24 September 2026", the way the guide writes a day;
    None (unreleased) -> "not yet released"."""
    if date is None:
        return NOT_YET
    d = datetime.date.fromisoformat(date)
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year)


# ------------------------------------------------------------ the guide's page
# THE OTHER TEXT.  The guide's "What's new" is the changelog written for a
# reader rather than for a release (the owner, 2026-09-24): its own words,
# but the same versions, in the same order, on the same days.  Its headings
# are read here, beside the changelog's, so that the guide's test (which
# holds the two lists equal) and the release check (which holds the tagged
# version's day) read them alike:
#
#     ## a0.3.2 — not yet released
#     ## a0.3.1 — 24 September 2026
#     ## a0.3.1 — 24 September 2026 {#a031}     an anchor of its own, allowed
#     ## Before a0.2.0                          what came before versions: last
#
# A `## ` inside a fenced block of code is an example, not a heading.
GUIDE_PAGE = "html-guide/markdown/reference/whats-new.md"
NOT_YET = "not yet released"
GUIDE_HEADING = re.compile(r"(?P<version>\S+) — (?P<day>.+?)(?: \{#[\w-]+\})?")
BEFORE = "Before "

# version, date ("YYYY-MM-DD" or None) and released as a Section has them;
# line: the heading's line on the page, counted from 1
Heading = namedtuple("Heading", "version date released line")


def _day(said_, where, n):
    """"24 September 2026" -> "2026-09-24"; "not yet released" -> None."""
    if said_ == NOT_YET:
        return None
    m = re.fullmatch(r"([1-9][0-9]?) (\w+) ([0-9]{4})", said_)
    try:
        if not m or m.group(2) not in MONTHS:
            raise ValueError
        return datetime.date(int(m.group(3)), MONTHS.index(m.group(2)) + 1,
                             int(m.group(1))).isoformat()
    except ValueError:
        raise ChangelogError("%s:%d: %r is neither a day as the guide writes one "
                             "('24 September 2026') nor %r" % (where, n, said_, NOT_YET)) from None


def whats_new(text, where=GUIDE_PAGE):
    """The text of the guide's "What's new" -> ([Heading, ...] in the page's
    order, the version its last heading, "Before <version>", names -- None
    when there is none).  ChangelogError, naming the line, for a `## ` that
    is neither, for a version lib/version.py cannot read or a rehearsal's
    name, for a day spelt any other way, and for a heading after "Before"."""
    heads, before, fence = [], None, False
    for n, raw in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        if raw.startswith("```"):
            fence = not fence
            continue
        line = raw.rstrip()
        if fence or not line.startswith("## "):
            continue
        head = line[3:].strip()
        if before is not None:
            raise ChangelogError("%s:%d: %r comes after '%s%s', which is the page's last heading"
                                 % (where, n, head, BEFORE, before))
        if head.startswith(BEFORE):
            before = head[len(BEFORE):].strip()
            _held(before, where, n)
            continue
        m = GUIDE_HEADING.fullmatch(head)
        if not m:
            raise ChangelogError("%s:%d: %r is neither a version and its day ('a0.3.1 — 24 "
                                 "September 2026') nor the '%s<version>' heading"
                                 % (where, n, head, BEFORE))
        _held(m.group("version"), where, n)
        d = _day(m.group("day"), where, n)
        heads.append(Heading(m.group("version"), d, d is not None, n))
    return heads, before


def guide_page(root=ROOT):
    """whats_new() of the page in the tree at `root`."""
    path = os.path.join(root, *GUIDE_PAGE.split("/"))
    with open(path, encoding="utf-8") as f:
        return whats_new(f.read(), where=path)


if __name__ == "__main__":
    # `python3 lib/changelog.py` lists the versions and their days, or says
    # which line is wrong -- for the developer about to release
    try:
        for s in read():
            print("%-10s %s" % (s.version, s.date or UNRELEASED))
    except ChangelogError as e:
        sys.exit(str(e))
