// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — maths, drawn.  Served at /lib/mathjax.js (with /lib/mathjax.css);
   every page that can carry maths links it, and the 2 MB of MathJax beside
   it (lib/mathjax/tex-svg.js) is fetched only by a page that turns out to
   have some.  Plain ES2017, no build step.

     ParsehMath.ready()            -> Promise: MathJax loaded, or a refusal
     ParsehMath.svg(tex, display)  -> Promise<{svg, error}>  one formula
     ParsehMath.typeset(root)      -> Promise<n>: draw every .math under root
     ParsehMath.has(root)          is there any maths in there at all

   WHAT IS IN THE PAGE BEFORE IT IS DRAWN.  The renderers write the TeX into
   an attribute and the same TeX, as text, inside the element:

     <span class="math" data-tex="a^2+b^2">a^2+b^2</span>
     <div class="math mathblock" data-tex="\int_0^1 x">\int_0^1 x</div>

   so a page whose script never runs -- a bundle opened from disk, a print,
   a card in a reader nobody wrote -- still SAYS what the formula was, in
   the notation it was written in, instead of showing a blank.  Drawing it
   replaces the text with an <svg> and leaves data-tex where it is, which is
   what lets a second pass, a re-render, or an editor read it back.

   WHY NOTHING IS STORED AS SVG.  A drawn formula is four to six kilobytes
   of path data; a document with forty of them would be a quarter of a
   megabyte of markup nobody can read or edit, and it would go stale the
   moment the notation changed.  The TeX is the source and the SVG is made
   from it, here, every time -- except on the way OUT of the toolbox (an
   Anki card, an export), where there is no script to do the drawing and the
   SVG is written in because it must be.

   LOCAL FONT CACHE.  Each formula carries its own glyphs rather than
   pointing at a shared <defs>, because a formula is routinely lifted out of
   the page it was drawn in -- onto a card, into a clipboard, through an
   export -- and one that points at a <defs> left behind arrives blank. */
