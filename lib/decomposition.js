// SPDX-License-Identifier: GPL-3.0-or-later
/* Shared character selection and tree presentation. All data comes from the local server. */
(function () {
  'use strict';
  const OPERATORS = {
    '⿰': 'Left and right', '⿱': 'Top and bottom', '⿲': 'Three across', '⿳': 'Three stacked',
    '⿴': 'Full enclosure', '⿵': 'Enclosed from above', '⿶': 'Enclosed from below',
    '⿷': 'Enclosed from the left', '⿸': 'Upper-left enclosure', '⿹': 'Upper-right enclosure',
    '⿺': 'Lower-left enclosure', '⿻': 'Overlapping parts', '⿼': 'Enclosed from the right',
    '⿽': 'Lower-right enclosure', '⿾': 'Reflected form', '⿿': 'Rotated form', '㇯': 'Part removed'
  };
  const HAN = /^(?:\p{Unified_Ideograph}|[\uF900-\uFAFF\u{2F800}-\u{2FA1F}]|〇)(?:[\uFE00-\uFE0F\u{E0100}-\u{E01EF}])?$/u;
  const eligible = text => HAN.test(text);
  const segmenter = typeof Intl.Segmenter === 'function' ? new Intl.Segmenter(undefined, {granularity: 'grapheme'}) : null;
  function units(text) {
    if (segmenter) return Array.from(segmenter.segment(text), x => x.segment);
    return text.match(/[^][\uFE00-\uFE0F\u{E0100}-\u{E01EF}]?/gu) || [];
  }
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }
  function button(text, action, cls) {
    const node = el('button', cls, text); node.type = 'button'; node.onclick = action; return node;
  }
  async function request(what, body, signal) {
    const response = await fetch('/lookup/api/' + what, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {}), signal
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw Error(data.error || 'The local server did not answer.');
    return data;
  }
  function mount(opts) {
    if (!['ja', 'zh'].includes(opts.lang)) return null;
    const noun = opts.lang === 'ja' ? 'Kanji' : 'Hanzi', label = 'Decompose ' + noun;
    let active = false, generation = 0, controller, returnFocus, history = [], observer;
    const cache = new Map();
    const toggle = button(label, activate, 'cd-toggle');
    toggle.setAttribute('aria-pressed', 'false'); toggle.title = 'Temporarily select a character to inspect its components';
    opts.toolbar.appendChild(toggle);
    const bar = el('div', 'cd-modebar'); bar.hidden = true; bar.setAttribute('role', 'status');
    bar.append(el('span', '', 'Choose a ' + noun.toLowerCase() + ' in the text.'));
    bar.append(button('Done', () => setActive(false), 'cd-done'));
    document.body.appendChild(bar);
    const modal = el('dialog', 'cd-dialog'); modal.lang = 'en'; modal.dir = 'ltr';
    const heading = el('h2', '', noun + ' components'); heading.id = 'cd-heading';
    modal.setAttribute('aria-labelledby', heading.id);
    const head = el('div', 'cd-head');
    const close = button('×', closeModal, 'cd-close'); close.setAttribute('aria-label', 'Close decomposition');
    head.append(heading, close);
    const nav = el('nav', 'cd-nav'); nav.setAttribute('aria-label', 'Component navigation');
    const content = el('div', 'cd-content'); content.setAttribute('aria-live', 'polite');
    const foot = el('div', 'cd-foot');
    modal.append(head, nav, content, foot); document.body.appendChild(modal);
    modal.addEventListener('cancel', e => { e.preventDefault(); closeModal(); });
    modal.addEventListener('click', e => { if (e.target === modal) {
      const r = modal.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeModal();
    } });

    function textArea(target) { return target.closest && target.closest(opts.scope); }
    function wrap() {
      if (!active) return;
      observer.disconnect();
      document.querySelectorAll(opts.scope).forEach(root => {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
          acceptNode(node) {
            if (!node.parentElement || node.parentElement.closest('rt,rp,button,a,input,textarea,select,[contenteditable],.cd-char'))
              return NodeFilter.FILTER_REJECT;
            return units(node.data).some(eligible) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
          }
        });
        const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(node => {
          const fragment = document.createDocumentFragment();
          units(node.data).forEach(unit => {
            if (!eligible(unit)) { fragment.appendChild(document.createTextNode(unit)); return; }
            const span = el('span', 'cd-char', unit);
            span.dataset.character = unit; span.tabIndex = 0; span.setAttribute('role', 'button');
            span.setAttribute('aria-label', label + ' ' + unit); fragment.appendChild(span);
          });
          node.replaceWith(fragment);
        });
      });
      observer.observe(opts.observe || document.querySelector('main') || document.body, {subtree: true, childList: true, characterData: true});
    }
    observer = new MutationObserver(() => { if (active) wrap(); });
    function setActive(on) {
      active = on; toggle.classList.toggle('on', on); toggle.setAttribute('aria-pressed', String(on));
      document.body.classList.toggle('cd-mode', on); bar.hidden = !on;
      if (on) {
        if (opts.onModeChange) opts.onModeChange(true);
        wrap();
      } else {
        observer.disconnect();
        // Remove only our temporary targets; ruby and word containers stay intact.
        document.querySelectorAll('.cd-char').forEach(span => {
          const parent = span.parentNode; span.replaceWith(...span.childNodes); parent.normalize();
        });
        toggle.focus({preventScroll: true});
        if (opts.onModeChange) opts.onModeChange(false);
      }
    }
    async function activate() {
      if (active) { setActive(false); return; }
      toggle.disabled = true;
      try {
        const data = await request('decompositions');
        cache.clear();
        if (data.packs.some(p => p.have && p.languages.includes(opts.lang))) {
          if (modal.open) closeModal();
          setActive(true);
        }
        else { history = []; openModal(toggle); installMessage(); }
      } catch (error) {
        history = []; openModal(toggle); message('Could not load component data', error.message, activate);
      } finally { toggle.disabled = false; }
    }
    function openModal(from) {
      if (!modal.open) {
        returnFocus = from || document.activeElement;
        if (opts.onOpen) opts.onOpen();
        modal.showModal(); close.focus();
      }
    }
    function closeModal() {
      generation++; if (controller) controller.abort();
      modal.close();
      const target = returnFocus && returnFocus.isConnected ? returnFocus : toggle;
      target.focus({preventScroll: true});
    }
    function message(title, detail, retry) {
      content.replaceChildren(el('h3', 'cd-message-title', title), el('p', 'cd-message', detail));
      if (retry) content.append(button('Try again', retry, 'cd-retry'));
      nav.replaceChildren(); foot.replaceChildren();
    }
    function setupLink(text) {
      const link = el('a', '', text); link.href = '/lookup/#character-components'; return link;
    }
    function installMessage() {
      message('Install character components', 'Add a component pack once, then explore characters offline.');
      content.append(setupLink('Open dictionary & component setup'));
    }
    function navigate(char, from, back = false) {
      if (!modal.open) history = [];
      if (!back) history.push(char);
      openModal(from); load(char);
    }
    async function load(char) {
      const ticket = ++generation;
      if (controller) controller.abort(); controller = new AbortController();
      content.replaceChildren(el('div', 'cd-hero', char), el('p', 'cd-message', 'Loading components…'));
      nav.replaceChildren(); foot.replaceChildren();
      try {
        const data = cache.get(char) || await request('decompose', {code: opts.lang, character: char}, controller.signal);
        if (ticket !== generation || !modal.open) return;
        if (cache.size > 64) cache.clear(); cache.set(char, data);
        render(data);
      } catch (error) {
        if (error.name === 'AbortError' || ticket !== generation) return;
        message('Could not load ' + char, error.message, () => load(char));
        if (history.length > 1) nav.append(button('Return to ' + history[0], () => {
          history = [history[0]]; navigate(history[0], null, true);
        }));
      }
    }
    function render(data) {
      nav.replaceChildren();
      if (history.length > 1) {
        nav.append(button('← Back', () => { history.pop(); navigate(history[history.length - 1], null, true); }));
        nav.append(button('Return to ' + history[0], () => { history = [history[0]]; navigate(history[0], null, true); }));
      }
      content.replaceChildren(); foot.replaceChildren();
      if (data.status === 'not_installed') { installMessage(); return; }
      if (data.status === 'missing') {
        content.append(el('div', 'cd-hero', data.character));
        if (data.meanings[data.character]) content.append(el('p', 'cd-meaning', data.meanings[data.character]));
        content.append(el('p', 'cd-message', 'No component decomposition is available for this character.'));
        content.append(setupLink('Manage component packs and fallback coverage'));
      } else {
        const viewport = el('div', 'cd-tree-viewport'); viewport.tabIndex = 0;
        viewport.setAttribute('aria-label', 'Component tree. Scroll to explore a wide tree.');
        const tree = el('ul', 'cd-tree'); tree.append(treeNode(data.tree, data, true));
        viewport.append(tree); content.append(viewport);
        if (data.status === 'atomic') content.append(el('p', 'cd-message', 'This character is a basic component in this source.'));
        else content.append(el('p', 'cd-hint', 'Select a component to explore it. Basic components stay together; scroll to see wider trees.'));
      }
      if (!data.dictionary || !Object.keys(data.dictionary).length) {
        foot.append(el('p', '', 'Install the ' + (opts.lang === 'ja' ? 'Japanese' : 'Chinese') + ' dictionary to show component meanings. '), setupLink('Open setup'));
      } else foot.append(el('p', '', 'Meanings: ' + (data.dictionary.source || 'installed dictionary') +
        (data.dictionary.licence ? ' · ' + data.dictionary.licence : '')));
      if (data.variant_fallback) foot.append(el('p', '', 'Showing the default character structure for this glyph variant.'));
      for (const source of data.sources || []) {
        const line = el('p'); const link = el('a', '', source.name); link.href = source.url; link.target = '_blank'; link.rel = 'noopener';
        line.append(link, document.createTextNode(' · ' + source.licence + ' · ' + source.attribution)); foot.append(line);
      }
      // Start at the centered root of a wide horizontal tree.
      requestAnimationFrame(() => {
        const view = content.querySelector('.cd-tree-viewport');
        if (view) view.scrollLeft = Math.max(0, (view.scrollWidth - view.clientWidth) / 2);
      });
    }
    function treeNode(node, data, root = false) {
      const li = el('li', root ? 'cd-root' : ''), box = el('div', 'cd-node');
      const char = node.character;
      if (char) {
        const glyph = !root && eligible(char) ? button(char, () => navigate(char), 'cd-glyph') : el('span', 'cd-glyph', char);
        glyph.lang = opts.lang;
        if (glyph.tagName === 'BUTTON') glyph.setAttribute('aria-label', 'Explore components of ' + char);
        box.append(glyph);
        const meaning = data.meanings[char] || data.meanings[node.variantOf] || '';
        const meaningLabel = el('span', 'cd-meaning', meaning || (node.variantOf ? 'Form of ' + node.variantOf : 'Meaning unavailable'));
        if (meaning) meaningLabel.title = meaning;
        box.append(meaningLabel);
        if (node.partial) box.append(el('small', 'cd-layout', 'Partial form'));
      } else box.append(el('span', 'cd-structure', node.kind === 'unknown' ? 'Unlabelled component' : (OPERATORS[node.operator] || 'Component group')));
      if (node.operator && char && node.children) box.append(el('small', 'cd-layout', OPERATORS[node.operator] || 'Combined components'));
      if (node.truncated) box.append(el('small', 'cd-layout', 'Select to explore further'));
      li.append(box);
      if (node.children && node.children.length) {
        const children = el('ul');
        for (const child of node.children) children.append(treeNode(child, data));
        li.append(children);
      }
      return li;
    }
    // Capture on window so neither reader's copy/card/seek/editor handlers
    // receive the click. Pointer defaults remain intact for text selection.
    for (const type of ['click', 'dblclick', 'pointerdown', 'mousedown', 'touchstart', 'mouseover', 'mouseenter']) {
      window.addEventListener(type, e => {
        if (!active || modal.open || !textArea(e.target)) return;
        e.stopImmediatePropagation();
        if (type !== 'click' && type !== 'dblclick') return;
        e.preventDefault();
        if (type === 'dblclick') return;
        const target = e.target.closest('.cd-char');
        const selection = window.getSelection();
        if (target && !(selection && !selection.isCollapsed)) navigate(target.dataset.character, target);
      }, {capture: true, passive: false});
    }
    window.addEventListener('keydown', e => {
      if (modal.open && e.key !== 'Escape') { e.stopImmediatePropagation(); return; }
      if (e.key === 'Escape' && (active || modal.open)) {
        e.preventDefault(); e.stopImmediatePropagation();
        if (modal.open) closeModal(); else setActive(false);
      } else if (active && !modal.open && textArea(e.target)) {
        // Keep the readers' letter shortcuts from firing on character targets.
        if (e.key !== 'Tab') e.stopImmediatePropagation();
        if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('.cd-char')) {
          e.preventDefault(); navigate(e.target.dataset.character, e.target);
        }
      }
    }, true);
    return {get active() { return active; }, toggle, close: closeModal, leave: () => setActive(false)};
  }
  window.Parseh.CharacterDecomposition = {mount, eligible};
})();
