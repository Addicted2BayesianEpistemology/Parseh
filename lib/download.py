#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""How Parseh fetches the big optional files: resumably, stoppably, and
saying how far it has got.

    download.fetch(url, dest, say=..., progress=..., cancel=..., sha256=...)
    download.probe(url)                  how big, before anything is fetched
    download.Meter(progress, cancel, total)
                                         the same two things for a build

EVERY OPTIONAL DOWNLOAD GOES THROUGH HERE -- a dictionary's extract
(Turkish's is 431 MB, German's a gigabyte), a corpus's three exports, a
translation model and its engine, WordNet, a component pack -- so that the
five downloaders (lib/getdict.py, getcorpus.py, getmt.py, getsyn.py,
getdecomposition.py) do the same four things the same way, and the page that
starts them (Settings, Reading help) can draw one bar for all of them.  Each
used to carry its own copy of the same read loop, and each copy threw the
bytes away when the line dropped at 80%.

IT RESUMES.  The bytes go to `dest + ".part"`, never to `dest`, and a small
sidecar beside it (`dest + ".part.json"`) records where they came from: the
URL, the ETag and Last-Modified the server gave, and the size it announced.
When a download is cut -- a dropped line, a laptop closed, the Stop button
-- the .part and its sidecar stay, and the next fetch of the same URL asks
only for the rest (`Range: bytes=N-`), with `If-Range`, so that a server
whose file has changed since answers with the whole new file instead of the
rest of it.  The answer is checked as well as trusted: a 206 whose first
byte, total, ETag or Last-Modified is not the one recorded is thrown away and
the file fetched whole, so a file is never stitched from two versions of
itself (the fault TO-DO §19.16 names in Parseh's own server).  A server that
gave no validator at all cannot be resumed from safely, and starts again.
`dest` itself appears only when the file is whole, by one rename -- so a
file at `dest` is always a complete one, which is what lets a downloader say
"using the download already here" and mean it.

IT STOPS.  `cancel` -- a threading.Event, or any callable answering True --
is asked before every block is read, and when it answers, `Cancelled` is
raised with the .part and its sidecar left for the next time.  Stopping is
not failing: nothing is thrown away that a second press of *get it* could
use.

IT SAYS HOW FAR.  `progress(done, total, phase)`: bytes so far, the whole
size or None where the server does not say, and which phase this is
("download", or the downloader's own "build").  At most about four calls a
second, because the page polls and a thread that reports forty thousand
blocks a minute spends its time reporting.  `say`, the sentence the command
line prints and the page shows beside the bar, gets a line every few
seconds, as the downloaders always printed.

IT IS CHECKED, where Parseh knows what the bytes must be.  `sha256` is the
digest the file must have -- the translation engine's three files are pinned
in lib/getmt.py, the component packs' sources in lib/getdecomposition.py,
the models' digests come with the records that list them -- and a file that
does not match is refused (`Mismatch`) and deleted, never renamed into
place.  A mismatch after a RESUMED download may be the one stitch the checks
above could not see, so that one is fetched whole once more before it is
refused.

Standard library only, like the rest of lib/: this runs inside serve.py's
threads and from the command line alike.
"""
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

BLOCK = 1 << 16          # bytes per read: small enough that Stop is prompt
TICK = 0.25              # seconds between progress calls: about four a second
SAY_EVERY = 3.0          # seconds between the spoken "N MB of M" lines


class Cancelled(Exception):
    """The person stopped it.  Not an error: whatever was downloaded is kept
    for the next time, and whatever was half built has been removed."""

    def __init__(self, message="stopped"):
        super().__init__(message)


class Mismatch(ValueError):
    """The bytes are not the ones Parseh knows they must be.  A ValueError,
    because that is what lib/getdecomposition.py always raised for its own
    checksum, and what the server's job threads already report as an
    error."""


class Incomplete(OSError):
    """The connection closed before the size it announced.  An OSError,
    like every other way a line can drop, so each downloader's existing
    "could not download" answer covers it -- and the .part is kept."""


def stopped(cancel):
    """Has the person pressed Stop?  `cancel` is None (never), a
    threading.Event, or a callable answering True."""
    if cancel is None:
        return False
    is_set = getattr(cancel, "is_set", None)
    if is_set is not None:
        return bool(is_set())
    return bool(cancel())


def check(cancel):
    """Raise Cancelled if the person has pressed Stop."""
    if stopped(cancel):
        raise Cancelled()


class Meter:
    """A build's progress, at most about four times a second, and its Stop
    button, in one call.

        m = Meter(progress, cancel, total=os.path.getsize(src))
        for ...:
            m.at(bytes_read)            # raises Cancelled when Stop is pressed
        m.end()

    A BUILD OF SEVERAL STEPS IS ONE BAR, not a bar per step that fills and
    empties again: `share(lo, hi)` hands a step its stretch of the bar as a
    fraction, so a dictionary's reading can be the first 90% and its
    linking the rest.  How big each share is, is measured by the downloader
    that asks for it and written beside the call, so the time left the page
    works out of the bar's pace is roughly right rather than confidently
    wrong.

    `total` is None where there is nothing to count against; `at` then
    reports the count alone, and the page draws a bar that moves without
    a time left, which is the truth.
    """

    def __init__(self, progress=None, cancel=None, total=None, phase="build"):
        self.progress = progress
        self.cancel = cancel
        self.total = total
        self.phase = phase
        self._last = 0.0
        self._done = 0

    def at(self, done):
        """`done` units of `total` are done: say so if a quarter-second has
        passed, and stop here if the person has pressed Stop."""
        check(self.cancel)
        self._done = done
        if self.progress is None:
            return
        now = time.monotonic()
        if now - self._last >= TICK:
            self._last = now
            self.progress(done, self.total, self.phase)

    def share(self, lo, hi):
        """A step's stretch of the bar: a function taking the step's own
        fraction (0 to 1) and reporting it as lo..hi of the whole.  A bar
        of steps needs a whole to be shares of: where the caller gave none,
        it is a thousand, and the bar counts in thousandths."""
        if not self.total:
            self.total = 1000

        def at(fraction):
            fraction = min(max(fraction, 0.0), 1.0)
            self.at(int(self.total * (lo + (hi - lo) * fraction)))
        return at

    def end(self):
        """The build is done: the bar is full, whatever the last tick was."""
        if self.progress is not None:
            total = self.total if self.total is not None else self._done
            self.progress(total, total, self.phase)


def shifted(progress, before, whole):
    """A progress function for one file of several, reporting into the bar
    of all of them: `before` bytes of the earlier files are done, and
    `whole` is the size of them all -- or None where one of them did not
    say, and then each file reports its own bar, which is honest where one
    long bar would have to guess."""
    if progress is None:
        return None
    if whole is None:
        return progress

    def moved(done, total, phase):
        progress(before + done, whole, phase)
    return moved


def part_of(dest):
    return dest + ".part"


def sidecar_of(dest):
    return dest + ".part.json"


def leftover(dest):
    """Bytes of an interrupted download of `dest` still on disk, waiting to
    be resumed (0 when there is none)."""
    try:
        if os.path.isfile(sidecar_of(dest)):
            return os.path.getsize(part_of(dest))
    except OSError:
        pass
    return 0


def discard(dest):
    """Throw away an interrupted download of `dest`: the next fetch starts
    from the beginning.  Nothing at `dest` itself is touched."""
    for p in (part_of(dest), sidecar_of(dest)):
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass


def _read_sidecar(dest):
    try:
        with open(sidecar_of(dest), encoding="utf-8") as f:
            rec = json.load(f)
        return rec if isinstance(rec, dict) else None
    except (OSError, ValueError):
        return None


def _write_sidecar(dest, rec):
    """Written beside the .part and moved over the old one, so a sidecar is
    never half a JSON file -- a torn sidecar would make a good .part look
    like one nobody can vouch for."""
    tmp = sidecar_of(dest) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f)
    os.replace(tmp, sidecar_of(dest))


def _strong(etag):
    """An ETag If-Range may carry: a weak one (W/"...") promises the same
    meaning, not the same bytes, and a server must ignore it there."""
    return bool(etag) and not etag.startswith("W/")


def _resumable(url, dest):
    """How many bytes of `dest` can be asked for from where they stopped,
    and the sidecar that vouches for them -- (0, None) when there is nothing
    to resume from: no .part, no sidecar, a different URL, or a server that
    gave nothing to tell its versions of the file apart by."""
    rec = _read_sidecar(dest)
    try:
        have = os.path.getsize(part_of(dest))
    except OSError:
        have = 0
    if (not rec or rec.get("url") != url or have <= 0
            or not (rec.get("etag") or rec.get("last_modified"))):
        return 0, None
    return have, rec


_RANGE = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)")


def _content_range(value):
    """(first byte, total or None) from a Content-Range header, or None."""
    m = _RANGE.match((value or "").strip())
    if not m:
        return None
    return int(m.group(1)), (None if m.group(3) == "*" else int(m.group(3)))


def _changed(rec, headers):
    """Does this answer say the file is not the one the .part was cut from?
    A validator the server leaves out of a 206 proves nothing either way
    (If-Range already asked it); one that differs proves it changed."""
    etag = headers.get("ETag")
    modified = headers.get("Last-Modified")
    return bool((etag and rec.get("etag") and etag != rec["etag"])
                or (modified and rec.get("last_modified")
                    and modified != rec["last_modified"]))


def size_text(n):
    """A size as the page and the command line say it: 431 MB, 0.8 MB,
    17 kB -- never "0 MB" for a file that is not empty."""
    if n >= 1e6:
        return "%.0f MB" % (n / 1e6)
    if n >= 1e5:
        return "%.1f MB" % (n / 1e6)
    return "%.0f kB" % max(n / 1e3, 1 if n else 0)


def digest(path):
    """The SHA-256 of a file, in hex, read a megabyte at a time."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def lock(dest):
    """The lock of one destination, for this process.  TWO JOBS CAN WANT
    THE SAME FILE: every corpus glossed in English downloads
    `eng_sentences`, and the server runs one job per pair -- two of them
    writing one .part at once would interleave their bytes.  fetch() holds
    it for the whole download; a caller that first asks whether the file is
    already here holds it across the question and the fetch (it is
    re-entrant)."""
    key = os.path.abspath(dest)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


def fetch(url, dest, *, say=None, progress=None, cancel=None, resume=True,
          sha256=None, phase="download", headers=None, size=None, limit=None,
          timeout=60):
    """Download `url` to `dest`, resuming an interrupted download of it.

    `say(text)` gets a line every few seconds; `progress(done, total,
    phase)` at most about four times a second; `cancel` (an Event, or a
    callable) is asked before every block and raises `Cancelled`, keeping
    the .part.  `sha256` is the digest the file must have (`Mismatch`
    otherwise, and the bytes are deleted).  `headers` are sent with every
    request (a downloader's User-Agent).  `size` is the size Parseh already
    knows, used for the bar where the server does not say (GitHub's
    generated archives never do).  `limit` refuses a file larger than that
    many bytes (ValueError).  `resume=False` throws any .part away first.

    Returns `dest`.  Errors are the ones urllib raises (HTTPError, URLError,
    a timeout), plus `Incomplete` for a connection that closed early; each
    downloader turns them into its own words, as it always did.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with lock(dest):
        if not resume:
            discard(dest)
        for attempt in (1, 2):
            resumed = _fetch_once(url, dest, say=say, progress=progress,
                                  cancel=cancel, phase=phase, headers=headers,
                                  size=size, limit=limit, timeout=timeout)
            if sha256:
                got = digest(part_of(dest))
                if got.lower() != sha256.lower():
                    discard(dest)
                    if resumed and attempt == 1:
                        # the rest came from a file that only looked the same
                        if say:
                            say("    the pieces did not match; downloading "
                                "it whole again")
                        continue
                    raise Mismatch(
                        "%s is not the file Parseh expects: its SHA-256 is "
                        "%s, not %s.  Nothing was installed."
                        % (url.rsplit("/", 1)[-1], got, sha256))
            break
        os.replace(part_of(dest), dest)
        try:
            os.unlink(sidecar_of(dest))
        except FileNotFoundError:
            pass
    return dest


def _fetch_once(url, dest, *, say, progress, cancel, phase, headers, size,
                limit, timeout):
    """One request, resumed where the sidecar allows it, and its body
    written to the .part.  Returns whether it RESUMED (so the digest check
    knows a mismatch may be a stitch)."""
    check(cancel)
    part = part_of(dest)
    have, rec = _resumable(url, dest)
    if not have:
        discard(dest)
    send = dict(headers or {})
    if have:
        send["Range"] = "bytes=%d-" % have
        if _strong(rec.get("etag")):
            send["If-Range"] = rec["etag"]
        elif rec.get("last_modified"):
            send["If-Range"] = rec["last_modified"]
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=send),
                                   timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code == 416 and have:
            # NOTHING LEFT TO ASK FOR: the .part may already be the whole
            # file, cut just before its rename.  The size recorded when it
            # started says whether it is; otherwise start again.
            e.close()
            if rec.get("size") == have:
                return True
            discard(dest)
            return _fetch_once(url, dest, say=say, progress=progress,
                               cancel=cancel, phase=phase, headers=headers,
                               size=size, limit=limit, timeout=timeout)
        raise
    with r:
        status = r.getcode()
        resumed = False
        if status == 206 and have:
            cr = _content_range(r.headers.get("Content-Range"))
            total = cr[1] if cr else None
            if (cr is None or cr[0] != have or _changed(rec, r.headers)
                    or (total and rec.get("size") and total != rec["size"])):
                # A 206 FOR SOME OTHER FILE, or for another stretch of this
                # one: never appended.  Once more, from the beginning.
                r.close()
                discard(dest)
                return _fetch_once(url, dest, say=say, progress=progress,
                                   cancel=cancel, phase=phase,
                                   headers=headers, size=size, limit=limit,
                                   timeout=timeout)
            total = total or rec.get("size")
            done, mode, resumed = have, "ab", True
            if say:
                say("    carrying on from %s%s" % (
                    size_text(have), " of %s" % size_text(total) if total else ""))
        else:
            # A WHOLE FILE: the first request, or a server that answered
            # the Range with all of it (its file changed, or it cannot
            # resume).  Whatever was in the .part goes.
            if have and say:
                say("    the file changed since, or cannot be resumed: "
                    "starting again")
            length = r.headers.get("Content-Length")
            total = int(length) if length and length.isdigit() else None
            _write_sidecar(dest, {"url": url,
                                  "etag": r.headers.get("ETag") or "",
                                  "last_modified":
                                      r.headers.get("Last-Modified") or "",
                                  "size": total})
            done, mode = 0, "wb"
        shown = total if total is not None else size
        if limit and shown and shown > limit:
            discard(dest)
            raise ValueError("%s is %s, more than the %s it may be"
                             % (url.rsplit("/", 1)[-1], size_text(shown),
                                size_text(limit)))
        last_tick = last_say = time.monotonic()
        if progress:
            progress(done, shown, phase)
        with open(part, mode) as f:
            while True:
                check(cancel)
                block = r.read(BLOCK)
                if not block:
                    break
                f.write(block)
                done += len(block)
                if limit and done > limit:
                    f.close()
                    discard(dest)
                    raise ValueError("%s grew past the %s it may be"
                                     % (url.rsplit("/", 1)[-1],
                                        size_text(limit)))
                now = time.monotonic()
                if progress and now - last_tick >= TICK:
                    last_tick = now
                    progress(done, max(shown, done) if shown else None, phase)
                if say and now - last_say >= SAY_EVERY:
                    last_say = now
                    say("    %s%s" % (size_text(done), " of %s" % size_text(shown)
                                        if shown else ""))
    # A CONNECTION THAT CLOSED EARLY SAYS NOTHING: urllib hands back an
    # empty read at the cut exactly as at the end.  Only the size the
    # server announced tells them apart.
    if total is not None and done < total:
        raise Incomplete("the connection closed at %s of %s; what came "
                         "is kept, and the next try carries on from there"
                         % (size_text(done), size_text(total)))
    if progress:
        progress(done, done, phase)
    if say:
        say("    %s" % size_text(done))
    return resumed


def probe(url, headers=None, timeout=30):
    """The size of what `url` would download, in bytes, or None where the
    server does not say (or cannot be reached).  No body is read: a HEAD,
    and where that says nothing, a GET of its first byte, whose
    Content-Range names the whole size."""
    send = dict(headers or {})
    try:
        req = urllib.request.Request(url, headers=send, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            length = r.headers.get("Content-Length")
            if r.getcode() == 200 and length and length.isdigit():
                return int(length)
    except urllib.error.HTTPError:
        pass                                  # some servers refuse HEAD
    except (urllib.error.URLError, OSError, ValueError):
        return None                           # offline: a GET would not do better
    try:
        send["Range"] = "bytes=0-0"
        req = urllib.request.Request(url, headers=send)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.getcode() == 206:
                cr = _content_range(r.headers.get("Content-Range"))
                return cr[1] if cr else None
            length = r.headers.get("Content-Length")
            return int(length) if length and length.isdigit() else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def plan(download=None, measured=False, kept=None, have=0, peak=None):
    """The answer every downloader's plan() gives, in one shape:

        download   the whole download's size in bytes (None: not known)
        measured   True when that size is from the downloader's shipped
                   table of measured sizes, False when it was read from the
                   server just now or is not known
        disk_peak  the most room the run needs at once beyond what is on
                   disk already: what is still to download plus what is
                   built beside it before the old one goes (None: not known)
        kept       what the result occupies once done (None: not known)
        have       bytes of the download already here -- an interrupted
                   one waiting to resume, or a whole one kept from before

    `peak` is the downloader's own disk_peak where it knows better than
    "the rest of the download plus what is kept"."""
    rest = None if download is None else max(download - have, 0)
    if peak is None and rest is not None and kept is not None:
        peak = rest + kept
    return {"download": None if download is None else int(download),
            "measured": bool(measured and download is not None),
            "disk_peak": None if peak is None else int(peak),
            "kept": None if kept is None else int(kept),
            "have": int(have or 0)}
