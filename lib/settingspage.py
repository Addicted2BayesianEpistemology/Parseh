# SPDX-License-Identifier: GPL-3.0-or-later
"""The Settings section, and the page a device that has not been let in sees.

Settings opens from the hub, says which Parseh this is (its version), and
holds three pages: **Network** -- who may reach this Parseh, on which port,
with which certificate (lib/network.py keeps the answers; TO-DO §1.1, §3.3,
§3.4, and the owner's decisions of 2026-09-23) -- **Reading help**, the
dictionaries, corpora, models and component packs this computer has fetched
(lib/lookuppage.py draws it; TO-DO §11.10) -- and **Updating Parseh**, another
version in place of this one (lib/updatepage.py draws it, lib/updater.py does
it; TO-DO §13.16).  The section was a section rather
than a page from the start because the next settings to come out of the pages
were always going to live beside the first.

WHO MAY CHANGE WHAT is written below, once, as a table: every setting, and
for each risky one the part of the owner's sentence it trips.  Both routers
that change anything (serve.py's /settings/api/ and /lookup/api/) ask it
before they act, and the pages draw each control's lock from it -- so the
page and the server cannot say different things.

EVERY ACTION IS A BUTTON HERE, because that is the rule this toolbox is
written to: there is no line in the guide that says to edit a file or to
type a command.  Opening the Wi-Fi door, letting a phone in, moving the
port, pointing Parseh at a certificate of your own -- all of it from this
page, and it takes effect the moment it is saved.

WHY THE PAGE MOVES ITSELF.  A change to the port or to the doors means the
server binds a different socket; the page that saved it would be left
talking to an address that has stopped existing.  So the save answers with
the addresses that will work, and the page waits for one of them to come
back and goes there.  It is the only honest way to do this without asking
anybody to restart anything.

THE LOCKED PAGE IS ALONE.  A device on the Wi-Fi that has not been let in is
served `locked_page` at every address it asks for -- the stylesheet and the
scripts included, since it may have none of them.  So that page carries its
own style and its own script and fetches nothing: it is a sentence, a field
and a button.
"""
import html
import json
import os
import sys
import time

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(LIB)
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import mobile                                                  # noqa: E402
import network                                                 # noqa: E402

NAME = "Parseh"


# ---------------------------------------------------------------------------
# WHO MAY SAVE IS A PROPERTY OF THE SETTING, NOT OF THE PAGE (TO-DO §11.10,
# the owner, 2026-09-24).  Settings used to refuse every save that did not
# come from the computer, wholesale -- a rule that only looked like a rule
# about Settings because Network was the only setting there was.  It is a rule
# about RISK, and what counts as risky is written down here, once, rather than
# left to grow by accident:
#
#     a setting is risky when it changes who may reach Parseh, what Parseh
#     exposes, or what Parseh will run.
#
# A risky setting is changed on the computer Parseh runs on and nowhere else;
# anything else is open to every device that has been let in.  Each risky
# entry names the part of that sentence it trips, and that part is what a
# phone is told when it is refused -- by the server, which is the rule, and by
# the page, which only repeats it.  Decide each new one against the sentence,
# not by feel.
REACH = "it decides who may reach %s" % NAME
EXPOSE = "it decides what %s exposes" % NAME
RUN = "it changes what %s will run" % NAME

# setting -> (the part of the sentence it trips, or None; one more sentence
# saying what that means here, for the lock line under it)
SETTINGS = {
    "network.doors": (REACH, "A device that has been let in must not be able to let the "
                             "rest of the network in."),
    "network.extra": (REACH, "A device on a network named here is trusted without a code."),
    "network.port": (REACH, "Moving it changes every address, this device's included."),
    "network.cert": (EXPOSE, "It is what %s shows every device as itself, and its path "
                             "names a file on this computer." % NAME),
    "network.code": (REACH, "Whoever can read the code can let a device in."),
    "network.forget": (REACH, "Forgetting a device shuts it out; only the computer decides "
                              "who is let in."),
    # THE READING HELP IS NOT RISKY.  Getting a dictionary puts somebody else's
    # data on this computer's own disk and changes nothing about who can reach
    # what.  Removing one changes neither either -- it costs a download, and
    # the page says how big before it asks.  The translation engine is code
    # that runs in the reader, but its bytes are pinned by hash in
    # lib/getmt.py: fetching it adds nothing the person who installed this
    # Parseh did not already choose.
    "reading.get": (None, "It puts a download on this computer's disk."),
    "reading.remove": (None, "It frees the space a download took."),
    "reading.stop": (None, "It stops a download this page started."),
    # UPDATING PARSEH (TO-DO §13.16) replaces the program itself.
    "parseh.update": (RUN, "An update replaces %s itself." % NAME),
    # ASKING WHICH VERSION IS NEWEST changes none of the three: it is one
    # question to GitHub that says nothing about the person, and its answer
    # is only shown.  So "Check now", and the daily look (config/updates.json),
    # are open to any device let in; installing what it found is not.
    "parseh.check": (None, "It asks GitHub which release is newest, and installs nothing."),
}

