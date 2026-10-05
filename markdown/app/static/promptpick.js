// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh studio — WHAT A PROMPT IS ASKED TO TEACH: the boxes, the presets, the level and the length of the
   studio's two prompts (the authoring prompt's page, static/app.js `initPrompt`, and the editor's exercise
   dialog, static/editor.js `exercisePrompt`; brief §7), drawn from what the server answers and from nothing else.

   THE SERVER SAYS WHAT EXISTS (markdown/app/promptboxes.py): every box with its group, its one line, its size
   and whether this language can use it; the presets; the levels and the lengths; and the prompt itself.  This
   file holds no list of any of it, so a box the server gains is drawn the day it exists, a count is read off the
   answer and never written down here, and the prompt is never put together in the browser: this says what is
   ticked, the page asks, the server makes the prompt.

     const teach = ParsehPromptPick.boxes(element, {presets, total, remember, title, why, types, onChange})
       teach.draw(answer)       the route's answer: boxes, presets, types, preticked, always_chars
       teach.boxes()            the ids ticked, or null while there is no choice (ask for the default)
       teach.types()            the same for the exercise types (the dialog's)
       teach.agrees(answer)     is what the answer made the same as what is ticked?  (a remembered id the
                                server no longer has is dropped on a draw, and the page asks once more)
       teach.stale()            the server refused what was remembered: the next ask is the default, and the
                                ids it does know are put back by the draw that follows
       teach.total(text, always)  the live total of the prompt (the page's; the dialog's is the row's)
       teach.busy(sentence)     the whole panel greyed for a reason, or '' to give it back
     const under = ParsehPromptPick.line(element, {surface, lang, remember, ids, onChange})
       under.draw(answer)       fills "for a learner at" and "length" from answer.levels / answer.lengths
       under.params()           {level, length, translit} as far as they are chosen: what a request carries
       under.setLang(code)      another language: the options (the scheme of the transliteration) are asked again
       under.ready()            a promise: the options are known, or the server did not say in time
       under.busy(on)           the selects off, while the page is doing something else
   The options (lib/llmrow.js `ParsehLLMRow.options`) are the row's own control, drawn beside the level and the
   length: which language has which is the server's to say. */
(function (root) {
  "use strict";
  if (root.ParsehPromptPick) return;
  const doc = root.document;
  const KEY = "parseh_prompt_";
  const ID = /^[A-Za-z0-9_-]{1,40}$/;
  const WHY = "whatever you do not tick is still named in the prompt as reserved, so the model does not " +
    "write it by accident; fewer boxes make a shorter prompt, for a chatbot that takes less at once.";

  function make(tag, cls, text) {
    const n = doc.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  // "12,500", exactly: these are counts the server measured, not estimates
  const said = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  /* ---- what this device remembers: the ticked set, the level and the length --------------------------------
     ONE SET FOR EVERY LANGUAGE (brief §7.4), every access inside try: a page with its storage refused works,
     it just forgets.  A value is only ever read back as plain ids: whatever else is under the key (a hand
     edit, another version) is no choice at all. */
  function recall(key) {
    try { return JSON.parse(root.localStorage.getItem(KEY + key)); } catch (e) { return null; }
  }
  function keep(key, value) {
    try { root.localStorage.setItem(KEY + key, JSON.stringify(value)); } catch (e) { /* refused: nothing is kept */ }
  }
  function recalledIds(key) {
    const v = recall(key);
    return Array.isArray(v) && v.every(x => typeof x === "string" && ID.test(x)) ? v : null;
  }
  function recalledId(key) {
    const v = recall(key);
    return typeof v === "string" && ID.test(v) ? v : "";
  }

  /* ---- the boxes ------------------------------------------------------------------------------------------- */
  function boxes(container, opts) {
    opts = opts || {};
    const keyed = opts.remember || "";            // the key the ticked set is kept under; none: nothing is kept
    const first = keyed ? recalledIds(keyed) : null;
    let ticked = first ? new Set(first) : null;   // null until there is a choice: then the server's default is asked for
    let lost = null;                              // what was remembered when the server refused it (stale)
    let typesOn = null;
    let answer = null, built = "", busyWhy = "", totalEl = null, busyEl = null, lastTotal = null;
    const el = make("section", "pp");
    el.hidden = true;
    container.appendChild(el);

    const change = () => { if (opts.onChange) opts.onChange(); };
    const remember = () => { if (keyed && ticked) keep(keyed, [...ticked]); };

    function item(kind, x) {
      const label = make("label", "pp-box");
      label.dataset[kind] = x.id;
      const input = make("input");
      input.type = "checkbox";
      input.value = x.id;
      input.addEventListener("change", () => {
        const set = kind === "type" ? typesOn : ticked;
        if (input.checked) set.add(x.id); else set.delete(x.id);
        if (kind === "box") remember();
        paint();
        change();
      });
      label.append(input, make("span", "pp-name", x.name), make("span", "pp-size"),
                   make("span", "pp-says", x.line), make("span", "pp-offwhy"));
      return label;
    }
    function group(title, items, kind) {
      const set = make("fieldset", "pp-group");
      set.dataset.group = title;
      if (title) set.appendChild(make("legend", null, title));
      items.forEach(x => set.appendChild(item(kind, x)));
      return set;
    }
    function preset(p) {
      ticked = new Set(p.boxes);
      remember();
      paint();
      change();
    }
    function build(a) {
      el.textContent = "";
      el.appendChild(make("h" + (opts.level || 3), "pp-title", opts.title || "teach the model to write:"));
      el.appendChild(make("p", "pp-why", opts.why || WHY));
      busyEl = make("p", "pp-busy");
      busyEl.setAttribute("role", "status");
      el.appendChild(busyEl);
      if (opts.presets && a.presets && a.presets.length) {
        const row = make("div", "pp-presets");
        row.setAttribute("role", "group");
        row.setAttribute("aria-label", "ready-made choices of boxes");
        a.presets.forEach(p => {
          const b = make("button", "pp-preset", p.name);
          b.type = "button";
          b.dataset.preset = p.id;
          b.addEventListener("click", () => preset(p));
          row.appendChild(b);
        });
        el.appendChild(row);
      }
      // A GROUP IS DRAWN WHERE ITS FIRST BOX IS, with a heading: the server orders the boxes, and a group is
      // whatever string they share (a box of a group nobody here has heard of still has its place)
      const groups = new Map();
      a.boxes.forEach(b => {
        if (!b.shown) return;
        const g = b.group || "";
        if (!groups.has(g)) groups.set(g, []);
        groups.get(g).push(b);
      });
      groups.forEach((items, title) => el.appendChild(group(title, items, "box")));
      if (a.types && a.types.length) {
        const set = group(opts.types || "the exercises to ask for", a.types, "type");
        set.classList.add("pp-types");
        el.appendChild(set);
      }
      totalEl = null;
      if (opts.total) {
        totalEl = make("div", "pp-total");
        totalEl.setAttribute("aria-live", "polite");
        el.appendChild(totalEl);
      }
    }

    // WHAT IS DRAWN FOLLOWS THE ANSWER'S SHAPE (its boxes, their names, groups and lines, its presets and types):
    // a size or a reason a box is off changes in place, so a person ticking boxes with the keyboard keeps the
    // focus where it is
    function draw(a) {
      answer = a;
      if (!a || !Array.isArray(a.boxes)) { el.hidden = true; return; }
      el.hidden = false;
      const known = new Set(a.boxes.map(b => b.id));
      if (ticked === null) {
        const mine = a.preticked ? a.preticked.boxes : a.boxes.filter(b => b.on).map(b => b.id);
        const back = lost ? lost.filter(id => known.has(id)) : [];
        // a remembered set none of which the server knows any more is no choice: the default stands
        ticked = new Set(lost && (back.length || !lost.length) ? back : mine);
        lost = null;
      } else {
        ticked = new Set([...ticked].filter(id => known.has(id)));
      }
      if (Array.isArray(a.types)) {
        const kinds = new Set(a.types.map(t => t.id));
        typesOn = typesOn === null
          ? new Set(a.preticked ? a.preticked.types : a.types.filter(t => t.on).map(t => t.id))
          : new Set([...typesOn].filter(id => kinds.has(id)));
      }
      const shape = JSON.stringify([a.boxes.map(b => [b.id, b.name, b.group, b.line, !!b.shown]),
        (a.presets || []).map(p => [p.id, p.name]), (a.types || []).map(t => [t.id, t.name, t.line])]);
      if (shape !== built) { build(a); built = shape; }
      paint();
      if (lastTotal) total(lastTotal[0], lastTotal[1]);
    }

    function paint() {
      if (!answer || !answer.boxes) return;
      busyEl.textContent = busyWhy;
      const sizes = (x, label) => {
        const input = label.querySelector("input");
        input.checked = (label.dataset.type !== undefined ? typesOn : ticked).has(x.id);
        input.disabled = !!(busyWhy || x.disabled);
        label.classList.toggle("pp-off", !!x.disabled);
        const size = label.querySelector(".pp-size");
        size.textContent = x.disabled ? "" : said(x.chars) + (x.chars === 1 ? " character" : " characters");
        size.dataset.chars = String(x.chars);
        label.querySelector(".pp-offwhy").textContent = x.disabled || "";
      };
      el.querySelectorAll("[data-box]").forEach(label => {
        const b = answer.boxes.find(x => x.id === label.dataset.box);
        if (b) sizes(b, label);
      });
      el.querySelectorAll("[data-type]").forEach(label => {
        const t = (answer.types || []).find(x => x.id === label.dataset.type);
        if (t) sizes(t, label);
      });
      // A PRESET SHOWS AS ACTIVE ONLY WHILE THE TICKED SET IS ITS SET, counted over the boxes this language has: a
      // preset that ticks the reading marks is still the preset in a language that has none
      const shown = new Set(answer.boxes.filter(b => b.shown).map(b => b.id));
      const mine = [...ticked].filter(id => shown.has(id)).sort().join(",");
      const allOff = answer.boxes.every(b => !b.shown || b.disabled);
      el.querySelectorAll("[data-preset]").forEach(btn => {
        const p = (answer.presets || []).find(x => x.id === btn.dataset.preset);
        const on = !!p && p.boxes.filter(id => shown.has(id)).sort().join(",") === mine;
        btn.setAttribute("aria-pressed", String(on));
        btn.disabled = !!busyWhy || allOff;
      });
    }

    function agrees(a) {
      if (!a || !Array.isArray(a.boxes) || ticked === null) return true;
      if (!a.boxes.every(b => !b.shown || b.disabled || b.on === ticked.has(b.id))) return false;
      return !Array.isArray(a.types) || typesOn === null || a.types.every(t => t.on === typesOn.has(t.id));
    }

    // THE LIVE TOTAL is worked out by the row's own counter, so that the two numbers on the page can never disagree
    function total(text, always) {
      lastTotal = [text, always];
      if (!totalEl) return;
      totalEl.textContent = "";
      const s = root.ParsehLLMRow ? root.ParsehLLMRow.promptSize(text) : null;
      if (!s || !s.chars) return;
      totalEl.textContent = "the prompt, without your question: " + s.line +
        (always ? " · " + said(always) + " characters of it are always there, whatever you tick" : "");
      totalEl.dataset.chars = String(s.chars);
      totalEl.dataset.tokens = String(s.tokens);
    }

    return {
      el, draw, agrees, total,
      boxes: () => ticked === null ? null : [...ticked],
      types: () => typesOn === null ? null : [...typesOn],
      stale: () => { lost = ticked ? [...ticked] : null; ticked = null; },
      busy: why => { busyWhy = why || ""; paint(); }
    };
  }

  /* ---- the level, the length and the options, under the question ------------------------------------------ */
  function line(container, opts) {
    opts = opts || {};
    const prefix = typeof opts.remember === "string" ? opts.remember : null;   // null: nothing is kept
    const state = {level: prefix === null ? "" : recalledId(prefix + "level"),
                   length: prefix === null ? "" : recalledId(prefix + "length")};
    const el = make("div", "pp-under");
    const selects = {};
    const change = () => { if (opts.onChange) opts.onChange(); };
    function field(key, words) {
      const label = make("label", "pp-pick");
      label.hidden = true;                        // until the server has given the list
      label.appendChild(doc.createTextNode(words + ": "));
      const select = make("select");
      select.dataset.key = key;
      if (opts.ids && opts.ids[key]) select.id = opts.ids[key];
      select.addEventListener("change", () => {
        state[key] = select.value;
        if (prefix !== null) keep(prefix + key, select.value);
        change();
      });
      label.appendChild(select);
      el.appendChild(label);
      selects[key] = select;
    }
    field("level", "for a learner at");
    field("length", "length");
    const slot = make("div", "pp-options");
    el.appendChild(slot);
    container.appendChild(el);
    // THE OPTIONS ARE THE ROW'S OWN CONTROL (lib/llmrow.js), asked of the server by language: no table of which
    // language has what is kept here, and a language with none draws nothing
    const choices = root.ParsehLLMRow && root.ParsehLLMRow.options
      ? root.ParsehLLMRow.options(slot, {surface: opts.surface, lang: opts.lang, onOption: change}) : null;

    function fill(key, list) {
      const select = selects[key], sig = JSON.stringify(list);
      // a list the server did not give is a choice that cannot be made: not drawn, rather than drawn empty
      select.parentNode.hidden = !list.length;
      if (select.dataset.sig === sig) return;
      select.dataset.sig = sig;
      select.textContent = "";
      list.forEach(x => select.appendChild(new root.Option(x.name, x.id)));
      // a remembered id this server does not offer is no choice: "not said"
      if (!list.some(x => x.id === state[key])) state[key] = "";
      select.value = state[key];
    }
    return {
      el,
      draw: a => {
        if (a && Array.isArray(a.levels)) fill("level", a.levels);
        if (a && Array.isArray(a.lengths)) fill("length", a.lengths);
      },
      params: () => {
        const out = {};
        if (state.level) out.level = state.level;
        if (state.length) out.length = state.length;
        return Object.assign(out, choices ? choices.options() : {});
      },
      setLang: code => choices ? choices.setLang(code) : Promise.resolve(),
      ready: () => choices ? choices.optionsReady() : Promise.resolve(),
      busy: on => el.querySelectorAll("select").forEach(s => { s.disabled = !!on; }),
      destroy: () => { if (choices) choices.destroy(); }
    };
  }

  root.ParsehPromptPick = {boxes, line, said};
})(window);
