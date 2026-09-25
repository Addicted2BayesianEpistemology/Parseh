#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The server tests/studio_audio.mjs drives: the real studio routes on a
TEMPORARY library, a TEMPORARY exercises/ store and a TEMPORARY clip tray,
with real recordings (ffmpeg) in it.

    python3 tests/studio_harness.py studio   markdown/app/server.py's handler:
                                             the studio at /, no clip tray routes
    python3 tests/studio_harness.py parseh   serve.py's handler: the studio at
                                             /studio, the tray at /clips

Seeds two clips in the tray (Persian, "سلام" and "خداحافظ") and a document
holding tests/fixtures/studio/audio/audio.md with its recording and picture.
Prints `READY {json}` once listening.  SIGTERM or SIGINT removes the temp
tree.  Never touches markdown/library/, exercises/ or clips/."""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODE = sys.argv[1] if len(sys.argv) > 1 else "studio"

if MODE == "parseh":
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    import serve                                   # noqa: E402
    Handler, studio = serve.Handler, serve.studio
elif MODE == "studio":
    sys.path.insert(0, str(ROOT / "markdown" / "app"))
    import server                                  # noqa: E402
    Handler, studio = server.Handler, server
else:
    sys.exit("usage: studio_harness.py studio|parseh")
import audiofile  # noqa: E402  (the modules the studio imported)
import clips      # noqa: E402
import decks      # noqa: E402
import store      # noqa: E402
# the door that says who may reach Parseh (lib/network.py): pointed at the
# temporary tree below, so a suite can neither read the owner's own settings
# nor shut his Wi-Fi door by running.  Imported in BOTH modes: the studio
# alone does not read it, but the assignment below runs either way.
import network    # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="parseh-studio-audio-test-"))
store.LIB = tmp / "library"
network.STORE = str(tmp / "config" / "network.json")
# and the LaTeX drawings' themes, their drawings and their packages
import latexthemes, latexdraw, texpackages
latexthemes.STORE = str(tmp / "config" / "latex.json")
latexdraw.DRAWN = str(tmp / "latex-drawn")
texpackages.TREE = str(tmp / "texmf")
import offline  # the phone-keeping memories (lib/offline.py) too
offline.DIGESTS = str(tmp / "config" / "digests.json")
offline.WHERES = str(tmp / "config" / "wheres.json")
store.LIB.mkdir()
decks.set_dir(tmp / "exercises")
tray = tmp / "clips"
tray.mkdir()
store.set_clips_dir(tray)
clips.set_dir(tray)
assert store.lib() == tmp / "library" and Path(clips.DIR) == tray


def cleanup(*_):
    shutil.rmtree(tmp, ignore_errors=True)
    os._exit(0)


signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)
Handler.log_message = lambda self, *a: None
if MODE == "parseh":
    Handler.log_request = lambda self, *a, **k: None


def tone(name, seconds, hz):
    p = tmp / name
    subprocess.run([audiofile.ffmpeg() or "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "sine=frequency=%d:duration=%s" % (hz, seconds),
                    "-c:a", "libmp3lame", str(p)], check=True)
    return p.read_bytes()


try:
    hello = clips.save_audio(tone("hello.mp3", 3, 523), "hello",
                             {"lang": "fa", "label": "1.2", "text": "سلام",
                              "source": {"kind": "book", "title": "A Persian reader"}})
    bye = clips.save_audio(tone("bye.mp3", 3, 392), "goodbye",
                           {"lang": "fa", "label": "0:14", "text": "خداحافظ",
                            "source": {"kind": "film", "title": "Street market"}})
    fixture = ROOT / "tests" / "fixtures" / "studio" / "audio"
    rich = store.create((fixture / "audio.md").read_text(encoding="utf-8"))
    store.save_audio(rich["id"], "greeting.mp3", (fixture / "audio" / "greeting.mp3").read_bytes())
    store.save_image(rich["id"], "swatch.png", (fixture / "images" / "swatch.png").read_bytes())

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    studio.SERVER["instance"] = srv
    print("READY " + json.dumps({"port": srv.server_address[1], "studio": studio.BASE, "mode": MODE,
                                 "library": str(store.LIB), "tray": str(tray),
                                 "rich_doc_id": rich["id"], "rich_doc_dir": str(store.doc_dir(rich["id"])),
                                 "clips": [hello, bye], "audio_accept": audiofile.ACCEPT,
                                 "audio_human": audiofile.HUMAN},
                                ensure_ascii=False), flush=True)
    srv.serve_forever()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