# Asking how things stand is not a setting: open to every device let in, and
# a phone may always SEE what it may not change.
READ = "read"
# The one route open to a device that has NOT been let in: the knock itself
# (serve.py's _gate lets nothing else through for such a device).
KNOCK = "knock"

# EVERY ROUTE THAT CHANGES OR ASKS ANYTHING UNDER /settings/api/ AND
# /lookup/api/, and what it is.  A route that is not here is refused, for
# everybody: a new one is not open because somebody forgot to write it down,
# and tests/test_settings_risk.py fails when serve.py answers a route this
# table does not name.
ROUTES = {
    "/settings/api/ping": READ,
    "/settings/api/pair": KNOCK,
    # one body saves all four, so all four must be allowed
    "/settings/api/network": ("network.doors", "network.extra", "network.port", "network.cert"),
    "/settings/api/code": ("network.code",),
    "/settings/api/forget": ("network.forget",),
    # the reading help: what is there, and what it would cost
    "/lookup/api/status": READ,
    "/lookup/api/plan": READ,
    "/lookup/api/dicts": READ,
    "/lookup/api/corpora": READ,
    "/lookup/api/models": READ,
    "/lookup/api/syn": READ,
    "/lookup/api/decompositions": READ,
    # a reader's own read -- the Kanji/Hanzi dialog -- and not a setting at all
    "/lookup/api/decompose": READ,
    # getting, and getting everything for a language at once
    "/lookup/api/getdict": ("reading.get",),
    "/lookup/api/getcorpus": ("reading.get",),
    "/lookup/api/getmodel": ("reading.get",),
    "/lookup/api/getsyn": ("reading.get",),
    "/lookup/api/getdecomposition": ("reading.get",),
    "/lookup/api/getall": ("reading.get",),
    # removing
    "/lookup/api/dropdict": ("reading.remove",),
    "/lookup/api/dropcorpus": ("reading.remove",),
    "/lookup/api/dropmodel": ("reading.remove",),
    "/lookup/api/dropsyn": ("reading.remove",),
    "/lookup/api/dropdecomposition": ("reading.remove",),
    "/lookup/api/stop": ("reading.stop",),
    # updating Parseh (lib/updater.py): what is waiting and how far an update
    # has got, open; asking GitHub, open; everything that brings a version in
    # or puts one in place, the computer's alone
    "/settings/api/update/state": READ,
    "/settings/api/update/plan": READ,
    "/settings/api/update/check": ("parseh.check",),
    "/settings/api/update/daily": ("parseh.check",),
    "/settings/api/update/fetch": ("parseh.update",),
    "/settings/api/update/stop": ("parseh.update",),
    "/settings/api/update/upload": ("parseh.update",),
    "/settings/api/update/discard": ("parseh.update",),
    "/settings/api/update/apply": ("parseh.update",),
}


def may(setting, where):
    """May a device at `where` (lib/network.py's SELF, VPN, LAN or AWAY)
    change `setting`?  A setting that is not in the table is refused."""
    if setting not in SETTINGS:
        return False
    return SETTINGS[setting][0] is None or where == network.SELF


def refusal(setting):
    """What a device that may not change `setting` is told: the part of the
    sentence it trips, and what that means here."""
    risk, why = SETTINGS.get(setting, (None, ""))
    if setting not in SETTINGS:
        return "%s knows no setting called %s, so nobody may change it." % (NAME, setting)
    return ("That is changed on the computer %s runs on and nowhere else, because "
            "%s. %s" % (NAME, risk, why)).strip()


def may_post(route, where):
    """The gate both routers ask before they act -> (True, "") or (False, why).

    A read is open to every device let in, the knock to every device at all
    (serve.py's own gate decides who may knock), a change to whoever may change
    every setting it touches, and a route missing from ROUTES to nobody."""
    what = ROUTES.get(route)
    if what is None:
        return False, ("%s has no setting at %s: it is not in the table of settings "
                       "(lib/settingspage.py), so it is refused." % (NAME, route))
    if what in (READ, KNOCK):
        return True, ""
    for setting in what:
        if not may(setting, where):
            return False, refusal(setting)
    return True, ""


