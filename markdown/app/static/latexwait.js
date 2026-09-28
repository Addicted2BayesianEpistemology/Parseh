// SPDX-License-Identifier: GPL-3.0-or-later
/* THE DRAWINGS A PAGE OPENED WITHOUT (the owner, 2026-09-28).  A document
   page is made at once, whatever it holds (htmlgen's latex_defer): a LaTeX
   drawing not made yet stands as its source, marked data-latex-pending.  This
   has them made on the computer a few at a time, under a bar that says how
   many are done, and swaps each into the page as it comes -- matched by its
   number, data-latex-idx.  A page opened while the computer cannot be reached
   keeps its sources and says so, with Try again.  The document page and a
   note's page both load it; it needs nothing else of theirs. */
(function () {
  "use strict";
  var sheet = document.getElementById("sheet");
  var url = sheet && sheet.getAttribute("data-drawings");
  if (!url || !sheet.querySelector("[data-latex-pending]")) return;
  var BATCH = 4, PATIENCE = 5 * 60 * 1000;
  var total = null, busy = false;

  var box = document.createElement("div");
  box.className = "latex-waiting";
  box.innerHTML = '<p class="latex-waiting-say" role="status" aria-live="polite"></p>' +
    '<div class="latex-waiting-bar" role="progressbar" aria-label="LaTeX drawings being made" ' +
    'aria-valuemin="0" aria-valuemax="100"><i></i></div>' +
    '<button type="button" class="latex-waiting-again" hidden>Try again</button>';
  document.body.appendChild(box);
  var say = box.querySelector(".latex-waiting-say"), bar = box.querySelector(".latex-waiting-bar");
  var again = box.querySelector(".latex-waiting-again");
  again.addEventListener("click", function () { run(); });

  function left() { return sheet.querySelectorAll("[data-latex-pending]").length; }
  function show(done, all) {
    var n = all || left();
    say.textContent = "Making the LaTeX drawings: " + Math.min(done, n) + " of " + n;
    var pc = n ? Math.round(100 * done / n) : 100;
    bar.setAttribute("aria-valuenow", String(pc));
    bar.firstChild.style.width = pc + "%";
  }

  function swap(html) {
    var t = document.createElement("template");
    t.innerHTML = html;
    var fresh = {};
    Array.prototype.forEach.call(t.content.querySelectorAll("[data-latex-idx]"), function (el) {
      if (!el.hasAttribute("data-latex-pending")) fresh[el.getAttribute("data-latex-idx")] = el;
    });
    var put = [];
    Array.prototype.forEach.call(sheet.querySelectorAll("[data-latex-pending][data-latex-idx]"), function (el) {
      var f = fresh[el.getAttribute("data-latex-idx")];
      if (!f) return;
      var n = f.cloneNode(true);
      el.replaceWith(n);
      put.push(n);
    });
    if (window.ParsehMath && put.length) put.forEach(function (n) { window.ParsehMath.typeset(n); });
  }

  function ask() {
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, PATIENCE);
    return fetch(url, {method: "POST", credentials: "same-origin", cache: "no-store",
                       headers: {"Content-Type": "application/json"},
                       body: JSON.stringify({batch: BATCH}), signal: ctl ? ctl.signal : undefined})
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) throw new Error(j.error || ("Parseh answered " + r.status + "."));
          return j;
        });
      }, function () {
        throw new Error("Parseh's computer cannot be reached from here: the drawings are shown as they are written until it can.");
      })
      .then(function (j) { clearTimeout(timer); return j; }, function (e) { clearTimeout(timer); throw e; });
  }

  function run() {
    if (busy) return;
    busy = true;
    box.classList.remove("err", "gone");
    again.hidden = true;
    bar.hidden = false;
    show(total === null ? 0 : total - left(), total);
    (function round() {
      ask().then(function (j) {
        if (total === null) total = (j.left || 0) + (j.drawn || 0);
        swap(j.html || "");
        var done = total - (j.left || 0);
        show(done, total);
        if (j.left > 0 && j.drawn > 0) return round();
        busy = false;
        say.textContent = total > 1 ? "The " + total + " LaTeX drawings are made." : "The LaTeX drawings are made.";
        setTimeout(function () { box.classList.add("gone"); }, 1600);
      }, function (e) {
        busy = false;
        box.classList.add("err");
        bar.hidden = true;
        say.textContent = e.message;
        again.hidden = false;
      });
    })();
  }
  run();
})();
