## [a0.4.0] - unreleased
### Added
- LaTeX drawings: a ::::latex block is compiled by LaTeX itself, beside the formulas MathJax draws
- The same drawing on screen, in the PDF, in an HTML export and on a phone, made once and kept
- A drawing that cannot be made shows its source and one line saying why, with the button that mends it
- Settings → LaTeX drawings: named themes of packages, languages, a font, a preamble and a compiler
- Themes exported and imported as files; a rename rewrites every block that names the theme
- TeX packages got into Parseh's own texmf/, what they cost said first; how long a drawing may take
- The transliteration cloud works on an exported page, changing that open page only

### Changed
- Every Settings page starts with the bar of its doors, Network included
- Documents, decks, bundles and shelves are stored in a new shape: going back to a0.3.2 says so first

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
