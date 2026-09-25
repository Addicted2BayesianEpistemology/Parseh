# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings -> LaTeX drawings (TO-DO §8.39, a0.4.0): the themes a latex block
is drawn with, the TeX this computer has, the packages Parseh got for it, how
long a drawing may take, and the drawings kept.

EVERY CHANGE HERE IS THE COMPUTER'S ALONE (lib/settingspage.py, RUN): a theme
is LaTeX that every block naming it runs, a package is somebody else's code
TeX then runs, and renaming a theme rewrites what a person wrote.  A phone
sees all of it, each part with its lock and the sentence the server would
refuse it with; it may export a theme (a read), and forget the drawings
nothing uses (it frees space and changes nothing any drawing will be).

The routes are serve.py's (`/settings/api/latex/...`, each a literal there, as
tests/test_settings_risk.py finds them); what each one does is api() below.
"""
import html
import json
import os
import shutil
import subprocess
import sys

LIB = os.path.dirname(os.path.realpath(__file__))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import latexdraw                                             # noqa: E402
import latexthemes                                           # noqa: E402
import settingspage                                          # noqa: E402
import texpackages                                           # noqa: E402

PAGE = "/settings/latex/"
GUIDE = "/guide/site/dialect/latex-drawings.html"
SAMPLE = r"\ce{2H2 + O2 -> 2H2O}"

# what each route does, and the setting it is (lib/settingspage.py ROUTES)
KEYS = ("latex.theme", "latex.rename", "latex.import", "latex.packages", "latex.limit",
        "latex.forget")


def esc(s):
    return html.escape(str(s), quote=True)


def fonts():
    """The font families this computer has, for a theme's font."""
    fc = shutil.which("fc-list")
    if not fc:
        return []
    try:
        out = subprocess.run([fc, ":", "family"], capture_output=True, text=True,
                             timeout=15, stdin=subprocess.DEVNULL).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    names = sorted({l.split(",")[0].strip() for l in out.splitlines() if l.strip()})
    return names[:2000]


def view(where):
    """Everything the page draws, in one answer."""
    doc = latexthemes.all_of()
    comps = latexdraw.compilers()
    checks = {}
    for t in doc["themes"]:
        for pid, f, tl, lic in latexthemes.files_needed(t):
            if f not in checks:
                checks[f] = texpackages.installed(f)
    return {
        "themes": doc["themes"], "default": doc["default"], "timeout": doc["timeout"],
        "limits": [latexthemes.TIMEOUT_MIN, latexthemes.TIMEOUT_MAX],
        "compilers": {k: (v or None) for k, v in comps.items()},
        "catalogue": [latexthemes.PACKAGES[p] for p in latexthemes.ORDER],
        "groups": latexthemes.GROUPS,
        "files": checks,
        "needs": {t["name"]: [list(x[:2]) + [list(x[2]), x[3]] for x in latexthemes.files_needed(t)]
                  for t in doc["themes"]},
        "tex": texpackages.distribution(),
        "packages": texpackages.status(),
        "kept": latexdraw.size(),
        "may": {k: settingspage.may(k, where) for k in KEYS},
        "where": where or "",
        "rule": latexthemes.NAME_RULE,
        "sample": SAMPLE,
    }


def page(where):
    v = view(where)
    notice = ""
    if not v["may"]["latex.theme"]:
        notice = ('<div class="notice">You are reading this on another device. %s</div>'
                  % settingspage.lockline("latex.theme", where,
                                          "Themes and packages are changed on the computer only."))
    main = """<main class="settings lx">
%(doors)s
<h1 class="idx">latex drawings</h1>
<p class="sub">The themes a latex block is drawn with, the TeX this computer has, and the
drawings kept. A formula written <code>:::math</code> is not touched by anything here.</p>
%(notice)s
<div id="lx"><p>Reading what is here&hellip;</p></div>
<p class="foot">The themes are kept in <code>config/latex.json</code>, the packages Parseh got
in <code>texmf/</code>, and the drawings in <code>markdown/latex/</code>, made again whenever
they are needed. <a href="%(guide)s">LaTeX drawings</a>, in the guide.</p>
</main>""" % {"doors": settingspage.settings_doors(PAGE), "notice": notice, "guide": GUIDE}
    script = ('<script id="lx-state" type="application/json">%s</script>\n<script>%s</script>'
              % (settingspage._in_script(v), SCRIPT))
    return settingspage.frame("LaTeX drawings &mdash; %s settings" % settingspage.NAME,
                              '<a href="/settings/">settings</a> &middot; latex drawings',
                              "LaTeX drawings", GUIDE, main, style=STYLE, script=script)


