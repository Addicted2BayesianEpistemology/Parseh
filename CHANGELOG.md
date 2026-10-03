## [a0.4.3] - unreleased
### Added
- Browser transcription workspace with video beside the transcript, word/caption replay, ±1/2/5-second playback controls, caption filters and a persistent word editor
- Brief word playback with automatic pause, installed-dictionary suspect flags and original/replacement meanings in browser transcript review
- Dictionary meanings for native Whisper alternatives alongside their recognition scores in the word inspector
- Native faster-whisper beam alternatives mapped to source words, with sequence log scores kept separate from word probabilities
- Browser Settings → LLM Integration: a reusable OpenAI-compatible endpoint, host-local credentials, model discovery and Unsloth run-settings link import
- Review-first Whisper results with short sentence LLM replies, word-count progress, local failure recovery, retry of unresolved words, keyboard edits and inspectable responses
- Remote installed-model profiles from Studio links, with explicit API loading of quantization, KV cache, context and vision options
- Separate models, prompts and downloadable skills for suspect-word and whole-text review, including confident words and contiguous ASR spans
- Individual pending draft decisions and explicit Use this transcript preserve the existing box and timing guards
- Optional, local exact word times for every speech-to-text language, with hash-pinned int8 CTC networks and a remembered add-page switch
- A Parseh-made transcript carries its word timing through the add-page editor and stores it with the matching video
- Two transcript tidy cues: the existing text cues and recorded pauses
- Mobile-mode keyboard arrows skip narration or video by the selected amount
- Partial-word foreground colours in Studio, with selection-first editing, Unicode-safe boundaries, one-word linguistic clouds, PDF and standalone-HTML output

### Changed
- Markdown and exercise-deck cards made from books or videos mark target and context fields as the target language automatically
- Studio and exported word clouds are linguistic only; foreground colour is applied from the source editor

### Fixed
- Partial-word colours compile and remain visible in PDFs, including headings, target-language blocks and exercise prompts

## [a0.4.2] - 2026-09-30
### Added
- Glosses an LLM writes are aligned to their chunks: a meaning says what its own words say, in the text's order
- Every prompt is assembled by one kit from its instructions, its answer contract and its data, and opens with a version line
- The LLM row: one control for every prompt, saying its size before the copy, on the studio, the exercise dialog, the add page, the tidy, the player, the reader and Ask LLM
- A video's vocabulary in the books' entries, asked of the chatbots and drawn as in the reader, with macro buttons that say what they write
- A book made by an agent in place, watched from the library, steered through asks, finished with one button

## [a0.4.1] - 2026-09-29
### Added
- Speech to text, optional and local: a transcript made on this computer while adding a video, from a film on this machine or a YouTube video recorded through the tab
- Settings → Speech to text: the program, two Whisper models and the processor, open to any device let in
- The graphics card is used only once Parseh has proved it works; the CPU always does
- A YouTube video recorded for its transcript keeps that recording's waveform when it is added
- Hover ⏸ in a book's reader, in both interfaces: the narration waits while a gloss is open
- Edit times by ear in a book's header, and a video's timings, open where the listener is

### Changed
- An update, and going back, leave the speech program and its models as they are (stt/)
- Typing in the transcript, the address or the film's path makes a prepared LLM prompt stale
- The offline page's Try again says that it tried, and Go back is a button of its own

### Fixed
- A page not kept on the device opens from a computer that is only slow, instead of "Parseh cannot be reached"
- Stopping the tab share after a waveform was drawn no longer pauses the video or resets its speed
- The transcript editor saves the draft as it hands the transcript back

## [a0.4.0] - 2026-09-28
### Added
- LaTeX drawings: a ::::latex block, or [...]{latex} inline, compiled by LaTeX itself, beside the formulas MathJax draws
- The same drawing on screen, in the PDF, in an HTML export and on a phone; a live preview kept only once it is saved
- A drawing that cannot be made shows its source and one line saying why, with the button that mends it
- The sheet that draws a block: its preview filling its pane beside the source, a caption, size and position folded away
- Settings → LaTeX drawings, styled like the rest of Settings: named themes of packages, languages, a font, a preamble and a compiler
- Themes exported and imported as files; a rename rewrites every block that names the theme
- A theme's packages beyond the base kept in Parseh's own folder, listed with the base, asked about and gotten one at a time
- More packages to pick from: syntax trees and dependency arcs, the IPA, pinyin over Chinese characters
- A deck's exercises filtered by where they came from, beside its text and tag filters
- Flashcards that are asked both ways: both (random) and both (repeat), the second two linked cards in a deck
- The transliteration cloud works on an exported page and on the guide's own words
- On a phone's video, the subtitles have a text size of their own, reached in full-screen too

### Changed
- Every Settings page starts with the bar of its doors, Network included
- Deleting a document asks in the studio's own window, and the card leaves the list at once
- Documents, decks, bundles and shelves are stored in a new shape: going back to a0.3.3 says so first
- The size sliders of books and videos reach further, at both ends

### Fixed
- Exporting a page to HTML from another device could land on "Parseh cannot be reached": it shows a bar now

## [a0.3.3] - 2026-09-25
### Added
- Estimate the next N seconds, beside estimate the rest

## [a0.3.2] - 2026-09-25
### Added
- Estimate the rest by the sound: boundaries placed in the pauses of the waveform, in books and videos
- Update Parseh from Settings, from GitHub or a zip, to any version, keeping your content and settings
- Releases on GitHub, one zip per version; Parseh shows its version on the hub and in Settings
- Downloads show their size, progress and time left, can be stopped, and resume where they stopped
- On a phone, the dictionary opens in a sheet, and sparsely glossed books and videos mark their glossed chunks

### Changed
- Dictionaries and the other downloads moved to Settings → Reading help, laid out by language
- "Offline" only when the computer is really gone, with ↻ to check again
- Who may change a setting is decided per setting: Network and updates on the computer only
- Languages you add are kept in config/
- Exported pages open on sepia

### Fixed
- Pages of other websites could make Parseh change things
- A phone could read the Wi-Fi pairing code
- The test suites wrote into config/

## [a0.3.1] - 2026-09-24
### Changed
- Fill in the blanks and matching: a click opens the word cloud in the browser too
- Flashcards in the PDF are cards to cut out and fold
- Answering an exercise no longer copies the word to the clipboard

### Added
- On a phone, a video on the whole screen can show the captions around the one being said
- On a phone, a dictionary button in the gloss cloud

### Fixed
- A framing caption drawn dark on dark over a video on the whole screen

## [a0.3.0] - 2026-09-23
### Added
- Videos and Markdown for mobile
- Settings, with Network: who may reach Parseh, the port, your own certificate
- A phone on the Wi-Fi is let in once with a pairing code
- Notes open at once, and the reader fetches the ones near you ahead
- On Android, a kept book downloads in the background, its text first
- What is kept on a phone is checked file by file
- A kept deck brings its exercises, pictures and recordings
- Delete a gloss, with undo
- Gloss a stretch with an LLM, in books and videos
- HTML export of markdown and crammed decks

### Removed
- The "draft" flag of books and videos

## [a0.2.0] - 2026-09-22
### Added
- PWA mobile version
- Book and Exercises for mobile
- Cram mode shows which exercises were more difficult at the end of a session