(function () {
  'use strict';
  if (window.ParsehMath) return;

  /* WHERE THE LIBRARY IS, worked out from where THIS file is.  A built
     book reader is meant to open off the disk as well as through the
     server (tex2html writes its script tags relative, __LIB__), so an
     address beginning with a slash would be right in the studio and wrong
     on a file:// page.  document.currentScript is this script while it is
     running, and mathjax/tex-svg.js sits beside it either way. */
  var SRC = (function () {
    var me = document.currentScript && document.currentScript.src;
    if (!me) return '/lib/mathjax/tex-svg.js';
    return me.replace(/[^/]*$/, '') + 'mathjax/tex-svg.js';
  })();
  var loading = null, failed = '';

  /* THE SECOND COPY OF EVERY FORMULA, and why this rule lives here and not
     in mathjax.css.

     tex2svg answers a container holding TWO children: the <svg>, and an
     <mjx-assistive-mml> carrying the same formula as MathML for a screen
     reader.  MathJax hides that second one with a stylesheet it installs
     when IT typesets a page -- and nothing here ever asks it to: the SVG is
     lifted out by innerHTML and put where it belongs, which is the whole
     point (a formula that can be moved onto a card).  So the stylesheet is
     never installed, and browsers now draw MathML natively, and every
     formula appears twice: once as the picture and once again beside it.

     Hiding it rather than turning it off (options.enableAssistiveMml) keeps
     the formula readable to a screen reader, which is the reason MathJax
     writes it.  And it is installed HERE rather than in mathjax.css because
     it is not styling: it is what makes the output right, and a page that
     linked the script and forgot the stylesheet would otherwise show
     everything twice.  These are MathJax's own rules, copied. */
  var styled = false;
  function installStyle() {
    if (styled || document.getElementById('parseh-mjx-style')) return;
    styled = true;
    var st = document.createElement('style');
    st.id = 'parseh-mjx-style';
    st.textContent =
      'mjx-assistive-mml{position:absolute!important;top:0;left:0;' +
      'clip:rect(1px,1px,1px,1px);padding:1px 0 0 0!important;border:0!important;' +
      'display:block!important;width:auto!important;overflow:hidden!important;' +
      '-webkit-user-select:none;user-select:none}' +
      'mjx-assistive-mml[display="block"]{width:100%!important}' +
      '.math{position:relative}';
    (document.head || document.documentElement).appendChild(st);
  }

  function ready() {
    installStyle();
    if (failed) return Promise.reject(new Error(failed));
    if (window.MathJax && window.MathJax.tex2svg) return Promise.resolve(window.MathJax);
    if (loading) return loading;
    // MathJax reads its configuration off the window as it starts, so this
    // is set before the script is asked for and never after
    if (!window.MathJax) {
      window.MathJax = {
        startup: {typeset: false},        // nothing is drawn until we say so
        svg: {fontCache: 'local'},        // see above: a formula travels alone
        options: {enableMenu: false}      // a right-click menu on somebody's
      };                                  // homework is not what this is for
    }
    loading = new Promise(function (done, no) {
      var s = document.createElement('script');
      s.src = SRC;
      s.async = true;
      s.onload = function () {
        var wait = 0;
        // the bundle sets MathJax.tex2svg during its own start-up, a tick
        // after the script itself has run
        var look = function () {
          if (window.MathJax && window.MathJax.tex2svg) return done(window.MathJax);
          if (++wait > 200) {
            failed = 'the maths renderer loaded but never started';
            return no(new Error(failed));
          }
          setTimeout(look, 25);
        };
        look();
      };
      s.onerror = function () {
        failed = 'the maths renderer (lib/mathjax/tex-svg.js) is not on this machine';
        no(new Error(failed));
      };
      document.head.appendChild(s);
    });
    return loading;
  }

  // WHAT WENT WRONG, in TeX's own words.  MathJax does not throw on bad
  // input: it draws the mistake, marking it, which is right for a page and
  // useless for an editor that ought to say what is wrong.  This reads the
  // mark back out, so the box under the editor can.
  function errorOf(node) {
    if (!node || !node.querySelector) return '';
    var bad = node.querySelector('[data-mjx-error]');
    if (bad) return bad.getAttribute('data-mjx-error') || 'that is not a formula';
    if (node.querySelector('merror')) return 'that is not a formula';
    return '';
  }

  function svg(tex, display) {
    return ready().then(function (MJ) {
      var node;
      try {
        node = MJ.tex2svg(String(tex == null ? '' : tex), {display: !!display});
      } catch (e) {
        return {svg: '', error: (e && e.message) || 'that is not a formula'};
      }
      return {svg: node.innerHTML, error: errorOf(node)};
    });
  }

  function marks(root) {
    return (root || document).querySelectorAll('.math[data-tex]:not([data-drawn])');
  }
  function has(root) { return marks(root).length > 0; }

  /* Draw everything under `root` that has not been drawn.  Answers how many.
     A formula that will not parse is left as the TeX it was written as and
     marked, rather than replaced by a red box nobody can correct: on a page
     the author can at least see what they wrote. */
  function typeset(root) {
    var all = marks(root);
    if (!all.length) return Promise.resolve(0);
    return ready().then(function (MJ) {
      var n = 0;
      Array.prototype.forEach.call(all, function (el) {
        var tex = el.getAttribute('data-tex') || '';
        var display = el.classList.contains('mathblock');
        var node;
        try {
          node = MJ.tex2svg(tex, {display: display});
        } catch (e) {
          el.setAttribute('data-drawn', 'no');
          el.title = (e && e.message) || 'that is not a formula';
          return;
        }
        var bad = errorOf(node);
        if (bad) {
          el.setAttribute('data-drawn', 'no');
          el.title = bad;
          return;
        }
        el.innerHTML = node.innerHTML;
        el.setAttribute('data-drawn', 'yes');
        el.removeAttribute('title');
        n++;
      });
      return n;
    }).catch(function (e) {
      // no renderer on this machine: every formula keeps its own notation,
      // and says once why it is not a picture
      Array.prototype.forEach.call(all, function (el) {
        el.setAttribute('data-drawn', 'no');
        el.title = (e && e.message) || 'the maths renderer did not load';
      });
      return 0;
    });
  }

  window.ParsehMath = {ready: ready, svg: svg, typeset: typeset, has: has,
                       errorOf: errorOf, SRC: SRC};
})();
