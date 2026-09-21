---
title: When something looks wrong
linkTitle: Troubleshooting
weight: 1
description: The messages the pages show, what each one means, and what to do about it — from starting Parseh to studying a deck.
---

Parseh says what went wrong in words, on the page where it happened: in a
note under a greyed-out button, in a message at the foot of the window, in
a badge beside a build, in a dialog. The tables below quote those words as
the pages show them, so you can find yours with the guide's search box or
your browser's find-in-page, and say what each one means and what to do
next. A message in *italics* is what a page says, one in `code` what a
terminal prints; a label in **bold** is a button or a link.

When a message is not here, read it twice: most of them name the file,
the rule or the button they are about.

## Starting Parseh and installing it

| What you see | What it means, and what to do |
|---|---|
| The browser says the connection is not private, or the certificate is not trusted. | Expected, once per browser. Parseh makes its own certificate the first time it starts, and nobody else vouches for it — it is your server on your network. Choose **Advanced** and go on to the address. If the machine's addresses have changed (a new network, a new Tailscale address) and a device refuses the old certificate, make a fresh one: `./serve.sh cert` (Windows: `serve.bat cert`), then restart. |
| A page will not load at all. | The server is not running, or it runs on another port. On Linux and macOS, `./serve.sh status` says `running: pid …, https port …` or `not running`, and `./serve.sh log` shows its last lines. On Windows the server runs in its own window: that window is the log. Start it again with `./serve.sh`, **Parseh.command** on a Mac, or a double-click on **serve.bat**. |
| *Parseh stopped. Start it again with ./serve.sh in the project directory and reload this page.* (the studio says *Server stopped*) | Somebody pressed a stop button: **⏻ stop** on the hub, ⏻ in the video player, **stop server** in a book's reader, **Stop server** in the studio and the exercises. Nothing is lost. Start Parseh again as above — on Windows with a double-click on **serve.bat** — and reload the page. |
| Stopping asks *1 task is still running* (or *N tasks are*) and lists them. | The server is still doing something you started — a build, an upload, a backup, a download being packed. Stopping now cuts it off. Answer **Cancel**, wait for the **Working…** pill to go, then stop. |
| `./serve.sh` says `already running: pid … on port …` | A server is already up. Use it, or `./serve.sh restart` to replace it (for instance after updating Parseh). |
| `./serve.sh` says `failed to start -- the log says:` and quotes the log. | Usually the port is taken by another program (`Address already in use`). Start on another port — `./serve.sh 9000`, `serve.bat 9000` — or stop the other program. |
| `note: no 'ilya-frank' environment -- serving with …` | Serving works with any Python 3, but rebuilding books, dividing Japanese and Chinese into words and opening a modern Anki export need the packages of the environment. Run the installer once: `./install.sh`, **Parseh.command** on a Mac, **install.bat** on Windows. |
| Screen capture (the frame button on a card) does nothing, or copying to the clipboard fails. | The page is not on a secure address. Browsers only allow both on `https://` pages and on `localhost`. Use one of the `https://` addresses Parseh printed when it started. An old `http://` bookmark on the same port is sent to the `https://` address by itself; a server started with `--http` — or on Windows with no `openssl` to make a certificate, which the setup wizard says — serves plain http, where both work on `localhost` only. |
| The installer ends with `N checks passed, M missing.` | *M* counts the `MISS` lines, and each says what is missing and what it is for. Several matter for one job only: `ffmpeg` snaps a narration's timings to its silences and cuts a card's recording on the server, with its waveform — without it the timings are not snapped and the clip is recorded in the browser instead, as a WAV; `pdftotext` only re-extracts a book's source. Something optional that is simply not there — LuaLaTeX, a dictionary, a parallel corpus, a translation model, a word analyzer — is a `--` line, and is not counted as missing. What serving needs is in the first part of the report, `required to serve the reader`. |
| *The installation did not finish -- the messages above say why.* (**install.bat**; **Parseh.command** and `./install.sh` say *…the lines above say why*) | A step failed on the way, and the lines above it say which and why — often it was only the network, during a download. Mend what they name and double-click **install.bat** (or **Parseh.command**) again. |
| *Parseh needs Python 3, and this computer does not have it.* (**serve.bat**) | Windows found no Python 3.8 or newer. The simplest answer is the one it gives first: close the window and double-click **install.bat**, which brings its own Python with everything else Parseh needs. Or answer **Y** to *Install Python 3.12 now?* and winget installs it; where there is no winget, the download page of python.org opens. |
| *Python was installed but cannot be found from here yet: close this window and double-click serve.bat again.* | Just that: the window was opened before Python was there, and cannot see it. Close it and double-click **serve.bat** again. |
| `python3 does not run here (…).` (`./serve.sh`, usually on a Mac) | The Mac's `python3` is only a stub until Apple's command line tools are installed, and Parseh has no environment of its own yet. Double-click **Parseh.command**: the first time, it installs Parseh's environment, with a Python of its own. |
| `openssl is needed to make the certificate (apt install openssl), or run with --http to serve without TLS` (quoted by `./serve.sh` after `failed to start`) | Parseh makes its certificate with `openssl`, and this machine has none. Install it with the system's package manager, then start again; meanwhile `python3 serve.py --http` serves plain http. **serve.bat** never stops here: without `openssl` it serves plain http by itself, and its wizard offers to install one (**Install OpenSSL with winget now?**). |
| The installer says `no micromamba for …: install Python 3, or conda and then ./install.sh --conda` | There is no ready-made micromamba for this kind of machine. Install Python 3 (or conda) yourself and run the installer again; with conda, `./install.sh --conda` makes the environment with it. |
| `no Noto Serif CJK JP — a Japanese page falls back to another face …` (or the same for Chinese) | You have Japanese or Chinese content, and the font its pages and PDFs are set in is not on the machine. Install the Noto CJK fonts with your system's package manager (the line says how); the pages work meanwhile, a PDF cannot build. |
| `tex: 'ngerman' is in no language.dat, so its books break at ENGLISH points` (or another language) | The hyphenation patterns are installed but TeX cannot see them, so a book in that language would break its words at English points. Run the two commands the line gives, then `./install.sh --pdf` again. |