class Refused(Exception):
    pass


def api(what, body, where, libraries=(), rename=None, used=None):
    """One route's work -> (status, answer).  `rename` is the studio's
    latexrename module, `used` a function giving every drawing's key in use:
    both are the server's, which knows the libraries."""
    body = body or {}
    try:
        if what == "state":
            return 200, dict(view(where), ok=True)
        if what == "fonts":
            return 200, {"ok": True, "fonts": fonts()}
        if what == "sample":
            theme = latexthemes.clean(dict(body.get("theme") or {}, name=body.get("theme", {}).get("name") or "sample"))
            r = latexdraw.draw(body.get("tex") or SAMPLE, None, theme=theme)
            return 200, {"ok": True, "result": r, "preamble": latexthemes.preamble(theme)}
        if what == "save":
            t = latexthemes.save(body.get("theme") or {}, was=body.get("was"))
            return 200, {"ok": True, "theme": t}
        if what == "delete":
            latexthemes.delete(body.get("name") or "")
            return 200, {"ok": True}
        if what == "default":
            latexthemes.set_default(body.get("name") or "")
            return 200, {"ok": True}
        if what == "rename-plan":
            return 200, dict(rename.plan(body.get("old") or "", body.get("new") or "", libraries),
                             ok=True)
        if what == "rename":
            done = rename.apply(body.get("old") or "", body.get("new") or "", libraries)
            return 200, dict(done, ok=True)
        if what == "import-read":
            t = latexthemes.read_export(body.get("data") or "")
            taken = latexthemes.find(t["name"]) is not None
            return 200, {"ok": True, "theme": t, "preamble": latexthemes.preamble(t),
                         "taken": taken}
        if what == "import":
            t = latexthemes.read_export(body.get("data") or "")
            name = body.get("name") or t["name"]
            if latexthemes.find(name) is not None:
                raise Refused("There is a theme called %s already: choose another name." % name)
            return 200, {"ok": True, "theme": latexthemes.import_theme(t, name)}
        if what == "limit":
            latexthemes.set_timeout(body.get("seconds"))
            latexdraw.forget_failures()
            return 200, {"ok": True}
        if what == "forget":
            return 200, dict(latexdraw.forget_unused(used() if used else set()), ok=True)
        if what == "package-plan":
            names = [n for n in (body.get("packages") or []) if isinstance(n, str)]
            return 200, dict(texpackages.plan(names), ok=True)
        if what == "package-get":
            for n in body.get("packages") or []:
                texpackages.start(n)
            return 200, dict(texpackages.status(), ok=True)
        if what == "package-remove":
            texpackages.remove(body.get("package") or "")
            return 200, dict(texpackages.status(), ok=True)
        if what == "package-stop":
            texpackages.stop(body.get("package"))
            return 200, dict(texpackages.status(), ok=True)
        if what == "package-status":
            return 200, dict(texpackages.status(), ok=True)
    except (latexthemes.ThemeError, Refused, ValueError) as e:
        return 400, {"ok": False, "error": str(e)}
    return 404, {"ok": False, "error": "no such route"}


