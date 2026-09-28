# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings -> Speech to text (TO-DO §7.23, a0.4.1): the program that turns a
video's sound into a transcript, the two models it reads, and what this
computer will run them on.

A DOOR OF ITS OWN, drawn the way the LaTeX drawings are (lib/latexpage.py):
the owner decided on 2026-09-28 that speech to text is not a section of the
reading help.  It is not about reading what nobody has glossed; it is a tool of
the page a video is ADDED on, and the page that installs it says so.  The
reading help carries one line pointing here.

ANY DEVICE THAT HAS BEEN LET IN MAY DO ALL OF IT -- get, remove, stop -- and the
door's pill says so (lib/settingspage.py SETTINGS says why: whoever presses the
button, the only bytes that can arrive are the ones Parseh pins, each checked
against its hash).  So this page draws no lock and no dead button; its
buttons are hidden only where the table said no, which it never does today.

THE ROWS ARE THE READING HELP'S ROWS (lib/lookuppage.py ROW_JS and STYLE): a
state that is a glyph, a word and a colour, a bar that moves with the time
left, Get it / Stop / Remove.  A person reads this page as they read that one.
What is new is the processor: the CPU that always works, and an NVIDIA
graphics card that is used only when Parseh has proved it can be -- with what
is missing, said in words, when it cannot, and a button that looks again.

WHAT THE PAGE SAYS ABOUT THE PROCESSOR is worked out by lib/getstt.py and
arrives in the state; the requirements of a graphics card are made from its
GPU_NEEDS table, so that a later version of the program changes one place and
this page says the new thing.  The first sentence about the processor is that
the CPU already works: a card can make speech to text faster, and none is
required.

The routes are serve.py's (`/lookup/api/speech`, `speechcheck`, `getspeech`,
`dropspeech`, `stopspeech`, each in lib/settingspage.py ROUTES).
"""
import html
import os
import sys

LIB = os.path.dirname(os.path.realpath(__file__))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import getstt                                                # noqa: E402
import languages                                             # noqa: E402
import lookuppage                                            # noqa: E402
import settingspage                                          # noqa: E402

PAGE = "/settings/speech/"
GUIDE = getstt.GUIDE
# the three settings this page's buttons are, and only these
KEYS = ("speech.get", "speech.remove", "speech.stop")


def esc(s):
    return html.escape(str(s), quote=True)


def door_tags():
    """What the Settings hub says under this door: which models are ready, or
    that nothing is installed -- a door that says so is doing its job."""
    ready = [k for k in getstt.MODELS if getstt.model_ready(k)] if getstt.runtime_ready() else []
    if not ready:
        return '<span class="tag">not installed</span>'
    return "".join('<span class="tag on">%s</span>' % esc(k) for k in ready)


def credits():
    """The licence line of each part: {"speech:runtime": {who, licence}, ...}."""
    import notices
    return {k: {"who": v[0], "licence": v[1]} for k, v in notices.speech_credits().items()}


def view(jobs=None, where="", device=""):
    """Everything the page draws, in one answer: drawn from it when it opens and
    from the next one every time it asks how things stand (`speech` with
    {"full": true}, or `speechcheck`)."""
    st = getstt.status()
    kept = st["runtime"]["size"] + sum(m["size"] for m in st["models"].values())
    try:
        free = lookuppage.disk_free(getstt.STT_DIR)
    except OSError:
        free = None
    return {"ok": True, "speech": st,
            "jobs": {"speech": jobs or {}},
            "sizes": {"speech:%s" % k: getstt.plan(k) for k in getstt.PARTS},
            "credits": credits(),
            "languages": [{"code": L.code, "name": L.name, "native": L.native,
                           "rtl": L.dir == "rtl", "whisper": L.code in getstt.WHISPER_LANGUAGES}
                          for L in languages.LANGS.values()],
            "kept": kept, "free": free, "where": where or "", "device": device or "",
            "may": {k: settingspage.may(k, where) for k in KEYS}}


def page(jobs=None, where="", device=""):
    """/settings/speech/, the whole page."""
    v = view(jobs, where, device)
    main = """<main class="settings rh sp">
