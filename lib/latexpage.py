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
    main = """<main class="settings lx">
%(doors)s
<h1 class="idx">latex drawings</h1>
<p class="sub">The themes a latex block is drawn with, the TeX this computer has, and the
drawings kept. A formula written <code>:::math</code> is not touched by anything here.</p>
<div id="lx"><p>Reading what is here&hellip;</p></div>
<p class="foot">The themes are kept in <code>config/latex.json</code>, the packages Parseh got
in <code>texmf/</code>, and the drawings in <code>markdown/latex/</code>, made again whenever
they are needed. <a href="%(guide)s">LaTeX drawings</a>, in the guide.</p>
</main>""" % {"doors": settingspage.settings_doors(PAGE), "guide": GUIDE}
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
            r = latexdraw.draw(body.get("tex") or SAMPLE, None, theme=theme, preview=True)
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
            keys = used() if used else set()
            latexdraw.repair_owners(keys)
            return 200, dict(latexdraw.forget_unused(keys), ok=True)
        if what == "package-plan":
            names = list(dict.fromkeys(n for n in (body.get("packages") or []) if isinstance(n, str)))
            return 200, dict(texpackages.plan(names), ok=True)
        if what == "package-get":
            for n in dict.fromkeys(n for n in (body.get("packages") or []) if isinstance(n, str)):
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
.lx .grp-why{margin:0 0 5px;font-size:13px;color:var(--dim)}
.lx label.pk{display:block;margin:3px 0;font-size:14px}
.lx label.pk small{color:var(--dim)}
.lx label.pk code{font-size:12px}
.lx .missing{color:var(--danger,#c33);font-size:12px}
.lx textarea{width:100%;min-height:6rem;font-family:ui-monospace,monospace}
.lx pre.pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--boxbg);padding:8px;border-radius:6px;font-size:12px;max-height:22rem;overflow:auto}
.lx .said{min-height:1.2em;font-size:13px}
.lx .bad{color:var(--danger,#c33)}
@keyframes lx-plan-flash{0%{outline:3px solid var(--accent);outline-offset:3px}100%{outline:3px solid transparent;outline-offset:7px}}
@media (prefers-reduced-motion:reduce){.lx [data-package-panel].flash{animation:none}}
.lx img.sample{max-width:100%;background:#fff;padding:6px;border-radius:4px}
.lx .tex-status{margin:.65rem 0 1rem}
.lx .tex-status>div{display:grid;grid-template-columns:minmax(8rem,.8fr) minmax(0,2fr);gap:6px 12px;align-items:center;
  padding:8px 0;border-top:1px solid var(--rule)}
.lx .tex-status>div:last-child{border-bottom:1px solid var(--rule)}
.lx .tex-status dt{font-size:14px;font-weight:600}
.lx .tex-status dd{margin:0;min-width:0;display:flex;align-items:center;gap:6px 10px;flex-wrap:wrap}
.lx .st{display:inline-flex;align-items:center;gap:5px;font-size:12px;line-height:1.2;
  padding:2px 9px 2px 7px;border-radius:20px;border:1px solid currentColor;white-space:nowrap;
  background:color-mix(in srgb,currentColor 9%,transparent)}
.lx .st i{font-style:normal;font-weight:700}
.lx .st.ok{color:var(--ok)}
.lx .st.not,.lx .st.wait{color:var(--dim);border-style:dashed;background:none}
.lx .st.run{color:var(--accent)}
.lx .st.bad{color:var(--danger);background:color-mix(in srgb,var(--danger) 8%,transparent)}
.lx .tex-status .compiler-version{min-width:0;color:var(--dim);font:12px ui-monospace,monospace;overflow-wrap:anywhere}
@media (max-width:40rem){.lx .tex-status>div{grid-template-columns:1fr;gap:4px}}
.lx table{border-collapse:collapse;width:100%}
.lx td,.lx th{text-align:left;padding:4px 6px;border-bottom:1px solid var(--rule);font-size:13px}
.lx [data-package-panel]{scroll-margin-block:2rem}
.lx [data-package-panel].flash{animation:lx-plan-flash 1.1s ease-out}
.lx .pkg-intro{margin:.35rem 0 .65rem;color:var(--dim);font-size:13px}
.lx .pkg-live{min-height:1.35em;margin:.35rem 0;font-size:13px}
.lx .pkg-table{margin:.45rem 0}
.lx .pkg-table th,.lx .pkg-table td{vertical-align:top}
.lx .pkg-table th[scope=row]{font-weight:600;white-space:nowrap}
.lx .pkg-why{display:block;margin-top:2px;color:var(--dim);font-size:12px;overflow-wrap:anywhere}
.lx .pkg-state{min-width:12rem}
.lx .pkg-detail{display:block;margin-top:3px;color:var(--dim);font-size:12px;overflow-wrap:anywhere}
.lx .pkg-detail.bad{color:var(--danger)}
.lx .pkg-actions{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.lx .pkg-confirm{font-size:12px;color:var(--danger);margin-bottom:4px}
.lx .pkg-empty{color:var(--dim);font-size:13px}
.lx .pkg-bulk{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:.65rem 0}
@media (max-width:40rem){
  .lx .pkg-table,.lx .pkg-table tbody,.lx .pkg-table tr,.lx .pkg-table th,.lx .pkg-table td{display:block;width:100%}
  .lx .pkg-table thead{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
  .lx .pkg-table tr{border:1px solid var(--rule);border-radius:8px;background:var(--boxbg);padding:6px 8px;margin:8px 0}
  .lx .pkg-table th,.lx .pkg-table td{border:0;padding:4px 0;display:grid;grid-template-columns:7rem minmax(0,1fr);gap:5px 10px}
  .lx .pkg-table th::before,.lx .pkg-table td::before{content:attr(data-label);font-size:12px;color:var(--dim);font-weight:400}
  .lx .pkg-table .pkg-action{display:block}
  .lx .pkg-table .pkg-action::before{display:block;margin-bottom:4px}
  .lx .pkg-table .pkg-state{min-width:0}
}
"""

SCRIPT = r"""
(function () {
  'use strict';
  var S = JSON.parse(document.getElementById('lx-state').textContent);
  var root = document.getElementById('lx');
  var API = '/settings/api/latex/';
  var editing = null;       // the theme being edited: {was, theme}
  var packagePlans = {};    // name -> one quoted row, kept while the rest redraws
  var packageAsked = {};    // one-off names typed into the package box
  var packageRequest = {};  // name -> the quote currently allowed to change it
  var packageSerial = 0;
  var packageMessage = '';
  var removing = null;
  var polling = false;
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

  function unique(a) { return a.filter(function (x, at) { return x && a.indexOf(x) === at; }); }
  function packageAvailable(name) {
    var plan = packagePlans[name] || {};
    return !!(((S.packages || {}).available || {})[name] || plan.here === 'available');
  }
  function themeNeed(t) {
    var features = [], names = [];
    (S.needs[t.name] || []).forEach(function (need) {
      if (S.files[need[1]] !== false) return;
      var want = (need[2] || []).filter(function (name) { return !packageAvailable(name); });
      if (!want.length) return;
      if (features.indexOf(need[0]) < 0) features.push(need[0]);
      names = names.concat(want);
    });
    return {features: features, names: unique(names)};
  }
  function missingMarkup(t) {
    var need = themeNeed(t);
    if (!need.features.length) return '';
    return '<div class="missing">Not installed here: ' + need.features.map(esc).join(', ') +
      (need.names.length ? ' <button type="button" class="plain" data-install="' + esc(need.names.join(' ')) +
       '" aria-label="Review packages needed by ' + esc(t.name) + '"' + dis('latex.packages') +
       '>Review packages…</button>' : '') + '</div>';
  }
  function requiredPackages() {
    var rows = {};
    S.themes.forEach(function (t) {
      var need = themeNeed(t);
      need.names.forEach(function (name) {
        var row = rows[name] || (rows[name] = {name: name, themes: [], licence: ''});
        if (row.themes.indexOf(t.name) < 0) row.themes.push(t.name);
        (S.needs[t.name] || []).forEach(function (one) {
          if ((one[2] || []).indexOf(name) >= 0 && !row.licence) row.licence = one[3] || '';
        });
      });
    });
    Object.keys(packageAsked).forEach(function (name) {
      if (packageAvailable(name)) return;
      rows[name] = rows[name] || {name: name, themes: [], licence: ''};
      rows[name].asked = true;
    });
    return rows;
  }
  function packageRows() {
    var rows = requiredPackages(), installed = (S.packages || {}).installed || {}, jobs = (S.packages || {}).jobs || {};
    Object.keys(installed).forEach(function (name) {
      rows[name] = rows[name] || {name: name, themes: [], licence: ''};
      rows[name].installed = installed[name];
    });
    Object.keys(jobs).forEach(function (name) {
      rows[name] = rows[name] || {name: name, themes: [], licence: ''};
      rows[name].job = jobs[name];
    });
    Object.keys(packagePlans).forEach(function (name) {
      rows[name] = rows[name] || {name: name, themes: [], licence: ''};
      rows[name].plan = packagePlans[name];
    });
    return Object.keys(rows).sort().map(function (name) { return rows[name]; });
  }
  function packageWhy(row) {
    if (row.themes.length) return 'for the theme' + (row.themes.length === 1 ? ' ' : 's ') + row.themes.map(esc).join(', ');
    return row.asked ? 'you asked for it' : '';
  }
  function packageState(row) {
    var name = row.name, job = row.job || {}, plan = row.plan || {}, state = job.state ||
      (job.running ? 'running' : (job.error ? (job.error === 'Stopped.' ? 'stopped' : 'failed') : ''));
    var cost = plan.size == null ? '' : ', ' + MB(plan.size);
    var get = '<button type="button" class="go" data-package-get="' + esc(name) +
      '" aria-label="Get ' + esc(name + cost) + '"' + dis('latex.packages') + '>Get it</button>';
    var retry = '<button type="button" class="go" data-package-retry="' + esc(name) +
      '" aria-label="Try getting ' + esc(name) + ' again"' + dis('latex.packages') + '>Try again</button>';
    var stop = '<button type="button" class="plain" data-package-stop="' + esc(name) +
      '" aria-label="Stop getting ' + esc(name) + '"' + dis('latex.packages') + '>Stop</button>';
    if (row.installed) {
      if (removing === name) return {kind: 'got', text: '<span class="st ok"><i aria-hidden="true">✓</i> Got</span>',
        detail: 'Remove only the copy Parseh got.', action: '<div class="pkg-confirm">Remove ' + esc(name) +
        ' from Parseh?</div><div class="pkg-actions"><button type="button" class="danger" data-remove-yes="' + esc(name) +
        '" aria-label="Yes, remove ' + esc(name) + ' from Parseh"' + dis('latex.packages') + '>Remove</button>' +
        '<button type="button" class="plain" data-remove-no>Cancel</button></div>'};
      return {kind: 'got', text: '<span class="st ok"><i aria-hidden="true">✓</i> Got</span>',
        detail: '', action: '<button type="button" class="plain" data-remove="' + esc(name) +
        '" aria-label="Remove ' + esc(name) + ' from Parseh"' + dis('latex.packages') + '>Remove…</button>'};
    }
    if (state === 'queued' || state === 'waiting') return {kind: 'waiting',
      text: '<span class="st wait"><i aria-hidden="true">○</i> Waiting</span>', detail: 'Another package is being got first.', action: stop};
    if (state === 'running') return {kind: 'getting',
      text: '<span class="st run"><i aria-hidden="true">↻</i> Getting</span>',
      detail: (job.total ? job.done + ' of ' + job.total : '') + (job.say ? (job.total ? ' — ' : '') + esc(job.say) : ''), action: stop};
    if (state === 'failed') return {kind: 'failed',
      text: '<span class="st bad"><i aria-hidden="true">!</i> Could not get it</span>', detail: esc(job.error || 'It failed.'), action: retry};
    if (state === 'stopped') return {kind: 'stopped',
      text: '<span class="st not"><i aria-hidden="true">—</i> Stopped</span>', detail: '', action: retry};
    if (state === 'available' || packageAvailable(name) || plan.here === 'available') return {kind: 'available',
      text: '<span class="st ok"><i aria-hidden="true">✓</i> Available to this TeX</span>', detail: 'Parseh will not add a second copy.', action: ''};
    if (plan.state === 'asking') return {kind: 'asking',
      text: '<span class="st wait"><i aria-hidden="true">○</i> Asking about it</span>', detail: '', action: ''};
    if (plan.repository === 'unavailable' || plan.can_get === false || plan.state === 'unavailable') return {kind: 'unavailable',
      text: '<span class="st bad"><i aria-hidden="true">!</i> Not available here</span>',
      detail: esc(plan.why || 'This TeX Live repository does not offer it.'), action: ''};
    if (plan.state === 'ready') return {kind: 'ready', text: '<span class="st run"><i aria-hidden="true">→</i> To get</span>',
      detail: '', action: get, ready: true, size: plan.size};
    return {kind: 'review', text: '<span class="st not"><i aria-hidden="true">?</i> Cost not checked</span>',
      detail: 'Review its cost before getting it.', action: '<button type="button" class="plain" data-package-review="' + esc(name) +
      '" aria-label="Review the cost of ' + esc(name) + '"' + dis('latex.packages') + '>Review cost</button>'};
  }
  function packageRow(row, state) {
    var plan = row.plan || {}, licence = plan.licence || (row.installed || {}).licence || row.licence || '';
    var size = plan.size != null ? MB(plan.size) : ((row.installed || {}).size != null ? MB(row.installed.size) : '');
    return '<tr data-package-row="' + esc(row.name) + '"><th scope="row" data-label="Package"><code>' + esc(row.name) +
      '</code></th><td data-label="Needed for">' + packageWhy(row) + '</td><td data-label="Licence">' + esc(licence) +
      '</td><td data-label="Size">' + esc(size || 'Not known yet') + '</td><td class="pkg-state" data-label="State" aria-live="polite">' +
      state.text + (state.detail ? '<span class="pkg-detail' + (state.kind === 'failed' || state.kind === 'unavailable' ? ' bad' : '') +
      '">' + state.detail + '</span>' : '') + '</td><td class="pkg-action" data-label="Action">' + state.action + '</td></tr>';
  }
  function renderPackages() {
    var panel = root.querySelector('[data-package-panel]');
    if (!panel) return;
    var typed = panel.querySelector('[data-pkgname]');
    typed = typed ? typed.value : '';
    var rows = packageRows().map(function (row) { return {row: row, state: packageState(row)}; });
    var ready = rows.filter(function (x) { return x.state.ready; });
    var total = ready.reduce(function (n, x) { return n + (+x.state.size || 0); }, 0);
    var bulk = ready.length > 1 ? '<div class="pkg-bulk"><button type="button" class="go" data-package-get-all="' +
      esc(ready.map(function (x) { return x.row.name; }).join(' ')) + '" aria-label="Get all ' + esc(ready.map(function (x) { return x.row.name; }).join(', ')) +
      '"' + dis('latex.packages') + '>Get all' + (total ? ' — ' + MB(total) : '') + '</button><span>' + ready.length + ' packages ready</span></div>' : '';
    panel.innerHTML = '<h3 id="tex-packages">TeX packages</h3><p class="pkg-intro">Packages needed by the themes stay here. Review a cost before getting one; Parseh gets them one at a time.</p>' +
      '<div class="pkg-live" data-pkg-said aria-live="polite" aria-atomic="true" tabindex="-1">' + esc(packageMessage) + '</div>' + bulk +
      '<table class="pkg-table"><thead><tr><th scope="col">Package</th><th scope="col">Needed for</th><th scope="col">Licence</th><th scope="col">Size</th><th scope="col">State</th><th scope="col">Action</th></tr></thead><tbody>' +
      (rows.length ? rows.map(function (x) { return packageRow(x.row, x.state); }).join('') : '<tr><td colspan="6" class="pkg-empty">No package needs attention.</td></tr>') +
      '</tbody></table><div class="row"><input type="text" data-pkgname placeholder="a TeX Live package, e.g. chemfig"' + dis('latex.packages') +
      '><button type="button" class="plain" data-package-plan' + dis('latex.packages') + '>What it costs…</button></div>' + lock('latex.packages');
    var input = panel.querySelector('[data-pkgname]');
    if (input) input.value = typed;
  }
  function flashPackages() {
    var panel = root.querySelector('[data-package-panel]');
    if (!panel) return;
    panel.classList.remove('flash'); void panel.offsetWidth; panel.classList.add('flash');
  }
  function revealPackages(focus) {
    var panel = root.querySelector('[data-package-panel]');
    if (!panel) return;
    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    panel.scrollIntoView({block: 'center', behavior: reduced ? 'auto' : 'smooth'});
    try { (focus || panel.querySelector('[data-pkg-said]')).focus({preventScroll: true}); } catch (e) {}
  }
  function refreshThemeNeeds() {
    Array.prototype.forEach.call(root.querySelectorAll('[data-theme-missing]'), function (box) {
      var name = box.getAttribute('data-theme-missing');
      var theme = S.themes.filter(function (t) { return t.name === name; })[0];
      if (theme) box.innerHTML = missingMarkup(theme);
    });
  }

  function themeCard(t) {
    var isDef = t.name.toLowerCase() === S.default.toLowerCase();
    var comp = S.compilers[t.compiler];
    return '<div class="theme" data-theme="' + esc(t.name) + '"><h3>' + esc(t.name) +
      (isDef ? ' <small>(the default: a block naming no theme)</small>' : '') + '</h3>' +
      '<div class="facts">' + esc(t.compiler) + (comp ? '' : ' — not on this computer') + ' · ' +
      (t.packages.length ? esc(t.packages.join(', ')) : 'no packages') +
      (t.languages ? ' · text in the languages Parseh teaches' : '') +
      (t.font ? ' · font ' + esc(t.font) : '') + (t.preamble ? ' · a preamble of its own' : '') + '</div>' +
      '<div data-theme-missing="' + esc(t.name) + '">' + missingMarkup(t) + '</div>' +
      '<div class="row">' +
      '<button type="button" class="plain" data-edit="' + esc(t.name) + '" aria-label="Edit theme ' + esc(t.name) + '"' + dis('latex.theme') + '>Edit</button>' +
      '<button type="button" class="plain" data-rename="' + esc(t.name) + '" aria-label="Rename theme ' + esc(t.name) + '"' + dis('latex.rename') + '>Rename…</button>' +
      (isDef ? '' : '<button type="button" class="plain" data-default="' + esc(t.name) + '" aria-label="Make ' + esc(t.name) + ' the default theme"' + dis('latex.theme') + '>Make it the default</button>') +
      '<a class="parseh-btn" href="' + API + 'export?name=' + encodeURIComponent(t.name) + '" aria-label="Export theme ' + esc(t.name) + '">Export</a>' +
      (t.name.toLowerCase() === 'default' ? '' : '<button type="button" class="plain" data-delete="' + esc(t.name) + '" aria-label="Delete theme ' + esc(t.name) + '"' + dis('latex.theme') + '>Delete…</button>') +
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
      return '<div class="grp"><h4>' + esc(g[1]) + '</h4>' +
        (g[2] ? '<p class="grp-why">' + esc(g[2]) + '</p>' : '') + rows + '</div>';
    }).join('');
    return '<section class="edit"><h2>' + (editing.was ? 'The theme ' + esc(editing.was) : 'A new theme') + '</h2>' +
      (editing.was ? '' : '<div class="fld"><span>Its name — ' + esc(S.rule) + '</span><input type="text" data-name value="' + esc(t.name) + '"></div>') +
      '<div class="fld"><span>The compiler</span>' + comps + '</div>' +
      '<label class="pk"><input type="checkbox" data-languages' + (t.languages ? ' checked' : '') + '> <b>Text in the languages Parseh teaches</b> <small>Each language\'s face, as \\textfa{…}, \\textja{…}, \\texthi{…} and so on (xelatex or lualatex).</small></label>' +
      '<div class="fld"><span>A font of this computer for the drawing (xelatex or lualatex); empty for LaTeX\'s own</span><input type="text" data-font list="lx-fonts" value="' + esc(t.font) + '"><datalist id="lx-fonts"></datalist></div>' +
      '<div class="fld"><span>Packages</span>' + groups + '</div>' +
      '<div class="fld"><span>A preamble of its own, after the packages</span><textarea data-preamble>' + esc(t.preamble) + '</textarea></div>' +
      '<div class="fld"><span>Draw a sample with the theme as it is here</span><textarea data-sample>' + esc(S.sample) + '</textarea></div>' +
      '<div class="row"><button type="button" class="plain" data-draw-sample>Draw the sample</button><button type="button" class="go" data-save>Save the theme</button><button type="button" class="plain" data-cancel>Cancel</button></div>' +
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
      return '<div data-compiler="' + esc(c) + '"><dt><code>' + esc(c) + '</code></dt><dd>' +
        (v ? '<span class="st ok"><i aria-hidden="true">✓</i> Available</span><span class="compiler-version">' + esc(v.version) + '</span>'
           : '<span class="st not"><i aria-hidden="true">—</i> Not on this computer</span>') +
        '</dd></div>';
    }).join('');
    root.innerHTML =
      '<section><h2>The themes</h2><p class="why">A latex block names its theme after the fence — <code>::::latex chemistry</code> — and a block that names none is drawn with the default. Each theme is compiled on its own: nothing here touches a <code>:::math</code> formula.</p>' +
      S.themes.map(themeCard).join('') +
      '<div class="row"><button type="button" class="plain" data-new' + dis('latex.theme') + '>New theme</button>' +
      '<button type="button" class="plain" data-import-open' + dis('latex.import') + '>Import a theme…</button>' +
      '<input type="file" data-import accept=".json,application/json" hidden' + dis('latex.import') + '></div>' +
      lock('latex.theme') + '<div class="said" data-top-said></div><div data-import-out></div></section>' +
      editor() +
      '<section><h2>TeX on this computer</h2><p class="why">' + esc(S.tex.said || '') + '. Parseh installs no TeX: it draws with the TeX this computer has, and puts the packages it gets for the drawings in its own folder, <code>texmf/</code>.</p><h3>Compilers</h3><dl class="tex-status">' + comps + '</dl>' +
      '<div data-package-panel></div></section>' +
      '<section><h2>How long a drawing may take</h2><p class="why">A drawing that has not finished by then is stopped, and its block says so.</p><div class="row"><input type="number" data-limit min="' + S.limits[0] + '" max="' + S.limits[1] + '" value="' + S.timeout + '"' + dis('latex.limit') + '> seconds <button type="button" class="go" data-save-limit' + dis('latex.limit') + '>Save</button></div>' + lock('latex.limit') + '<div class="said" data-limit-said></div></section>' +
      '<section><h2>The drawings kept</h2><p class="why">' + S.kept.drawings + ' saved drawings, ' + MB(S.kept.bytes) + '. A live preview is temporary and is kept only when its document or exercise is saved. Saved source owns its drawing; one no saved source names is let go after a day. Each is made again when its block, theme, packages or TeX change.</p><div class="row"><button type="button" class="plain" data-forget' + dis('latex.forget') + '>Forget drawings nothing uses</button></div><div class="said" data-forget-said></div></section>';
    renderPackages();
    var fl = root.querySelector('#lx-fonts');
    if (fl) post('fonts').then(function (r) { if (r.ok) fl.innerHTML = r.fonts.map(function (f) { return '<option value="' + esc(f) + '">'; }).join(''); });
  }

  function say(sel, text, bad) { var el = root.querySelector(sel); if (el) { el.textContent = text || ''; el.className = 'said' + (bad ? ' bad' : ''); } }

  root.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button') : null;
    if (!b) return;
    var a = function (n) { return b.getAttribute(n); };
    if (a('data-import-open') !== null) { var picker = root.querySelector('[data-import]'); if (picker) picker.click(); return; }
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
    if (a('data-install') !== null) { planPackages(a('data-install').split(' ').filter(Boolean)); return; }
    if (a('data-package-plan') !== null) {
      var n = root.querySelector('[data-pkgname]').value.trim();
      if (n) { packageAsked[n] = true; planPackages([n]); }
      return;
    }
    if (a('data-package-review')) { planPackages([a('data-package-review')]); return; }
    if (a('data-package-get')) { startPackages([a('data-package-get')]); return; }
    if (a('data-package-retry')) { startPackages([a('data-package-retry')]); return; }
    if (a('data-package-get-all')) { startPackages(a('data-package-get-all').split(' ').filter(Boolean)); return; }
    if (a('data-package-stop')) {
      post('package-stop', {package: a('data-package-stop')}).then(function (r) {
        if (!r.ok) { packageMessage = r.error || 'Could not stop that package.'; }
        else { S.packages = r; packageMessage = 'Stopped ' + a('data-package-stop') + '.'; }
        renderPackages();
      }).catch(function () { packageMessage = 'Could not stop that package.'; renderPackages(); });
      return;
    }
    if (a('data-remove')) { removing = a('data-remove'); renderPackages(); return; }
    if (a('data-remove-no') !== null) { removing = null; renderPackages(); return; }
    if (a('data-remove-yes')) {
      var removeName = a('data-remove-yes');
      post('package-remove', {package: removeName}).then(function (r) {
        removing = null;
        if (!r.ok) { packageMessage = r.error || 'Could not remove ' + removeName + '.'; renderPackages(); return; }
        S.packages = r;
        packageMessage = 'Removed ' + removeName + ' from Parseh.';
        renderPackages();
        refreshPackageFacts();
      }).catch(function () { removing = null; packageMessage = 'Could not remove ' + removeName + '.'; renderPackages(); });
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
          '<div class="row"><button type="button" class="go" data-import-go>Import this theme</button></div></section>';
      });
    });
  });

  function planPackages(names) {
    names = unique(names.map(function (name) { return String(name || '').trim(); }));
    var skipped = names.filter(packageAvailable);
    names = names.filter(function (name) { return !packageAvailable(name); });
    if (!names.length) {
      packageMessage = skipped.length ? 'That package is already available to this TeX.' : 'Enter a TeX Live package name first.';
      renderPackages(); flashPackages(); revealPackages(); return;
    }
    var serial = ++packageSerial;
    names.forEach(function (name) {
      packageAsked[name] = true;
      packageRequest[name] = serial;
      packagePlans[name] = Object.assign({}, packagePlans[name] || {}, {name: name, state: 'asking'});
    });
    packageMessage = 'Asking what ' + (names.length === 1 ? names[0] + ' costs' : names.length + ' packages cost') + '… Nothing has been downloaded.';
    renderPackages(); flashPackages(); revealPackages();
    post('package-plan', {packages: names}).then(function (p) {
      if (serial !== packageSerial) return;
      if (!p.ok) {
        names.forEach(function (name) {
          if (packageRequest[name] === serial) packagePlans[name] = Object.assign({}, packagePlans[name], {state: 'unavailable', can_get: false, why: p.error || 'Could not ask what it costs.'});
        });
        packageMessage = p.error || 'Could not ask what the packages cost.';
        renderPackages(); flashPackages(); revealPackages(); return;
      }
      var seen = {};
      (p.packages || []).forEach(function (row) {
        if (!row || !row.name || packageRequest[row.name] !== serial) return;
        seen[row.name] = true;
        var next = Object.assign({}, row);
        next.state = row.here === 'available' ? 'available' :
          (row.repository === 'unavailable' || row.can_get === false ? 'unavailable' : 'ready');
        packagePlans[row.name] = next;
      });
      names.forEach(function (name) {
        if (packageRequest[name] !== serial || seen[name]) return;
        packagePlans[name] = Object.assign({}, packagePlans[name], {state: 'unavailable', can_get: false,
          why: p.why || 'The TeX Live repository did not answer for this package.'});
      });
      var ready = names.filter(function (name) { return (packagePlans[name] || {}).state === 'ready'; });
      var unavailable = names.length - ready.length;
      packageMessage = ready.length ? ready.length + ' package' + (ready.length === 1 ? '' : 's') + ' ready to get' +
        (unavailable ? '; ' + unavailable + ' unavailable here' : '') + '. Nothing has been downloaded.' :
        (unavailable ? 'These packages are not available from this TeX Live repository.' : 'Nothing needs to be downloaded.');
      renderPackages(); flashPackages();
      revealPackages(root.querySelector('[data-package-get]') || root.querySelector('[data-pkg-said]'));
    }).catch(function () {
      if (serial !== packageSerial) return;
      names.forEach(function (name) {
        if (packageRequest[name] === serial) packagePlans[name] = Object.assign({}, packagePlans[name], {state: 'unavailable', can_get: false, why: 'Could not ask what it costs. Check the connection and try again.'});
      });
      packageMessage = 'Could not ask what the packages cost. Check the connection and try again.';
      renderPackages(); flashPackages(); revealPackages();
    });
  }
  function startPackages(names) {
    names = unique(names.map(function (name) { return String(name || '').trim(); })).filter(function (name) {
      return (packagePlans[name] || {}).state === 'ready';
    });
    if (!names.length) { packageMessage = 'Review a package cost before getting it.'; renderPackages(); return; }
    packageMessage = 'Getting ' + names.join(', ') + ' one at a time…';
    renderPackages();
    post('package-get', {packages: names}).then(function (st) {
      if (!st.ok) { packageMessage = st.error || 'Could not start getting those packages.'; renderPackages(); return; }
      S.packages = st;
      packageMessage = 'Getting ' + names.join(', ') + ' one at a time…';
      renderPackages();
      pollPackages();
    }).catch(function () { packageMessage = 'Could not start getting those packages.'; renderPackages(); });
  }
  function refreshPackageFacts() {
    post('state').then(function (v) {
      if (!v.ok) return;
      S = v;
      renderPackages();
      refreshThemeNeeds();
    });
  }
  function pollPackages() {
    if (polling) return;
    polling = true;
    function check() {
      post('package-status').then(function (st) {
        if (!st.ok) { packageMessage = st.error || 'Could not check package progress.'; polling = false; renderPackages(); return; }
        S.packages = st;
        renderPackages();
        var busy = Object.keys(st.jobs || {}).some(function (name) {
          var job = st.jobs[name] || {};
          return job.running || job.state === 'queued' || job.state === 'waiting' || job.state === 'running';
        });
        if (busy) { setTimeout(check, 1000); return; }
        polling = false;
        refreshPackageFacts();
      }).catch(function () { packageMessage = 'Could not check package progress.'; polling = false; renderPackages(); });
    }
    check();
  }

  draw();
  if (q.get('theme')) { var t0 = S.themes.filter(function (x) { return x.name.toLowerCase() === q.get('theme').toLowerCase(); })[0]; if (t0 && may('latex.theme')) { editing = {was: t0.name, theme: JSON.parse(JSON.stringify(t0))}; draw(); } }
  if (q.get('make') && may('latex.theme')) { root.querySelector('[data-new]').click(); }
  if (q.get('install') && may('latex.packages')) planPackages([q.get('install')]);
})();
"""