def open_to_all(settings):
    """Is every one of `settings` open to any device let in?  What a door and
    a page say about themselves, in the same words the server refuses in."""
    return all(SETTINGS[s][0] is None for s in settings)


def parseh_version():
    """This Parseh's version, as the one file that holds it says (TO-DO
    §16.1, lib/version.py), for Settings to show.  Imported when asked, so
    that a page drawn in a test that never asks does not need it."""
    import version                                             # noqa: E402
    return version.VERSION


def esc(s):
    return html.escape(str(s), quote=True)


def when(at):
    """A moment, said the way the rest of the toolbox says one (lib/prefs.js's
    `when`): near enough to read at a glance, and never a raw timestamp."""
    try:
        gap = max(0.0, time.time() - float(at or 0))
    except (TypeError, ValueError):
        return "at some point"
    if not at:
        return "at some point"
    if gap < 90:
        return "a moment ago"
    if gap < 3600:
        return "%d minutes ago" % round(gap / 60)
    if gap < 86400:
        return "%d hours ago" % round(gap / 3600)
    if gap < 30 * 86400:
        return "%d days ago" % round(gap / 86400)
    return time.strftime("%d %B %Y", time.localtime(float(at)))


def _in_script(obj):
    """JSON for a <script> tag: the one sequence that could end the tag early
    is spelt so that it cannot."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


STYLE = """
main.settings { max-width: 58rem; margin: 0 auto; padding: 1rem 1rem 4rem; }
.settings h1.idx { margin-bottom: .2rem; }
.settings .sub { opacity: .8; margin-top: 0; }
.settings section { border: 1px solid var(--rule, #8884); border-radius: .6rem;
  padding: .9rem 1.1rem 1.1rem; margin: 1.1rem 0; background: var(--card, transparent); }
.settings section > h2 { margin: .2rem 0 .3rem; font-size: 1.15rem; }
.settings .why { opacity: .82; margin: .25rem 0 .8rem; }
.settings label.door { display: block; margin: .45rem 0; }
.settings label.door b { font-weight: 600; }
.settings label.door .said { display: block; margin-left: 1.7rem; opacity: .8; font-size: .92rem; }
.settings input[type=text], .settings input[type=number], .settings textarea {
  font: inherit; padding: .35rem .5rem; border-radius: .35rem;
  border: 1px solid var(--rule, #8886); background: var(--bg, transparent);
  color: inherit; max-width: 100%; }
.settings textarea { width: 100%; min-height: 4.5rem; font-family: ui-monospace, monospace; }
.settings .fld { margin: .6rem 0; }
.settings .fld > span { display: block; font-size: .92rem; opacity: .85; margin-bottom: .15rem; }
.settings .code { font: 700 2.2rem/1.1 ui-monospace, monospace; letter-spacing: .12em;
  margin: .3rem 0; user-select: all; }
.settings .left { opacity: .75; font-size: .92rem; }
.settings table.devices { border-collapse: collapse; width: 100%; margin-top: .5rem; }
.settings table.devices td, .settings table.devices th { text-align: left;
  padding: .3rem .5rem; border-bottom: 1px solid var(--rule, #8883); font-size: .95rem; }
.settings .warn { border-left: 3px solid #c90; padding-left: .7rem; margin: .6rem 0; }
.settings .bad { color: #c33; }
.settings .doing { margin: .8rem 0; min-height: 1.4rem; }
.settings .actions { display: flex; gap: .6rem; flex-wrap: wrap; align-items: center;
  margin-top: 1rem; }
.settings .addr { font-family: ui-monospace, monospace; }
.settings .shut input { pointer-events: none; }
@media (max-width: 40rem) { .settings section { padding: .8rem; } }
.settings input:disabled, .settings textarea:disabled, .settings button:disabled {
  opacity: .55; cursor: not-allowed; }
/* WHO MAY CHANGE IT, IN WORDS: a lock and a sentence, never a colour alone
   and never a dead button left to explain itself */
.settings .gate { display: inline-flex; align-items: center; gap: 5px; font-size: 12px;
  color: var(--dim); border: 1px dashed var(--rule); border-radius: 20px;
  padding: 1px 8px 1px 6px; background: var(--boxbg); }
.settings .gate svg { width: 12px; height: 12px; flex: none; }
.settings .gate.open { border-style: solid; }
.settings .lockline { display: flex; gap: 8px; align-items: flex-start; font-size: 13px;
  background: var(--boxbg); border: 1px dashed var(--rule); border-radius: 8px;
  padding: 8px 10px; margin-top: 10px; }
.settings .lockline svg { width: 15px; height: 15px; flex: none; margin-top: 2px; color: var(--dim); }
.settings .lockline .w { color: var(--dim); }
.settings .notice { border-inline-start: 3px solid var(--accent); background: var(--card);
  padding: 10px 12px; margin: 0 0 16px; font-size: 13.5px; border-radius: 0 8px 8px 0; }
.settings .ver { color: var(--dim); font-size: 13.5px; margin: -.2rem 0 1rem; }
/* Settings' doors as one row at the top of a settings page */
.settings .sdoors { display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 18px; }
.settings .sdoor { flex: 1 1 11rem; display: block; text-decoration: none; color: var(--ink);
  background: var(--card); border: 1px solid var(--rule); border-radius: 10px;
  padding: 9px 12px; min-width: 0; }
.settings .sdoor:hover { border-color: var(--accentlt); }
.settings .sdoor.on { border-color: var(--accent); box-shadow: inset 0 -3px 0 var(--accent); }
.settings .sdoor b { display: block; font-size: 14.5px; }
.settings .sdoor small { display: block; color: var(--dim); font-size: 12.5px; line-height: 1.35; }
.settings .sdoor .gate { margin-top: 5px; }
"""

LOCK = ('<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" '
        'rx="1.5" fill="currentColor"/><path d="M5 7V5a3 3 0 0 1 6 0v2" fill="none" '
        'stroke="currentColor" stroke-width="1.6"/></svg>')
TICK = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" fill="none" '
        'stroke="currentColor" stroke-width="2"/></svg>')

# THE DOORS OF SETTINGS, each with the settings behind it: what the door says
# about who may change them is worked out from SETTINGS, never written twice.
DOORS = (
    ("/settings/reading-help/", "Reading help",
     "Dictionaries, translated sentences, translation models, character parts",
     ("reading.get", "reading.remove", "reading.stop")),
    ("/settings/network/", "Network",
     "Who may reach %s, the code, the port, the certificate" % NAME,
     ("network.doors", "network.extra", "network.port", "network.cert", "network.code",
      "network.forget")),
    ("/settings/update/", "Updating %s" % NAME,
     "Another version in place of this one: newer, older, or the same again",
     ("parseh.update", "parseh.check")),
)


def gate(settings):
    """The pill that says who may change these settings."""
    if open_to_all(settings):
        return '<span class="gate open">%sany device let in</span>' % TICK
    return '<span class="gate">%schanged on the computer only</span>' % LOCK


def lockline(setting, where, said=None):
    """What stands under a control that this device may not change: a lock,
    and the sentence the server would refuse it with.  Nothing where the
    device may."""
    if may(setting, where):
        return ""
    return ('<div class="lockline" data-lock="%s">%s<span>%s <span class="w">%s</span></span></div>'
            % (esc(setting), LOCK, esc(said or "Changed on the computer only."),
               esc(SETTINGS[setting][1])))


def settings_doors(here):
    """Settings' doors as one row, the one at `here` marked."""
    out = []
    for href, name, what, settings in DOORS:
        on = href == here
        out.append('<a class="sdoor%s" href="%s"%s><b>%s</b><small>%s</small>%s</a>'
                   % (" on" if on else "", esc(href), ' aria-current="page"' if on else "",
                      esc(name), esc(what), gate(settings)))
    return '<nav class="sdoors" aria-label="settings">%s</nav>' % "".join(out)


def frame(title, where_html, m_where, guide, main, style="", script="", extra_head=""):
    """A page of Settings: the head, the two bars (browser and mobile, as
    docs/mobile.md has every page that opens on a phone carry them), the
    main and its script."""
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
%(apphead)s
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/langs.css">
<link rel="stylesheet" href="/lib/mobile.css">
<script src="/lib/parseh.js"></script>
%(extra_head)s
<style>%(style)s</style>
</head><body class="index" data-mobile-page>
<div class="parseh-bar" data-layout="browser">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="where">%(where)s</span>
  <span class="sp"></span>
  %(modes)s
  <a class="parseh-btn" href="%(guide)s" title="the guide">guide</a>
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
</div>
<div class="parseh-bar m-bar" data-layout="mobile">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="m-where">%(m_where)s</span>
  <span class="sp"></span>
  %(modes)s
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
</div>
%(main)s
%(script)s
</body></html>
""" % {"title": title, "apphead": mobile.app_head(), "extra_head": extra_head,
       "style": STYLE + style, "name": NAME, "where": where_html, "modes": mobile.mode_switch(),
       "guide": esc(guide), "m_where": esc(m_where), "main": main, "script": script}


def _switch(key, title, said, on, may_save):
    return ('<label class="door"><input type="checkbox" data-door="%s"%s%s> '
            '<b>%s</b><span class="said">%s</span></label>'
            % (esc(key), " checked" if on else "",
               "" if may_save else " disabled", esc(title), said))


def network_page(state):
    """/settings/network/.  `state` is what serve.py knows and this module
    must not find out for itself: the settings, the addresses the server is
    answering on, the pairing code, whose certificate is in use, where the
    browser asking is (lib/network.py's SELF, VPN, LAN) and what it calls
    itself.

    EACH SECTION ASKS THE TABLE for itself (SETTINGS, above): what this device
    may not change is drawn disabled with its reason under it, and the
    pairing code -- which lets a device in to whoever reads it -- is not
    drawn at all where the code may not be made."""
    doc = state["settings"]
    where = state.get("where") or (network.SELF if state.get("may_save") else network.LAN)
    can = {k: may(k, where) for k in SETTINGS}
    save_keys = ROUTES["/settings/api/network"]
    may_all = all(can[k] for k in save_keys)
    devs = network.devices(doc)
    rows = "".join(
        '<tr><td>%s</td><td>%s</td><td class="addr">%s</td>'
        '<td><button type="button" class="parseh-btn" data-forget="%s"%s>'
        'Forget this device</button></td></tr>'
        % (esc(d["name"]), esc(when(d["at"])), esc(d["ip"]), esc(d["id"]),
           "" if can["network.forget"] else " disabled")
        for d in devs)
    if not rows:
        rows = ('<tr><td colspan="4">No device has been let in yet. A phone on the '
                'Wi-Fi is asked for the code below the first time it opens Parseh.</td></tr>')

    if state["own_cert"]:
        cert_said = ("Parseh is using the certificate you pointed it at, and never "
                     "writes to it: renewing it is yours to do.")
    elif state["has_authority"]:
        cert_said = ("Parseh is using a certificate of its own, signed by an authority "
                     "it made for this computer alone. A phone told to trust that "
                     "authority once (<a href=\"/m/install/\">As an app</a>) never sees "
                     "a warning again, and a fresh certificate under it costs the phone "
                     "nothing.")
    else:
        cert_said = ("Parseh is serving plain http, or a certificate that was put in "
                     "<code>.tls/</code> by hand.")

    addrs = "".join('<li class="addr">%s</li>' % esc(a) for a in state["addresses"])
    if can["network.code"]:
        code = ('<div class="code" data-code>%s</div>\n  <p class="left" data-left>%s</p>\n'
                '  <p><button type="button" class="parseh-btn" data-fresh-code>Make a fresh '
                'code</button>\n  <span class="left">&mdash; the old one stops working at '
                'once.</span></p>' % (esc(state["code_said"]), esc(state["left_said"])))
    else:
        # THE CODE IS NOT DRAWN FOR A DEVICE THAT MAY NOT MAKE ONE.  A phone
        # let in cannot make a code, but a phone that could READ it could pass
        # it on for as long as it lasts -- which is letting the network in one
        # device at a time, the very thing the lock is for.
        code = lockline("network.code", where, "The code is shown on the computer only.")
    notice = "" if may_all else (
        '<div class="notice">You are reading this on <b>%s</b>, %s. Everything here is '
        'shown as it stands, and each part says who may change it: all of it decides who '
        'may reach %s, so all of it is changed on the computer %s runs on.</div>'
        % (esc(state.get("device") or "another device"), esc(_came_in(where)), NAME, NAME))
    main = """<main class="settings">
<h1 class="idx">network</h1>
<p class="sub">Who may reach this %(name)s, on which port, with which certificate.</p>
%(notice)s

<section>
  <h2>Who may reach %(name)s</h2>
  <p class="why">This computer always can, and is never asked anything. The other
  two are doors, and they are shut until you open them. With both of them shut
  %(name)s listens on <code>127.0.0.1</code> and nothing on the network can knock
  at all.</p>
  %(vpn)s
  %(lan)s
  <div class="fld"><span>Other networks that count as a VPN &mdash; one address
  range (<code>10.8.0.0/24</code>) or name (<code>laptop.example.ts.net</code>) per
  line. A device on one of these is trusted without a code, as a Tailscale device
  is.</span>
  <textarea data-extra%(shut_extra)s rows="3">%(extra)s</textarea></div>
  %(lock_doors)s
</section>

<section>
  <h2>Letting a device on the Wi-Fi in</h2>
  <p class="why">A device on the Wi-Fi is asked for this code once. It gets nothing
  but the asking page until it types it; afterwards this computer remembers it and
  it is never asked again. A device on a VPN is never asked, and this computer
  never is.</p>
  %(code)s
  <table class="devices">
    <tr><th>Device</th><th>Let in</th><th>Address</th><th></th></tr>
    %(devices)s
  </table>
  <p><button type="button" class="parseh-btn" data-forget-all%(shut_forget)s>Forget every device</button>
  <span class="left">&mdash; every phone and laptop has to be let in again.</span></p>
  %(lock_forget)s
</section>

<section>
  <h2>The port</h2>
  <p class="why">%(name)s answers on this port. The default is
  <code>%(default_port)d</code>.</p>
  <div class="fld"><span>Port</span>
  <input type="number" data-port min="1024" max="65535" value="%(port)d"%(shut_port)s></div>
  <div class="warn">Moving the port changes every address: a bookmark on a phone
  stops working until it is made again, and the mobile interface installed as an
  app has to be installed again from its new address. <b>8765 is also the port
  Anki&rsquo;s AnkiConnect add-on uses</b>, which is why %(name)s left it.</div>
  %(lock_port)s
</section>

<section>
  <h2>The certificate</h2>
  <p class="why">%(cert_said)s</p>
  <div class="fld"><span>Use my own certificate &mdash; the certificate file
  (leave both empty for %(name)s&rsquo;s own)</span>
  <input type="text" data-cert size="60" value="%(cert)s"%(shut_cert)s></div>
  <div class="fld"><span>&hellip; and its private key</span>
  <input type="text" data-key size="60" value="%(key)s"%(shut_cert)s></div>
  <p class="left">%(name)s reads these two files and never writes to either.</p>
  %(lock_cert)s
</section>

<section>
  <h2>Where %(name)s is answering now</h2>
  <ul>%(addrs)s</ul>
</section>

<div class="actions">
  %(save)s
  <span class="doing" data-doing></span>
</div>
</main>""" % {
        "name": NAME, "notice": notice, "code": code,
        "vpn": _switch("vpn", "A VPN (Tailscale, and anything named below)",
                       "Your own devices, wherever they are. Trusted without a code: "
                       "a device is on your tailnet only because you put it there.",
                       doc["vpn"], can["network.doors"]),
        "lan": _switch("lan", "The Wi-Fi this computer is on",
                       "Every device on the same network as this computer may knock. "
                       "Each one still has to be let in once with the code below. "
                       "Shut on a fresh install.",
                       doc["lan"], can["network.doors"]),
        "lock_doors": lockline("network.doors", where) or lockline("network.extra", where),
        "shut_extra": "" if can["network.extra"] else " disabled",
        "extra": esc("\n".join(doc["extra"])),
        "devices": rows,
        "shut_forget": "" if can["network.forget"] else " disabled",
        "lock_forget": lockline("network.forget", where),
        "port": doc["port"], "default_port": network.DEFAULT_PORT,
        "shut_port": "" if can["network.port"] else " disabled",
        "lock_port": lockline("network.port", where),
        "cert": esc((doc["cert"] or {}).get("cert") or ""),
        "key": esc((doc["cert"] or {}).get("key") or ""),
        "shut_cert": "" if can["network.cert"] else " disabled",
        "lock_cert": lockline("network.cert", where),
        "cert_said": cert_said, "addrs": addrs,
        "save": ('<button type="button" class="parseh-btn" data-save>Save the network '
                 'settings</button>' if may_all else ""),
    }
    script = """
<script id="settings-state" type="application/json">%(state)s</script>
<script>
(function () {
  'use strict';
  var S = JSON.parse(document.getElementById('settings-state').textContent);
  var doing = document.querySelector('[data-doing]');
  function say(text, bad) {
    doing.textContent = text || '';
    doing.className = 'doing' + (bad ? ' bad' : '');
  }
  function post(where, body) {
    return fetch(where, {method: 'POST', headers: {'Content-Type': 'application/json'},
                         body: JSON.stringify(body || {})})
      .then(function (r) { return r.json().then(function (j) { return {r: r, j: j}; }); });
  }
  function on(sel, fn) {
    var el = document.querySelector(sel);
    if (el) el.addEventListener('click', fn);
  }
  function doorOn(key) {
    var el = document.querySelector('[data-door="' + key + '"]');
    return !!(el && el.checked);
  }

  /* THE PAGE MOVES ITSELF.  A saved port or a closed door means the socket
     this page is talking through is about to be closed and another opened;
     the answer says which addresses will work, and we knock at each in turn
     until one answers.  no-cors because the new address is another origin
     as far as the browser is concerned: we may not read the answer, but a
     promise that resolves is an answer, which is all we need to know. */
  function moveTo(candidates) {
    var i = 0, tries = 0;
    (function knock() {
      if (!candidates.length) return;
      if (i >= candidates.length) i = 0;
      var url = candidates[i];
      i++; tries++;
      fetch(url + 'settings/api/ping', {mode: 'no-cors', cache: 'no-store'})
        .then(function () { location.href = url + 'settings/network/'; })
        .catch(function () {
          if (tries > 40) {
            say('Saved. This page cannot find ' + NAMEOF + ' again by itself: open ' +
                candidates[0] + ' .', true);
            return;
          }
          setTimeout(knock, 400);
        });
    })();
  }
  var NAMEOF = S.name;

  on('[data-save]', function () {
    say('Saving\\u2026');
    var body = {
      vpn: doorOn('vpn'), lan: doorOn('lan'),
      port: parseInt(document.querySelector('[data-port]').value, 10),
      extra: document.querySelector('[data-extra]').value.split(/\\r?\\n/)
               .map(function (s) { return s.trim(); }).filter(Boolean),
      cert: {cert: document.querySelector('[data-cert]').value.trim(),
             key: document.querySelector('[data-key]').value.trim()}
    };
    post('/settings/api/network', body).then(function (got) {
      if (!got.j.ok) { say(got.j.error || 'that was refused', true); return; }
      if (!got.j.moving) { say('Saved.'); return; }
      say('Saved \\u2014 ' + NAMEOF + ' is moving to ' + got.j.go[0] +
          (got.j.cert_again ? ' , with a new certificate this device will ask about once.'
                            : '. This page follows it.'));
      setTimeout(function () { moveTo(got.j.go); }, 900);
    }, function () { say('the save could not be sent', true); });
  });

  on('[data-fresh-code]', function () {
    post('/settings/api/code', {}).then(function (got) {
      if (!got.j.ok) { say(got.j.error || 'that was refused', true); return; }
      document.querySelector('[data-code]').textContent = got.j.code;
      document.querySelector('[data-left]').textContent = got.j.said;
      say('A fresh code. The old one no longer works.');
    });
  });

  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('[data-forget]') : null;
    if (!b) return;
    post('/settings/api/forget', {id: b.getAttribute('data-forget')}).then(function (got) {
      if (!got.j.ok) { say(got.j.error || 'that was refused', true); return; }
      location.reload();
    });
  });

  on('[data-forget-all]', function () {
    if (!confirm('Every device that has been let in will have to be let in again. Go on?')) return;
    post('/settings/api/forget', {all: true}).then(function () { location.reload(); });
  });
})();
</script>""" % {"state": _in_script({"name": NAME, "may_save": may_all})}
    return frame("Network &mdash; %s settings" % NAME,
                 '<a href="/settings/">settings</a> &middot; network', "Network",
                 "/guide/site/getting-started/other-devices.html", main,
                 extra_head='<script src="/lib/explain.js" defer></script>', script=script)


def hub(reading_tags="", update_tags=""):
    """/settings/ -- the section itself.  Each door says what is behind it
    rather than only naming it, and who may change it, in the words of the
    table above; `reading_tags` is what the reading help has (serve.py knows
    it: the hub's own door says the same).  And which Parseh this is: the
    version, from the one file that holds it."""
    net = DOORS[1][3]
    main = """<main class="settings">
<h1 class="idx">settings</h1>
<p class="sub">What this %(name)s is set to, and what this computer has fetched to help you read.</p>
<p class="ver" data-version>This is %(name)s <b>%(version)s</b>.</p>
<div class="doors">
  <a class="door" href="/settings/reading-help/">
    <div class="dname">Reading help</div>
    <div class="dwhat">Reading what nobody has glossed: a dictionary for each language,
    sentences people translated, translation models, and the parts of a kanji or a
    hanzi &mdash; fetched once, kept on this computer.</div>
    <div class="tags">%(reading_gate)s%(reading_tags)s</div>
  </a>
  <a class="door" href="/settings/network/">
    <div class="dname">Network</div>
    <div class="dwhat">Who may reach %(name)s &mdash; this computer, a VPN, the
    Wi-Fi &mdash; letting a phone in with a code, the port, and the certificate.</div>
    <div class="tags">%(net_gate)s<span class="tag on">%(where)s</span><span class="tag">port %(port)d</span></div>
  </a>
  <a class="door" href="/settings/update/">
    <div class="dname">Updating %(name)s</div>
    <div class="dwhat">Another version of %(name)s in place of this one &mdash; the newest
    release from GitHub, or a zip of your own; newer, older, or the same one again &mdash;
    keeping your books, videos, decks, dictionaries and settings.</div>
    <div class="tags">%(update_gate)s%(update_tags)s</div>
  </a>
</div>
</main>""" % {"name": NAME, "version": esc(parseh_version()),
              "reading_gate": gate(DOORS[0][3]), "reading_tags": reading_tags,
              "update_gate": gate(DOORS[2][3]), "update_tags": update_tags,
              "net_gate": gate(net),
              "where": esc(doors_said(network.settings())), "port": network.port()}
    return frame("Settings &mdash; %s" % NAME, "settings", "Settings", "/guide/", main,
                 style="\n.settings .doors { display: grid; gap: 1rem; }\n"
                       ".settings .doors .tags { align-items: center; }\n")


def _came_in(where):
    """How a device reached this page, said in a clause."""
    return {network.LAN: "let in over the Wi-Fi", network.VPN: "on a VPN",
            network.SELF: "the computer %s runs on" % NAME}.get(where, "another device")


def doors_said(doc):
    """The one line that says who can reach Parseh as it stands -- on the
    Settings door, and in what the server prints when it starts."""
    if doc["lan"] and doc["vpn"]:
        return "this computer, a VPN and the Wi-Fi"
    if doc["lan"]:
        return "this computer and the Wi-Fi"
    if doc["vpn"]:
        return "this computer and a VPN"
    return "this computer only"


def locked_page(where_said, why=""):
    """What a device on the Wi-Fi sees until it is let in, at every address
    it asks for: one sentence, one field, one button, and nothing else -- it
    has no stylesheet of ours and no script of ours, and must not need any."""
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(name)s &mdash; this device has not been let in</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 17px/1.5 system-ui, sans-serif; margin: 0; padding: 2rem 1.2rem;
         max-width: 32rem; margin-inline: auto; }
  h1 { font-size: 1.35rem; margin: 0 0 .6rem; }
  p { margin: .6rem 0; }
  input { font: 700 1.5rem ui-monospace, monospace; letter-spacing: .1em;
          width: 100%%; box-sizing: border-box; padding: .5rem .6rem; text-align: center;
          text-transform: uppercase; border: 1px solid #8887; border-radius: .4rem;
          background: transparent; color: inherit; }
  button { font: inherit; padding: .55rem 1.1rem; margin-top: .8rem;
           border-radius: .4rem; border: 1px solid #8887; background: #8882;
           color: inherit; cursor: pointer; }
  .said { min-height: 1.4rem; margin-top: .8rem; }
  .bad { color: #c33; }
  .small { opacity: .75; font-size: .92rem; }
</style>
</head><body>
<h1>This device has not been let in</h1>
<p>%(name)s is running on another computer, and it lets a device on %(where)s in
only once you say so. <b>Type the code shown on %(name)s&rsquo;s computer</b>, under
<i>Settings &rarr; Network</i>.</p>
<form id="f">
  <input id="c" name="code" autocomplete="off" autocapitalize="characters"
         spellcheck="false" placeholder="ABC-123" aria-label="the code">
  <button type="submit">Let this device in</button>
</form>
<p class="said" id="said">%(why)s</p>
<p class="small">Once it is in, this device is remembered and never asked again.
A device you do not recognise is forgotten from the same page on the computer.</p>
<script>
document.getElementById('f').addEventListener('submit', function (e) {
  e.preventDefault();
  var said = document.getElementById('said');
  said.className = 'said'; said.textContent = 'Asking\\u2026';
  fetch('/settings/api/pair', {method: 'POST', headers: {'Content-Type': 'application/json'},
                               body: JSON.stringify({code: document.getElementById('c').value})})
    .then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.ok) { said.textContent = 'Let in. Opening %(name)s\\u2026';
                  setTimeout(function () { location.href = '/'; }, 500); }
      else { said.className = 'said bad'; said.textContent = j.error || 'that code was refused'; }
    })
    .catch(function () { said.className = 'said bad'; said.textContent = 'the computer did not answer'; });
});
</script>
</body></html>
""" % {"name": NAME, "where": esc(where_said), "why": esc(why)}