%(doors)s
<h1 class="idx">speech to text</h1>
<p class="sub">A transcript made on this computer, while you add a video. It is optional:
nothing is fetched until you press a button here, and no sound and no transcript is ever
sent to a speech-recognition service.</p>
<p class="whomay">%(gate)s <span>Any device that has been let in may get, remove or stop what is on
this page. Whoever presses the button, only the files %(name)s pins can be fetched, each checked
against its own hash.</span></p>
<div id="sp-band" class="band"></div>
<div id="sp"><p class="rh-wait">Reading what is here&hellip;</p></div>
<p class="foot">What is fetched here lives in the <code>stt/</code> folder &mdash;
<code>runtime/</code> for the program, <code>models/</code> for the models, and <code>tmp/</code> for
the sound of a video while it is being transcribed, which is deleted when it has been &mdash; and
nothing else of %(name)s depends on it. It is offered only on the page a video is added on:
<a href="/youtube/add/">Add a video</a>. Every licence is also on the
<a href="/licences/">licences</a> page. <a href="%(guide)s" data-guide>How speech to text works</a>,
in the guide.</p>
</main>""" % {"doors": settingspage.settings_doors(PAGE), "gate": settingspage.gate(KEYS),
              "name": settingspage.NAME, "guide": esc(GUIDE)}
    script = ('<script id="sp-state" type="application/json">%s</script>\n<script>%s</script>'
              % (settingspage._in_script(v), SCRIPT))
    return settingspage.frame("Speech to text &mdash; %s settings" % settingspage.NAME,
                              '<a href="/settings/">settings</a> &middot; speech to text',
                              "Speech to text", GUIDE, main,
                              style=lookuppage.STYLE + STYLE, script=script)


STYLE = r"""
.sp .whomay{display:flex;gap:8px 10px;align-items:baseline;flex-wrap:wrap;margin:.2rem 0 1rem;font-size:13.5px;color:var(--dim)}
.sp .whomay .gate{flex:none}
.sp section.about{padding:14px 16px}
.sp .about a{color:var(--accent)}
.sp .about p{margin:.35rem 0;font-size:14px}
.sp .about ul{margin:.4rem 0 .2rem;padding-inline-start:1.25rem;font-size:14px}
.sp .about li{margin:.15rem 0}
.sp .tagline{display:inline-block;font-size:12.5px;color:var(--accent);border:1px solid var(--rule);border-radius:20px;
  padding:1px 9px;margin-inline-start:8px;white-space:nowrap;vertical-align:middle;background:var(--boxbg)}
.sp .need{margin:.35rem 0 .1rem;padding-inline-start:1.25rem;font-size:13.5px}
.sp .need li{margin:.1rem 0}
.sp .need a{color:var(--accent)}
.sp .it .mem{color:var(--dim);font-size:12.5px}
.sp details.tech{margin-top:8px;font-size:12.5px;color:var(--dim)}
.sp details.tech summary{cursor:pointer;color:var(--dim);width:max-content;max-width:100%}
.sp details.tech dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:2px 14px;margin:6px 0 0}
.sp details.tech dt{color:var(--faint)}
.sp details.tech dd{margin:0;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.sp .modes{margin:0;padding:12px 16px 14px;border-top:1px solid var(--rule);font-size:13.5px}
.sp .modes dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 14px;margin:.3rem 0 0}
.sp .modes dt{font-weight:600}
.sp .modes dd{margin:0;color:var(--dim)}
.sp .langs{display:flex;flex-wrap:wrap;gap:6px 8px;padding:12px 16px 14px}
.sp .lang-chip{display:inline-flex;align-items:baseline;gap:7px;border:1px solid var(--rule);border-radius:8px;
  padding:3px 10px;font-size:13.5px;background:var(--boxbg)}