More in [Installing Parseh](../getting-started/installing.md) and
[Starting and stopping](../getting-started/starting-and-stopping.md).

## The guide

![The guide's front page, served by Parseh before its first compile](shots/guide-not-compiled.png){width=100 align=center}


| What you see | What it means, and what to do |
|---|---|
| The front page says *The guide has not been compiled yet.* | The pages you are reading are Markdown until they are compiled into web pages. When Parseh serves the guide (the hub's **guide** button), the same notice has a **Compile the guide** button: press it, and the new pages open when it is done. Opened from the disk, the guide cannot compile itself: run the installer, which compiles it every time (`./install.sh --guide` compiles only the guide). |
| *The guide was compiled from older pages. Compile it again to see the newest.* | A page of the guide changed since the last compile — after an update, say. Press **Compile the guide again**. |
| *The last compile failed. What it said is below.* or *The compile ended with errors. Opening the pages it wrote…* | The compile wrote every page it could and stopped on an error: each `warning:` or `error:` line below names the page and the line. That is a fault in a page of the guide, not in your content; the other pages work. |
| *The search needs the compiled guide (site/search-index.js), and it is not there yet.* and *The list of pages appears once the guide is compiled.* | The same thing: nothing has been compiled yet. See the first row. |
| **PDF manual** answers *the PDF manual is not in this checkout; the guide is at /guide/* | The file `HOW TO USE THIS TOOLBOX.pdf` is missing from the checkout. These pages are the guide; the PDF is a printable companion to them. |
| `https://<user>.github.io/Parseh/` answers *404* or still shows older pages. | GitHub Pages publishes what is committed on `main`: switch it on once (**Settings → Pages → Source: Deploy from a branch**, branch **main**, folder **/ (root)**, **Save**) and give it a minute or two; a changed page appears after it is compiled and `html-guide/site/` committed and pushed. [Compiling and publishing](../writing-this-guide/compiling.md) has the whole setup. |
| `build.py` says `error: … is not empty and … nothing was touched` and exits with status 2. | A compile replaces its folder whole, so `--out`, `--pages` and `--export` only go into a folder that is new, empty or one they made themselves before; each says it in its own words — `--out`: `does not hold an earlier compile of the guide (no build.json of its own)`; `--pages`: `was not laid out by --pages (no .parseh-guide-pages in it)`; `--export`: `does not hold an exported guide`. Name another folder. |

More in [Compiling and publishing](../writing-this-guide/compiling.md).

## Books

| What you see | What it means, and what to do |
|---|---|
| **PDF behind the text — build it** in the reader's header. | You edited a chunk. The reader was rebuilt with your edit at once; the PDF is LaTeX, and is built only when you ask. Click the notice, or **build PDF**, and follow the build to its end. |
| *…: the build failed — …* after **build PDF**, **build** or **rebuild** on a card. | The message quotes the first error TeX gave (a line starting with `!`), or the line saying what could not run. *no lualatex on this machine: the PDF needs TeX Live (or MiKTeX); building the reader alone* means just that: the reader is built, the PDF needs TeX. `./install.sh --pdf` adds the TeX packages a PDF needs; on Windows, your TeX's own package manager does. |
| The reader refuses an edit: *this text would stop paragraph N reproducing source/paras/…, which verify_book.py checks* | A book's chunks, joined, must still say what the text it was made from says. Adding vowels, harakat or punctuation is free; changing a word is not. If the change is meant — you are correcting the source itself — tick **this paragraph need not reproduce `source/paras/`** in the chunk sheet: the check then stands aside for that paragraph alone. |
| A feature this guide describes is missing from a reader, or the **download** sheet sizes **all of it** as far smaller than it is. | What a reader can do is written into the page when it is built, so a book built before a feature has not got it — and a reader built before the size fix says the size of the first recording only. Press **rebuild the reader** in its header (a few seconds, no LaTeX), or **rebuild** on its card in the library. |
| The library card says **no audio yet** for a book that has a narration. | The book came in from a bundle made with **everything but the recording**, which leaves the recording itself out. Put its `audio/` folder back in the book's own folder, or add the narration again from the reader's **narration** panel. |
| An upload on the **Bring a book back** panel says *that is not a Parseh bundle: it carries no parseh-bundle.json. The download button makes one; a zip of a folder is not one.* | Only a zip made by **download** (or by **Backup every book**) carries the manifest that lets Parseh check it. Unzip, edit, and zip the same folder again with its `parseh-bundle.json` at the top, or download the book afresh. |
| *the bundle is damaged or locked and cannot be read* | The download was cut short, or the zip has a password. Download it again. |
| An upload is refused with *verify_book refused this book*, *the text no longer reproduces its own source paragraphs*, or *… does not parse* | The bundle was checked before anything was written, and one of its chapters breaks a rule: the message quotes the place. Fix it in the files and upload again; nothing on the shelf was touched. |
| An upload answers that the book is already here, with a choice to replace it. | A bundle never overwrites a book by surprise. Replace it, or cancel and keep the one on the shelf. |
| **cut the audio…** is greyed out, with a reason under it. | The reason is the answer: *this book has no narration file to cut the audio from*; *this subparagraph has no times yet: time it (narration, or edit times) and the audio can be cut*; *none of this book's recordings covers … yet*; *… was timed in the recording …, whose file is not on this machine*; *cutting the audio needs this page opened from the toolbox's server*. |
| The cut editor draws no waveform, and the clip comes out as a `.wav`. | The machine serving Parseh has no `ffmpeg`, so the clip is recorded in the browser instead of cut by the server. It still works. Install `ffmpeg` (the installer's report says whether it is there) for the waveform and MP3 clips. |
| The server's console says `!! … declares a narration at …, which is missing` | `book.json` names a recording that is not in the book's `audio/`. Put the file back, or open the reader's **narration** panel, which says the same and lets you add it again. |
| A book taken off the shelf with ✕ is gone from the library. | Nothing was deleted: the whole folder was moved to `books/.trash/`, named after the book and the minute. Move it back into `books/<language>/` and write the library page again: **rebuild** on any book's card does, or `python3 lib/make_index.py`. |

More in [Books](../books/_index.md).

## Videos

| What you see | What it means, and what to do |
|---|---|
| **cut the audio…** is greyed out on a YouTube video: *only Chrome and Edge, on a computer, can record the sound of a tab* (or *this browser cannot read the sound of a shared tab*) | A YouTube video's sound reaches no script, so the clip is recorded from the tab as it plays — which only Chrome and Edge on a computer can do, and not a very old version of them (the second message). Open the video in an up-to-date one. On a phone the button is always grey. A film on this machine has none of this: its clip is cut from the file, in any browser. |
| *recording this tab needs the page opened at the toolbox's https address, in Chrome or Edge* | Open the page at one of the `https://` addresses Parseh printed. |
| *the tab was shared without its sound: press “record” and, when Chrome asks, leave “Also allow tab audio” turned on* | In Chrome's question, the switch that shares the tab's sound was off. Press **record** again and leave it on. |
| *no sound was captured — is the video muted? Turn its sound on and record again* | Nothing but near-silence was recorded between the two ends. Check the video can be heard there, and record again. |
| Saving a phrase in the player is refused: *… chunks do not reproduce the text*, with the text and the chunks under it. | A caption's phrases, joined, must give back the caption word for word, and the caption must say what its line of `transcript.txt` says: that check is what stops a model, or a careless edit, quietly rewriting the video. So adding vowel marks is free, and changing a word is refused. If the change was a slip, undo it. If the transcript itself is wrong — YouTube misheard a name, dropped a particle — tick **this phrase need not reproduce `transcript.txt`** at the foot of the phrase's **✎ edit** form (the refusal scrolls it into view) and save again with the correction: the edit is written, the caption's text follows its phrases, and that caption is no longer checked against the transcript. See [When YouTube heard wrong](../videos/editing-a-phrase.md#when-youtube-heard-wrong). |
| Unticking **this phrase need not reproduce `transcript.txt`** is refused: *segment N: text differs from transcript.txt* | The caption still says something its line of the transcript does not. Put its words back as the transcript has them in the same save as the untick, or leave the box ticked. |
| The video checker warns `N captions not checked against transcript.txt: a chunk of each is marked as departing from it` | Not a fault: it counts the captions freed with the box above, so that none is forgotten. |
| A caption cannot be cut, joined or deleted in the player. | On purpose. The captions are what the checker holds a video's two files to, caption for caption, so once the video is added only a caption's **start** moves (**the timings**, in the player's bar). Its phrases can still be cut and joined — **✂ cut in two**, **join next**, **join previous** in the ✎ form — and its words corrected as above. To re-cut the captions themselves, mend the transcript before adding (**Edit the transcript…** on the add page), or download the video with **⤓** in the player's bar, edit the files, and bring the zip back through **Bring a video back** on the video index. |
| The video checker warns `missing 'tr' -- still a draft` | The checker says so when the video is a draft (`"draft": true` in `video.json`) and a chunk has no transliteration yet. In a draft that is a warning; once the draft flag comes off it is an error. Fill it in from the player. |
| A colour or a gloss you wrote by hand into a video's annotations file has gone. | `merge_parts.py` rebuilt `annotations.json` from `parts/`, which never had it. Edit the parts and merge again, or edit `annotations.json` and stop merging. |
| A video taken off the index with ✕ is gone. | Nothing was deleted: it was moved to the `.trash/` folder under `youtube/videos/`, named after the video and the minute. Move it back into its language's folder beside `.trash/`. |

More in [Videos](../videos/_index.md).

## Cards, clips and Anki

| What you see | What it means, and what to do |
|---|---|
| An edit you made inside Anki is gone. | A rebuilt deck was imported without syncing first: the build writes every card as the store has it. Redo the edit in Anki, then always sync first (**Anki** on the hub, steps 1–4) before you rebuild and import. |
| The sync wizard says *A package built by Parseh … not an export from Anki. It says nothing about what Anki holds, so there is nothing to sync* | You dropped the `.apkg` the build button made, not an export from Anki. It can still be brought in (**Bring this deck in**, **Add the N new cards**), but to sync, export the deck from Anki: **File → Export…**, *Anki Deck Package (.apkg)*. |
| The sync says `that file is not an Anki deck export -- export with File > Export > Anki Deck Package (.apkg)` | The file is not a deck package. Export again from Anki as the message says. |
| *this export is in Anki's modern compressed format, which needs the zstandard package* | The environment lacks one package. Run the installer again (it adds what an environment lacks), or export from Anki again with **Support older Anki versions** ticked. |
| Building a deck refuses: *the note type … in your Anki collection has fields …, but this exporter writes …* | The note type gained or lost a field inside Anki. Building now would fork a second note type and orphan your review history, so it refuses. The exporter has to be taught the new shape first: the card store's own `README.md`, in `youtube/anki/`, says how. |
| **Here, not in Anki yet** in the sync's preview. | Harmless: cards made on these pages since your last import. Anki has never seen them; step 5's import gives them to it. |
| **Images and recordings not in this export** | Export from Anki again with **Include media** ticked, or those pictures and recordings go missing from the cards. |
| A card vanished from a deck here. | Look in the deck's `deleted/` folder, in the card store (`youtube/anki/`, then the language and the deck): a sync that removed cards you deleted inside Anki moves their files there. Move a file back into `cards/` beside it to undo. |
| A card pasted into a document as markdown shows no picture or plays nothing. | Its files wait in the clip tray, and come into a document when it is saved. Save the document. If the clip was deleted from the tray (**The clip tray** on the hub) in the meantime, cut it again. |

More in [The round trip with Anki](../cards-and-anki/round-trip.md)
and [The clip tray](../cards-and-anki/clip-tray.md).

## Reading help: dictionaries, sentences, the translation model

| What you see | What it means, and what to do |
|---|---|
| No **dictionary** switch in a reader's header. | Nothing is installed for that language yet. Open **reading help** in the header (or the hub's **Reading what nobody has glossed**) and press **get it** beside the language. |
| The panel gives dictionary entries but never a sentence. | No parallel corpus is installed for that pair of languages, or nothing in it shares a rare word with your chunk. Coverage is very uneven; a thin pair finds a sentence less often. Get one under **Sentences somebody has already translated** on the reading-help page; Japanese and Chinese need their dictionary first. |
| The panel never shows a machine's reading. | There is no button for it: it is drawn when the panel opens or not at all. Either no model is installed for the pair — models go to and from English only — or the **dictionary** switch is off, which is the switch the reading rides on. |
| *the model could not be run* | The model's files are incomplete, or the page is served by something other than Parseh (which names `.wasm` files as the browser requires). On the reading-help page, **remove** the model and **get it** again. |
| The sources sidebar offers a verb as `\dw`, not `\vb`. | Its language's recipe did not take that hit for a verb it can fill in — a Chinese verb that neither splits nor takes a complement, a word the dictionary lists only as another verb's form — or the dictionary predates the recipes. Press **rebuild** beside the language on the reading-help page. |
| A character chosen after **Decompose Kanji** (or **Decompose Hanzi**) says *Install character components*. | No component pack is installed. **Open dictionary & component setup** leads to **Kanji & Hanzi components** on the reading-help page: **get it** beside KanjiVG (Japanese), Make Me a Hanzi (Chinese) or CJKVI-IDS (both). |
| The tree says *No component decomposition is available for this character.* | The installed packs do not cover it. The fallback pack, CJKVI-IDS, covers the most; **Manage component packs and fallback coverage** leads there. |
| The tree's foot says *Install the Japanese dictionary to show component meanings.* (or Chinese) | The tree works without a dictionary; the meanings of the components come from it. **Open setup** and **get it** beside the language. |

More in [The reading-help page](../lookup-and-languages/reading-help.md).

## Studio

![The name-conflict dialog, with a name that is taken too said under its field](shots/name-in-use.png){width=100 align=center}


| What you see | What it means, and what to do |
|---|---|
| A dialog: *This name is already in use* | A link names a document by its title, so no two documents of one library may share one. The dialog shows each clash with two fields — **Rename the document already in the library** (with **open it ↗** to look at it first) and **Rename the document being saved** (or *added*). Change either or both and press **Use these names**; every link to a renamed document follows it. **Cancel** writes nothing, and the editor keeps your text. It opens on **Save**, **Save & view**, Ctrl+S, a new document's first save, **Paste LLM answer**, **Upload .md / .zip** and **Load from backup**. |
| Under a field: *“X” is already the name of another document — choose another name* | The name you typed is taken too. Type another; the dialog stays open. |
| *A document needs a name — give it one* or *A name cannot hold “\|”: a link to it in a table would split the cell — choose another name* (dialog: *This name cannot be used*) | A name may not be empty, and may not hold a `|`. Give another. |
| A link drawn in red and dashed, whose tooltip says *No document named “X” in this library — create or upload one with this name and this link will work again* | The document it names was deleted, renamed outside Parseh, or not written yet. Links are never removed: make or upload a document with that title, or rename one to it, and the link works again with nothing rewritten. |
| A document's title now ends in a number — *A note 2*, *A note 3* — and you did not rename it. | Names became unique with links by name, and a library written before could hold two documents of one name — a book's notes were all called *A note*. The first time the server met each library after the update (the studio's when it started, a book's or a video's notes when they were first opened), it kept the name for the oldest document and put 2, 3… after the name of each later one, in its header; the server's console said so. Links that named it still find the oldest. Rename it as you like — change its `title:` line in the editor and save — and see [Links written before names](../studio/names-and-links.md#links-written-before-names). |
| An exercise drawn as a box: *Exercise needs attention.* with a list under it. | The list names each problem in the exercise's markdown — a field that is not known, a missing answer, a picture that is not under `images/`. Fix them in the editor; **✎ Edit** on the exercise in the preview reopens its form. Such an exercise has no **+ Deck** button until it is fixed. |
| The build badge says **build failed — see message**. | Point at the badge to read what LaTeX said. *xelatex not found — install TeX Live* means just that. *fonts not provisioned yet* happens only in the first moments after the server starts: wait a moment and build again. |
| *Large print needs the TeX package extsizes (extarticle.cls), which this TeX installation does not have.* | The larger print sizes need one TeX package. On Linux and macOS, `./install.sh --pdf` installs it. On Windows, where that script does not run, add the package `extsizes` with your TeX's own package manager — the **Packages** page of MiKTeX Console, or the TeX Live Manager. Meanwhile build at **Normal · 11 pt**. |
| **source changed — rebuild** beside a PDF. | The markdown changed after the PDF was built — perhaps only because another document was renamed and a link in this one followed it. **Build PDF** again. |
| **built with other options — rebuild** | **PDF options ▾** now says another print size or colour than the PDF was built with. **Build PDF** again to use them. |
| **N RTL FAIL** (or **N text FAIL**), **not verified**, **N overfull** | The PDF was checked against the markdown: the first lists the strings of the target language that did not come out right in the PDF; **not verified** means PyMuPDF, which does the check, is not installed (run the installer); **overfull** counts lines that stick out into the margin. |
| An upload opens a dialog saying *Its header has no …* | A studio document's header needs `title`, `subtitle`, `note`, `lang` and `target`. The dialog asks for exactly the missing ones and adds them; the rest of the file stays as it is. |
| **Load from backup** says *that zip holds no library* (or *that is not a zip file*) | The file is not a library backup: that is what **Backup** writes. A single document's zip goes in through **Upload .md / .zip** instead. |
| A picture or a recording is refused on upload: *only PNG, JPEG, SVG and PDF figures are supported*, *image larger than 15 MB*, *only … recordings are supported* | The studio takes those picture formats, and the recording formats the message lists (MP3, M4A, AAC, Ogg, Opus, WAV, FLAC, WebM). Convert the file and upload again. |
| A starter's picture or chime you deleted shows as missing, and is not copied back. | By design: once deleted, a starter's file stays deleted for that document. Delete the line that names it, or upload a file of your own under that name. |
| The editor writes right to left and you did not ask for it. | The document's `lang:` is a right-to-left language, so the editor opened in that direction. Press **⇥ LTR editor** to switch; the choice is remembered for this document. |

More in [Names and links](../studio/names-and-links.md) and
[Printing to PDF](../studio/pdf.md).

## Exercises

| What you see | What it means, and what to do |
|---|---|
| *this exercise was already answered — showing what comes next* | You answered the same exercise in another tab (or a request was sent twice). It is not scheduled a second time; the page simply moves on. |
| *the document has changed since the page was loaded: reload it, then copy* | The document was saved elsewhere after this page loaded, so **+ Deck** could pick the wrong exercise. Reload the page and copy again. |
| *this exercise is in X, but the deck "Y" is for Z* | A deck has one language. Choose (or make) a deck of the exercise's language. **Move to deck…** says *the destination deck must have the same language* for the same reason. |
| **Import deck…** says *this is not a deck export: parseh-exercise-deck.json is missing* or *the file is not a zip* | **Import deck…** takes the zip a deck's **Export** makes. A zip of every deck, made by **Backup** on the Exercises page, goes back through **Load from backup** beside it. |
| *… is not a recording: only … recordings can be imported*, *the zip is larger than 512 MB uncompressed* | The import checks every file before it writes anything. Remove the offending file from the zip, or export the deck again. |
| An exercise has no **+ Deck** button. | It shows errors (fix them first), or you are in the editor's preview, which has none: open the document's reading view. |
| A flashcard does not play its recording by itself. | Many browsers let a page make no sound until you have clicked on it. Click the card's 🔊 once; from then on the recordings play. |
| **Study now** shows *next exercise in …* or *no exercises scheduled* | Nothing is due. That is the scheduler working: come back then, or use **Cram exercises** on the deck's page, which never changes the schedule. |

More in [Studying](../exercises/studying.md) and [Export, import and
backup](../exercises/export-import-backup.md).

## Working…, and the Browser | Mobile switch

![The Working… pill, opened into its list](shots/working-pill.png){width=70 align=center}


| What you see | What it means, and what to do |
|---|---|
| The **Working:** pill in the corner stays on *Preparing the download…* | The server is packing the zip — a book with its recordings, a whole shelf — before it can send it. The pill goes once the file has been sent; the file itself arrives in your browser's downloads, as always. |
| The pill says **Working:** but nothing seems to happen on the page. | The work may have been started on another page or in another tab: the pill shows everything the server is doing. Click it for the list; **open the page** goes to the page each one was started from. |
| Something was refused, and the pill said nothing. | On purpose: the pill says only what is running. A refusal is said by the page that asked, as a message or a dialog. |
| In **Mobile** mode a door opens the ordinary page. | Only the hub has a mobile version so far; every other door opens its browser page until its own mobile page is written. |
| The hub has no Anki, clip tray, reading help or stop button any more. | The hub is in **Mobile** mode, which leaves out everything that edits or administers. Press **Browser** in its top bar. |

More in [The Working… indicator](../getting-started/working-indicator.md)
and [Browser and Mobile](../getting-started/mobile-mode.md).

