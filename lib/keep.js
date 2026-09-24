// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — "Keep on this phone", and knowing when the computer is away
   (docs/mobile.md, TO-DO §19.2, §19.4, §19.5, and §0 for 2026-09-23).

   The worker (lib/sw.js) holds what is kept; this is the side a person sees:

     - on the mobile page of a THING that can be kept -- a book's reader, a
       video's page, a deck, a studio document -- the buttons go into the slot
       the page names (`data-keep-slot`, whose value is the class that page
       dresses its own buttons in), or under ⋯ where it names none.  Nothing
       is kept: **Keep on this phone**.  It asks the computer what the thing
       is made of (`<thing>/__offline`, lib/offline.py), says how big the text
       is and lists the recordings to PICK one by one (the owner's choice,
       2026-09-22: a narrated book is hundreds of megabytes and nobody wants
       all of it by surprise), and keeps what is picked with the progress
       showing;
     - KEPT, IT IS TWO BUTTONS, NOT ONE, SIDE BY SIDE (the owner's 4 of
       2026-09-23, and his 4 of the 23rd's second round: "they should divide
       the space that currently is allocated to Change what is kept in two,
       one half for change the other for remove").  Keeping used to be all or
       nothing, and the one button only removed.  Now **Change what is kept**
       opens the same list with what is on the phone already ticked -- Save
       fetches what is ticked and frees what is not, saying both numbers, and
       asks once before it frees anything -- and **Remove from this phone**
       stands in the other half of the same line.  The two go in one wrapper
       (`kp-pair`), which wears `kp-btn` as well as its own name because every
       sheet that places the one button places it by that class: the reader's
       header and the player's give `.kp-btn` its order and its own line and
       hide it while ⋯ is shut (lib/mobile.css), and the pair has to stand
       exactly where the button stood.  The list is the computer's, so with
       the computer away the button says so rather than opening a list nobody
       could fill;
     - AND A TICK MEANS THE FILE IS REALLY THERE (his 3, 2026-09-23: "the
       boxes should by default show the things that are actually kept in
       memory, and there should be a check of this, it should actually look
       for the file and check that the download was complete and correct").
       A tick used to mean "this address is a key in that cache" -- which a
       kept 503, a page sent where a picture was asked for, and a fetch cut
       off by a tunnel all satisfy.  Opening the sheet now asks the worker to
       LOOK (`{check}`, lib/sw.js) -- at what this sheet has a box for, and at
       what Save mends unasked, and at those only where the phone says it has
       them, because asking after all nine hundred addresses of a narrated
       book was a hundred and ninety megabytes read before the sheet could be
       touched.  The boxes are ticked from that answer and from nothing else:
       what was kept and is no longer whole is said plainly, unticked, and
       fetched again by Save.  The text and the pages are not a row and are
       mended without being asked, since they are what the thing opens on;
     - AND THE NOTES COME WITH THE BOOK (the owner's second block of
       2026-09-23).  A kept book used to keep its text and its recordings and
       leave its notes on the computer, so every seam on a train opened on
       nothing.  The sheet has a row of its own for them -- *its notes · 34 ·
       about 280 kB* -- beside the recordings, which can be unticked, and a
       second for the notes' own recordings, which cannot be kept by
       surprise.  What a note opens ON -- the studio's sheet, its thirteen
       faces, and MathJax where a note has a formula -- is kept ONCE for the
       phone (lib/sw.js puts it in the shared cache), so the second book's
       notes cost their own pages and nothing more;
     - AND WHAT THE COMPUTER NO LONGER HAS IS GIVEN BACK (his 8).  A note
       deleted at the desk is in no list any more, so no tick could reach it:
       Save compares what the door names with what the worker holds and frees
       the difference, having said how many it is first;
     - AND A BOOK COMES IN THE BACKGROUND WHERE IT CAN (the owner's decision
       of 2026-09-23): on Android the press hands it to the browser's own
       download -- the text, then the recordings -- which goes on with the
       page closed, and the button says "— you can leave this page".  The
       iPad, Firefox, and everything that is not a book keep as before.  All
       of it is in "a book kept in the background", below;
     - a REGISTRY of what is kept, in this browser (`parseh_kept`): what each
       thing is, where its page is, which version was kept, how big it was and
       when.  The kept page (/m/kept/) and the offline home read it;
     - OUT OF DATE: on opening a kept thing the version is asked for again.
       The small parts -- the page, the text, the pictures -- are renewed in
       silence (the worker does that behind every answer); anything heavy that
       has changed says so and waits for a tap;
     - THE CHIP: every page of the app says whether the computer can be
       reached.  Nothing while all is well; when it cannot be, a small
       "offline" chip in the bar, which opens the list of what is kept.
     - AND A PAGE OPENS IN THE STATE THE LAST ONE WAS IN (his 5, 2026-09-23:
       "when changing pages the app rechecks if it's offline and assumes being
       online even if the page before showed being offline; good on the check,
       but assume that the status is the same of the page previous").  Every
       probe writes what it found under `parseh_away`, and the next page reads
       it before it asks anybody anything -- so a shelf opened from an offline
       hub opens offline, with its unkept cards already quiet, rather than
       pretending for three seconds that all is well.  It is a MEMORY and it
       is treated as one: older than a few minutes it is not trusted at all,
       and the probe behind it corrects it either way.

   AND WITH THE COMPUTER AWAY, THE PAGES STILL WORK (the owner's 1 and 2,
   2026-09-23).  The way in is kept by the worker, so the hub and the shelves
   open as they always do rather than showing "Parseh cannot be reached".
   Three things here make that honest:

     - a shell page opens from the phone's copy, which is as old as the last
       time the computer was reached; when the worker has read the page again
       and found it changed it says so (`shellFresh`) and the block is
       replaced in place, so nobody is left reading yesterday's shelf;
     - what is on a shelf and is NOT on this phone is drawn and cannot be
       tapped, with a line saying so -- exactly as a book whose reader was
       never built already looks (lib/mobile.py, `m-book m-off`);
     - what the clock makes wrong -- what is due -- is not shown at all while
       the computer is away.  The lists stay; the numbers nobody should act on
       go.

   AND THE APP GETS ITSELF READY AFTERWARDS, SAYING SO (TO-DO §0, the owner's
   decision of 2026-09-23).  The worker used to fetch the whole way in -- fifty-
   nine addresses, three and a quarter megabytes -- inside its install event,
   and a worker that grinds through three megabytes over a tunnel never leaves
   the installing state, which is a state Chrome will not install a site from.
   So install keeps the one page it always kept, and the WARMING is asked for
   from here, by a page that is up:

     - {warm: 'way-in'} on every mobile page, once, as soon as the computer is
       known to be there.  It costs nothing on a phone that is already warm:
       the worker skips every address any cache of this origin holds, so the
       ask settles at done === of with no fetch at all;
     - {warm: 'studio'} only where the studio's own face is really wanted --
       a studio page, a deck page, or the moment a note is opened in a reader
       or a player -- because that list is the thirteen faces and the two and
       a quarter megabytes they weigh, and nothing else should pay for them;
     - AND IT IS NOT SILENT (his words).  Any page may carry an element with
       [data-parseh-warm]: while a warming runs it reads "Getting ready — 41
       of 59", and when everything asked for on this page has settled it says
       so and stays saying it, because the install page tells somebody to wait
       until it says it is ready and a line that vanished would have told him
       nothing.  A page where no warming was ever asked for shows nothing.

   NEITHER ASK IS EVER MADE IN THE BROWSER MODE OR WITH THE COMPUTER AWAY: this
   is the app fetching its own pages, and neither a browser page nor a tunnel
   with nothing at the end of it has any business starting it.  */
(function () {
  'use strict';
  if (window.ParsehKeep) return;

  var REG = 'parseh_kept';
  var P = function () { return window.Parseh; };
  function mobile() {
    var p = P();
    if (p && p.mode && p.mode.isMobile) return p.mode.isMobile();
    return document.documentElement.getAttribute('data-mode') === 'mobile';
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  // The toolbox's own pages have a toast; the studio's pages -- a deck, a
  // document, the two libraries -- keep theirs inside their own script, out of
  // reach from here.  So what cannot be toasted is said in a line beside the
  // buttons, where the tap that asked for it was: nothing this script says is
  // ever said to nobody.
  var said = null;
  function say(m, bad) {
    var p = P();
    if (p && p.toast) { p.toast(m, bad); return; }
    // under the PAIR, not between the two buttons: the line is about what was
    // just pressed, and a paragraph dropped inside a row of two halves would
    // push one of them off the line it shares
    var host = pair || btn;
    if (!host || !host.parentNode) return;
    if (!said || !said.isConnected) {
      said = el('p', 'kp-said');
      said.setAttribute('role', 'status');
      host.parentNode.insertBefore(said, host.nextSibling);
    }
    said.className = 'kp-said' + (bad ? ' kp-bad' : '');
    said.textContent = m;
  }
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function reg() {
    try { return JSON.parse(get(REG) || '{}') || {}; } catch (e) { return {}; }
  }
  function saveReg(r) { put(REG, JSON.stringify(r)); }
  /* AND THE REGISTRY IS NOT THE TRUTH ABOUT THE CACHES (the owner's 3,
     2026-09-23).  It is this browser's own note of what was kept and when,
     and it can outlive what it describes: a browser short of room throws a
     cache away without asking anybody, and the note stays -- so a shelf went
     on offering a book that had nothing behind it and the button went on
     saying "Change what is kept" over an empty phone.  The worker knows what
     the caches really are (lib/sw.js, kept()) and nothing had ever asked it.
     Asked once a page is idle, and only ever to REMOVE: a cache with no note
     beside it cannot be described from here -- its title, its version and
     what was picked are the note and not the cache -- so it is left alone
     rather than written down wrongly. */
  function reconcile() {
    tell({kept: 1}).then(function (d) {
      var real = {}, r = reg(), lost = 0, k;
      ((d && d.keptList) || []).forEach(function (x) { if (x && x.id && x.files) real[x.id] = true; });
      for (k in r) {
        if (!Object.prototype.hasOwnProperty.call(r, k) || real[k]) continue;
        delete r[k];
        lost++;
      }
      if (!lost) return;
      saveReg(r);
      paint();
      refresh();
    }, function () { /* no worker to ask: the note is all there is */ });
  }
  function big(n) {
    n = +n || 0;
    return n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB'
         : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e8 ? 0 : 1) + ' MB'
         : n >= 1e3 ? Math.round(n / 1e3) + ' kB' : n + ' bytes';
  }
  // Several things said in one line, the way a person would say them: the
  // sheet now has three kinds of choice to report on rather than one, and
  // "a, b and c" is the only shape that stays readable as they come and go.
  function joined(parts) {
    if (parts.length < 2) return parts[0] || '';
    return parts.slice(0, -1).join(', ') + ' and ' + parts[parts.length - 1];
  }

  /* WHICH THING THIS PAGE IS.  A book's reader is /books/<…>/reader/ and a
     video's page /youtube/v/<id>/; its id is that address, which is what the
     worker names its cache by and what the registry is keyed on. */
  function thing() {
    var p = location.pathname, m;
    if (/^\/books\/(?:[^\/]+\/){1,2}reader\/(index\.html)?$/.test(p))
      return {id: p.replace(/index\.html$/, ''), door: p.replace(/index\.html$/, '') + '__offline'};
    if (/^\/youtube\/v\/[^\/]+\/(index\.html)?$/.test(p))
      return {id: p.replace(/index\.html$/, ''), door: p.replace(/index\.html$/, '') + '__offline'};
    // a deck: its own page, whose door is under the API (§19.9).  Kept, it
    // can be CRAMMED with the computer away; studying it away is a check-out,
    // which the deck page offers separately (§19.10, decks.js).
    m = /^(\/exercises\/deck\/([a-z]+)\/([a-z0-9][a-z0-9-]*)\/)$/.exec(p);
    if (m) return {id: m[1], door: '/exercises/api/decks/' + m[2] + '/' + m[3] + '/__offline'};
    // a studio document (§19.8): the page as the computer rendered it
    m = /^(\/studio\/doc\/([a-z0-9-]+))\/?$/.exec(p);
    if (m) return {id: m[1], door: m[1] + '/__offline'};
    return null;
  }

  function worker() {
    return navigator.serviceWorker && navigator.serviceWorker.controller
      ? navigator.serviceWorker.controller : null;
  }
  function tell(msg, onEach) {
    var w = worker();
    if (!w) return Promise.reject(new Error('this browser is not keeping anything yet'));
    // WHICH ANSWER IS THIS JOB'S.  The worker also speaks unasked -- it says
    // when a shell page it read again has changed -- so a job waits for the
    // word that answers it and lets everything else pass.
    var want = msg.keep ? 'kept' : msg.free ? 'freed' : msg.drop ? 'dropped'
             : msg.inside ? 'inside' : msg.check ? 'check' : msg.kept ? 'keptList' : null;
    /* AND WHOSE.  The worker used to answer only the page that asked, which
       is all that made a key enough; a book kept in the BACKGROUND ends with
       no page to answer (lib/sw.js, `settle`), so its `{kept}` goes to every
       page -- and a keep of something else waiting here must not take it for
       its own.  Nothing changes for a keep that is alone: its answer carries
       its own id, as it always did. */
    var mine = msg.keep ? msg.keep.id : null;
    return new Promise(function (done, fail) {
      var hear = function (e) {
        var d = e.data || {};
        if (d.keeping) { if (onEach && (!mine || d.keeping === mine)) onEach(d); return; }
        if (want && !(want in d)) return;
        if (mine && d.kept !== mine) return;
        navigator.serviceWorker.removeEventListener('message', hear);
        done(d);
      };
      navigator.serviceWorker.addEventListener('message', hear);
      w.postMessage(msg);
      setTimeout(function () {
        navigator.serviceWorker.removeEventListener('message', hear);
        fail(new Error('the phone did not answer'));
      }, 20 * 60 * 1000);
    });
  }

  /* ---- what a thing is made of ---- */
  function made(door) {
    return fetch(door, {headers: {'Accept': 'application/json'}})
      .then(function (r) { return r.ok ? r.json() : null; });
  }

  /* ---- the sheet that asks what to keep, and what to keep now ---- */
  /* `have` is what the thing's cache holds already, as addresses, or null for
     a thing that is not on this phone at all.  The same sheet does both, so
     that the list of recordings is one list with one look, whether it is
     being chosen for the first time or changed.  `holds` is what this phone
     holds ONCE for everything -- the shared cache and the app shell together
     (lib/sw.js, inside()) -- the files that are kept once for the whole phone rather
     than once for every book -- which is how this sheet can tell the truth
     about what the notes would really cost the second time. */
  function sheet(rec, at, have, holds) {
    var changing = !!have, mine = have || [];
    holds = holds || [];
    var media = rec.media || [];
    /* THE NOTES ARE ONE TICK, BESIDE THE RECORDINGS (the owner's 1,
       2026-09-23).  A book's notes were left behind when the book was kept,
       so a kept book had seams that opened on nothing.  They are kept as a
       GROUP -- every note's bare page, the pictures in them, and the seams'
       list that is how the reader finds them at all -- because there is
       nothing here anybody could want half of: a note whose mark is kept and
       whose page is not is worse than no note.  Their own recordings are a
       second tick beside it (his 6), so that nothing heavy is ever kept by
       surprise.  A thing with no notes mount -- a deck, a document -- says
       nothing about notes at all, and no row is drawn for it. */
    var notes = rec.notes && ((rec.notes.small || []).length) ? rec.notes : null;
    var noteSmall = notes ? (notes.small || []) : [];
    var noteShared = notes ? (notes.shared || []) : [];
    var nmedia = notes ? (notes.media || []) : [];
    var nmediaBytes = nmedia.reduce(function (n, m) { return n + (m.bytes || 0); }, 0);
    /* TWO QUESTIONS, AND THEY ARE NOT THE SAME ONE (the owner's 3,
       2026-09-23).  `here` is whether this thing's cache holds that address
       at all, which is what says whether there is anything to GIVE BACK.
       `has` is whether what it holds is WHOLE -- the worker's check, below --
       which is what says whether there is anything to FETCH.  They came apart
       the moment a tick stopped meaning "a key is in a cache": a recording
       whose download was cut off is here and is not whole, and both facts
       matter -- Save fetches it again, and the broken bytes go.
       Until the check has answered, `has` falls back to `here`, which is the
       old guess and is said to be one on the sheet. */
    var sound = null, broken = {};
    var here = function (u) { return mine.indexOf(u) >= 0; };
    /* AND THE FALLBACK IS PER ADDRESS, not for the sheet as a whole.  The
       check is asked about what this sheet has a box for and what Save mends
       unasked, and about nothing else -- a note's own page is one of eight
       hundred behind a single tick, and asking after every one of them was
       most of what made one press cost the phone a hundred and ninety
       megabytes of reading.  So an address that was looked at answers from
       the look, and an address that was never sent answers from the cache's
       own word, exactly as it did before there was a check at all.  Written
       `sound ? !!sound[u] : here(u)`, as it was, every address nobody asked
       about read as broken the moment the answer landed, and the next Save
       would have fetched the whole of somebody's notes over again. */
    var has = function (u) { return sound && (u in sound) ? sound[u] : here(u); };
    // A GROUP IS HERE WHEN ANY OF IT IS, not when all of it is.  A note
    // written at the desk since the book was kept is in the computer's list
    // and not on the phone; reading that as "the notes are not kept" would
    // untick a row the owner never touched, and the next Save would offer to
    // free what he is reading.  So the tick says whether the group is here,
    // and Save fetches whatever of it is missing -- which is why these two
    // are the cache's own word (`here`) and are what says there is room to
    // give back, while the tick itself follows the check (`has`).
    var notesHere = noteSmall.some(function (x) { return here(x.url); });
    var nmediaHere = nmedia.some(function (m) { return here(m.url); });
    // WHAT THE STUDIO'S OWN FILES WOULD STILL COST (the owner's 3, 4 and 5).
    // A note opens on the studio's sheet, in the studio's thirteen faces, and
    // where it has a formula on MathJax -- about four megabytes, paid ONCE
    // for the phone.  The worker says what the shared cache holds already, so
    // a second book's notes are offered at the price of their own pages.
    var owing = noteShared.filter(function (x) { return holds.indexOf(x.url) < 0; });
    var owedBytes = owing.reduce(function (n, x) { return n + (x.bytes || 0); }, 0);
    var box = el('div', 'kp-sheet');
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', changing ? 'change what is kept' : 'keep on this phone');
    var small = (rec.small || []).reduce(function (n, x) { return n + (x.bytes || 0); }, 0);
    box.appendChild(el('h2', 'kp-h', changing ? 'Change what is kept' : 'Keep on this phone'));
    box.appendChild(el('p', 'kp-what', (rec.title || 'this') + ' — the text and the pages take ' +
                       big(small) + '.'));
    var picks = [], rows = [], noteBox = null, nmedBox = null, aside = null;
    /* WHAT A ROW SAYS, IN TWO LINES (the owner's 2, 2026-09-23: "indicate
       also chapters and section range that each narration covers in the
       rectangles instead of only the range of paragraphs").  A row said
       "n2 · 7.1 – 36.1", which is where a narration begins and ends in
       PARAGRAPH addresses -- exact, and no use at all to somebody deciding
       which two of fifty recordings to take on a train.  So the chapter and
       the section come first, in the reader's own wording (`where`,
       lib/offline.py), and the paragraphs go under them, small and dim, for
       whoever does know his book by them.  A record made before `where`
       existed -- an older computer answering a newer app -- has none, and
       then the paragraphs are the whole of what there is to say and they
       stay on top, exactly as they were. */
    function nameCell(top, under) {
      var cell = el('span', 'kp-name');
      cell.appendChild(el('span', 'kp-top', top));
      if (under) cell.appendChild(el('span', 'kp-sub', under));
      return cell;
    }
    // a row for a whole group, with the same look as a recording's, because
    // it is the same kind of choice: one box, what it is, what it costs
    function group(list, name, size, on) {
      var row = el('label', 'kp-row');
      var tick = document.createElement('input');
      tick.type = 'checkbox';
      tick.checked = !!on;
      row.appendChild(tick);
      row.appendChild(nameCell(name, ''));
      row.appendChild(el('span', 'kp-size', size));
      list.appendChild(row);
      return tick;
    }
    if (media.length || notes) {
      box.appendChild(el('p', 'kp-lead', changing
        ? 'What is on this phone is ticked. Tick what to fetch, untick what to give the room back ' +
          'for — a finger drawn down the boxes takes every one it crosses.'
        : media.length
        ? 'Its recordings are the heavy part. Pick what to keep:'
        : 'Pick what to keep:'));
      // Select all and Clear all are two things, and each says which it is
      var both = el('div', 'kp-pickall');
      var all = el('button', 'kp-small', 'Select all');
      all.type = 'button';
      var none = el('button', 'kp-small', 'Clear all');
      none.type = 'button';
      both.appendChild(all);
      both.appendChild(none);
      box.appendChild(both);
      var list = el('div', 'kp-list');
      media.forEach(function (m) {
        var row = el('label', 'kp-row');
        var tick = document.createElement('input');
        tick.type = 'checkbox';
        tick.checked = has(m.url);
        tick.value = m.url;
        picks.push(tick);
        row.appendChild(tick);
        var where = (m.where || '').trim(), covers = (m.covers || '').trim();
        var top = [], under = [];
        if (!where && m.id) top.push(m.id);
        top.push(where || covers || m.url.split('/').pop());
        if (where && m.id) under.push(m.id);
        if (where && covers) under.push(covers);
        var cell = nameCell(top.join(' · '), under.join(' · '));
        row.appendChild(cell);
        row.appendChild(el('span', 'kp-size', big(m.bytes)));
        list.appendChild(row);
        rows.push({row: row, cell: cell, url: m.url, why: null});
      });
      if (notes) {
        // TICKED UNLESS HE UNTICKS IT, on a first keep: a book's notes are a
        // third of a megabyte beside a text that is already kept, and a seam
        // that opens on nothing is the fault this row exists to mend.
        noteBox = group(list, 'its notes · ' + (notes.count || noteSmall.length),
                        'about ' + big(notes.bytes || 0), changing ? notesHere : true);
        // and their recordings, which are not: they are as heavy as a
        // narration, and the same rule holds for both (the owner's 6)
        if (nmedia.length)
          nmedBox = group(list, 'the notes’ recordings · ' + nmedia.length +
                          (nmedia.length === 1 ? ' file' : ' files'), big(nmediaBytes), nmediaHere);
      }
      box.appendChild(list);
      dragging(list);
      var every = function (on) {
        picks.forEach(function (b) { b.checked = on; });
        if (noteBox) noteBox.checked = on;
        if (nmedBox) nmedBox.checked = on;
        total();
      };
      all.addEventListener('click', function () { every(true); });
      none.addEventListener('click', function () { every(false); });
    }
    if (notes && owing.length) {
      aside = el('p', 'kp-aside', 'A note opens on the studio’s own sheet and in its own faces: ' +
                 big(owedBytes) + ' of them come with the first notes kept here, and are then ' +
                 'shared by every book and video on this phone rather than kept again.');
      box.appendChild(aside);
    }
    var sum = el('p', 'kp-sum', '');
    box.appendChild(sum);
    /* WHAT A PRESS WOULD DO, said in addresses as well as in bytes.  The
       worker is told addresses and nothing else, so every choice here says
       which addresses it means: a recording picked one by one, the notes as
       one group, and the notes' recordings as another. */
    function split() {
      var add = [], gone = [], ticked = [], bytes = small;
      var fetch = [], free = [], fetches = 0, frees = 0, mends = 0;
      // FETCHING SOMETHING THAT IS HERE AND BROKEN IS A MEND, and it is
      // counted apart so that the sheet can say it happened: the press that
      // says "Save fetches 4 kB" over a book that would not open owes the
      // owner the reason why.
      function fetchIt(url, size) {
        fetch.push(url);
        fetches += size || 0;
        // ON THE PHONE ALREADY, ASKED OF BOTH THINGS THAT KNOW.  `here` is
        // this thing's own cache, which is where its text, its pictures and
        // its recordings sit; what a note opens on sits in the shared one
        // instead, and of that the worker's own look is the only word there
        // is (`broken`).  Counted by `here` alone, a torn studio face was
        // fetched again and the line said nothing about why.
        if (here(url) || broken[url]) mends++;
      }
      picks.forEach(function (b, i) {
        var m = media[i], whole = has(m.url), inCache = here(m.url);
        if (b.checked) { ticked.push(m.url); bytes += m.bytes || 0; }
        if (b.checked && !whole) { add.push(m); fetchIt(m.url, m.bytes); }
        else if (!b.checked && inCache) {
          free.push(m.url);
          frees += m.bytes || 0;
          // WHAT WAS UNTICKED ON PURPOSE AND WHAT WAS UNTICKED BY THE CHECK
          // are two different things, and only the first is worth asking
          // about before Save runs: a recording that is here and whole is a
          // journey's worth of data to fetch again, while a broken one is
          // room being given back for nothing lost.
          if (whole) gone.push(m);
        }
      });
      var noteOn = !!(noteBox && noteBox.checked), nmedOn = !!(nmedBox && nmedBox.checked);
      if (noteOn) {
        bytes += notes.bytes || 0;
        noteSmall.forEach(function (x) {
          if (has(x.url)) return;
          fetchIt(x.url, x.bytes);
        });
        // what they open on, which two books never pay for twice
        owing.forEach(function (x) { fetchIt(x.url, x.bytes); });
      } else if (noteBox && notesHere) {
        // only this thing's own copies: the studio's files are in the shared
        // cache and belong to every other book that kept its notes
        noteSmall.forEach(function (x) {
          if (!here(x.url)) return;
          free.push(x.url);
          frees += x.bytes || 0;
        });
      }
      /* AND WHAT A NOTE OPENS ON, HERE AND NO LONGER WHOLE, IS MENDED --
         which until now the sheet promised and Save never did.  `owing` is
         the wrong instrument for it and cannot be made the right one: it asks
         whether the address is a KEY in the shared cache, and a torn body is
         a key like any other, so a studio face that came back half written
         was reported broken in the line above the buttons and then passed
         over by every press.  The worker's own look is the only thing that
         can tell the two apart, and it is asked whether or not the notes are
         ticked: these fifteen files are shared by every book on the phone,
         nothing frees them when a tick comes off, and a face left torn draws
         every note on the phone wrong. */
      noteShared.forEach(function (x) {
        if (!broken[x.url] || fetch.indexOf(x.url) >= 0) return;
        fetchIt(x.url, x.bytes);
      });
      if (nmedOn) {
        bytes += nmediaBytes;
        nmedia.forEach(function (m) {
          ticked.push(m.url);
          if (has(m.url)) return;
          fetchIt(m.url, m.bytes);
        });
      } else if (nmedBox && nmediaHere) {
        nmedia.forEach(function (m) {
          if (!here(m.url)) return;
          free.push(m.url);
          frees += m.bytes || 0;
        });
      }
      /* THE TEXT AND THE PAGES ARE NOT A ROW, AND ARE MENDED WITHOUT BEING
         ASKED (the owner's 3 and 7, 2026-09-23).  Nobody chooses them: they
         are what the thing opens ON, and one of them missing or half fetched
         is exactly the fault that left every book stopping halfway through
         loading in airplane mode.  There is nothing here to weigh up and
         nothing to confirm -- it is a few kilobytes, and without them the
         rest of what is kept is unreachable -- so Save simply brings them.
         Only once the check has spoken, though: before that `has` is the old
         guess, and a guess must not send for a megabyte of chapters. */
      if (changing && sound) {
        [].concat(rec.small || [], rec.shared || []).forEach(function (x) {
          if (!x || !x.url || has(x.url) || fetch.indexOf(x.url) >= 0) return;
          fetchIt(x.url, x.bytes);
        });
      }
      /* WHAT THE COMPUTER NO LONGER HAS (the owner's 8, 2026-09-23).  A note
         deleted at the desk would sit on the phone for ever otherwise: it is
         in no list any more, so no tick can ever reach it and no untick can
         free it.  Everything the door named is gathered here, and whatever
         this thing's cache holds and the door no longer names goes on the
         next Save -- which is why nothing still listed can ever be in it.
         The room is small and the point is not the room: the phone is made
         to match the book. */
      var stale = [];
      if (changing) {
        var listed = {};
        [rec.small, rec.shared, rec.media, noteSmall, noteShared, nmedia].forEach(function (g) {
          (g || []).forEach(function (x) { if (x && x.url) listed[x.url] = true; });
        });
        stale = mine.filter(function (u) { return !listed[u]; });
      }
      return {add: add, gone: gone, ticked: ticked, bytes: bytes, mends: mends,
              fetch: fetch, free: free.concat(stale), stale: stale,
              fetches: fetches, frees: frees, notes: noteOn, nmedia: nmedOn,
              noteOff: !!(noteBox && !noteOn && notesHere),
              nmedOff: !!(nmedBox && !nmedOn && nmediaHere),
              files: (rec.small || []).length + ticked.length + (noteOn ? noteSmall.length : 0)};
    }
    function total() {
      var s = split();
      // SAID BEFORE IT HAPPENS, in the same breath as the two numbers (the
      // owner's 8): he is told how many the computer has lost, on the sheet
      // that holds the press which will free them.
      var lost = s.stale.length
        ? ' It also gives back ' + s.stale.length + (s.stale.length === 1 ? ' file' : ' files') +
          ' the computer no longer has — a note deleted there is freed here.'
        : '';
      // AND WHAT IT MENDS, said in the same breath (the owner's 3): a press
      // that fetches something he never unticked has to say why it is doing
      // it, or the numbers stop being worth reading.
      var mend = !s.mends ? ''
        : s.mends === 1
        ? ' One file of it is fetched again: what was kept of it is no longer whole.'
        : ' ' + s.mends + ' files of it are fetched again: what was kept of them is no longer whole.';
      sum.textContent = !changing
        ? 'In all: ' + big(s.bytes) +
          (s.notes && owedBytes ? ', and ' + big(owedBytes) + ' of the studio’s own files, ' +
                                  'once for this phone.' : '')
        : (!s.fetches && !s.frees && !s.stale.length)
        ? 'Nothing to change: what is ticked is whole on this phone.'
        : 'Save fetches ' + big(s.fetches) + ', frees ' + big(s.frees) + '.' + mend + lost;
      if (aside) aside.hidden = !s.notes;
      return s;
    }
    picks.concat([noteBox, nmedBox]).forEach(function (b) {
      if (b) b.addEventListener('change', total);
    });
    total();

    /* ---- IS WHAT WAS KEPT STILL THERE, AND STILL WHOLE? ----
       The owner's 3 of 2026-09-23, and it is the sheet's oldest lie being
       mended: a box was ticked because the address was a key in a cache,
       which a refusal kept by mistake, a page sent where a recording was
       asked for, and a fetch cut off by a tunnel all satisfy just as well as
       the file itself does.  So the worker is asked to LOOK -- at the body,
       at its digest where the computer could afford to give one and at its
       length where it could not (lib/sw.js, check()) -- and the boxes are
       ticked from that answer and from nothing else.
       It is asked only when there is something to check: on a first keep
       nothing is on the phone and every box starts empty anyway.  The sheet
       opens first and fills in after, because the answer walks each file it
       was given and a sheet nobody can see yet is no use to anybody. */
    function checked(list) {
      sound = {};
      var torn = [];
      (list || []).forEach(function (x) {
        if (!x || !x.url) return;
        sound[x.url] = !!x.whole;
        // ON THE PHONE AND NOT WHOLE, REMEMBERED BY ADDRESS.  `torn` is a
        // list to count and to draw with; this is the same fact asked of one
        // address at a time, which is what `split` needs when it comes to
        // decide whether a file already here is nevertheless to be fetched.
        // The worker looked in this thing's cache AND in the shared one, so
        // this knows things `here` cannot: what a note opens on is in nobody's
        // own cache and is exactly where the unmended fault was hiding.
        if (x.here && !x.whole) { broken[x.url] = true; torn.push(x.url); }
        else delete broken[x.url];
      });
      picks.forEach(function (b, i) { b.checked = has(media[i].url); });
      // WHAT CAN STILL BE GIVEN BACK is the cache's own word and does not
      // change with the check: a broken copy is room, and unticking it frees
      // that room exactly as unticking a whole one does.
      notesHere = noteSmall.some(function (x) { return here(x.url); });
      nmediaHere = nmedia.some(function (m) { return here(m.url); });
      // A GROUP STAYS TICKED WHILE ANY OF IT IS HERE, where a recording that
      // is not whole is unticked.  They differ because a recording is one
      // file and a group is eight hundred: unticking the notes because one
      // note's page came back torn would offer to free the other seven
      // hundred and ninety-nine he never touched, while leaving it ticked
      // fetches what is missing and keeps the rest exactly where they are.
      // So the notes answer from `here` -- nobody asked the worker about
      // them, for the reason written over `want` -- and their recordings,
      // which are rows of their own kind, answer from the look.
      if (noteBox) noteBox.checked = noteSmall.some(function (x) { return has(x.url); });
      if (nmedBox) nmedBox.checked = nmedia.some(function (m) { return has(m.url); });
      var tornRows = 0;
      rows.forEach(function (r) {
        var bad = torn.indexOf(r.url) >= 0;
        r.row.classList.toggle('kp-torn', bad);
        if (!bad) return;
        tornRows++;
        if (r.why) return;
        r.why = el('span', 'kp-sub kp-whytorn',
                   'kept, but no longer whole — tick it to fetch it again');
        r.cell.appendChild(r.why);
      });
      // AND THE LINE SAYS WHICH OF THE TWO THINGS WILL HAPPEN TO WHAT IS
      // BROKEN, because they are not the same thing.  A recording is a row,
      // so it is unticked and the choice is his: tick it and Save brings it,
      // leave it and Save gives back the room a broken copy is taking.  The
      // text, the pages, and what a note opens on are nobody's choice -- the
      // thing does not open without them -- so Save fetches those again
      // unasked, and saying "they are unticked" of them would be untrue as
      // well as pointless.  THE SECOND HALF OF THAT SENTENCE IS NOW TRUE OF
      // ALL OF THEM: a torn file among the studio's shared ones was named
      // here and mended by no press at all, which is a promise made on the
      // one sheet whose whole purpose is to stop the numbers lying.
      if (checking) {
        checking.className = 'kp-check' + (torn.length ? ' kp-bad' : '');
        var rest = torn.length - tornRows;
        var what = [];
        if (tornRows)
          what.push((tornRows === 1 ? 'The recording among them is unticked'
                                    : 'The ' + tornRows + ' recordings among them are unticked') +
                    ' — tick again whatever Save should fetch; what is left unticked gives its ' +
                    'room back.');
        if (rest)
          what.push((tornRows ? 'The rest are' : 'They are') +
                    ' the text, the pages, or what a note opens on, which Save fetches again ' +
                    'without asking.');
        checking.textContent = !torn.length
          ? 'Looked at file by file: what is ticked is whole on this phone.'
          : (torn.length === 1 ? 'One file kept here is no longer whole. '
                               : torn.length + ' files kept here are no longer whole. ') +
            what.join(' ');
      }
      total();
    }
    /* WHAT IS WORTH ASKING ABOUT, AND WHAT ONE PRESS COSTS THE PHONE.  Every
       address the door named used to go, all nine hundred and ten of the
       owner's narrated book, and five hundred and seventeen of those carry a
       SHA-256 the worker then honours by reading the body and hashing it:
       one press was a hundred and ninety-two megabytes read into a phone
       before the sheet could be used.  Two things cut it, and neither of them
       weakens what a box means:

         - ONLY WHAT THIS SHEET IS DRAWN FROM.  A box is drawn for each
           recording and one apiece for the two groups; `split` also mends the
           text, the pages and what a note opens on without being asked.
           Those are the answers this sheet acts on.  The eight hundred note
           pages and pictures behind a single tick are not: the tick asks
           whether ANY of the group is here (`notesHere`), which is the
           cache's own word and always was, and Save fetches whatever of the
           group is missing whether or not anybody hashed it first.
         - AND ONLY WHAT SOMETHING SAYS IS ALREADY ON THE PHONE.  An address
           that neither this thing's cache (`mine`) nor the shared list
           (`holds`) has heard of cannot be whole, and the worker would walk
           every cache to say so.  Skipped, `has` falls back to `here`, which
           answers false for it -- the same answer, for nothing.  This is the
           owner's own words for what he asked for: look for the file that IS
           kept and see whether the download was complete.

       AND WHAT THE COMPUTER SAYS IT CANNOT PROMISE GOES WITH IT.  An answer
       the computer composes as it sends -- a note's page from a template, a
       deck's exercises with the scheduler's numbers riding in them -- has no
       length anybody here can predict, and the record says so (`check:
       "here"`, lib/offline.py).  Passed on, the worker tests that it is there
       and nothing else; dropped, every one of them would be measured against
       a guess and called broken. */
    var checking = null;
    if (changing) {
      var want = [], seen = {};
      [rec.small, rec.shared, media, noteShared, nmedia].forEach(function (g) {
        (g || []).forEach(function (x) {
          if (!x || !x.url || seen[x.url]) return;
          seen[x.url] = true;
          if (!here(x.url) && holds.indexOf(x.url) < 0) return;
          want.push({url: x.url, bytes: x.bytes || 0, digest: x.digest || '',
                     check: x.check || ''});
        });
      });
      if (want.length) {
        checking = el('p', 'kp-check', 'Looking at what is on this phone, file by file…');
        checking.setAttribute('role', 'status');
        box.insertBefore(checking, sum);
        tell({check: at.id, want: want}).then(function (d) { checked((d && d.urls) || []); },
          function () {
            // nobody answered: the boxes are the registry's old word, and the
            // sheet says so rather than passing a guess off as the check
            checking.className = 'kp-check kp-bad';
            checking.textContent = 'What is on this phone could not be looked at just now: ' +
                                   'the boxes are what was kept the last time.';
          });
      }
    }

    var row = el('div', 'kp-btns');
    var go = el('button', 'kp-go', changing ? 'Save' : 'Keep it');
    go.type = 'button';
    var no = el('button', 'kp-no', 'Not now');
    no.type = 'button';
    row.appendChild(no);
    row.appendChild(go);
    box.appendChild(row);
    var back = el('div', 'kp-back');
    back.appendChild(box);
    document.body.appendChild(back);
    var shut = function () { back.remove(); };
    no.addEventListener('click', shut);
    back.addEventListener('click', function (e) { if (e.target === back) shut(); });
    /* THE ROOM A BACKGROUND KEEP NEEDS FOR A MOMENT (the owner, 2026-09-23:
       warn when short).  Only on the background way: the browser holds the
       download until it is put away, so it is on the phone twice, where the
       worker's own way needs the room once and its sheet stays as it was.
       Said in the sheet, and the press then reads "Keep it anyway".  What
       was allowed is a SIZE, not a yes: a sheet whose ticks have since grown
       -- a tick, Select all, the check re-ticking a box -- asks again.  And
       while the phone is asked, the press is held: a second tap in that
       moment used to start a second keep of the same book. */
    var roomNeed = -1, roomSaid = null, asking = false;
    var needOf = function (s) { return changing ? s.fetches : s.bytes + (s.notes ? owedBytes : 0); };
    go.addEventListener('click', function () {
      if (asking) return;
      var s = total();
      if (bgFor(rec) && needOf(s) > roomNeed) {
        asking = true;
        go.disabled = true;
        if (roomSaid) roomSaid.remove();
        go.textContent = changing ? 'Save' : 'Keep it';
        var need = needOf(s);
        roomFor(need).then(function (r) {
          // Not now, or a tap outside, while the phone was asked: nothing goes
          if (!back.isConnected) return;
          asking = false;
          go.disabled = false;
          roomNeed = need;
          if (!r) { go.click(); return; }
          roomSaid = roomSaid || el('p', 'kp-check kp-bad kp-room', '');
          roomSaid.textContent = roomWords(r);
          box.insertBefore(roomSaid, row);
          go.textContent = 'Keep it anyway';
        });
        return;
      }
      // held from here on, on the background way: the press goes ahead now
      if (bgFor(rec)) go.disabled = true;
      if (!changing) {
        // nothing is on this phone, so what split() would fetch is exactly
        // what was ticked: the page and its text go with it whatever happens
        var urls = (rec.small || []).map(function (x) { return x.url; })
          .concat((rec.shared || []).map(function (x) { return x.url; }), s.fetch);
        shut();
        start(rec, at, urls, s.bytes, s.ticked, s.notes);
        return;
      }
      // FREEING SOMETHING THAT IS ALREADY ON THE PHONE IS ASKED FOR ONCE (the
      // owner's 4): fetching it again may cost a train journey's worth of
      // data, and an untick is easy to make by accident on a small screen.
      // Each kind of untick names itself, so the question is about the thing
      // he actually unticked.  What the COMPUTER has lost is not in this
      // question at all (his 8): there is nothing to weigh -- it cannot be
      // fetched again, from here or anywhere -- so it is said, not asked.
      var what = [];
      if (s.gone.length)
        what.push(s.gone.length + (s.gone.length === 1 ? ' recording' : ' recordings'));
      if (s.noteOff) what.push('its notes');
      if (s.nmedOff) what.push('the notes’ recordings');
      if (what.length && !window.confirm(
          'Give back ' + big(s.frees) + ' by taking ' + joined(what) + ' off this phone?\n\n' +
          'The computer keeps them: this only frees the room here, and they can be ' +
          'fetched again from this same list.')) { go.disabled = false; return; }
      shut();
      change(rec, at, s);
    });
  }

  /* A FINGER DRAWN ACROSS THE BOXES (the owner's 4, 2026-09-23).  Picking
     fifteen chapters of a narration one tap at a time is what made keeping
     feel like work.  The row says `touch-action: none` (lib/parseh.css), so
     the browser hands the drag here instead of scrolling the sheet with it,
     and every other part of the sheet still scrolls as it did.  What the
     first box becomes is what the whole stroke does: starting on a ticked box
     clears the run, starting on an empty one fills it. */
  function dragging(list) {
    var on = false, want = false, took = false;
    function rowAt(x, y) {
      var e = document.elementFromPoint(x, y);
      return e && e.closest ? e.closest('.kp-row') : null;
    }
    function set(row) {
      if (!row || !list.contains(row)) return;
      var b = row.querySelector('input');
      if (!b || b.checked === want) return;
      b.checked = want;
      b.dispatchEvent(new Event('change', {bubbles: true}));
    }
    list.addEventListener('pointerdown', function (e) {
      var row = e.target && e.target.closest ? e.target.closest('.kp-row') : null;
      if (!row || !list.contains(row)) return;
      var b = row.querySelector('input');
      if (!b) return;
      on = true;
      took = true;
      want = !b.checked;
      e.preventDefault();
      try { list.setPointerCapture(e.pointerId); } catch (err) {}
      set(row);
    });
    // The boxes are already as the stroke left them, and the click that
    // follows would toggle the one under the finger a second time -- a label
    // and a checkbox both act on it.  A click that no stroke of ours came
    // before is the keyboard's, and is left alone.
    list.addEventListener('click', function (e) {
      if (!took) return;
      took = false;
      if (e.target && e.target.closest && e.target.closest('.kp-row')) e.preventDefault();
    });
    list.addEventListener('pointermove', function (e) {
      if (!on) return;
      e.preventDefault();
      set(rowAt(e.clientX, e.clientY));
    });
    ['pointerup', 'pointercancel'].forEach(function (name) {
      list.addEventListener(name, function (e) {
        if (!on) return;
        on = false;
        if (name === 'pointercancel') took = false;      // no click will follow
        try { list.releasePointerCapture(e.pointerId); } catch (err) {}
      });
    });
  }

  function remember(rec, at, bytes, files, ticked, notes) {
    var r = reg();
    r[at.id] = entryOf(rec, at, bytes, files, ticked, notes);
    saveReg(r);
  }
  /* WHAT THE REGISTRY SAYS OF ONE THING, made in one place.  A keep that
     ends while this page is open writes it at once (`remember`); a book kept
     in the BACKGROUND may end with every page closed, so the same entry is
     made at the press and left in the job's note, for whichever page opens
     next to write down (`bgKeep`, `written`).  Two copies of this shape would
     be two registries that drift. */
  function entryOf(rec, at, bytes, files, ticked, notes) {
    var e = {title: rec.title || at.id, page: rec.page || at.id, kind: rec.kind || 'thing',
             version: rec.version || '', bytes: bytes, at: Date.now() / 1000,
             files: files, media: ticked};
    // WHETHER ITS NOTES CAME WITH IT, written only where the thing can have
    // any.  The out-of-date bar reads it to know whether Keep it again should
    // fetch them, and /m/kept/ says it in a tag.  A deck and a document have
    // no notes mount, and a book kept before any of this existed was never
    // asked: for both of them the field is ABSENT, which means "this is not
    // known" and is not the same as "they were not kept".  A guess written
    // here would come back later as a tag that lies.
    if (rec.notes) e.notes = !!notes;
    // AND WHICH VERSION OF THEM.  The notes carry a version of their own,
    // apart from the thing's, so that a note written at the desk speaks to
    // whoever kept the notes and stays quiet for whoever refused them.
    if (rec.notes && notes) e.notesVersion = rec.notes.version || '';
    return e;
  }

  /* `again` says this press is a RENEW, and it matters because the worker
     now skips what the phone already holds (lib/sw.js, keep()): a first keep
     and a Save want that -- a face kept for another book is not fetched a
     second time -- but "Keep it again" is the one press whose whole purpose
     is to bring what CHANGED, and a changed chapter keeps the address it
     always had.  Without the word, the press that exists to mend a stale
     copy would fetch nothing at all. */
  function start(rec, at, urls, bytes, ticked, notes, again) {
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(function () {});
    say('keeping ' + (rec.title || 'it') + ' — ' + big(bytes));
    paint('keeping');
    var each = function (p) { paint('keeping', Math.round(p.done * 100 / p.of), p); };
    // WHICH WAY, decided here and per press (the owner, 2026-09-23): a book
    // goes by the browser's own download where this page's registration has
    // one, and everything else -- and everything on the iPad -- by the worker
    // exactly as before.  Both answer in the same words.
    var job = bgFor(rec)
      ? bgKeep(rec, at, urls, [bytes, urls.length, ticked || [], notes], again ? 'again' : false, each)
      : tell({keep: {id: at.id, urls: urls, version: rec.version || '', renew: !!again}}, each);
    job.then(function (d) {
      busy = null;
      // A FIRST KEEP THAT BROUGHT NOTHING AT ALL -- cancelled before anything
      // had come -- is not written down: the book stays not kept (the owner)
      if (d && d.nothing) { paint(); say(d.line, true); return; }
      // TAKEN OFF, or written down already by another page following it:
      // nothing to write and nothing to say here
      if (d && d.quiet) { paint(); return; }
      // the entry a background keep's end carries is the one to write -- it
      // may keep the version the phone really holds (a Keep it again cut
      // short); where there is none, the press's own, as always
      if (d && d.entry) enter(at.id, d);
      else remember(rec, at, bytes, urls.length, ticked || [], notes);
      paint();
      /* TAKEN UP, AND IT DID NOT BRING WHAT THIS PRESS ASKED FOR (a sheet
         opened before another tab pressed): what is written down is what that
         keep brought, and its success is not said as this press's -- the
         owner's words say what happened instead (2026-09-24). */
      if (d && d.uncovered) { say(COMING(rec.title || 'it'), true); return; }
      // a background keep says which of its own facts it was, in its own words
      if (d && d.bad && d.line) say(d.line, true);
      else if (d && d.failed && d.failed.length)
        say(d.failed.length + ' of its files could not be kept — try again with the computer awake', true);
      else say((rec.title || 'it') + ' is on this phone now');
    }).catch(function (e) {
      busy = null;
      paint();
      say(e.message || 'it could not be kept', true);
    });
  }

  /* Save, on a thing that is here already: what was ticked and is not on the
     phone is fetched, what was unticked and is on it is freed.  The room goes
     first, so that a phone that is nearly full can be made to fit by the same
     press that fills it. */
  function change(rec, at, s) {
    paint('keeping');
    var each = function (p) { paint('keeping', Math.round(p.done * 100 / p.of), p); };
    var bg = bgFor(rec) && s.fetch.length, freed = false;
    /* ON THE BACKGROUND WAY, WHETHER IT WILL GO AT ALL IS SETTLED BEFORE
       ANYTHING IS FREED.  The room goes first, so a phone nearly full can be
       made to fit by the press that fills it -- but a press the browser then
       refuses (its setting, or two books already coming) would have given
       back what he unticked and fetched nothing, with the registry still
       naming what was freed. */
    var ready = bg ? bgReady(rec, at, s.fetch, true) : Promise.resolve();
    var followed = false;
    var job = ready.then(function (r) {
      /* THE BOOK IS COMING ALREADY -- pressed in another tab since this sheet
         opened: this press takes that keep up and frees nothing, and what is
         written down and said at the end is what THAT keep brought.  What
         this sheet would have changed is for a Save once it is in. */
      if (r === 'coming') { followed = true; return null; }
      if (!s.free.length) return null;
      return tell({free: {id: at.id, urls: s.free}}).then(function (d) { freed = true; return d; });
    });
    job.then(function () {
      if (followed) return bgTakeUp(at, each);
      if (!s.fetch.length) return null;
      /* AND THIS PRESS FETCHES WHAT IT ASKS FOR, WHOLE (`renew`).  The worker
         passes over any address this phone already holds (lib/sw.js, keep()),
         which is right for a first keep -- a face kept for another book is
         not fetched twice -- and exactly wrong here: everything in this list
         is either missing or a broken copy under the address it is meant to
         mend, so skipping "what is already there" would leave the fault where
         it was and report success.  Nothing whole is ever in this list, so
         nothing whole is ever fetched again. */
      if (bgFor(rec)) return bgKeep(rec, at, s.fetch, [s.bytes, s.files, s.ticked, s.notes], true, each);
      return tell({keep: {id: at.id, urls: s.fetch, version: rec.version || '', renew: true}}, each);
    }).then(function (d) {
      busy = null;
      if (d && d.quiet) { paint(); return; }
      if (followed) {
        if (d && d.entry) enter(at.id, d);
        paint();
        var inIt = {};
        ((d && d.urls) || []).forEach(function (u) { inIt[u] = true; });
        var covered = !s.free.length && s.fetch.every(function (u) { return inIt[u]; });
        // its line is that keep's, said here only where it is this Save's
        // too; otherwise the owner's words for what happened (2026-09-24)
        if (covered) { if (d && d.line) say(d.line, !!d.bad); }
        else say(COMING(rec.title || 'it'), true);
        return;
      }
      if (d && d.entry) enter(at.id, d);
      else remember(rec, at, s.bytes, s.files, s.ticked, s.notes);
      paint();
      if (d && d.bad && d.line) { say(d.line, true); return; }
      if (d && d.failed && d.failed.length) {
        say(d.failed.length + ' of them could not be fetched — try again with the computer awake', true);
        return;
      }
      // each thing that happened says what it was: what was fetched, what was
      // given back because it was unticked, and what was freed because the
      // computer has lost it (the owner's 8) are three different facts
      var news = [];
      if (s.fetch.length) news.push('what was ticked is on this phone now');
      if (s.mends)
        news.push(s.mends === 1 ? 'one file that was no longer whole is mended'
                                : s.mends + ' files that were no longer whole are mended');
      if (s.free.length > s.stale.length) news.push('the room of what was not is given back');
      if (s.stale.length)
        news.push(s.stale.length === 1
          ? 'one file the computer no longer has is freed'
          : s.stale.length + ' files the computer no longer has are freed');
      say(news.length ? joined(news) : 'nothing was changed');
    }).catch(function (e) {
      busy = null;
      // FREED, AND THEN REFUSED (the browser weighed the room only as it was
      // asked, for instance): what is written down is the phone as it now
      // is -- without what was given back, and without what never came
      if (freed && bg) {
        var not = {};
        s.fetch.forEach(function (u) { not[u] = true; });
        var gone = 0;
        [].concat(rec.media || [], (rec.notes && rec.notes.media) || []).forEach(function (m) {
          if (m && not[m.url]) gone += m.bytes || 0;
        });
        var left = s.ticked.filter(function (u) { return !not[u]; });
        remember(rec, at, Math.max(0, s.bytes - gone), s.files - (s.ticked.length - left.length), left, s.notes);
      }
      paint();
      say(e.message || 'it could not be changed', true);
    });
  }

  /* A DECK THAT IS OUT MAY NOT BE TAKEN OFF THE PHONE (the owner's 8 and 9,
     2026-09-23).  Its answers are on this phone and nowhere else until it is
     given back, and the copy is what the study page reads: removing it would
     throw away a train journey's work without saying so.  decks.js keeps the
     check-out under `parseh_deck_out:<folder>/<slug>`. */
  function heldBack(at) {
    var m = /^\/exercises\/deck\/([a-z]+)\/([a-z0-9][a-z0-9-]*)\/$/.exec(at.id);
    if (!m) return '';
    var out = null;
    try { out = JSON.parse(get('parseh_deck_out:' + m[1] + '/' + m[2]) || 'null'); } catch (e) {}
    return out ? 'This deck is out on this phone: what has been answered here is not on the ' +
                 'computer yet. Give it back first, and then it can be removed.' : '';
  }

  function remove(at) {
    var no = heldBack(at);
    if (no) { say(no, true); return; }
    // A BOOK STILL COMING IN THE BACKGROUND IS STOPPED FIRST, and nothing of
    // it is put away (the owner, 2026-09-23): its notes say `removed` before
    // the download is stopped, so the worker never writes back what this
    // press takes off.  Where there is no background download at all -- the
    // iPad, everything but a book -- this is nothing and the drop is as it was.
    bgRemove(at.id).then(function (tokens) {
      return tell({drop: at.id}).then(function (d) {
        tokens.forEach(jobDrop);
        return d;
      });
    }).then(function (d) {
      var r = reg();
      delete r[at.id];
      saveReg(r);
      paint();
      // AND THE ROOM THAT REALLY WENT WITH IT.  What a note opens on -- the
      // studio's sheet, its faces, MathJax -- is kept once for the whole
      // phone, so it can only be given back when the last thing that leant
      // on it is gone; the worker says how many addresses that was (lib/sw.js,
      // reclaim()).  It is its own fact and gets its own words: a button
      // that says "taken off this phone" while four megabytes stay is a
      // button whose promise about room is not true.
      var over = d && d.shared ? d.shared : 0;
      say(over
        ? 'taken off this phone — and, nothing else being kept here now, the ' +
          over + ' shared files its notes opened on are given back too'
        : 'taken off this phone');
    }).catch(function (e) { say(e.message || 'it could not be removed', true); });
  }

  /* ---- a book kept in the background: Android's own download ---- */
  /* THE OWNER'S DECISION OF 2026-09-23 (TO-DO §0; lib/sw.js, `settle`, for
     the half that puts it away).  Keeping used to be one message to the
     worker and one loop there, and a browser stops a worker's event after
     five minutes -- which a narration of two hundred megabytes over a tunnel
     never finishes inside.  Where this page's registration has Background
     Fetch, a BOOK is handed to the browser's own download instead: it goes
     on with the page closed, the browser closed and the phone locked, and
     Android shows it in its own notification.  Everywhere else, and for
     everything that is not a book, the worker keeps as it always did.

     What the owner decided, and where each lives here:
       - EVERY keep of a book goes this way where it can: Keep it, Save, and
         Keep it again (`bgFor`);
       - in TWO downloads, the text first -- with the notes, which travel
         with it -- then the recordings, so that the book opens on a train as
         soon as its text is in (`bgKeep`);
       - a keep that ends part-way keeps what arrived, and says which of its
         three reasons it was (lib/sw.js, `keptLine`);
       - a second book waits behind the first and says so; a third that does
         not fit Android's five is refused (`bgFollow`, `TOO_MANY`);
       - the computer going quiet is waited out, and said (`keepingWords`);
       - a browser that refuses is said plainly and nothing is fetched
         (`REFUSED`); one that has only not started yet is waited for;
       - a keep that ends while every page is closed is written down, and its
         line said once, by the next page that opens (`bgMerge`, `foot`);
       - the room it needs for a moment -- about twice its size -- is asked
         about before it starts (`roomFor`);
       - and the page SAYS it is the background way: "— you can leave this
         page".

     THE PAGE STARTS IT, because since Chrome 149 the worker may not (driven:
     NotAllowedError).  The check is the owner's own -- `'backgroundFetch' in
     registration` -- made on THIS page's registration, which is the one
     place where the answer is also true. */
  var JOBS = 'parseh-jobs', JOB = '/__keepjob/', BG = 'parseh-keep:';
  var KEPT_ = 'parseh-kept-', SHARED_ = 'parseh-shared';
  var ICONS = [{src: '/lib/icons/parseh-192.png', sizes: '192x192', type: 'image/png'},
               {src: '/lib/icons/parseh-512.png', sizes: '512x512', type: 'image/png'}];
  var LEAVE = ' — you can leave this page';
  var REFUSED = 'Chrome will not download for Parseh in the background — turn on Automatic ' +
                'downloads for this site in Chrome’s Site settings.';
  var TOO_MANY = 'Two books are already coming onto this phone — keep this one once one of them is in.';
  // a press that took up a keep of the same book, which did not bring what
  // this press asked for (the owner, 2026-09-24)
  var COMING = function (t) {
    return t + ' was already coming onto this phone — change what is kept once it is in';
  };
  // Android keeps at most five downloads of one site going or waiting
  var MOST = 5;

  function keepingWords(pct, how) {
    var n = pct === undefined ? '' : pct + '%';
    if (!how || !how.bg) return 'Keeping… ' + n;
    if (how.waiting) return 'Waiting for ' + how.waiting + LEAVE;
    // THE COMPUTER GONE QUIET IS WAITED OUT (the owner): the browser carries
    // on by itself when it answers again, so the page says what it is doing
    if (away) return 'Keeping… ' + n + ' — waiting for the computer';
    return 'Keeping… ' + n + LEAVE;
  }

  /* THE REGISTRATION, asked for once when the page starts and with a
     deadline, so that nothing ever waits on it: a press that comes before the
     answer -- which cannot happen in practice, since a press first asks the
     computer what the thing is made of -- simply goes the way it always went.
     `getRegistration` answers `undefined` where there is none, where `ready`
     would wait for ever. */
  var bgReg = null, bgAsked = null;
  function bgLook() {
    if (bgAsked) return bgAsked;
    var sw = navigator.serviceWorker;
    if (!sw || !sw.getRegistration || !window.caches) return (bgAsked = Promise.resolve(null));
    bgAsked = Promise.race([
      sw.getRegistration().then(function (r) {
        return r && r.active && ('backgroundFetch' in r) ? r : null;
      }, function () { return null; }),
      new Promise(function (ok) { setTimeout(function () { ok(null); }, 3000); })
    ]).then(function (r) { bgReg = r || null; return bgReg; });
    return bgAsked;
  }
  function bgFor(rec) { return !!(bgReg && rec && rec.kind === 'book'); }
  function bgName(token, part, id) { return BG + token + ':' + part + ':' + id; }
  function bgParse(s) {
    if (typeof s !== 'string' || s.indexOf(BG) !== 0) return null;
    var rest = s.slice(BG.length), a = rest.indexOf(':'), b = rest.indexOf(':', a + 1);
    if (a < 1 || b <= a + 1) return null;
    return {token: rest.slice(0, a), part: rest.slice(a + 1, b), id: rest.slice(b + 1), name: s};
  }
  // what of Parseh is coming now, as [{token, part, id, name}] -- or NULL
  // where that cannot be known (no registration, or the browser would not
  // say), which is not the same answer as "nothing": a keep must never be
  // written off as cut short on the strength of a question nobody answered
  function bgIds() {
    if (!bgReg) return Promise.resolve(null);
    return bgReg.backgroundFetch.getIds().then(function (ids) {
      return (ids || []).map(bgParse).filter(Boolean);
    }, function () { return null; });
  }
  function bgAbort(name) {
    return bgReg.backgroundFetch.get(name).then(function (r) { return r ? r.abort() : false; })
      .catch(function () { return false; });
  }

  /* THE NOTES, read and written from here as the worker reads them.  Read
     WITHOUT making the cache: a browser that never kept anything in the
     background -- the iPad above all -- must not find an empty cache made
     for it by a page that only looked. */
  function jobsCache() {
    if (!window.caches) return Promise.resolve(null);
    return caches.has(JOBS).then(function (y) { return y ? caches.open(JOBS) : null; },
                                 function () { return null; });
  }
  function jobRead(key) {
    return jobsCache().then(function (c) { return c ? c.match(key) : null; })
      .then(function (r) { return r ? r.json() : null; })
      .catch(function () { return null; });
  }
  function jobWrite(key, v) {
    return caches.open(JOBS).then(function (c) {
      return c.put(key, new Response(JSON.stringify(v), {headers: {'Content-Type': 'application/json'}}));
    });
  }
  function jobDrop(token, again) {
    return jobsCache().then(function (c) {
      if (!c) return null;
      return c.keys().then(function (ks) {
        return Promise.all(ks.filter(function (k) {
          var p = new URL(k.url).pathname;
          return p === JOB + token || p.indexOf(JOB + token + '/') === 0;
        }).map(function (k) { return c.delete(k); }));
      });
    }).then(function () {
      // and once more a moment later: the second of a press's two downloads
      // may write its end just after the first one's was cleared
      if (!again) setTimeout(function () { jobDrop(token, true); }, 2500);
    }).catch(function () {});
  }
  // every keep that has a note, as its head: [{token, id, title, parts, ...}]
  function jobHeads() {
    return jobsCache().then(function (c) {
      if (!c) return [];
      return c.keys().then(function (ks) {
        var heads = ks.map(function (k) { return new URL(k.url).pathname; }).filter(function (p) {
          return p.indexOf(JOB) === 0 && p.slice(JOB.length).indexOf('/') < 0;
        });
        return Promise.all(heads.map(function (p) {
          return c.match(p).then(function (r) { return r ? r.json() : null; })
            .catch(function () { return null; });
        }));
      });
    }).then(function (all) { return (all || []).filter(Boolean); }, function () { return []; });
  }
  function jobMark(token, fields) {
    return jobRead(JOB + token).then(function (h) {
      if (!h) return null;
      for (var k in fields) if (Object.prototype.hasOwnProperty.call(fields, k)) h[k] = fields[k];
      return jobWrite(JOB + token, h).then(function () { return h; });
    });
  }

  /* REMOVE WHILE IT IS COMING (the owner): stopped first, and nothing of it
     put away.  Every note of this thing says `removed` BEFORE its download is
     stopped, so the worker's `settle`, woken by the stop, finds the word and
     keeps nothing.  Resolves with the tokens, whose notes go after the drop. */
  function bgRemove(id) {
    return jobHeads().then(function (heads) {
      var mine = heads.filter(function (h) { return h.id === id; });
      if (!mine.length) return [];
      return Promise.all(mine.map(function (h) { h.removed = true; return jobWrite(JOB + h.token, h); }))
        .then(bgIds)
        .then(function (live) {
          return Promise.all((live || []).filter(function (x) { return x.id === id; })
                                 .map(function (x) { return bgAbort(x.name); }));
        })
        .then(function () { return mine.map(function (h) { return h.token; }); });
    }).catch(function () { return []; });
  }

  /* THE ROOM IT NEEDS FOR A MOMENT (the owner: warn when short).  A download
     is held by the browser until it has been put away in the cache, so for a
     moment it is on the phone twice.  What the browser says this site may
     still use is the only figure there is; where it says nothing, nothing is
     said. */
  function roomFor(need) {
    if (!need || !navigator.storage || !navigator.storage.estimate) return Promise.resolve(null);
    return navigator.storage.estimate().then(function (e) {
      var free = Math.max(0, (e.quota || 0) - (e.usage || 0));
      return e.quota && free < need * 2 ? {need: need * 2, free: free} : null;
    }, function () { return null; });
  }
  function roomWords(r) {
    return 'Needs about ' + big(r.need) + ' free while it arrives; this phone has ' + big(r.free);
  }

  /* THE PRESS.  Answers what `tell({keep})` answers -- `{kept, done, of,
     failed, already, version}`, and `{keeping}` as it goes -- so that the
     page's own `start` and `change` are the same code on both ways; what is
     added (`line`, `bad`, `nothing`) says which of the owner's facts it was.
     `mem` is what `remember` will be given, so the note can write the same
     entry if this page is gone by then. */
  // which addresses are the heavy ones: a recording, the book's or a note's
  function heavyOf(rec) {
    var heavy = {};
    (rec.media || []).concat((rec.notes && rec.notes.media) || []).forEach(function (m) {
      if (m && m.url) heavy[m.url] = m;
    });
    return heavy;
  }
  /* WILL THE BACKGROUND WAY TAKE THIS PRESS?  What can be known before
     anything is done -- the browser's own setting, and whether Android's
     five would be passed -- asked apart, so that Save can ask it before it
     frees anything.  A book already coming is not a refusal: the press
     follows that keep (`bgKeep`). */
  function bgReady(rec, at, urls, again) {
    return refusedHere().then(function (no) {
      if (no) throw new Error(REFUSED);
      return bgIds();
    }).then(function (live) {
      live = live || [];
      // coming already: this press will take that keep up, not refuse it
      if (live.some(function (x) { return x.id === at.id; })) return 'coming';
      return planOf(at.id, urls, again, heavyOf(rec)).then(function (p) {
        var parts = (p.text.length ? 1 : 0) + (p.recs.length ? 1 : 0);
        if (parts && live.length + parts > MOST) throw new Error(TOO_MANY);
      });
    });
  }

  function bgKeep(rec, at, urls, mem, again, onEach) {
    var t = rec.title || at.id;
    var heavy = heavyOf(rec), want = {};
    [rec.small, rec.shared, rec.media, rec.notes && rec.notes.small, rec.notes && rec.notes.shared,
     rec.notes && rec.notes.media].forEach(function (g) {
      (g || []).forEach(function (x) {
        if (x && x.url && !want[x.url])
          want[x.url] = {bytes: x.bytes || 0, digest: x.digest || '', check: x.check || ''};
      });
    });
    var token = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    var first = !reg()[at.id];
    var plan = null, already = null;
    return refusedHere().then(function (no) {
      if (no) throw new Error(REFUSED);
      return bgIds();
    }).then(function (live) {
      live = live || [];
      // THIS BOOK IS COMING ALREADY: the press follows that keep rather than
      // starting a second one of the same book (a second tap, a second tab)
      var same = live.filter(function (x) { return x.id === at.id; })[0];
      return (same ? jobRead(JOB + same.token) : Promise.resolve(null)).then(function (h) {
        if (h && !h.removed) { already = h; return null; }
        return planOf(at.id, urls, again, heavy).then(function (p) {
          plan = p;
          var parts = (p.text.length ? 1 : 0) + (p.recs.length ? 1 : 0);
          if (parts && live.length + parts > MOST) throw new Error(TOO_MANY);
        });
      });
    }).then(function () {
      /* THIS BOOK IS COMING ALREADY -- a second tap, a second tab: the press
         takes that keep up, as a page opened while it runs does, and what is
         written down at its end is what THAT keep brings (its end carries
         its own entry), never this press's picks, which nothing fetched. */
      if (already) {
        var has = {};
        (already.urls || []).forEach(function (u) { has[u] = true; });
        var covered = urls.filter(Boolean).every(function (u) { return has[u]; });
        // the promise is every follower's on this page: a copy is marked
        return bgFollow(already, onEach).then(function (d) {
          if (!d || covered) return d;
          var c = {uncovered: true}, k;
          for (k in d) if (Object.prototype.hasOwnProperty.call(d, k)) c[k] = d[k];
          return c;
        });
      }
      var n = urls.filter(Boolean).length;
      // NOTHING TO FETCH: everything asked for is on this phone already
      if (!plan.text.length && !plan.recs.length)
        return {kept: at.id, done: n, of: n, failed: [], already: plan.already, version: rec.version || ''};
      var head = {v: 1, token: token, id: at.id, title: t, page: rec.page || at.id,
                  version: rec.version || '', renew: !!again, first: first,
                  // Keep it again, as against Save: one that brings nothing
                  // leaves the registry at the version the phone really holds
                  again: again === 'again', held: plan.held,
                  urls: urls.filter(Boolean), already: plan.already, parts: {}, want: {},
                  entry: entryOf(rec, at, mem[0], mem[1], mem[2], mem[3]),
                  started: Date.now() / 1000};
      if (plan.text.length) head.parts.text = plan.text;
      if (plan.recs.length) head.parts.rec = plan.recs;
      plan.text.concat(plan.recs).forEach(function (u) { if (want[u]) head.want[u] = want[u]; });
      var bf = bgReg.backgroundFetch, started = 0;
      var go = function (part, list, opts) {
        return bf.fetch(bgName(token, part, at.id), list.map(function (u) {
          return new Request(u, {cache: 'no-store', credentials: 'same-origin'});
        }), opts).then(function (r) { started++; return r; });
      };
      /* THE THING'S OWN CACHE IS MADE NOW, as the worker's `keep` makes it
         the moment it starts: while this book's download waits behind
         another's, an empty `parseh-kept-` cache is what tells `reclaim` that
         something is still kept, so the shared files this book was told it
         need not fetch are not swept from under it by another book's Remove. */
      return caches.open(KEPT_ + at.id).then(function () {
        return jobWrite(JOB + token, head);
      }).then(function () {
        return plan.text.length
          ? go('text', plan.text, {title: t + ' — its text, coming onto this phone', icons: ICONS})
          : null;
      }).then(function () {
        if (!plan.recs.length) return null;
        var o = {title: t + ' — its recordings, coming onto this phone', icons: ICONS};
        // ANDROID'S BAR COUNTS MEGABYTES (the owner): a recording's size is
        // exact -- the file's own length -- so the total can be given; one
        // too small would stop the download for ever, so a recording whose
        // size is not known leaves the total out altogether
        var sum = 0, exact = plan.recs.every(function (u) {
          var b = heavy[u] && heavy[u].bytes;
          sum += b || 0;
          return b > 0;
        });
        if (exact) o.downloadTotal = sum;
        return go('rec', plan.recs, o).catch(function (err) {
          if (!started) throw err;
          // the text is coming and the recordings were refused: the end says
          // they were not kept, and the text stays (the owner: what arrived).
          // Refused for want of room is its own fact, and is said as one --
          // the browser weighs a download against the room before it starts
          var full = err && err.name === 'QuotaExceededError';
          return jobWrite(JOB + token + '/rec', {part: 'rec', put: [], failed: plan.recs.slice(),
                                                 gone: [], noRoom: full ? plan.recs.slice() : [],
                                                 finished: Date.now() / 1000})
            .then(function () { return null; });
        });
      }).then(function () {
        return bgFollow(head, onEach);
      }, function (err) {
        // NOTHING STARTED: nothing is kept, and the note goes with it -- and
        // so does the empty cache a first keep made for it
        return jobDrop(token).then(function () {
          if (!first) return null;
          return caches.open(KEPT_ + at.id).then(function (c) { return c.keys(); }).then(function (ks) {
            return ks.length ? null : caches.delete(KEPT_ + at.id);
          }).catch(function () {});
        }).then(function () {
          if (err && err.name === 'QuotaExceededError')
            throw new Error(t + ': no room on this phone for ' + (plan.text.length + plan.recs.length) +
                            ' of its files');
          throw new Error(REFUSED);
        });
      });
    });
  }

  // THE BROWSER SAYS NO before anything is asked of it: the site's own
  // setting, where the browser will say what it is
  function refusedHere() {
    if (!navigator.permissions || !navigator.permissions.query) return Promise.resolve(false);
    return Promise.race([
      navigator.permissions.query({name: 'background-fetch'})
        .then(function (s) { return s && s.state === 'denied'; }, function () { return false; }),
      new Promise(function (ok) { setTimeout(function () { ok(false); }, 2000); })
    ]);
  }

  /* WHAT OF THE JOB IS ALREADY ON THIS PHONE, asked exactly as the worker's
     `keep` asks it (lib/sw.js, `held`): of this thing's own cache and of the
     shared one, and of no other; nothing is asked on a renew.  Nothing is
     MADE here: a press that is then refused must leave no empty cache behind
     (`bgKeep` makes the thing's own once the press is going ahead).  A
     download cannot pass over a file, so what is held is taken off the list
     before it is handed over, duplicates too -- each counted in `already`,
     as `keep` counts them. */
  function planOf(id, urls, again, heavy) {
    var seen = {}, uniq = [];
    urls.forEach(function (u) { if (u && !seen[u]) { seen[u] = true; uniq.push(u); } });
    var already = urls.filter(Boolean).length - uniq.length;
    var opened = function (name) {
      return caches.has(name).then(function (y) { return y ? caches.open(name) : null; });
    };
    return Promise.all([opened(SHARED_), opened(KEPT_ + id)]).then(function (cs) {
      var where = cs.filter(Boolean);
      return Promise.all(uniq.map(function (u) {
        return (function next(i) {
          if (i >= where.length) return false;
          return where[i].match(u, {ignoreVary: true})
            .then(function (r) { return r ? true : next(i + 1); });
        })(0);
      }));
    }).then(function (have) {
      // on a renew nothing is passed over, but what was here already is
      // remembered (`held`): a keep cut off before it could say how it
      // ended cannot tell that old copy from a new one (`interrupted`)
      var text = [], recs = [], held = [];
      uniq.forEach(function (u, i) {
        if (have[i] && !again) { already++; return; }
        if (have[i]) held.push(u);
        (heavy[u] ? recs : text).push(u);
      });
      return {text: text, recs: recs, already: already, held: held};
    });
  }

  /* FOLLOWING A KEEP TO ITS END, from the page that pressed or from one
     opened while it runs.  The progress comes from the browser's own
     registrations, counted in bytes against what the note says the files
     weigh; the END comes from the worker (`{kept}` with this keep's token),
     and is also looked for in the notes, in case it was said before anybody
     here was listening.  Resolves with the worker's end. */
  var following = {}, hearers = {};
  /* `leave`: this page writes a keep's proper end down by itself (Kept on
     this phone, lib/mobile.py's MERGE_JS), so such an end is left in the
     notes for it and the page is only nudged to look; what this follower
     writes down there is a keep cut off before its end was written, which
     that page cannot see. */
  function bgFollow(head, onEach, leave) {
    // several may follow one keep on one page -- the button, and the page's
    // own write-down of what is coming -- and each is told how far it is
    if (onEach) (hearers[head.token] = hearers[head.token] || []).push(onEach);
    if (following[head.token]) return following[head.token];
    var bf = bgReg.backgroundFetch;
    var weight = function (list) {
      return (list || []).reduce(function (n, u) {
        return n + ((head.want[u] && head.want[u].bytes) || 0);
      }, 0);
    };
    var total = 0;
    Object.keys(head.parts || {}).forEach(function (p) { total += weight(head.parts[p]); });
    var p = new Promise(function (done) {
      var parts = {}, over = false, top = 0, waiting = '', quiet = 0, timer = null;
      var recMoved = Date.now(), recLast = -1, sizing = false;
      function end(d) {
        if (over) return;
        over = true;
        clearInterval(timer);
        if (navigator.serviceWorker) navigator.serviceWorker.removeEventListener('message', hear);
        Object.keys(parts).forEach(function (k) {
          if (parts[k].r) parts[k].r.removeEventListener('progress', moved);
        });
        delete following[head.token];
        delete hearers[head.token];
        if (leave && d && !d.cut && !d.quiet) {
          var left = {left: true}, k;
          for (k in d) if (Object.prototype.hasOwnProperty.call(d, k)) left[k] = d[k];
          done(left);
          return;
        }
        jobDrop(head.token).then(function () { done(d); });
      }
      function hear(e) {
        var d = e.data || {};
        if (d.token === head.token && d.kept === head.id) end(d);
      }
      if (navigator.serviceWorker) navigator.serviceWorker.addEventListener('message', hear);
      function got() {
        var n = 0;
        for (var k in parts) if (Object.prototype.hasOwnProperty.call(parts, k)) n += parts[k].last || 0;
        return n;
      }
      function tell_() {
        var all = hearers[head.token] || [];
        if (over || !all.length) return;
        var pct = total ? Math.floor(got() * 100 / total) : 0;
        // never backwards: a download that starts a file again from nothing
        // is still further on than it was
        top = Math.max(top, Math.min(99, pct));
        var said = {keeping: head.id, done: top, of: 100, failed: 0, bg: true,
                    waiting: got() ? '' : waiting};
        all.forEach(function (f) { f(said); });
      }
      function moved(ev) {
        var r = ev.target, k = bgParse(r.id);
        if (!k) return;
        parts[k.part] = parts[k.part] || {};
        parts[k.part].r = r;
        parts[k.part].last = r.downloaded || 0;
        tell_();
      }
      /* A RECORDING THAT HAS GROWN ON THE COMPUTER since the list was made
         (the owner: Android's bar counts megabytes, and a page that is open
         notices and stops it; what had come stays).  The browser does not
         fail such a download: it stops a little short of the size it was
         given and waits there for ever (driven), which looks exactly like a
         download paused or a computer gone quiet -- and those are waited out.
         So a recordings download that has not moved for a minute is looked
         into, not stopped: the computer is asked what the book is made of
         now, and only if it names one of these recordings at another size
         than the note has is the download stopped. */
      function grown(r) {
        if (sizing || !r || !r.downloadTotal || r.result) return;
        if (r.downloaded !== recLast) { recLast = r.downloaded; recMoved = Date.now(); return; }
        if (Date.now() - recMoved < 60000) return;
        sizing = true;
        Promise.race([
          fetch(head.id + '__offline', {cache: 'no-store', headers: {'Accept': 'application/json'}})
            .then(function (res) { return res.ok ? res.json() : null; }, function () { return null; }),
          new Promise(function (ok) { setTimeout(function () { ok(null); }, 30000); })
        ]).then(function (rec) {
          sizing = false;
          recMoved = Date.now();
          if (!rec || over) return;
          var now = heavyOf(rec);
          var changed = (head.parts.rec || []).some(function (u) {
            return now[u] && head.want[u] && (now[u].bytes || 0) !== (head.want[u].bytes || 0);
          });
          if (!changed) return;
          jobMark(head.token, {overrun: true}).then(function () {
            return bgAbort(bgName(head.token, 'rec', head.id));
          });
        });
      }
      // WHAT A DOWNLOAD OF THIS KEEP THAT IS OVER BROUGHT, from its own note:
      // what it put away counts as come, and what it failed to bring is taken
      // off the total -- a recordings download refused for want of room must
      // not read as 99% while the text is still coming
      var counted = {};
      function settledPart(part) {
        if (counted[part]) return;
        counted[part] = 'asking';
        jobRead(JOB + head.token + '/' + part).then(function (o) {
          if (!o || o.settling) {
            // over, and being put away (or about to be): it has come
            counted[part] = false;
            parts[part] = parts[part] || {};
            parts[part].r = null;
            parts[part].last = Math.max(parts[part].last || 0, weight(head.parts[part]));
            tell_();
            return;
          }
          counted[part] = true;
          var lost = weight(o.failed || []);
          total = Math.max(0, total - lost);
          // the figure may go down once, where what never came is taken off
          if (lost) top = 0;
          parts[part] = parts[part] || {};
          parts[part].r = null;
          parts[part].last = weight(o.put || []);
          tell_();
        });
      }
      function look() {
        if (over) return;
        bgIds().then(function (live) {
          // the browser would not say what is coming: nothing is concluded
          // from a look that saw nothing
          if (over || live === null) return;
          var mine = live.filter(function (x) { return x.token === head.token; });
          var others = live.filter(function (x) { return x.token !== head.token; });
          mine.forEach(function (x) {
            if (parts[x.part] && (parts[x.part].r || parts[x.part].asking)) {
              if (x.part === 'rec') grown(parts[x.part].r);
              return;
            }
            parts[x.part] = parts[x.part] || {last: 0};
            parts[x.part].asking = true;
            bf.get(x.name).then(function (r) {
              parts[x.part].asking = false;
              if (!r || over) return;
              parts[x.part].r = r;
              parts[x.part].last = r.downloaded || 0;
              r.addEventListener('progress', moved);
              tell_();
            }, function () { parts[x.part].asking = false; });
          });
          // a download of this keep that is over: what it brought, or, until
          // its note says, its weight -- so a page opened while the
          // recordings come starts from where it is
          Object.keys(head.parts).forEach(function (part) {
            if (mine.some(function (x) { return x.part === part; })) return;
            parts[part] = parts[part] || {};
            if (!counted[part]) { parts[part].r = null; settledPart(part); }
          });
          /* WAITING BEHIND ANOTHER BOOK (the owner: it waits, and says so) --
             behind one pressed BEFORE this one, and only that.  Chrome holds a
             new download for a while after a page loads, so a book pressed
             first can sit at nothing while a later one is registered; it must
             not then say it is waiting for the later one. */
          var ahead = others.map(function (x) { return x.token; })
            .filter(function (t, i, all) { return all.indexOf(t) === i; });
          if (!got() && ahead.length) {
            Promise.all(ahead.map(function (t) { return jobRead(JOB + t); })).then(function (hs) {
              var first = hs.filter(function (h) {
                return h && ((h.started || 0) < (head.started || 0) ||
                             ((h.started || 0) === (head.started || 0) && h.token < head.token));
              }).sort(function (x, y) { return (x.started || 0) - (y.started || 0); })[0];
              var was = waiting;
              waiting = first ? (first.title || 'another book') : '';
              if (waiting !== was) tell_();
            });
          } else if (waiting) { waiting = ''; tell_(); }
          /* NOTHING HAS COME YET, AND THAT IS WAITED OUT (the owner, 2026-09-23,
             on second thought).  A rule used to stop a download that had
             brought no byte in half a minute and call it Chrome refusing --
             and it stopped good keeps: Chrome holds a new download while any
             page is loading and for half a minute after, and on a computer for
             up to a minute after it starts (driven: three runs out of four
             stopped a keep that, left alone, arrived at about sixty seconds).
             A refusal the browser really gives shows at the press itself
             (`bgKeep`); a download that has not started simply waits, the
             button saying so, and the notification is there to cancel it. */
          if (mine.length) { quiet = 0; return; }
          // NOTHING OF IT IS COMING ANY MORE: the end is in the notes, or the
          // worker is putting it away now, or it was stopped before it could
          // say -- the browser gives an event five minutes and no more
          jobRead(JOB + head.token + '/end').then(function (d) {
            if (over) return;
            if (d) { end(d); return; }
            /* ITS NOTE GONE, OR SAYING REMOVE: the book was taken off this
               phone (Remove, here or on Kept on this phone), or another page
               following it wrote it down first.  Either way there is nothing
               to write and nothing to say -- and above all the entry of a
               book just removed must not be written back. */
            return jobRead(JOB + head.token).then(function (h) {
              if (over) return null;
              if (!h || h.removed) { end({kept: head.id, token: head.token, quiet: true}); return null; }
              return settling(head).then(function (busyNow) {
                quiet = busyNow ? 0 : quiet + 1;
                if (quiet < 30) return null;
                return interrupted(head).then(function (d2) {
                  // and Remove may have landed while the caches were looked at
                  return jobRead(JOB + head.token).then(function (h2) {
                    end(h2 && !h2.removed ? d2 : {kept: head.id, token: head.token, quiet: true});
                  });
                });
              });
            });
          });
        });
      }
      timer = setInterval(look, 2000);
      look();
    });
    following[head.token] = p;
    return p;
  }

  // is the worker putting some of it away now?  (a fresh "settling" note)
  function settling(head) {
    return Promise.all(Object.keys(head.parts || {}).map(function (part) {
      return jobRead(JOB + head.token + '/' + part);
    })).then(function (outs) {
      return outs.some(function (o) {
        return o && o.settling && Date.now() / 1000 - (o.at || 0) < 330;
      });
    });
  }

  /* STOPPED BEFORE IT COULD SAY: the worker's putting-away was cut off, or
     never ran.  What arrived is what the caches hold now, and that is what is
     written down -- the owner's "keep what arrived" -- with today's words for
     files that did not come. */
  function interrupted(head) {
    var urls = [];
    Object.keys(head.parts || {}).forEach(function (p) { urls = urls.concat(head.parts[p]); });
    var dropped = false;
    return Promise.all([caches.has(KEPT_ + head.id), caches.has(SHARED_)]).then(function (y) {
      // its own cache, made at the press, is gone: it was taken off the phone
      if (!y[0] && !head.first) dropped = true;
      return Promise.all([y[0] ? caches.open(KEPT_ + head.id) : null,
                          y[1] ? caches.open(SHARED_) : null]);
    }).then(function (cs) {
      cs = cs.filter(Boolean);
      return Promise.all(urls.map(function (u) {
        return (function next(i) {
          if (i >= cs.length) return false;
          return cs[i].match(u, {ignoreVary: true}).then(function (r) { return r ? true : next(i + 1); });
        })(0);
      }));
    }).then(function (have) {
      if (dropped) return {kept: head.id, token: head.token, quiet: true, cut: true};
      // AN OLD COPY UNDER THE SAME ADDRESS IS NOT THE NEW ONE ARRIVING: on a
      // renew, what the phone held at the press cannot be told apart from
      // what came, so it is counted as not come
      var held = {};
      (head.held || []).forEach(function (u) { held[u] = true; });
      var failed = urls.filter(function (u, i) { return !have[i] || held[u]; });
      var nothing = failed.length === urls.length && !!(head.first || head.again);
      var n = (head.urls || []).length;
      var entry = nothing ? null : head.entry;
      // and Keep it again, cut short, leaves the version the phone really
      // holds written down, so the out-of-date bar offers it again
      if (entry && head.again && failed.length) {
        var was = reg()[head.id], e = {}, k;
        for (k in entry) if (Object.prototype.hasOwnProperty.call(entry, k)) e[k] = entry[k];
        if (was) e.version = was.version || '';
        entry = e;
      }
      // a first keep that brought nothing leaves no empty cache behind: the
      // worker's own drop takes it, and gives the shared room back with it
      if (nothing && head.first)
        tell({drop: head.id}).catch(function () {});
      return {kept: head.id, token: head.token, done: n, of: n, failed: failed, cut: true,
              already: head.already || 0, version: head.version || '', nothing: nothing,
              line: failed.length
                ? failed.length + ' of its files could not be kept — try again with the computer awake'
                : (head.title || 'it') + ' is on this phone now',
              bad: !!failed.length, entry: entry,
              finished: Date.now() / 1000};
    }).catch(function () {
      return {kept: head.id, token: head.token, failed: [], line: '', entry: null, cut: true};
    });
  }

  /* A KEEP THIS PAGE DID NOT PRESS, WRITTEN DOWN: one that ended while every
     page was closed, or that this page only watched.  The entry is the one
     made at the press; it never goes over a newer one (a Save since), and
     its line is said once, at the foot of the page (the owner). */
  function written(head, d) {
    if (!d || head.removed || d.quiet) return;
    // a page that draws the registry itself (Kept on this phone) draws again
    try { document.dispatchEvent(new CustomEvent('parseh:kept-written', {detail: {id: head.id}})); }
    catch (err) { /* an old browser: the next open shows it */ }
    var r = reg(), was = r[head.id];
    if (d.entry && !(was && (was.at || 0) > (head.started || 0))) {
      var e = {}, k;
      for (k in d.entry) if (Object.prototype.hasOwnProperty.call(d.entry, k)) e[k] = d.entry[k];
      e.at = d.finished || Date.now() / 1000;
      r[head.id] = e;
      saveReg(r);
    }
    // ONE LINE PER KEEP ON A PAGE: Kept on this phone says the lines it
    // writes down itself (lib/mobile.py, MERGE_JS), and both halves keep one
    // list of what has been said
    var pm = window.parsehMerge, told = pm && (pm.said || (pm.said = {}));
    if (told && head.token) {
      if (told[head.token]) return;
      told[head.token] = true;
    }
    foot(d.line, d.bad);
  }
  // the entry a background keep's end carries, written as the press's own
  function enter(id, d) {
    var r = reg(), e = {}, k;
    for (k in d.entry) if (Object.prototype.hasOwnProperty.call(d.entry, k)) e[k] = d.entry[k];
    e.at = d.finished || Date.now() / 1000;
    r[id] = e;
    saveReg(r);
  }

  /* THE LINE AT THE FOOT.  Said once, where the out-of-date bar stands, and
     it stays until it is put away: a toast that went in two seconds would be
     a line the owner never read, about a book that came while he was not
     looking.  Several at once share one bar. */
  var news = null;
  function foot(m, bad) {
    if (!m) return;
    if (!news || !news.isConnected) {
      news = el('div', 'kp-bar kp-news');
      news.setAttribute('role', 'status');
      var ok = el('button', 'kp-no', 'OK');
      ok.type = 'button';
      ok.addEventListener('click', function () { news.remove(); });
      news.appendChild(ok);
      document.body.appendChild(news);
    }
    var line = el('span', 'kp-newsline' + (bad ? ' kp-bad' : ''), m);
    news.insertBefore(line, news.lastChild);
  }

  /* WHAT ENDED WHILE NO PAGE WAS OPEN, written down by the first page that
     opens -- this one.  A keep with its end in the notes is written down
     and its line said; the pages that draw from the registry before any
     script of this file could run -- Kept on this phone and the offline page
     (lib/mobile.py) -- do that half themselves first and say so
     (`window.parsehMerging`).  A keep with NO end yet is never written off
     from one look: the download may have finished a moment ago with the
     worker not yet woken to put it away, or the browser may not have said
     what is coming.  It is FOLLOWED instead (`bgFollow`), which waits out a
     worker putting it away and takes a keep for cut short only after a
     minute of nothing at all -- on every page, these two included. */
  function bgMerge() {
    return jobHeads().then(function (heads) {
      return bgIds().then(function (live) {
        var going = {};
        (live || []).forEach(function (x) { going[x.token] = true; });
        return jobOrphans(heads, live).then(function () {
          return Promise.all(heads.map(function (h) {
            if (h.removed) return (live === null || going[h.token]) ? null : jobDrop(h.token);
            return jobRead(JOB + h.token + '/end').then(function (d) {
              if (d) {
                if (window.parsehMerging) return null;
                written(h, d);
                return jobDrop(h.token);
              }
              if (live === null || !bgReg) return null;
              // followed already on this page (asked again by Kept on this phone)
              if (following[h.token]) return null;
              // this page's own book, coming or being put away: its button
              // takes it up (`bgResume`)
              if (at && h.id === at.id && mobile()) return null;
              bgFollow(h, null, !!window.parsehMerging).then(function (d2) {
                var nudge = function (lines) {
                  try { document.dispatchEvent(new CustomEvent('parseh:kept-written',
                                                               {detail: {id: h.id, lines: lines || []}})); }
                  catch (err) { /* an old browser: the next open shows it */ }
                };
                // taken off, or written down elsewhere: the page draws again
                if (d2 && d2.quiet && window.parsehMerging) { nudge(); return; }
                if (d2 && d2.left && window.parsehMerge) {
                  /* ITS PROPER END, which the page writes down by itself -- if
                     its notes are still there.  Another page following the
                     same keep may have cleared them first; then the end this
                     follower heard is written down here instead, once. */
                  window.parsehMerge(function (lines) {
                    var told = window.parsehMerge.said || {};
                    if (told[h.token]) { nudge(lines); return; }
                    Promise.all([jobRead(JOB + h.token), caches.has(KEPT_ + h.id)]).then(function (a) {
                      var now = a[0];
                      jobDrop(h.token);
                      // removed, or gone with its thing's own cache: taken off
                      if ((now && now.removed) || (!now && !a[1])) { nudge(lines); return; }
                      written(h, d2);
                      paint();
                      refresh();
                    });
                  });
                  return;
                }
                written(h, d2);
                paint();
                refresh();
              });
              return null;
            });
          }));
        });
      });
    }).then(function () { paint(); refresh(); }).catch(function () {});
  }

  /* NOTES WITH NO KEEP: an end or an outcome written after its keep's notes
     were cleared (two downloads of one press can both finish it), left by
     nobody's fault and read by nothing.  They go, once the browser has said
     nothing of that keep is coming and no worker is putting it away. */
  function jobOrphans(heads, live) {
    if (live === null) return Promise.resolve();
    var have = {}, going = {};
    heads.forEach(function (h) { have[h.token] = true; });
    live.forEach(function (x) { going[x.token] = true; });
    return jobsCache().then(function (c) {
      if (!c) return null;
      return c.keys().then(function (ks) {
        return Promise.all(ks.map(function (k) {
          var p = new URL(k.url).pathname;
          if (p.indexOf(JOB) !== 0) return null;
          var t = p.slice(JOB.length).split('/')[0];
          if (have[t] || going[t] || p === JOB + t) return null;
          return c.match(k).then(function (r) { return r ? r.json() : null; }).then(function (o) {
            if (o && o.settling && Date.now() / 1000 - (o.at || 0) < 330) return null;
            return c.delete(k);
          });
        }));
      });
    }).catch(function () {});
  }

  /* A PAGE OPENED WHILE ITS BOOK IS COMING takes it up where it is: the
     button says how far, and the end is written down here when it comes. */
  // the keep of this thing now coming, followed to its end (a Save that found
  // it coming); where it has ended meanwhile there is nothing to follow
  function bgTakeUp(at_, onEach) {
    return bgIds().then(function (live) {
      var same = (live || []).filter(function (x) { return x.id === at_.id; })[0];
      return same ? jobRead(JOB + same.token) : null;
    }).then(function (h) {
      if (!h || h.removed) return {kept: at_.id, quiet: true};
      return bgFollow(h, onEach).then(function (d) {
        if (!d) return d;
        var c = {urls: h.urls || []}, k;
        for (k in d) if (Object.prototype.hasOwnProperty.call(d, k)) c[k] = d[k];
        return c;
      });
    });
  }

  function bgResume() {
    if (!at || !bgReg) return null;
    return jobHeads().then(function (heads) {
      var head = heads.filter(function (h) { return h.id === at.id && !h.removed; })[0];
      if (!head) return null;
      return jobRead(JOB + head.token + '/end').then(function (ended) {
        if (ended) return null;              // written down by `bgMerge` already
        var each = function (p) { paint('keeping', Math.round(p.done * 100 / p.of), p); };
        paint('keeping', 0, {bg: true});
        return bgFollow(head, each).then(function (d) {
          busy = null;
          written(head, d);
          paint();
          refresh();
        });
      });
    }).catch(function () {});
  }

  /* ---- the two buttons, in the slot the page names ---- */
  var btn = null, drop = null, pair = null, at = null;
  /* A KEEP IN PROGRESS IS REMEMBERED, NOT JUST PAINTED (the owner, 2026-09-23:
     mended on both ways).  Every twenty seconds the probe repaints the page
     (`paintAway`), and a repaint with no state used to put the button back to
     "Keep on this phone" in the middle of a keep -- for seconds on a small
     one, and for the whole of a narration, with the button live again under
     the thumb.  So what the keep last said is kept here, and any repaint
     while it runs says it again; only the end of the keep clears it. */
  var busy = null;
  function paint(state, pct, how) {
    if (!btn) return;
    if (state === 'keeping') busy = {pct: pct, how: how || null};
    else if (busy) { state = 'keeping'; pct = busy.pct; how = busy.how; }
    var have = reg()[at.id];
    if (state === 'keeping') {
      btn.disabled = true;
      btn.textContent = keepingWords(pct, how);
      if (drop) drop.hidden = true;
      return;
    }
    if (drop) {
      drop.hidden = !have;
      drop.disabled = false;
      drop.title = have
        ? 'it takes ' + big(have.bytes) + ' on this phone; removing it leaves the computer’s copy alone'
        : '';
    }
    // THE LIST IS THE COMPUTER'S (the owner's 4): what a thing is made of is
    // answered by `<thing>/__offline`, so with the computer away there is no
    // list to open and the button says that rather than failing quietly.
    btn.disabled = away;
    btn.textContent = (have ? 'Change what is kept' : 'Keep on this phone') +
                      (away ? ' — needs the computer' : '');
    btn.title = away
      ? 'which recordings a thing has is asked of the computer, and it cannot be reached'
      : have
      ? 'the recordings, with the ones on this phone ticked: Save fetches what is ticked and ' +
        'gives back the room of what is not'
      : 'keep this on the phone, so it works when the computer cannot be reached';
    btn.classList.toggle('kp-have', !!have);
  }
  function build() {
    if (btn) return;
    // where a page wants it: a slot it names -- the deck's actions row, the
    // document's toolbar -- else the header (a reader's and a player's, under
    // ⋯).  The slot's value is the class that page dresses its own buttons
    // in, so Keep stands in the row looking like the buttons beside it.
    var row = document.querySelector('[data-keep-slot]') ||
              document.querySelector('.dk-deckactions') ||
              document.querySelector('body[data-page=doc] .toolbar .navstack') ||
              document.querySelector('header .hrow') || document.querySelector('header');
    if (!row || !at) return;
    var dress = (row.getAttribute && row.getAttribute('data-keep-slot')) || '';
    /* THE TWO OF THEM SHARE ONE LINE, HALF EACH (the owner's 4, 2026-09-23).
       Remove from this phone used to hang under Change what is kept, on a
       line of its own, which put a button that throws away three hundred
       megabytes directly under the thumb that had just reached for the other
       one.  Side by side they are each half as wide, they read as the pair of
       choices they are, and the line below the pair is free again.

       THE WRAPPER WEARS `kp-btn` AS WELL AS ITS OWN NAME, and that is load-
       bearing rather than tidy: every sheet that places the one button places
       it by that class -- the reader's header and the player's give `.kp-btn`
       its order and its own full line, and hide it while ⋯ is shut
       (lib/mobile.css) -- so the pair has to answer to it to stand where the
       button stood.  What `.kp-btn` DRAWS is undrawn on the wrapper in
       lib/parseh.css: it is a row, not a button.  The two real buttons wear
       the page's own dress (`data-keep-slot`), so in a deck's row of actions
       they look like the buttons beside them. */
    pair = el('div', 'kp-btn kp-pair');
    pair.setAttribute('data-layout', 'mobile');
    btn = el('button', 'kp-keep' + (dress ? ' ' + dress : ''));
    btn.type = 'button';
    btn.setAttribute('data-layout', 'mobile');
    btn.addEventListener('click', function () {
      if (away) { say('this needs the computer, which cannot be reached', true); return; }
      // A BOOK ALREADY COMING -- pressed in another tab, or on this page
      // before it was reopened -- is taken up here, as a page opened while it
      // runs takes it up, rather than offered to be kept a second time.  Only
      // where the background way exists: elsewhere the press is as it was.
      if (bgReg && !busy) {
        bgIds().then(function (live) {
          if ((live || []).some(function (x) { return x.id === at.id; })) bgResume();
          else open_();
        });
        return;
      }
      open_();
    });
    function open_() {
      var have = reg()[at.id];
      made(at.door).then(function (rec) {
        if (!rec || !rec.ok) throw new Error('the computer did not say what this is made of');
        // WHAT IS ON THE PHONE IS ASKED OF THE WORKER rather than guessed
        // from the registry: the caches are the truth about the caches.  It
        // is asked on a FIRST keep too, now, because the studio's files and
        // faces that a note opens on are kept once for the whole phone (the
        // owner's 3, 4 and 5) -- without asking, this sheet would offer to
        // fetch four megabytes that the book kept last week already paid for.
        return tell({inside: at.id}).then(function (d) {
          sheet(rec, at, have ? ((d && d.urls) || []) : null, (d && d.shared) || []);
        }, function () {
          // no worker to ask: nothing is kept and nothing is shared, which is
          // what an empty phone looks like, and keeping will say so itself
          sheet(rec, at, have ? [] : null, []);
        });
      }).catch(function (e) { say(e.message || 'it cannot be kept just now', true); });
    }
    drop = el('button', 'kp-drop' + (dress ? ' ' + dress : ''));
    drop.type = 'button';
    drop.setAttribute('data-layout', 'mobile');
    drop.textContent = 'Remove from this phone';
    drop.hidden = true;
    drop.addEventListener('click', function () { remove(at); });
    pair.appendChild(btn);
    pair.appendChild(drop);
    row.appendChild(pair);
    paint();
  }

  /* ---- out of date: the heavy parts, which never renew in silence ---- */
  function look() {
    var have = reg()[at.id];
    // (`busy` counts on the background way only: on the worker's way the bar
    // came as it always did, keep or no keep)
    if (!have || away || (bgFor(have) && busy)) return;
    // WHILE IT IS COMING, THE BAR WAITS (the owner): the registry still holds
    // the old version until the keep has been put away, and a bar offering
    // Keep it again over a keep already under way would be a second press of
    // the same thing
    bgLook().then(bgIds).then(function (live) {
      if ((bgFor(have) && busy) || (live || []).some(function (x) { return x.id === at.id; })) return;
      lookNow(have);
    });
  }
  function lookNow(have) {
    made(at.door).then(function (rec) {
      if (!rec || !rec.ok || !rec.version) return;
      // TWO VERSIONS, ASKED APART (the owner's 7).  The thing's own moves
      // when its text, its pictures or its recordings do; the notes' moves
      // when a note is written, edited or deleted.  A book kept WITHOUT its
      // notes must not be told it is out of date because a note changed --
      // the press it would be offered would fetch it nothing it wanted.
      var noteMoved = !!(have.notes && rec.notes &&
                         (rec.notes.version || '') !== (have.notesVersion || ''));
      if (rec.version === have.version && !noteMoved) return;
      var mine = have.media || [];
      // THE NOTES GO WITH IT WHERE THEY WERE KEPT, and are left alone where
      // they were not (the owner's 7, 2026-09-23).  A note written or edited
      // at the desk moves the book's version exactly as an edited chapter
      // does, so this bar is now as often about a note as about the text --
      // but a group the owner unticked must not come back on this press.
      var notes = have.notes && rec.notes ? rec.notes : null;
      // the heavy things are counted from BOTH lists whatever the notes' own
      // tick says, because the two ticks are separate: somebody who kept the
      // notes' recordings and then unticked the notes still has them here,
      // and a line that left them out would promise a smaller fetch than the
      // press beside it would make
      var heavy = (rec.media || []).concat((rec.notes && rec.notes.media) || [])
        .filter(function (m) { return mine.indexOf(m.url) >= 0; });
      var bytes = heavy.reduce(function (n, m) { return n + (m.bytes || 0); }, 0);
      var bar = el('div', 'kp-bar');
      bar.setAttribute('role', 'status');
      // and the line says what keeping it again would FETCH, rather than
      // naming the recordings as the old thing: what changed may be a note,
      // and a line that guessed would be wrong half the time
      var also = [];
      if (bytes) also.push('the recordings are ' + big(bytes));
      if (notes) also.push('its notes are ' + big(notes.bytes || 0));
      bar.appendChild(el('span', '', 'What is kept here is older than the computer’s' +
                         (also.length ? ' — ' + joined(also) + '.' : '.')));
      var go = el('button', 'kp-go', 'Keep it again');
      go.type = 'button';
      var no = el('button', 'kp-no', 'Later');
      no.type = 'button';
      var asked = false;
      go.addEventListener('click', function () {
        var urls = (rec.small || []).map(function (x) { return x.url; }).concat(mine);
        if (notes) {
          (notes.small || []).forEach(function (x) { urls.push(x.url); });
          (notes.shared || []).forEach(function (x) { urls.push(x.url); });
        }
        var sum = bytes + (notes ? (notes.bytes || 0) : 0);
        var run = function () {
          bar.remove();
          start(rec, at, urls, sum, mine, !!notes, true);
        };
        // the room, as the sheet asks it (the owner): the background way only;
        // and the press is held while the phone is asked, or a second tap in
        // that moment would start a second keep of the same book
        if (!bgFor(rec) || asked) { run(); return; }
        asked = true;
        go.disabled = true;
        roomFor(sum).then(function (r) {
          if (!bar.isConnected) return;           // Later was pressed meanwhile
          go.disabled = false;
          if (!r) { run(); return; }
          bar.firstChild.textContent = roomWords(r);
          go.textContent = 'Keep it anyway';
          no.textContent = 'Not now';
        });
      });
      no.addEventListener('click', function () { bar.remove(); });
      bar.appendChild(go);
      bar.appendChild(no);
      document.body.appendChild(bar);
    }).catch(function () { /* the computer is away: what is kept is what there is */ });
  }

  /* ---- the chip: whether the computer can be reached (§19.5) ---- */
  /* AND IT STARTS WHERE THE PAGE STARTED.  The mark is on <html> before any
     script of this page runs -- lib/mobile.py writes AWAY_BOOT into the head
     of every page of the app, which reads the memory this file wrote on the
     page before and sets it.  Read here rather than guessed at false, so
     this file agrees with the page it arrived on from its first moment
     instead of contradicting it for the three seconds until the probe
     answers. */
  var chip = null, away = document.documentElement.hasAttribute('data-parseh-away');
  /* THE BAR THAT IS ACTUALLY ON THE SCREEN.  The hub carries BOTH layouts at
     one address -- two `.parseh-bar`s, one `data-layout="browser"` and one
     `data-layout="mobile"`, with the sheet showing whichever the mode asks
     for -- so taking the first one in the page put the chip inside the hidden
     one on exactly the page where the chip matters most (the app opens on the
     hub).  Every candidate is tried in turn and the first one that is drawn
     wins; the first of them is the answer where nothing is drawn yet, which
     is what a page still parsing looks like. */
  function bar() {
    var all = [].concat(
      [].slice.call(document.querySelectorAll('.parseh-bar')),
      [].slice.call(document.querySelectorAll('header .hrow')),
      [].slice.call(document.querySelectorAll('header.m-topbar')),
      [].slice.call(document.querySelectorAll('header')));
    for (var i = 0; i < all.length; i++)
      if (all[i].getClientRects().length) return all[i];
    return all[0] || null;
  }
  /* EVERYTHING THAT FOLLOWS FROM `away`, WHOEVER SAID IT.  The probe says it
     from what the computer answered; the page before this one says it from
     what it found a moment ago (`recall`).  Both draw the same page, and only
     the first of them counts as knowing (`probed`, and the warming that waits
     on it). */
  /* AND A PAGE THAT OPENED OFFLINE STAYS OFFLINE (the owner's rule of
     2026-09-23): "a book, a notebook, a deck of exercises does not change
     from offline to online mid-use.  If I enter offline they must be the
     offline version, full stop; if I want the online version I leave and
     come back."

     So within ONE page the mark is one-way.  It may go up -- the probe is
     allowed to discover, at any moment, that the computer has gone -- and it
     may not come down, because half a page drawn from what is kept and half
     from what the computer now says is neither version of it: a reader whose
     first chapters came off this phone would start fetching the next ones,
     a deck that offered what it holds would start offering what it does not.
     Leaving the page and coming back reads the memory afresh (AWAY_BOOT in
     lib/mobile.py) and probes again, which is the way back to online and the
     only one. */
  /* ASSUMED, THEN CONFIRMED -- and only the confirming binds.

     A page OPENS on what the page before it wrote down, so that nothing it
     does on sight is asked into a socket that will never answer; that is the
     first half of the rule.  Its own probe answers within three seconds, and
     what happens then is the difference between the rule's two halves:

       the probe says away    -> confirmed, and this page is an offline page
                                 for as long as it is open, whatever happens
                                 to the tunnel afterwards.  "A book, a
                                 notebook, a deck of exercises does not
                                 change from offline to online mid-use."
       the probe says there   -> the memory was three minutes stale and the
                                 computer is back.  The page corrects itself,
                                 in its first breath and not mid-use -- which
                                 is exactly what "if I want the online
                                 version I get out and get back in" has to
                                 mean.  Clamped instead, going back in would
                                 have given an offline page for another three
                                 minutes and the way back would have been
                                 shut. */
  var confirmed = false;
  function paintAway() {
    if (confirmed) away = true;
    // every page of the app can ask the one question "is the computer there?"
    // of the document itself, rather than each script pinging on its own
    if (away) document.documentElement.setAttribute('data-parseh-away', '');
    else document.documentElement.removeAttribute('data-parseh-away');
    refresh();
    paint();
    if (!away) { if (chip) { chip.remove(); chip = null; } return; }
    // still in the page AND still where it can be seen: a chip that was hung
    // before the sheets landed, or before the mode was applied, may be
    // sitting in a bar that is now the hidden one
    if (chip && chip.isConnected && chip.getClientRects().length) return;
    var b = bar();
    if (!b) return;
    if (chip && chip.parentNode === b) return;
    if (chip) chip.remove();
    chip = el('a', 'kp-off', 'offline');
    chip.href = '/m/kept/';
    chip.title = 'Parseh’s computer cannot be reached: what is kept on this phone still works';
    b.appendChild(chip);
  }
  function chipPaint() {
    // this is only ever reached from the probe, so by the time it runs the
    // question "is the computer there?" has an answer rather than a guess --
    // which is what the next page will open on (`recall`)
    probed = true;
    noted();
    // and a warming that was asked for before the computer was known to be
    // there goes now: this is the moment it became true
    warmSend();
    paintAway();
  }

  /* WHAT THE LAST PAGE FOUND (the owner's 5, 2026-09-23).  Every page used to
     start by assuming all was well and then ask -- so walking from an offline
     hub into the shelf gave three seconds of a page pretending the computer
     was there: cards that could be tapped and went nowhere, no chip, and the
     numbers the clock has made wrong still on the screen.  The probe's answer
     is written down here, and the next page opens on it.

     IT IS A MEMORY AND IT IS TREATED AS ONE.  It is not trusted past a few
     minutes -- a phone picked up in the evening must not open on what it
     found at lunchtime -- and the probe behind it corrects it either way,
     which is the half the owner asked to keep ("and yes do the check and if
     the situation changes, correct, of course").  Nothing here writes it but
     the probe: were `recall` to stamp it afresh, a remembered state would
     renew itself from page to page and never grow old at all. */
  /* HOW LONG THE MEMORY IS GOOD FOR IS ONE NUMBER, AND IT IS THIS ONE.  The
     probe here is the only thing that ever writes `parseh_away`, so how long
     what it wrote may be believed is its own to say -- and it was said twice,
     three minutes here and five in the studio's decks.js, which meant that
     for two minutes out of every five a deck page and the bar above it
     disagreed about whether the computer was there.  Both are exported below
     (`trusted`, `awayKey`) so that whoever reads the memory reads the
     writer's own terms with it; three minutes is the stricter of the two and
     is the one kept, because the cost of forgetting too soon is one honest
     probe and the cost of trusting too long is a page that lies. */
  var AWAY = 'parseh_away', TRUSTED = 180;
  function recall() {
    var r = null;
    try { r = JSON.parse(get(AWAY) || 'null'); } catch (e) { r = null; }
    if (!r || typeof r.away !== 'boolean') return null;
    var age = Date.now() / 1000 - (+r.at || 0);
    if (!(age >= 0) || age > TRUSTED) return null;
    return r;
  }
  /* AND THE MEMORY CARRIES ITS OWN TERMS (the owner's 2 of 2026-09-23).  It
     used to be `{at, away}`, and how long that was worth acting on lived
     here, in `TRUSTED`, exported for whoever read the entry.  But a reader
     can only ask this file for the number if this file has RUN, and it is
     deferred while the pages that read it are not: markdown/app/static's
     decks.js is a plain script at the foot of the body, so it runs BEFORE a
     deferred one in the head.  A cram page therefore always found
     `window.ParsehKeep` undefined, always threw the memory away, always
     decided the computer was there -- and asked it, with a POST, which no
     worker may cache and no deadline anywhere would cut short.  On the
     computer that ask is refused in microseconds and the page falls to the
     copy it holds; on a phone away from its tunnel the socket answers
     nothing at all and the page sits on "Loading exercises…" for ever.
     So the entry says how long it is good for, and a reader needs nothing
     of this file to read it on the writer's own terms. */
  /* AND WHAT IS WRITTEN DOWN IS WHAT THE PROBE FOUND, never what this page
     has settled into.  A page that opened offline stays offline while it is
     open (`paintAway`), and if that clamped state were the thing written
     down, a phone that walked back into range would write "away" again on
     every page, read it again on the next, and never find its way back --
     the very escape the rule names ("if I want the online version I leave
     and come back") would be shut.  `found` is the answer to the question
     that was actually asked; `away` is how this page is behaving. */
  var found = away;
  function noted() {
    put(AWAY, JSON.stringify({at: Date.now() / 1000, away: found, trusted: TRUSTED}));
  }
  /* THE PROBE KEEPS ITS OWN PATIENCE.  The worker waits a long time on a
     door it has no copy of, because cutting an honestly slow answer short
     when nothing can take its place is the worse failure (lib/sw.js,
     PATIENT) -- but this one ask is not waiting for an answer, it is asking
     WHETHER THERE IS ANYBODY THERE, and the chip that says "offline" is no
     use to a thumb half a minute after the train went into the tunnel.  So
     the probe gives it three seconds of its own and reads silence as away;
     if the computer was there all along, the next ping says so. */
  var PATIENCE = 3000;
  // the verdict, and how this page will behave on it: `found` is the answer
  // to "is anybody there?", `away` is clamped by `paintAway` so that a page
  // which opened offline stays offline until it is left
  function verdict(gone) {
    found = gone;                       // what was asked, for the next page
    if (gone) confirmed = true;         // and this page is settled: see paintAway
    away = gone || confirmed;
    chipPaint();
  }
  function ping() {
    // the computer itself, not the browser's idea of a network: a phone on
    // wifi with the computer asleep is offline as far as Parseh is concerned
    if (!navigator.onLine) { verdict(true); return; }
    var settled = false;
    var slow = setTimeout(function () {
      if (settled) return;
      settled = true;
      verdict(true);
    }, PATIENCE);
    fetch('/__activity', {method: 'GET', cache: 'no-store'})
      .then(function (r) {
        if (settled) return;
        settled = true; clearTimeout(slow);
        verdict(!r.ok && r.status === 503);
      })
      .catch(function () {
        if (settled) return;
        settled = true; clearTimeout(slow);
        verdict(true);
      });
  }

  /* ---- the app getting itself ready, and saying how it is going ---- */
  /* THE ASK.  `warmAsked` is what has been sent on this page and `warmWant`
     what is waiting to be: an ask made before the worker has taken the page
     over -- which is every ask on the first load after an install, where
     `navigator.serviceWorker.controller` is still null -- is kept rather than
     dropped, and goes with the next ping that finds the computer, or the
     moment the worker claims us.  Once per page and not on a timer: the
     worker skips what this phone holds, so a second ask would buy nothing
     that the first did not already buy.
     And `probed` is the difference between "the computer is there" and
     "nobody has looked yet", which `away` alone cannot tell: `away` starts
     false, because the chip must not flash on a page that opens perfectly
     well, and a warming read that as leave to fetch three megabytes before
     the first ping had come back.  Nothing is sent until the probe has
     answered once. */
  var warmAsked = {}, warmWant = [], warmRuns = {}, probed = false;
  function warm(what) {
    // the browser mode is the browser's own: nothing here fetches for an app
    // that is not being used as one
    if (!what || warmAsked[what] || !mobile()) return;
    if (warmWant.indexOf(what) < 0) warmWant.push(what);
    warmSend();
  }
  /* After the load event, and then in the first idle moment the browser can
     spare -- with a plain timer behind it for a browser that has no idle
     callback, and a ceiling so that a page which never finishes loading does
     not mean an app that never gets ready. */
  function whenIdle(fn) {
    var ran = false;
    var go = function () {
      if (ran) return;
      ran = true;
      if (window.requestIdleCallback) requestIdleCallback(fn, {timeout: 4000});
      else setTimeout(fn, 1200);
    };
    if (document.readyState === 'complete') setTimeout(go, 400);
    else window.addEventListener('load', function () { setTimeout(go, 400); });
    setTimeout(go, 15000);
  }

  function warmSend() {
    if (!probed || away || !warmWant.length) return;
    var w = worker();
    if (!w) return;
    while (warmWant.length) {
      var what = warmWant.shift();
      if (warmAsked[what]) continue;
      warmAsked[what] = true;
      w.postMessage({warm: what});
    }
  }
  /* WHICH PAGES WANT THE STUDIO'S OWN FACE (the owner's decision 2).  The
     studio's pages are set in it and say so in their sheet; a deck's pages
     are the studio's too, and read the same sheet.  A note opened in a
     reader or a player is the third, and it is not a page at all -- it is a
     mark being clicked, so it is caught below where the click happens. */
  /* The decks' own library is in it too: it is the studio's page, it reads
     the studio's sheet, and a Persian deck's name is drawn in the face that
     sheet names -- so a phone that opened only /exercises/ would show the
     one thing on the page that is not English in whatever face it had. */
  var STUDIO_PAGE = /^\/studio(?:\/|$)|^\/exercises(?:\/|$)/;

  /* WHAT THE WORKER SAYS AS IT GOES.  `warming` while a list is being
     settled, `warmed` when it is done; `done` counts addresses settled
     whether they were fetched or skipped, so a warm phone runs to the end at
     once.  Two lists can be warming together -- a deck page asks for both --
     so they are summed, and a list that has finished stays in the sum until
     they all have: numbers that went backwards as one list dropped out would
     read as a mistake rather than as progress. */
  function warmSaw(p, over) {
    if (!p || !p.what) return;
    var of = +p.of || 0;
    // A PASS THAT STOPPED IS NOT THE SAME AS A PASS THAT FINISHED.  The worker
    // says it has stopped working on a list whether it walked to the end or
    // gave up because the computer went away, and it says how far it really
    // got: taking "stopped" for "done" painted "Ready: its pages are on this
    // phone now" over a list that had hardly been fetched.  What was fetched
    // is kept, and the next ask picks up from it -- so a pass cut off leaves
    // the count where it stopped and waits, rather than claiming an end.
    var got = over && p.done !== undefined ? (+p.done || 0) : (over ? of : (+p.done || 0));
    var whole = !!over && got >= of;
    warmRuns[p.what] = {done: got, of: of, over: !!over, whole: whole};
    // AND IT MAY BE ASKED FOR AGAIN.  A list is asked once per page because a
    // second ask would buy nothing -- but that holds only for a list that was
    // WALKED.  One cut off by the computer going away has addresses still to
    // fetch, so the asking is opened again here and the next ping that finds
    // the computer sends it, which is how the rest arrives without anybody
    // reloading anything.
    if (over && !whole) { warmAsked[p.what] = false; warmWant.push(p.what); }
    warmPaint();
  }
  /* THE LINE, in Parseh's voice: it is the app telling somebody it is not
     quite ready yet, not a bar filling up.  Hidden until something is
     actually warming, so a page that asked for nothing carries an empty slot
     and shows nothing at all. */
  function warmPaint() {
    var slots = document.querySelectorAll('[data-parseh-warm]');
    if (!slots.length) return;
    var done = 0, of = 0, any = false, running = false, whole = true, k;
    for (k in warmRuns) {
      if (!Object.prototype.hasOwnProperty.call(warmRuns, k)) continue;
      any = true;
      done += warmRuns[k].done;
      of += warmRuns[k].of;
      if (!warmRuns[k].over) running = true;
      else if (!warmRuns[k].whole) whole = false;
    }
    for (var i = 0; i < slots.length; i++) {
      var s = slots[i];
      // WHO WAITED FOR IT SEES IT FINISH.  The install page asks somebody to
      // stay while the app gets ready, so a line that vanished at the very
      // moment it was ready would answer the waiting with nothing: there the
      // slot says `stay`, and the line turns into the word that ends it.
      // Everywhere else -- the hub above all, which is opened a dozen times a
      // day on a phone that has been ready for a week -- it goes when there
      // is nothing left to say.
      var stay = s.getAttribute('data-parseh-warm') === 'stay';
      s.hidden = !any || (!running && !stay);
      s.classList.toggle('kp-ready', any && !running && whole);
      s.textContent = !any ? ''
        : running ? 'Getting ready — ' + done + ' of ' + of
        : whole ? 'Ready: its pages are on this phone now, and open with the computer away.'
        : 'Stopped at ' + done + ' of ' + of + ' — the computer could not be reached. ' +
          'It carries on by itself the next time it can.';
    }
  }

  /* ---- what the clock makes wrong, while the computer is away ---- */
  /* What is due was worked out on the computer the last time it was reached;
     a day later it is a number nobody should act on, while the list beside it
     is still true.  A page marks its own with `data-clock-count` (decks.js
     does); the hub's counts say WHAT they count (serve.py's count_tag writes
     data-count-kind), so the one the clock moves is named rather than found
     by the words in it. */
  function markClock() {
    var due = document.querySelectorAll('.hub-mobile [data-count-kind="due"]');
    for (var i = 0; i < due.length; i++) due[i].setAttribute('data-clock-count', '');
  }
  function showClock(hide) {
    var all = document.querySelectorAll('[data-clock-count]');
    for (var i = 0; i < all.length; i++) {
      var e = all[i];
      if (hide) {
        if (e.style.display === 'none') continue;
        e.setAttribute('data-clock-was', e.style.display);
        e.style.display = 'none';
      } else if (e.style.display === 'none') {
        e.style.display = e.getAttribute('data-clock-was') || '';
      }
    }
  }

  /* ---- a card whose thing is not on this phone ---- */
  /* Offline, a shelf still shows everything the computer had when it was last
     reached.  Tapping one that is not kept would go nowhere, so it is drawn
     and cannot be tapped, with a line saying why -- which is exactly what a
     book whose reader was never built has always looked like. */
  var THINGS = [
    /^\/books\/(?:[^\/]+\/){1,2}reader\/$/,
    /^\/youtube\/v\/[^\/]+\/$/,
    /^\/exercises\/deck\/[a-z]+\/[a-z0-9][a-z0-9-]*\/$/,
    /^\/studio\/doc\/[a-z0-9-]+$/
  ];
  var marking = false;
  function thingOf(href) {
    if (!href) return '';
    var u;
    try { u = new URL(href, location.href); } catch (e) { return ''; }
    if (u.origin !== location.origin) return '';
    var path = u.pathname.replace(/index\.html$/, '');
    for (var i = 0; i < THINGS.length; i++) if (THINGS[i].test(path)) return path;
    return '';
  }
  function cardOf(a) {
    return (a.closest && a.closest('.m-book, .dk-card, .card')) || a;
  }
  function offPhone(card) {
    if (card.classList.contains('kp-away')) return;
    card.classList.add('kp-away');
    if (card.classList.contains('m-book')) card.classList.add('m-off');
    var links = card.tagName === 'A' ? [card]
              : Array.prototype.slice.call(card.querySelectorAll('a[href]'));
    links.forEach(function (a) {
      if (!a.getAttribute('href')) return;
      a.setAttribute('data-kp-href', a.getAttribute('href'));
      a.removeAttribute('href');
      a.setAttribute('aria-disabled', 'true');
    });
    var note = el('div', card.classList.contains('m-book') ? 'm-bnote kp-note' : 'kp-note',
                  'Not on this phone: it opens again when the computer can be reached. Keep it ' +
                  'on the phone from its own page while you are there, and it works anywhere.');
    card.appendChild(note);
  }
  function onPhone(card) {
    if (!card.classList.contains('kp-away')) return;
    card.classList.remove('kp-away', 'm-off');
    var back = card.tagName === 'A' ? [card]
             : Array.prototype.slice.call(card.querySelectorAll('[data-kp-href]'));
    back.forEach(function (a) {
      if (!a.getAttribute('data-kp-href')) return;
      a.setAttribute('href', a.getAttribute('data-kp-href'));
      a.removeAttribute('data-kp-href');
      a.removeAttribute('aria-disabled');
    });
    var note = card.querySelector('.kp-note');
    if (note) note.remove();
  }
  function notOnPhone() {
    if (marking) return;
    marking = true;
    try {
      var have = reg(), links = document.querySelectorAll('a[href], a[data-kp-href]');
      for (var i = 0; i < links.length; i++) {
        var a = links[i];
        var id = thingOf(a.getAttribute('href') || a.getAttribute('data-kp-href'));
        if (!id) continue;
        var card = cardOf(a);
        // a book still coming onto this phone (Kept on this phone draws it)
        // is on its way, and is not "not on this phone"
        if (card.hasAttribute && card.hasAttribute('data-kp-coming')) { onPhone(card); continue; }
        if (!away || have[id]) onPhone(card);
        else offPhone(card);
      }
    } finally { marking = false; }
  }
  // what a page must be told again whenever its list changes: which cards
  // cannot be tapped, and which numbers the clock has made wrong
  function refresh() {
    markClock();
    showClock(away);
    notOnPhone();
    // the hub's own slot sits beside a block the fresh shell replaces, and a
    // page that filled itself in has to be told what the line said
    warmPaint();
  }
  // the two library pages and the deck page paint from the computer's answer,
  // which arrives after this script has run, and paint again on every reload:
  // their lists are watched rather than read once
  var watching = null;
  function watchLists() {
    if (!window.MutationObserver) return;
    // one observer, moved to whatever is on the page now: a shelf swapped for
    // the computer's fresh one is a new node, and the old one is watched no
    // longer rather than for ever
    if (watching) watching.disconnect();
    else watching = new MutationObserver(function () { refresh(); });
    ['#deck-cards', '#cards', '#deck-counts', '.m-shelf'].forEach(function (sel) {
      var box = document.querySelector(sel);
      if (box) watching.observe(box, {childList: true, subtree: true});
    });
  }

  /* ---- a shell page, filled in when the computer's answer lands ---- */
  /* The way in is kept by the worker, so the hub and the shelves open at once
     from the phone's copy -- which is as old as the last time the computer was
     reached.  The worker reads the page again behind us and says when what
     came back differs; the list block is then replaced in place, so a shelf
     is never yesterday's with no way to notice.  The blocks are the ones a
     shell page is built round: the shelf a page marks as the computer's
     (`data-shell-block`), or the hub's doors, which serve.py writes.  A list
     the PHONE fills in -- /m/kept/ -- carries no mark and is never swapped:
     the computer knows nothing about it. */
  var BLOCKS = '[data-shell-block], .m-doors, .m-more-doors';
  function fillIn(url) {
    var u;
    try { u = new URL(url, location.href); } catch (e) { return; }
    if (u.pathname !== location.pathname) return;
    fetch(location.href, {credentials: 'same-origin'}).then(function (r) {
      return r.ok ? r.text() : null;
    }).then(function (html) {
      if (!html) return;
      var fresh = new DOMParser().parseFromString(html, 'text/html');
      var here = document.querySelectorAll(BLOCKS), there = fresh.querySelectorAll(BLOCKS);
      if (!here.length || here.length !== there.length) return;
      for (var i = 0; i < here.length; i++)
        here[i].replaceWith(document.importNode(there[i], true));
      // what a page draws on top of its own list -- how far a book was read --
      // is drawn again on the block that has just arrived
      document.dispatchEvent(new CustomEvent('parseh:shell-filled'));
      refresh();
      watchLists();
    }).catch(function () { /* it stays as it opened: no worse than before */ });
  }

  function start_() {
    /* THE STATE THE LAST PAGE WAS IN, BEFORE ANYTHING IS DRAWN (the owner's
       5).  It goes first because everything this function builds is drawn
       from it: the button that says it needs the computer, the cards that
       cannot be tapped, the counts the clock has made wrong.  `probed` stays
       false -- this is a memory and not an answer, and nothing that waits for
       the computer to be KNOWN to be there (the warming) may go on it. */
    var was = recall();
    if (was) away = was.away;
    at = thing();
    if (at && mobile()) build();
    /* A BOOK KEPT IN THE BACKGROUND (the owner, 2026-09-23): what ended while
       no page was open is written down now, its line said once at the foot,
       and a keep of this very thing still coming is taken up where it is.
       Nothing here asks the computer anything, so it runs away or not. */
    bgLook().then(bgMerge).then(function () { return mobile() ? bgResume() : null; });
    var p = P();
    if (p && p.mode && p.mode.onChange)
      p.mode.onChange(function (m) {
        if (m !== 'mobile') return;
        if (at) { build(); look(); }
        // the mode was switched while this page was open -- in another tab,
        // or by the toggle in the bar -- and it is an app page now
        warm('way-in');
        if (STUDIO_PAGE.test(location.pathname)) warm('studio');
      });
    if (navigator.serviceWorker) {
      navigator.serviceWorker.addEventListener('message', function (e) {
        var d = e.data || {};
        if (d.shellFresh) fillIn(d.shellFresh);
        if (d.warming) warmSaw(d.warming, false);
        if (d.warmed) warmSaw(d.warmed, true);
      });
      // a worker that has just claimed this page is the first one there is
      // anything to ask: the ask made before it was waiting for this
      navigator.serviceWorker.addEventListener('controllerchange', warmSend);
      // AND IT IS ASKED AGAIN WHETHER IT CAN KEEP A BOOK IN THE BACKGROUND.
      // On the first load after an install the page looked before any worker
      // was active, found none, and would have kept that answer for as long
      // as it was open -- sending a book the worker's way on the one phone
      // that had the better one (driven: a fresh phone's first keep went the
      // old way until this).
      navigator.serviceWorker.addEventListener('controllerchange', function () {
        bgAsked = null;
        bgLook();
      });
    }
    /* THE TWO ASKS.  The way in on every app page, and the studio's faces
       only where they are wanted.  Both are queued here and sent by the first
       ping that finds the computer (chipPaint), so neither is ever made while
       it is away.  A NOTE is the third place the studio's face is wanted, and
       a note is opened by clicking its mark: the mark's own handler stops the
       click going any further (lib/tex2html.py, youtube/lib/player.js), so
       this listens on the way DOWN, where nothing can stop it. */
    /* THE PAGE COMES FIRST, ALWAYS.  Asked the moment this script ran, the
       warming put a megabyte and a half of background fetching alongside
       whatever the page was still loading -- and on a phone over a tunnel
       that is bandwidth the page needed: a video's own YouTube player lost
       the race and the page said the video needed an internet connection
       while the phone was online (the owner, 2026-09-23).  So the app gets
       ready only once the page has finished loading AND the browser says it
       is idle: the app has all the time in the world, and the thing being
       read has none. */
    whenIdle(function () {
      warm('way-in');
      if (STUDIO_PAGE.test(location.pathname)) warm('studio');
      // and while it is idle it also puts its own note straight: what the
      // registry says is kept, and what the caches really hold
      if (mobile()) reconcile();
      /* AND THE OUT-OF-DATE QUESTION WAITS HERE TOO.  It went on a bare
         `setTimeout(look, 1500)` from the moment this script ran, which on a
         kept book, video or deck put a door that renders every note beside
         the book (serve.py, notes_to_keep) into the middle of a page that was
         still loading -- the very race the warming was taken off the loading
         path to end, and on the same phones over the same tunnels.  Nothing
         about "what is kept here is older than the computer's" is urgent: it
         ends in a bar with a button in it, and the bar is as good a minute
         later.  So it goes where the warming went, behind the load event and
         the first idle moment, and the page it belongs to comes first. */
      if (at && mobile()) look();
    });
    document.addEventListener('click', function (e) {
      if (e.target && e.target.closest && e.target.closest('[data-note]')) warm('studio');
    }, true);
    warmPaint();
    watchLists();
    // and the page is drawn in the state the last one was in, a moment before
    // the probe is asked whether it is still true
    if (was) paintAway();
    ping();
    setInterval(ping, 20000);
    window.addEventListener('online', ping);
    window.addEventListener('offline', function () { verdict(true); });
  }

  // `warm` is out here for the pages this script does not itself touch: the
  // studio's own scripts, and anything else that knows it is about to want a
  // face.  Asking twice is free -- the second ask is dropped here and a
  // third would be skipped address by address in the worker -- so a page may
  // ask whenever it becomes true rather than working out whether it already has.
  /* AND THE TERMS THE AWAY MEMORY IS WRITTEN ON GO OUT WITH IT.  The studio's
     own scripts read `parseh_away` for themselves -- a deck page decides from
     it whether to ask the computer at all -- and they were holding a second
     copy of both the name and the age, which drifted: five minutes there
     against three here.  A copy of a constant is a constant that will be
     wrong one day, so the writer publishes its own, and `recall` is here for
     whoever would rather have the answer than the arithmetic.  A page with no
     lib/keep.js on it finds nothing here, and that is the right answer too:
     nothing is writing the memory either, so what is in it belongs to some
     earlier page and asking the computer is the honest thing to do. */
  window.ParsehKeep = {reg: reg, big: big, tell: tell, made: made, ping: ping,
                       // keeps coming that this page is not following yet:
                       // Kept on this phone asks when it draws one
                       follow: function () { return bgLook().then(bgMerge); },
                       warm: warm, away: function () { return away; },
                       awayKey: AWAY, trusted: TRUSTED, recall: recall};
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start_);
  else start_();
})();
