# SPDX-License-Identifier: GPL-3.0-or-later
"""The Settings section, and the page a device that has not been let in sees.

Settings opens from the hub and holds, for now, one page: **Network** -- who
may reach this Parseh, on which port, with which certificate (lib/network.py
keeps the answers; TO-DO §1.1, §3.3, §3.4, and the owner's decisions of
2026-09-23).  The section is a section rather than a page because the next
settings to come out of the pages will live beside it.

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
"""


def _switch(key, title, said, on, may_save):
    return ('<label class="door"><input type="checkbox" data-door="%s"%s%s> '
            '<b>%s</b><span class="said">%s</span></label>'
            % (esc(key), " checked" if on else "",
               "" if may_save else " disabled", esc(title), said))


def network_page(state):
    """/settings/network/.  `state` is what serve.py knows and this module
    must not find out for itself: the settings, the addresses the server is
    answering on, the pairing code, whose certificate is in use, and whether
    the browser asking is the computer itself."""
    doc = state["settings"]
    may = bool(state["may_save"])
    devs = network.devices(doc)
    code = state["code"]
    rows = "".join(
        '<tr><td>%s</td><td>%s</td><td class="addr">%s</td>'
        '<td><button type="button" class="parseh-btn" data-forget="%s"%s>'
        'Forget this device</button></td></tr>'
        % (esc(d["name"]), esc(when(d["at"])), esc(d["ip"]), esc(d["id"]),
           "" if may else " disabled")
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
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Network &mdash; %(name)s settings</title>
%(apphead)s
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/langs.css">
<link rel="stylesheet" href="/lib/mobile.css">
<script src="/lib/parseh.js"></script>
<script src="/lib/explain.js" defer></script>
<style>%(style)s</style>
</head><body class="index" data-mobile-page>
<div class="parseh-bar" data-layout="browser">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="where"><a href="/settings/">settings</a> &middot; network</span>
  <span class="sp"></span>
  %(modes)s
  <a class="parseh-btn" href="/guide/site/getting-started/other-devices.html" title="the guide: from a phone or another computer">guide</a>
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
</div>
<div class="parseh-bar m-bar" data-layout="mobile">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="m-where">Network</span>
  <span class="sp"></span>
  %(modes)s
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
</div>
<main class="settings">
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
  <textarea data-extra%(shut)s rows="3">%(extra)s</textarea></div>
</section>

<section>
  <h2>Letting a device on the Wi-Fi in</h2>
  <p class="why">A device on the Wi-Fi is asked for this code once. It gets nothing
  but the asking page until it types it; afterwards this computer remembers it and
  it is never asked again. A device on a VPN is never asked, and this computer
  never is.</p>
  <div class="code" data-code>%(code)s</div>
  <p class="left" data-left>%(left)s</p>
  <p><button type="button" class="parseh-btn" data-fresh-code%(shut)s>Make a fresh code</button>
  <span class="left">&mdash; the old one stops working at once.</span></p>
  <table class="devices">
    <tr><th>Device</th><th>Let in</th><th>Address</th><th></th></tr>
    %(devices)s
  </table>
  <p><button type="button" class="parseh-btn" data-forget-all%(shut)s>Forget every device</button>
  <span class="left">&mdash; every phone and laptop has to be let in again.</span></p>
</section>

<section>
  <h2>The port</h2>
  <p class="why">%(name)s answers on this port. The default is
  <code>%(default_port)d</code>.</p>
  <div class="fld"><span>Port</span>
  <input type="number" data-port min="1024" max="65535" value="%(port)d"%(shut)s></div>
  <div class="warn">Moving the port changes every address: a bookmark on a phone
  stops working until it is made again, and the mobile interface installed as an
  app has to be installed again from its new address. <b>8765 is also the port
  Anki&rsquo;s AnkiConnect add-on uses</b>, which is why %(name)s left it.</div>
</section>

<section>
  <h2>The certificate</h2>
  <p class="why">%(cert_said)s</p>
  <div class="fld"><span>Use my own certificate &mdash; the certificate file
  (leave both empty for %(name)s&rsquo;s own)</span>
  <input type="text" data-cert size="60" value="%(cert)s"%(shut)s></div>
  <div class="fld"><span>&hellip; and its private key</span>
  <input type="text" data-key size="60" value="%(key)s"%(shut)s></div>
  <p class="left">%(name)s reads these two files and never writes to either.</p>
</section>

<section>
  <h2>Where %(name)s is answering now</h2>
  <ul>%(addrs)s</ul>
</section>

<div class="actions">
  <button type="button" class="parseh-btn" data-save%(shut)s>Save the network settings</button>
  <span class="doing" data-doing></span>
</div>
</main>
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
</script>
</body></html>
""" % {
        "name": NAME, "apphead": mobile.app_head(), "modes": mobile.mode_switch(),
        "style": STYLE,
        "notice": "" if state["may_save"] else (
            '<div class="warn">You are reading this from %s. The network settings '
            'are changed from the computer %s runs on and nowhere else &mdash; a '
            'device that has been let in must not be able to let the rest of the '
            'network in. Everything below is shown as it stands.</div>'
            % (esc(network.WHERE_SAID.get(state["where"], "another device")), NAME)),
        "vpn": _switch("vpn", "A VPN (Tailscale, and anything named below)",
                       "Your own devices, wherever they are. Trusted without a code: "
                       "a device is on your tailnet only because you put it there.",
                       doc["vpn"], may),
        "lan": _switch("lan", "The Wi-Fi this computer is on",
                       "Every device on the same network as this computer may knock. "
                       "Each one still has to be let in once with the code below. "
                       "Shut on a fresh install.",
                       doc["lan"], may),
        "extra": esc("\n".join(doc["extra"])),
        "shut": "" if may else " disabled",
        "code": esc(state["code_said"]), "left": esc(state["left_said"]),
        "devices": rows,
        "port": doc["port"], "default_port": network.DEFAULT_PORT,
        "cert": esc((doc["cert"] or {}).get("cert") or ""),
        "key": esc((doc["cert"] or {}).get("key") or ""),
        "cert_said": cert_said, "addrs": addrs,
        "state": _in_script({"name": NAME, "may_save": may}),
    }


def hub():
    """/settings/ -- the section itself.  One page today; the door says what
    is behind it rather than only naming it."""
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Settings &mdash; %(name)s</title>
%(apphead)s
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/langs.css">
<link rel="stylesheet" href="/lib/mobile.css">
<script src="/lib/parseh.js"></script>
<style>%(style)s</style>
</head><body class="index" data-mobile-page>
<div class="parseh-bar" data-layout="browser">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="where">settings</span>
  <span class="sp"></span>
  %(modes)s
  <a class="parseh-btn" href="/guide/" title="the guide: how to use Parseh">guide</a>
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
</div>
<div class="parseh-bar m-bar" data-layout="mobile">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="m-where">Settings</span>
  <span class="sp"></span>
  %(modes)s
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
</div>
<main class="settings">
<h1 class="idx">settings</h1>
<p class="sub">What this %(name)s is set to, on this computer.</p>
<div class="doors">
  <a class="door" href="/settings/network/">
    <div class="dname">Network</div>
    <div class="dwhat">Who may reach %(name)s &mdash; this computer, a VPN, the
    Wi-Fi &mdash; letting a phone in with a code, the port, and the certificate.</div>
    <div class="tags"><span class="tag on">%(where)s</span><span class="tag">port %(port)d</span></div>
  </a>
</div>
</main>
</body></html>
""" % {"name": NAME, "apphead": mobile.app_head(), "modes": mobile.mode_switch(),
       "style": STYLE + "\n.settings .doors { display: grid; gap: 1rem; }\n",
       "where": esc(doors_said(network.settings())),
       "port": network.port()}


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
