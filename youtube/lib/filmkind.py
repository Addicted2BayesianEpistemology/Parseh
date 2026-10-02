#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a video's own media is, said once: a picture with a sound, or a sound alone.

    got = filmkind.look(path)                  # before anything is written -> what it is, and what will be done
    done = filmkind.settle(video_dir, held)    # in place: its kind decided, a playable copy made if it needs one

A video that is a file on this machine keeps it as `media.<ext>` (lib/bundle.py).
Since W8 that file may be a SOUND -- a lesson recorded and never filmed -- and
this module is where the toolbox decides, once and for good, which of the two it
is, so that no page has to guess:

  * THE KIND is video.json's "kind": "audio" for a sound, written when the file
    is attached, and nothing at all for a video (as every video so far).  ffprobe
    is asked where it is installed (a stream that is not a cover picture inside
    the file: an mp3 with the album's art in it is still a sound); where it is
    not, the extension decides (bundle.SOUND_EXTS).
  * A SOUND THE BROWSER CANNOT PLAY -- .wma, .aiff, .amr, .mka, .caf, or a codec
    a browser has none for -- gets a PLAYABLE COPY made by ffmpeg, named
    media.<ext> as the film always is, and the original is kept beside it as
    media-orig.<ext> (a hard link where the disk allows it, so it costs nothing).
    A bundle carries the copy and not the original.  Where ffmpeg is not here the
    sound is attached as it is, and the answer says in words that this browser
    may not play it: a person is never left guessing why a recording is silent.
  * A VIDEO IS NOT TOUCHED.  Whatever a film was before, it still is.

Standard library only (ffmpeg and ffprobe are the person's own, optional).
"""
import json
import os
import shutil
import subprocess
import sys
import time

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(os.path.dirname(LIB))
for _p in (LIB, os.path.join(ROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import audiofile    # noqa: E402  ffmpeg's door, and the best format it can write here
import bundle       # noqa: E402  which file is a film, and the table of what may be one

# WHAT A BROWSER PLAYS AS IT IS: the container by its extension and the codec by
# ffprobe's name for it.  Both have to be there.  An allowlist, because the
# other answer -- "it is probably fine" -- is a recording that stays silent and
# says nothing.  Where ffprobe is absent the codec is not known and the
# extension alone decides.
NATIVE_EXTS = (".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav", ".flac", ".weba")
NATIVE_CODECS = frozenset(("mp3", "aac", "vorbis", "opus", "flac", "pcm_s16le",
                           "pcm_s24le", "pcm_u8", "pcm_f32le"))
# the longest an encode of one recording may take; a lesson of two hours is a
# minute or two, and past this something is stuck
CONVERT_SECONDS = 4 * 3600
# a held film nobody adopted goes after this (see sweep)
STAGED_DAYS = 2
STAGING = ".incoming"


def ffprobe():
    """The ffprobe executable, or None: next to ffmpeg, where it comes from."""
    exe = audiofile.ffmpeg()
    if exe:
        for name in ("ffprobe", "ffprobe.exe"):
            p = os.path.join(os.path.dirname(exe), name)
            if os.path.exists(p):
                return p
    return shutil.which("ffprobe")


def probe(path):
    """What ffprobe makes of the file -> {"video": a picture of its own is in it,
    "audio": a sound is, "acodec", "seconds"}, or None where there is no ffprobe
    or it cannot read the file.

    A stream marked `attached_pic` is a cover and no picture of the film, so an
    mp3 with the album art inside is a sound.
    """
    exe = ffprobe()
    if not exe:
        return None
    try:
        r = subprocess.run(
            [exe, "-v", "error", "-show_entries",
             "stream=codec_type,codec_name:stream_disposition=attached_pic:format=duration",
             "-of", "json", path], capture_output=True, timeout=60)
        found = json.loads(r.stdout.decode("utf-8")) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if not isinstance(found, dict):
        return None
    out = {"video": False, "audio": False, "acodec": "", "seconds": None}
    for s in found.get("streams") or []:
        if not isinstance(s, dict):
            continue
        if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic"):
            out["video"] = True
        elif s.get("codec_type") == "audio" and not out["audio"]:
            out["audio"] = True
            out["acodec"] = str(s.get("codec_name") or "")
    try:
        out["seconds"] = float((found.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        pass
    if not (out["video"] or out["audio"]):
        return None
    return out


def kind_of(ext, found=None):
    """"video" or "audio" for a file with this extension, ffprobe's reading of it
    (`probe`) deciding where there is one.  Without one the extension decides,
    and `.ogg` -- the one name both lists have -- is taken for a sound."""
    if found:
        return "video" if found["video"] else "audio"
    return "audio" if ext in bundle.SOUND_EXTS else "video"


def playable(ext, kind, found=None):
    """Can a browser play this as it is?  A video is not asked (it never was)."""
    if kind != "audio":
        return True
    if ext not in NATIVE_EXTS:
        return False
    return not found or not found["acodec"] or found["acodec"] in NATIVE_CODECS


def look(path, ext=None):
    """What a file is, before anything is written -> {"kind", "ext", "bytes",
    "seconds", "playable", "copy", "note"}.

    `copy` is what will be done about a sound a browser cannot play: "" where
    nothing is needed, "made" where ffmpeg will make one, "none" where it is not
    installed -- and then `note` says so, in words for the page to show.
    """
    ext = (ext or os.path.splitext(path)[1]).lower()
    found = probe(path)
    kind = kind_of(ext, found)
    ok = playable(ext, kind, found)
    copy = "" if ok else ("made" if audiofile.have_ffmpeg() else "none")
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    note = ""
    if copy == "made":
        note = ("%s is a sound this browser cannot play as it is: a playable copy "
                "is made when the video is added, and the original stays beside "
                "it" % ext)
    elif copy == "none":
        note = ("%s is a sound most browsers cannot play, and ffmpeg, which would "
                "make a playable copy, is not installed on this computer: it is "
                "added as it is, and may stay silent" % ext)
    return {"kind": kind, "ext": ext, "bytes": size,
            "seconds": found["seconds"] if found else None,
            "playable": ok, "copy": copy, "note": note}


def _convert(src, out):
    """Re-encode the sound of `src` into `out` (the best format ffmpeg writes
    here) or raise ValueError saying what ffmpeg said."""
    exe = audiofile.ffmpeg()
    _ext, codec = audiofile.best_output()
    try:
        r = subprocess.run([exe, "-nostdin", "-v", "error", "-y", "-i", src, "-vn",
                            "-sn", "-dn", "-map_metadata", "-1"] + codec + [out],
                           capture_output=True, timeout=CONVERT_SECONDS)
    except (OSError, subprocess.SubprocessError) as e:
        raise ValueError("ffmpeg could not make a playable copy of this sound (%s)" % e)
    if r.returncode != 0 or not os.path.isfile(out) or os.path.getsize(out) == 0:
        tail = (r.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-2:]
        raise ValueError("ffmpeg could not read this sound, so no playable copy was "
                         "made%s" % (": " + " ".join(tail) if tail else ""))


def _size_words(n):
    return "%.1f MB" % (n / 1e6) if n >= 1e6 else "%d kB" % max(1, round(n / 1e3))


def settle(video_dir, held):
    """The media of a video, put in its place and its kind written down.

    `held` is the file as it lies INSIDE the video's directory under a name that
    is not yet its own (`media.<ext>.part`: the hard link or the copy of the
    person's file, or the bytes that were sent).  It is renamed into place -- and
    that is the whole of it for a video and for a sound a browser plays.  For a
    sound it cannot, the playable copy is made first and the original is kept as
    media-orig.<ext>.

    THE NEW MEDIA ARRIVES BEFORE THE OLD LEAVES (attach_film's rule, and the
    narration upload's): everything that can fail -- the probe, the encode -- is
    done before one name is changed, so a failure leaves the video with the
    media it had.  -> {"film", "kind", "converted", "original", "note", "bytes"};
    ValueError, with a sentence, for what could not be done.
    """
    held_ext = os.path.splitext(os.path.splitext(held)[0])[1].lower()
    found = probe(held)
    kind = kind_of(held_ext, found)
    ok = playable(held_ext, kind, found)
    note, orig, made = "", "", None
    if not ok and audiofile.have_ffmpeg():
        out_ext, _codec = audiofile.best_output()
        made = os.path.join(video_dir, bundle.MEDIA_STEM + "-new" + out_ext)
        try:
            _convert(held, made)
        except ValueError:
            _drop(made)
            raise
        film = bundle.MEDIA_STEM + out_ext
        orig = bundle.ORIG_STEM + held_ext
        os.replace(held, os.path.join(video_dir, orig))
        os.replace(made, os.path.join(video_dir, film))
        note = ("%s is a sound this browser cannot play as it is, so a playable copy "
                "was made (%s, %s); the original is kept beside it as %s"
                % (held_ext, out_ext.lstrip("."), _size_words(os.path.getsize(
                    os.path.join(video_dir, film))), orig))
    else:
        film = bundle.MEDIA_STEM + held_ext
        os.replace(held, os.path.join(video_dir, film))
        if not ok:
            note = ("%s is a sound most browsers cannot play, and ffmpeg, which would "
                    "make a playable copy, is not installed on this computer: it was "
                    "added as it is, and may stay silent" % held_ext)
    for old in sorted(os.listdir(video_dir)):
        if (bundle.is_media_name(old) or bundle.is_orig_name(old)) and old not in (film, orig):
            _drop(os.path.join(video_dir, old))
    _say_kind(video_dir, kind)
    return {"film": film, "kind": kind, "converted": bool(orig), "original": orig,
            "note": note, "bytes": os.path.getsize(os.path.join(video_dir, film))}


def _say_kind(video_dir, kind):
    """video.json says what its media is, in the file's own style (the one
    ytpages.edit_meta writes it in).  ONLY A SOUND SAYS IT: "kind": "audio".  A
    video says nothing, as every video made before this did, so a film's
    video.json is the file it always was and nothing reads a missing key as
    anything but a picture.  A film that replaces a sound takes the key off.
    A folder with no video.json yet has nothing to say it in, and the
    extension reads (bundle.film_kind)."""
    path = os.path.join(video_dir, "video.json")
    try:
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return
    if not isinstance(meta, dict) or meta.get("kind") == (kind if kind == "audio" else None):
        return
    if kind == "audio":
        meta["kind"] = kind
    else:
        meta.pop("kind", None)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _drop(path):
    try:
        os.unlink(path)
    except OSError:
        pass


# ---------------------------------------------------------- a file that was sent
def staging(videos_dir):
    """Where a film or a sound that was SENT waits until a video takes it:
    youtube/videos/.incoming/, a dot-directory like .trash/ and .waveforms/ --
    never listed as a video, never served, never bundled, and on the same disk
    as the videos, so the link into a video's folder costs nothing."""
    return os.path.join(videos_dir, STAGING)


def staged(path, videos_dir):
    """Is `path` a file that was sent and is waiting there?  (Then adding the
    video takes it, and the waiting copy goes.)"""
    here = os.path.realpath(staging(videos_dir))
    there = os.path.realpath(path)
    return os.path.dirname(os.path.dirname(there)) == here


def release(path, videos_dir):
    """The video has the film; the copy that waited for it goes, and its folder
    with it.  Nothing of the person's own is ever named here: only a path that
    `staged` says is inside the waiting place."""
    if not staged(path, videos_dir):
        return
    _drop(path)
    try:
        os.rmdir(os.path.dirname(path))
    except OSError:
        pass


def sweep(videos_dir, now=None):
    """What was sent and never used goes after STAGED_DAYS, with what a stopped
    server left half written.  Off the way in and before each new upload."""
    now = time.time() if now is None else now
    base = staging(videos_dir)
    try:
        folders = os.listdir(base)
    except OSError:
        return
    for name in folders:
        folder = os.path.join(base, name)
        try:
            newest = max([os.path.getmtime(folder)] + [
                os.path.getmtime(os.path.join(folder, f)) for f in os.listdir(folder)])
        except (OSError, ValueError):
            continue
        if now - newest > STAGED_DAYS * 86400:
            shutil.rmtree(folder, ignore_errors=True)
