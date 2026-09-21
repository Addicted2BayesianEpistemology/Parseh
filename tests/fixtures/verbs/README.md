# Verb-entry cases, one file per language

`<code>.json` holds eight cases for `lib/verbs/<code>.py`, the recipe that
turns a dictionary hit into a `\vb`.  `tests/smoke.py --only verbs` reads them
and needs no dictionary installed: each case is built into a dictionary of
its own, one entry and nothing else, and run.

## Where the rows come from

Every entry and form row here is Wiktionary's, through the kaikki.org
extracts (Tatu Ylönen's wiktextract), as `lib/getdict.py` stores them in
`dict/<code>.db`.  Wiktionary's text is licensed CC BY-SA 4.0, and so is this
excerpt of it.

The rows are **trimmed conjugation facts for tests**, not a dictionary: only
the entry itself and the form rows its recipe reads (its stems, participles,
auxiliaries, the chunk word's own row, and the rows it has to refuse), in the
order the source wrote them.  The recipe agents cut them from the
dictionaries built on 2026-09-10 and checked that the one-entry dictionary
gives the same `\vb` as the whole one did.

## A case

    entry     the entry row: headword translit ipa reading pos sense
              sense_tags head
    forms     its form rows, [form, note, roman] or [form, note, roman, ipa],
              inserted in this order (rowids ascending: getdict writes an
              entry's own rows as one run, and recipes rely on that)
    word      the word as the chunk has it
    text      the chunk
    gloss     what the book is glossed in
    run       "lookup": lookup.look_up(code, text) then verbs.attach, and the
              vb is the one on the hit of `word` for this entry -- which the
              word must reach; "build": verbs.build(code, {entry, headword,
              pos}, word, text, gloss), for a case whose word the lookup does
              not reach through the rows kept
    expect    the fields of hit["vb"] that must come out, or null (fa writes
              {"tex": null, ...}) where the hit must carry no vb at all
    why/what  what the case is there to show

`expect` was written by each language's recipe agent and then brought up to
date with the core in three places, each checked to be only that change: an
Arabic video line is written without its harakat (`vb_video_bare`), a slash
between two words has no spaces round it (`aux. avere/essere`), and a
Japanese video line carries the kana after its headword.