STYLE = r"""
.lx .theme{border:1px solid var(--rule);border-radius:10px;padding:10px 14px;margin:10px 0;background:var(--card)}
.lx .theme h3{margin:0 0 4px;font-size:16px}
.lx .theme .facts{color:var(--dim);font-size:13px}
.lx .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
.lx .grp{margin:8px 0}
.lx .grp h4{margin:6px 0 4px;font-size:13px;color:var(--dim);text-transform:uppercase;letter-spacing:.08em}
.lx label.pk{display:block;margin:3px 0;font-size:14px}
.lx label.pk small{color:var(--dim)}
.lx label.pk code{font-size:12px}
.lx .missing{color:var(--danger,#c33);font-size:12px}
.lx textarea{width:100%;min-height:6rem;font-family:ui-monospace,monospace}
.lx pre.pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--boxbg);padding:8px;border-radius:6px;font-size:12px;max-height:22rem;overflow:auto}
.lx .said{min-height:1.2em;font-size:13px}
.lx .bad{color:var(--danger,#c33)}
.lx img.sample{max-width:100%;background:#fff;padding:6px;border-radius:4px}
.lx table{border-collapse:collapse;width:100%}
.lx td,.lx th{text-align:left;padding:4px 6px;border-bottom:1px solid var(--rule);font-size:13px}
"""