.sp .lang-chip .nat{font-size:16px;color:var(--accent)}
.sp .lang-chip.no{border-style:dashed;color:var(--dim)}
.sp .lang-chip.no .nat{color:var(--dim)}
.sp .lang-chip i{font-style:normal;font-weight:700;font-size:12px;color:var(--ok)}
.sp .lang-chip.no i{color:var(--dim)}
.sp a.plain{text-decoration:none}
.sp .band .who a{color:var(--accent)}
@media (max-width:620px){
  .sp .it-act a.plain,.sp .it-act button{flex:1 1 auto}
  .sp details.tech dl{grid-template-columns:1fr;gap:0}
  .sp details.tech dt{margin-top:4px}
  .sp .modes dl{grid-template-columns:1fr;gap:0}
  .sp .modes dt{margin-top:6px}
}
"""

SCRIPT = r"""
(function () {
  'use strict';
  var S = JSON.parse(document.getElementById('sp-state').textContent);
  var root = document.getElementById('sp');
  var band = document.getElementById('sp-band');
  var asking = {};         // a row's question: {kind: 'remove'|'bad'|'wait', said}
  var checking = false;    // the graphics card is being looked at
  var checked = false;     // ...and was, once, on opening
  var polling = null;
  /*ROW_JS*/

  var J = function () { return (S.jobs || {}).speech || {}; };
  function may(setting) { return !S.may || S.may[setting] !== false; }
  function size(id) { return (S.sizes || {})['speech:' + id] || {}; }
  function built(s) {
    if (!s) return '';
    var d = new Date(String(s).slice(0, 10) + 'T12:00:00');
    return 'built ' + (isNaN(d) ? esc(s) : d.toLocaleDateString('en-GB', {day: 'numeric', month: 'long', year: 'numeric'}));
  }
  // an error is the sentence the manager gave, without its own name in front of it
  function said(e) { return String(e || '').replace(/^getstt:\s*/, ''); }
  function GB(n) { return n == null ? '' : (n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB' : MB(n)); }

  /* ---- what each state of a part is called, in words a person reads */
  var OLD = {older: 'Built by an older Parseh', newer: 'Built by a newer Parseh', other_python: 'Built for another Python',
             broken: 'Incomplete'};
  function stateOf(r) {
    var j = r.job;
    if (j && j.running) {
      var pc = j.total ? Math.min(99, Math.floor(100 * j.done / j.total)) : null;
      return {cls: 'run', glyph: j.phase === 'build' ? '↻' : '↓',
              word: (j.phase === 'build' ? 'Installing' : 'Downloading') + (pc != null ? ' · ' + pc + '%' : '')};
    }
    if (r.withModel) return {cls: 'run', glyph: '↓', word: 'Comes first, with the model'};
    if (r.na) return {cls: 'na', glyph: '–', word: 'Not available'};
    if (j && (j.error || j.stopped) && !r.have) return {cls: 'bad', glyph: '!', word: 'Stopped'};
    if (r.have && OLD[r.state]) return {cls: r.state === 'broken' ? 'bad' : 'old', glyph: r.state === 'broken' ? '!' : '↻', word: OLD[r.state]};
    if (r.have) return {cls: 'ok', glyph: '✓', word: 'Installed'};
    return {cls: 'not', glyph: '○', word: 'Not yet'};
  }

  /* ---- the rows: the program, then the two models */
  function parts() {
    var sp = S.speech, rt = sp.runtime, lic = S.credits || {}, rows = [];
    var rtPlan = size('runtime');
    rows.push({id: 'runtime', name: 'The speech program', 'for': 'What runs a model: faster-whisper, with the libraries it needs, in a folder of its own. ' +
               'It is fetched with the first model, and it is not part of ' + 'Parseh' + '’s own installation.',
               have: rt.have, state: rt.state, why: rt.why, na: rt.state === 'unavailable', credit: lic['speech:runtime'],
               facts: rt.have ? 'faster-whisper ' + esc(rt.version) + ' · CTranslate2 ' + esc(rt.ctranslate2) + ' · ' + GB(rt.size) : '',
               kept: rt.size, reinstall: rt.state !== 'absent', noResume: true});
    Object.keys(sp.models).forEach(function (id) {
      var m = sp.models[id];
      rows.push({id: id, name: m.label, tag: m.tag, 'for': m.hint, have: m.have, state: m.state, why: m.why,
                 na: rt.state === 'unavailable' && !m.have, naWhy: rt.why, credit: lic['speech:' + id],
                 facts: m.have ? GB(m.size) + ' · ' + esc(m.repo) + (m.built ? ' · ' + built(m.built) : '') : '',
                 kept: m.size, needsProgram: !rt.ready, memory: m.memory});
    });
    rows.forEach(function (r) { r.job = J()[r.id] || null; });
    // the program comes first when a model is fetched: its own row says where it is
    var first = Object.keys(sp.models).filter(function (id) { var j = J()[id]; return j && j.running; })[0];
    if (first && !rt.ready && !rows[0].job) rows[0].withModel = first;
    rows.forEach(function (r) { r.usable = r.id === 'runtime' || rt.ready; });
    return rows;
  }

  /* ---- the size line of a part not installed: measured, said before anything starts */
  function sizeLine(r) {
    var p = size(r.id), bits = [];
    if (p.download != null) {
      var dl = '<b>' + GB(p.download) + '</b> to download';
      if (p.kept != null) dl += ', kept as about <b>' + GB(p.kept) + '</b>';
      bits.push(dl);
      if (r.needsProgram) bits.push('this includes the speech program, which comes first');
      if (p.disk_peak != null && p.disk_peak > (p.download || 0) * 1.1)
        bits.push('needs about ' + GB(p.disk_peak) + ' free while it is fetched');
    }
    if (p.have) bits.push(GB(p.have) + ' of it already here, from a download that was stopped');
    if (r.memory) bits.push('needs ' + esc(r.memory) + ' of memory to run');
    return bits.join(' · ');
  }

  function row(r) {
    var st = stateOf(r), j = r.job || {}, id = r.id, facts = '', note = '', act = '', q = asking[id];
    if (j.running) {
      sample(id, j);
      var bits = [];
      if (j.phase === 'build') bits.push('putting the program in place');
      else bits.push(j.total ? GB(j.done) + ' of ' + GB(j.total) : GB(j.done || 0) + ' so far');
      var lt = left(id, j);
      if (lt) bits.push('<b>' + lt + '</b>');
      else if (j.total && j.phase !== 'build') bits.push('<span class="q">working out the time left</span>');
      facts = bits.join(' · ');
      var pc = j.total ? Math.min(100, 100 * j.done / j.total) : null;
      note = '<div class="bar' + (pc == null ? ' loose' : '') + '" role="progressbar" aria-label="' + esc(r.name) + '"' +
        (pc != null ? ' aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + Math.round(pc) + '"><i style="width:' + pc.toFixed(1) + '%"></i>' : '><i></i>') + '</div>' +
        (j.say ? '<div class="note">' + esc(j.say) + '</div>' : '');
      act = may('speech.stop') ? '<button class="plain" type="button" data-stop="' + esc(id) + '" aria-label="Stop getting ' + esc(r.name) + '">Stop</button>' : '';
    } else if (r.withModel) {
      note = '<div class="note">It is installed first, as part of getting ' + esc(r.withModel) + ': see the bar below.</div>';
    } else if (r.na) {
      note = '<div class="note">' + esc(r.why || r.naWhy || 'Not available on this computer.') + '</div>';
    } else if (r.have) {
      facts = r.facts;
      if (!r.usable && !OLD[r.state]) note = '<div class="note">It cannot be used until the speech program is installed again.</div>';
      if (OLD[r.state]) {
        note = '<div class="note' + (r.state === 'broken' ? ' bad' : '') + '">' + esc(r.why) + '</div>';
        act += may('speech.get') ? '<button class="go" type="button" data-get="' + esc(id) + '">' +
          (r.id === 'runtime' ? 'Install it again' : 'Get it again') + '</button>' : '';
      }
      if (j.error) note += '<div class="note bad">The last try stopped: ' + esc(said(j.error)) + '</div>';
      else if (j.stopped) note += '<div class="note">You stopped the last try; what is here is unchanged.</div>';
      if (may('speech.remove')) act += '<button class="plain" type="button" data-remove="' + esc(id) + '" aria-label="Remove ' + esc(r.name) + '">Remove…</button>';
    } else {
      facts = sizeLine(r);
      if (r.id === 'runtime' && !j.stopped && !j.error)
        note = '<div class="note">It is installed by pip, which cannot carry on a half-fetched file: if you stop it, it starts again from the beginning.</div>';
      if (j.stopped) {
        note = '<div class="note bad">You stopped it' + (j.done ? ' at ' + GB(j.done) : '') + '. ' +
          (r.id === 'runtime' ? 'The program starts again from the beginning.' : 'Getting it again carries on from there.') + '</div>';
        act = '<button class="go" type="button" data-get="' + esc(id) + '">' + (r.id === 'runtime' ? 'Try again' : 'Carry on') + '</button>';
      } else if (j.error) {
        note = '<div class="note bad">' + esc(said(j.error)) + '</div>';
        act = '<button class="go" type="button" data-get="' + esc(id) + '">Try again</button>';
      } else {
        act = '<button class="go" type="button" data-get="' + esc(id) + '" aria-label="Get ' + esc(r.name) + '">Get it</button>';
      }
      if (!may('speech.get')) act = '';
    }
    if (q) note += ask(q, id);
    var credit = r.credit ? '<div class="it-lic">' + r.credit.who + ' · ' + r.credit.licence + '</div>' : '';
    return '<div class="it' + (j.running ? ' busy' : '') + '" data-row="' + esc(id) + '"><div class="it-main"><div class="it-head">' +
      '<span class="it-name">' + esc(r.name) + '</span>' + (r.tag ? '<span class="tagline">' + esc(r.tag) + '</span>' : '') +
      pill(st.cls, st.glyph, st.word) + '</div>' +
      '<div class="it-for">' + esc(r['for']) + '</div>' +
      (facts ? '<div class="it-facts">' + facts + '</div>' : '') + note + credit + '</div>' +
      '<span></span><div class="it-act">' + (q ? '' : act) + '</div></div>';
  }
  function ask(q, id) {
    if (q.kind === 'wait') return '<div class="ask"><span class="said">' + esc(q.said) + '</span></div>';
    if (q.kind === 'bad') return '<div class="ask bad"><span class="said">' + esc(q.said) + '</span>' +
      '<button class="plain" type="button" data-cancel="' + esc(id) + '">All right</button></div>';
    return '<div class="ask"><span class="said">' + q.said + '</span>' +
      '<button class="danger" type="button" data-yes="' + esc(id) + '">Remove</button>' +
      '<button class="plain" type="button" data-cancel="' + esc(id) + '">Keep it</button></div>';
  }

  /* ---- the processor: the CPU, which always works, and the graphics card, which is used only when proved */
  function needs() {
    return (S.speech.requirements || []).map(function (n) {
      return '<li>' + (n.link ? '<a href="' + esc(n.link) + '" rel="noopener" target="_blank">' + esc(n.what) + '</a>' : esc(n.what)) + '</li>';
    }).join('');
  }
  function tech(hw) {
    var c = hw.cuda, cpu = hw.cpu, sp = S.speech, rt = sp.runtime, dl = [];
    function add(k, v) { if (v) dl.push('<dt>' + esc(k) + '</dt><dd>' + v + '</dd>'); }
    add('Program', rt.ready ? 'faster-whisper ' + esc(rt.version) + ', CTranslate2 ' + esc(rt.ctranslate2) + ', for Python ' + esc(rt.python.replace(/^cp(\d)(\d+)$/, '$1.$2')) : 'not installed yet');
    add('CPU', esc(cpu.compute) + ', ' + cpu.threads + ' thread' + (cpu.threads === 1 ? '' : 's') + ' of ' + cpu.logical + ' logical');
    add('Graphics card', c.name ? esc(c.name) + (c.memory ? ', ' + GB(c.memory) : '') : (c.state === 'none' ? 'none found' : 'not looked at yet'));
    add('Driver', c.driver ? esc(c.driver) : '');
    add('Computes in', c.compute ? esc(c.compute) : (c.ready ? '' : 'not decided until the card is ready'));
    add('cuBLAS', c.cublas_dir ? esc(c.cublas_dir) : '');
    add('Looked at', hw.at ? new Date(hw.at * 1000).toLocaleString('en-GB') : 'not yet');
    add('Kind of computer', esc(sp.platform || 'unknown'));
    return '<details class="tech"><summary>technical details</summary><dl>' + dl.join('') + '</dl></details>';
  }
  function processor() {
    var sp = S.speech, hw = sp.hardware, c = hw.cuda, cpu = hw.cpu, guide = esc(sp.pin.help);
    var cpuRow = '<div class="it" data-row="cpu"><div class="it-main"><div class="it-head"><span class="it-name">Processor</span>' +
      pill('ok', '✓', 'CPU · ready') + '</div>' +
      '<div class="it-for">Speech to text will work on this computer. A compatible NVIDIA graphics card can make it considerably faster, but one is not required.</div>' +
      '<div class="it-facts">' + esc(cpu.said) + '</div></div><span></span><div class="it-act"></div></div>';
    var st, body = '', name = 'Graphics card', act = '';
    var check = '<button class="plain" type="button" data-check title="Look at the graphics card again, for after you have installed something it needed">' +
      (checking ? 'Looking…' : 'Check again') + '</button>';
    if (checking) {
      st = pill('run', '…', 'Looking'); body = 'Looking at the graphics card…';
    } else if (c.state === 'ready') {
      st = pill('ok', '✓', 'GPU acceleration ready');
      name = 'Graphics card · ' + esc(c.name || 'NVIDIA');
      body = 'Automatic mode will use the graphics card for faster transcription. You can still choose CPU if you prefer.';
      act = check;
    } else if (c.state === 'found-not-ready') {
      st = pill('old', '!', 'Found, not ready');
      name = 'Graphics card · ' + esc(c.name || 'NVIDIA');
      body = '<b>NVIDIA GPU found, but speech-to-text acceleration is not ready.</b> CPU transcription will still work.' +
        '<div class="note bad">Missing: ' + c.missing.map(esc).join('; ') + '.</div>' +
        '<div class="note">For GPU acceleration this installation needs:</div><ul class="need">' + needs() + '</ul>' +
        (sp.requirements_note ? '<div class="note">' + esc(sp.requirements_note) + '</div>' : '');
      act = '<a class="plain" href="' + guide + '" data-guide>How to enable GPU acceleration</a>' + check;
    } else if (c.state === 'none') {
      st = pill('not', '○', 'No NVIDIA graphics card');
      body = esc(c.why || 'No NVIDIA graphics card was found on this computer.');
      act = c.supported_build === false ? '' : check;
    } else {
      st = pill('not', '○', 'Not looked at yet');
      body = 'Parseh has not looked at the graphics card yet.';
      act = check;
    }
    var gpuRow = '<div class="it" data-row="gpu"><div class="it-main"><div class="it-head"><span class="it-name">' + name + '</span>' + st + '</div>' +
      '<div class="it-for">' + body + '</div>' + tech(hw) + '</div><span></span><div class="it-act">' + act + '</div></div>';
    var modes = '<div class="modes"><b>Processing</b>, chosen when you add a video:<dl>' +
      '<dt>Automatic — recommended</dt><dd>Uses the graphics card when Parseh can prove it is usable, and the CPU otherwise. Right now: <b>' +
        (c.ready ? esc(c.name || 'the NVIDIA graphics card') : 'the CPU') + '</b>.</dd>' +
      '<dt>CPU</dt><dd>Always the CPU, int8. Works on every computer, with or without a card.</dd>' +
      '<dt>NVIDIA GPU</dt><dd>Offered only where the card is ready' + (c.ready ? '' : ' — not on this computer yet') + '.</dd></dl></div>';
    return '<h2 class="part">Processor</h2><section class="shared">' + cpuRow + gpuRow + modes + '</section>';
  }

  function about() {
    var sp = S.speech, t = sp.models['large-v3-turbo'].download, l = sp.models['large-v3'].download;
    return '<section class="shared about"><p><b>What it is.</b> Whisper, a speech-recognition model, run on this computer by faster-whisper. ' +
      'It turns the sound of a video you are adding into a timed transcript, which you can edit before the video is added.</p><ul>' +
      '<li>It is optional. Until you get it here, nothing is fetched and nothing changes.</li>' +
      '<li>It happens on this computer: no sound and no transcript is sent to a speech-recognition service.</li>' +
      '<li>It works on a computer with no graphics card. Long videos take a while on the CPU.</li>' +
      '<li>The models are large: ' + GB(t) + ' and ' + GB(l) + ', and the program is ' + GB((S.sizes['speech:runtime'] || {}).download) + ' more.</li>' +
      '<li>It is offered only on the page a video is added on, <a href="/youtube/add/">Add a video</a>: not on a video already in your library.</li></ul></section>';
  }
  function languages() {
    var chips = S.languages.map(function (L) {
      return '<span class="lang-chip' + (L.whisper ? '' : ' no') + '"><span class="nat" lang="' + esc(L.code) + '"' + (L.rtl ? ' dir="rtl"' : '') + '>' +
        esc(L.native) + '</span><span>' + esc(L.name) + '</span><i>' + (L.whisper ? '✓' : 'not offered') + '</i></span>';
    }).join('');
    var some = S.languages.filter(function (L) { return !L.whisper; });
    return '<h2 class="part">Languages <span class="aside">— every language Parseh has' +
      (some.length ? '; Whisper does not list ' + some.map(function (L) { return esc(L.name); }).join(', ') : '') + '</span></h2>' +
      '<section class="shared"><div class="langs">' + chips + '</div></section>';
  }

  var ROWS = {};
  function draw() {
    ROWS = {};
    var rows = parts();
    rows.forEach(function (r) { ROWS[r.id] = r; });
    root.innerHTML = about() + processor() +
      '<h2 class="part">The program and the models</h2><section class="shared">' + rows.map(row).join('') + '</section>' + languages();
    drawBand();
  }
  function drawBand() {
    var who = S.where === 'self' ? 'You are on <b>the computer Parseh runs on</b>.' :
      'You are on <b>' + esc(S.device || 'another device') + '</b>, ' + (S.where === 'vpn' ? 'on a VPN' : 'let in over the Wi-Fi') + '.';
    who += ' ' + (may('speech.get') && may('speech.remove') ? 'You may get, remove and stop anything on this page.' : 'Some of this page is changed on the computer Parseh runs on.');
    band.innerHTML = '<div><div class="n">' + (S.kept ? MB(S.kept) : '0 MB') + '</div><div class="l">kept for speech to text</div></div>' +
      (S.free != null ? '<div><div class="n">' + MB(S.free) + '</div><div class="l">free on this computer</div></div>' : '<div></div>') +
      '<div class="who">' + who + '</div>';
  }

  /* ---- asking the server */
  function post(what, body) {
    return fetch('/lookup/api/' + what, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})})
      .then(function (r) { return r.json().then(function (j) { j.status = r.status; return j; }); });
  }
  function busy() {
    return Object.keys(J()).some(function (k) { return J()[k].running || J()[k].waiting; });
  }
  function refresh() {
    return post('speech', {full: true}).then(function (j) {
      if (!j || !j.ok) return;
      var was = busy();
      S = j;
      draw();
      if (busy() || was) schedule(busy() ? 1000 : 0);
      if (was && !busy() && window.ParsehActivity) ParsehActivity.poke(200);
    }).catch(function () {});
  }
  function schedule(ms) { clearTimeout(polling); if (ms) polling = setTimeout(refresh, ms); }
  function kick() {
    if (window.ParsehActivity) ParsehActivity.poke(200);
    refresh().then(function () { schedule(1000); });
  }
  function check() {
    if (checking) return;
    checking = true; draw();
    post('speechcheck', {}).then(function (j) { checking = false; if (j && j.ok) { S = j; } draw(); },
                                 function () { checking = false; draw(); });
  }

  root.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b || b.disabled) return;
    var id;
    if (b.hasAttribute('data-check')) { check(); return; }
    if ((id = b.getAttribute('data-get'))) {
      b.disabled = true; delete asking[id];
      post('getspeech', {key: id}).then(function (j) {
        if (!j.ok) { asking[id] = {kind: 'bad', said: j.error || 'That was refused.'}; draw(); return; }
        kick();
      });
      return;
    }
    if ((id = b.getAttribute('data-remove'))) {
      var r = ROWS[id], what = id === 'runtime' ? 'the speech program' : 'the ' + id + ' model';
      asking[id] = {kind: 'remove', said: 'Remove ' + esc(what) + '? It frees ' + (GB(r.kept) || 'a little room') +
                    '; getting it back is a ' + GB(size(id).download) + ' download.' +
                    (id === 'runtime' ? ' The models stay, but cannot be used until the program is back.' : '')};
      draw(); return;
    }
    if ((id = b.getAttribute('data-cancel'))) { delete asking[id]; draw(); return; }
    if ((id = b.getAttribute('data-stop'))) {
      b.disabled = true;
      post('stopspeech', {key: id}).then(kick);
      return;
    }
    if ((id = b.getAttribute('data-yes'))) {
      b.disabled = true; delete asking[id];
      post('dropspeech', {key: id}).then(function (j) {
        if (!j.ok) { asking[id] = {kind: 'bad', said: j.error || 'That was refused.'}; draw(); return; }
        refresh();
      });
    }
  });
  document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });

  draw();
  if (busy()) schedule(1000);
  // the graphics card is looked at once, on opening, where it has not been (a child, 0.2 s, no model loaded)
  if (!S.speech.hardware.checked && S.speech.hardware.cuda.supported_build !== false && !checked) { checked = true; check(); }
})();
""".replace("/*ROW_JS*/", lookuppage.ROW_JS)