SCRIPT = r"""
(function () {
  'use strict';
  var S = JSON.parse(document.getElementById('lx-state').textContent);
  var root = document.getElementById('lx');
  var API = '/settings/api/latex/';
  var editing = null;       // the theme being edited: {was, theme}
  var q = new URLSearchParams(location.search);
  function esc(s) { return String(s == null ? '' : s).replace(/[<>&"]/g, function (c) {
    return {'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;'}[c]; }); }
  function post(what, body) {
    return fetch(API + what, {method: 'POST', headers: {'Content-Type': 'application/json'},
                              body: JSON.stringify(body || {})})
      .then(function (r) { return r.json().catch(function () { return {ok: false, error: r.statusText}; }); });
  }
  function may(k) { return !!S.may[k]; }
  function dis(k) { return may(k) ? '' : ' disabled'; }
  function lock(k) { return may(k) ? '' : '<div class="lockline">Changed on the computer only.</div>'; }
  function MB(n) { return n == null ? '' : (n >= 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1e3)) + ' kB'); }
  function reload() { return post('state').then(function (v) { if (v.ok) { S = v; draw(); } }); }

  function themeCard(t) {
    var isDef = t.name.toLowerCase() === S.default.toLowerCase();
    var comp = S.compilers[t.compiler];
    var needs = (S.needs[t.name] || []).filter(function (n) { return S.files[n[1]] === false; });
    return '<div class="theme" data-theme="' + esc(t.name) + '"><h3>' + esc(t.name) +
      (isDef ? ' <small>(the default: a block naming no theme)</small>' : '') + '</h3>' +
      '<div class="facts">' + esc(t.compiler) + (comp ? '' : ' — not on this computer') + ' · ' +
      (t.packages.length ? esc(t.packages.join(', ')) : 'no packages') +
      (t.languages ? ' · text in the languages Parseh teaches' : '') +
      (t.font ? ' · font ' + esc(t.font) : '') + (t.preamble ? ' · a preamble of its own' : '') + '</div>' +
      (needs.length ? '<div class="missing">Not installed here: ' + needs.map(function (n) { return esc(n[0]); }).join(', ') +
        ' <button type="button" data-install="' + esc(needs.map(function (n) { return n[2].join(' '); }).join(' ')) + '"' + dis('latex.packages') + '>Install…</button></div>' : '') +
      '<div class="row">' +
      '<button type="button" data-edit="' + esc(t.name) + '"' + dis('latex.theme') + '>Edit</button>' +
      '<button type="button" data-rename="' + esc(t.name) + '"' + dis('latex.rename') + '>Rename…</button>' +
      (isDef ? '' : '<button type="button" data-default="' + esc(t.name) + '"' + dis('latex.theme') + '>Make it the default</button>') +
      '<a class="parseh-btn" href="' + API + 'export?name=' + encodeURIComponent(t.name) + '">Export</a>' +
      (t.name.toLowerCase() === 'default' ? '' : '<button type="button" data-delete="' + esc(t.name) + '"' + dis('latex.theme') + '>Delete…</button>') +
      '</div><div class="said" data-said-for="' + esc(t.name) + '"></div></div>';
  }

  function editor() {
    if (!editing) return '';
    var t = editing.theme;
    var comps = ['xelatex', 'pdflatex', 'lualatex'].map(function (c) {
      return '<label><input type="radio" name="lx-comp" value="' + c + '"' + (t.compiler === c ? ' checked' : '') + '> ' + c +
        (S.compilers[c] ? '' : ' <small>(not on this computer)</small>') + '</label> ';
    }).join('');
    var groups = S.groups.map(function (g) {
      var rows = S.catalogue.filter(function (p) { return p.group === g[0]; }).map(function (p) {
        var here = S.files[p.file];
        return '<label class="pk"><input type="checkbox" data-pkg="' + esc(p.id) + '"' + (t.packages.indexOf(p.id) >= 0 ? ' checked' : '') + '> <b>' + esc(p.name) +
          '</b> <small>' + esc(p.what) + ' <code>' + esc(p.example) + '</code>' + (here === false ? ' <span class="missing">not installed</span>' : '') + '</small></label>';
      }).join('');
      return '<div class="grp"><h4>' + esc(g[1]) + '</h4>' + rows + '</div>';
    }).join('');
    return '<section class="edit"><h2>' + (editing.was ? 'The theme ' + esc(editing.was) : 'A new theme') + '</h2>' +
      (editing.was ? '' : '<div class="fld"><span>Its name — ' + esc(S.rule) + '</span><input type="text" data-name value="' + esc(t.name) + '"></div>') +
      '<div class="fld"><span>The compiler</span>' + comps + '</div>' +
      '<label class="pk"><input type="checkbox" data-languages' + (t.languages ? ' checked' : '') + '> <b>Text in the languages Parseh teaches</b> <small>Each language\'s face, as \\textfa{…}, \\textja{…}, \\texthi{…} and so on (xelatex or lualatex).</small></label>' +
      '<div class="fld"><span>A font of this computer for the drawing (xelatex or lualatex); empty for LaTeX\'s own</span><input type="text" data-font list="lx-fonts" value="' + esc(t.font) + '"><datalist id="lx-fonts"></datalist></div>' +
      '<div class="fld"><span>Packages</span>' + groups + '</div>' +
      '<div class="fld"><span>A preamble of its own, after the packages</span><textarea data-preamble>' + esc(t.preamble) + '</textarea></div>' +
      '<div class="fld"><span>Draw a sample with the theme as it is here</span><textarea data-sample>' + esc(S.sample) + '</textarea></div>' +
      '<div class="row"><button type="button" data-draw-sample>Draw the sample</button><button type="button" data-save class="parseh-btn">Save the theme</button><button type="button" data-cancel>Cancel</button></div>' +
      '<div class="said" data-edit-said></div><div data-sample-out></div></section>';
  }

  function current() {
    var box = root.querySelector('section.edit');
    var t = JSON.parse(JSON.stringify(editing.theme));
    var n = box.querySelector('[data-name]');
    if (n) t.name = n.value.trim();
    var c = box.querySelector('input[name="lx-comp"]:checked');
    if (c) t.compiler = c.value;
    t.languages = box.querySelector('[data-languages]').checked;
    t.font = box.querySelector('[data-font]').value.trim();
    t.packages = Array.prototype.map.call(box.querySelectorAll('[data-pkg]:checked'), function (x) { return x.getAttribute('data-pkg'); });
    t.preamble = box.querySelector('[data-preamble]').value;
    return t;
  }

  function draw() {
    var comps = Object.keys(S.compilers).map(function (c) {
      var v = S.compilers[c];
      return '<tr><td>' + c + '</td><td>' + (v ? '✓ ' + esc(v.version) : '— not on this computer') + '</td></tr>';
    }).join('');
    var inst = S.packages.installed || {}, jobs = S.packages.jobs || {};
    var pk = Object.keys(inst).sort().map(function (n) {
      var p = inst[n];
      return '<tr><td>' + esc(n) + '</td><td>' + esc(p.licence || '') + '</td><td>' + MB(p.size) + '</td><td><button type="button" data-remove="' + esc(n) + '"' + dis('latex.packages') + '>Remove…</button></td></tr>';
    }).join('') || '<tr><td colspan="4">No package got through Parseh yet.</td></tr>';
    var running = Object.keys(jobs).map(function (n) {
      var j = jobs[n];
      return '<div>' + esc(n) + ': ' + (j.running ? 'installing' + (j.total ? ' ' + j.done + '/' + j.total : '') + ' — ' + esc(j.say || '') +
        ' <button type="button" data-stop="' + esc(n) + '"' + dis('latex.packages') + '>Stop</button>' : (j.error ? '<span class="bad">' + esc(j.error) + '</span>' : '✓ installed')) + '</div>';
    }).join('');
    root.innerHTML =
      '<section><h2>The themes</h2><p class="why">A latex block names its theme after the fence — <code>::::latex chemistry</code> — and a block that names none is drawn with the default. Each theme is compiled on its own: nothing here touches a <code>:::math</code> formula.</p>' +
      S.themes.map(themeCard).join('') +
      '<div class="row"><button type="button" data-new' + dis('latex.theme') + '>New theme</button>' +
      '<label class="parseh-btn">Import a theme… <input type="file" data-import accept=".json,application/json" hidden' + dis('latex.import') + '></label></div>' +
      lock('latex.theme') + '<div class="said" data-top-said></div><div data-import-out></div></section>' +
      editor() +
      '<section><h2>TeX on this computer</h2><p class="why">' + esc(S.tex.said || '') + '. Parseh installs no TeX: it draws with the TeX this computer has, and puts the packages it gets for the drawings in its own folder, <code>texmf/</code>.</p><table>' + comps + '</table>' +
      '<h3>Packages Parseh got</h3><table><tr><th>Package</th><th>Licence</th><th>Size</th><th></th></tr>' + pk + '</table>' + running +
      '<div class="row"><input type="text" data-pkgname placeholder="a TeX Live package, e.g. chemfig"' + dis('latex.packages') + '><button type="button" data-plan' + dis('latex.packages') + '>What it costs…</button></div><div data-plan-out></div>' + lock('latex.packages') + '</section>' +
      '<section><h2>How long a drawing may take</h2><p class="why">A drawing that has not finished by then is stopped, and its block says so.</p><div class="row"><input type="number" data-limit min="' + S.limits[0] + '" max="' + S.limits[1] + '" value="' + S.timeout + '"' + dis('latex.limit') + '> seconds <button type="button" data-save-limit' + dis('latex.limit') + '>Save</button></div>' + lock('latex.limit') + '<div class="said" data-limit-said></div></section>' +
      '<section><h2>The drawings kept</h2><p class="why">' + S.kept.drawings + ' drawings, ' + MB(S.kept.bytes) + '. Each is made once and kept, and made again when its block, its theme, its packages or the TeX change; one nothing has asked for in 30 days is let go when Parseh starts.</p><div class="row"><button type="button" data-forget' + dis('latex.forget') + '>Forget drawings nothing uses</button></div><div class="said" data-forget-said></div></section>';
    var fl = root.querySelector('#lx-fonts');
    if (fl) post('fonts').then(function (r) { if (r.ok) fl.innerHTML = r.fonts.map(function (f) { return '<option value="' + esc(f) + '">'; }).join(''); });
  }

  function say(sel, text, bad) { var el = root.querySelector(sel); if (el) { el.textContent = text || ''; el.className = 'said' + (bad ? ' bad' : ''); } }

  root.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button') : null;
    if (!b) return;
    var a = function (n) { return b.getAttribute(n); };
    if (a('data-new') !== null) { editing = {was: null, theme: {name: q.get('make') || '', compiler: 'xelatex', packages: S.themes[0] ? S.themes[0].packages.slice() : [], languages: false, font: '', preamble: ''}}; draw(); return; }
    if (a('data-edit')) { var t = S.themes.filter(function (x) { return x.name === a('data-edit'); })[0]; editing = {was: t.name, theme: JSON.parse(JSON.stringify(t))}; draw(); return; }
    if (a('data-cancel') !== null) { editing = null; draw(); return; }
    if (a('data-draw-sample') !== null) {
      say('[data-edit-said]', 'Drawing…');
      post('sample', {theme: current(), tex: root.querySelector('[data-sample]').value}).then(function (r) {
        var out = root.querySelector('[data-sample-out]');
        if (!r.ok) { say('[data-edit-said]', r.error, true); return; }
        var res = r.result;
        say('[data-edit-said]', res.ok ? 'Drawn.' : res.said, !res.ok);
        out.innerHTML = (res.ok ? '<img class="sample" src="' + esc(res.url) + '" alt="the sample">' : (res.detail ? '<pre class="pre">' + esc(res.detail) + '</pre>' : '')) +
          '<details><summary>The whole preamble</summary><pre class="pre">' + esc(r.preamble) + '</pre></details>';
      });
      return;
    }
    if (a('data-save') !== null) {
      post('save', {theme: current(), was: editing.was}).then(function (r) {
        if (!r.ok) { say('[data-edit-said]', r.error, true); return; }
        editing = null; reload();
      });
      return;
    }
    if (a('data-default')) { post('default', {name: a('data-default')}).then(reload); return; }
    if (a('data-delete')) {
      if (!confirm('Delete the theme ' + a('data-delete') + '? A block that names it will say that this Parseh has no such theme.')) return;
      post('delete', {name: a('data-delete')}).then(function (r) { if (!r.ok) say('[data-top-said]', r.error, true); else reload(); });
      return;
    }
    if (a('data-rename')) {
      var old = a('data-rename');
      var neu = prompt('A new name for the theme ' + old + ' — ' + S.rule, old);
      if (!neu || neu === old) return;
      post('rename-plan', {old: old, new: neu}).then(function (p) {
        var where = '[data-said-for="' + old.replace(/"/g, '') + '"]';
        if (!p.ok || p.refused) { say(where, p.refused || p.error, true); return; }
        if (p.blocked.length) { say(where, 'Nothing can be renamed now: ' + p.blocked.join('; ') + '.', true); return; }
        if (!confirm('Renaming ' + old + ' to ' + neu + ' rewrites the name in ' + p.blocks + ' block' + (p.blocks === 1 ? '' : 's') + ': ' + p.said + '. No drawing changes. Go on?')) return;
        post('rename', {old: old, new: neu}).then(function (r) {
          if (!r.ok) { say(where, r.error, true); return; }
          reload().then(function () { say('[data-top-said]', 'Renamed ' + old + ' to ' + neu + ': ' + r.said + ' put right.'); });
        });
      });
      return;
    }
    if (a('data-install')) { planInstall(a('data-install').split(' ').filter(Boolean)); return; }
    if (a('data-plan') !== null) { var n = root.querySelector('[data-pkgname]').value.trim(); if (n) planInstall([n]); return; }
    if (a('data-get')) { post('package-get', {packages: a('data-get').split(' ')}).then(function () { poll(); }); return; }
    if (a('data-stop')) { post('package-stop', {package: a('data-stop')}).then(reload); return; }
    if (a('data-remove')) {
      if (!confirm('Remove ' + a('data-remove') + '? Only what Parseh itself installed is ever removed.')) return;
      post('package-remove', {package: a('data-remove')}).then(function (r) { if (!r.ok) alert(r.error); reload(); });
      return;
    }
    if (a('data-save-limit') !== null) {
      post('limit', {seconds: +root.querySelector('[data-limit]').value}).then(function (r) { say('[data-limit-said]', r.ok ? 'Saved.' : r.error, !r.ok); });
      return;
    }
    if (a('data-forget') !== null) {
      post('forget').then(function (r) { if (r.ok) { say('[data-forget-said]', r.drawings + ' drawings forgotten, ' + MB(r.bytes) + ' freed.'); } else say('[data-forget-said]', r.error, true); });
      return;
    }
    if (a('data-import-go') !== null) {
      var name = root.querySelector('[data-import-name]').value.trim();
      post('import', {data: importing, name: name}).then(function (r) {
        if (!r.ok) { say('[data-top-said]', r.error, true); return; }
        importing = null; root.querySelector('[data-import-out]').innerHTML = '';
        reload().then(function () { say('[data-top-said]', 'Imported as ' + r.theme.name + '.'); });
      });
    }
  });

  var importing = null;
  root.addEventListener('change', function (e) {
    var f = e.target.matches && e.target.matches('[data-import]') ? e.target.files[0] : null;
    if (!f) return;
    f.text().then(function (text) {
      post('import-read', {data: text}).then(function (r) {
        var out = root.querySelector('[data-import-out]');
        if (!r.ok) { say('[data-top-said]', r.error, true); return; }
        importing = text;
        // THE WHOLE PREAMBLE, SHOWN BEFORE THE IMPORT COMPLETES (the owner,
        // 2026-09-24): it is LaTeX this computer will run for every block
        // that names the theme
        out.innerHTML = '<section><h3>The theme ' + esc(r.theme.name) + ', as it would be compiled (' + esc(r.theme.compiler) + ')</h3>' +
          '<pre class="pre">' + esc(r.preamble) + '</pre>' +
          '<div class="fld"><span>Keep it as — ' + esc(S.rule) + (r.taken ? '. A theme called ' + esc(r.theme.name) + ' is here already: choose another name' : '') + '</span>' +
          '<input type="text" data-import-name value="' + esc(r.taken ? '' : r.theme.name) + '"></div>' +
          '<div class="row"><button type="button" data-import-go>Import this theme</button></div></section>';
      });
    });
  });

  function planInstall(names) {
    var out = root.querySelector('[data-plan-out]');
    out.textContent = 'Asking what it costs…';
    post('package-plan', {packages: names}).then(function (p) {
      if (!p.ok) { out.textContent = p.error; return; }
      if (!p.can) { out.innerHTML = '<span class="bad">' + esc(p.why) + '</span>'; return; }
      var rows = p.packages.map(function (x) { return esc(x.name) + (x.size ? ', ' + MB(x.size) : ', size not known before it starts') + (x.licence ? ' (' + esc(x.licence) + ')' : ''); }).join('; ');
      out.innerHTML = 'Into Parseh\'s own <code>texmf/</code>, from ' + esc(p.tex || 'TeX') + ': ' + rows +
        '. <button type="button" data-get="' + esc(names.join(' ')) + '">Get it</button>';
    });
  }
  function poll() {
    post('package-status').then(function (st) {
      S.packages = st; draw();
      var busy = Object.keys(st.jobs || {}).some(function (n) { return st.jobs[n].running; });
      if (busy) setTimeout(poll, 1000); else reload();
    });
  }

  draw();
  if (q.get('theme')) { var t0 = S.themes.filter(function (x) { return x.name.toLowerCase() === q.get('theme').toLowerCase(); })[0]; if (t0 && may('latex.theme')) { editing = {was: t0.name, theme: JSON.parse(JSON.stringify(t0))}; draw(); } }
  if (q.get('make') && may('latex.theme')) { root.querySelector('[data-new]').click(); }
  if (q.get('install') && may('latex.packages')) planInstall([q.get('install')]);
})();
"""
