## The errors no tool finds

The tools check that the text is reproduced, that the JSON is well formed and that the macros are legal. They cannot see the errors below. The first three are what a proof-reader reads for, hardest first, and nothing else; the fourth belongs to the book as a whole and is found by sweeps and by reading across batches (**How to check**).

### 1. A word dropped at a chunk seam -- the one that matters

A chunk looks complete and is not: what belongs to it stands at the edge of the next chunk, and the annotator, finishing the chunk in front of them, left it out of the gloss, the vocabulary line and the transliteration. The fidelity check cannot see it, because it compares the text and the text is right. Where it falls depends on the language (**The conventions of {{LANG_NAME}}** say what to look for); some shapes, for the idea:

- a link between a noun and the qualifier that opens the next chunk (the Persian ezafe: the noun's ending changes because of what follows);
- a language that puts what governs last -- the person, tense and negation of a clause live on its final verb, which may stand in the next chunk or the next paragraph, and a chunk before it that glosses a person or a tense of its own is borrowing one from somewhere;
- a case, an ending or a particle left with nothing to attach to: a genitive waiting for what it possesses, a preposition without its noun, a clitic or an auxiliary that belongs to the verb in the neighbouring chunk;
- a connective that joins the two sides of the boundary, glossed as if it joined something else; a converb or participle glossed with the meaning of the clause that follows instead of its own.

How to look: read every chunk together with the first word or two of the next, and a paragraph's last chunk with the first of the paragraph after. Ask of each: does it know the person and tense its verb will give it? is something left hanging? has a connective gone? Assume more remain after any pass: this is the largest class.

### 2. A misparsed idiom

An expression read word by word as if it were not one: a fixed phrase whose meaning is not in its pieces, or a phrase that parses as something else. The dangerous one is the misreading that comes out as fluent {{GLOSS_NAME}} (German's *die Nase voll haben*, "to have one's nose full", is fluent English and wrong: it means to be fed up). How to look: read the chunk as if the idiom were not there and see whether what is left is a sentence; if it is not, or if the words are also a common construction with another meaning, the idiom is the parse.
### 3. Two fields agreeing on the wrong reading

The text and its transliteration agreeing on the wrong sound -- a vowel mark and the transliteration both wrong in the same way: every check that compares them passes, because they agree with each other. Only a reader who knows the word finds it. Its general form is the common one: **two fields of one chunk agreeing on a reading the text does not support** -- a `voc` and an `en` that teach two readings of one word, a note that puts someone in a scene they are not in, a question put to a person who is not there. The annotation is then wrong about the story and not about the grammar, and the cause is always a chunk read in isolation: check what a chunk says against who speaks, who is addressed and who is present, which the paragraph before tells you. Where the language gives a transliteration in few chunks the pure form is rare, and this general form is where the findings are.

### 4. The book disagreeing with itself

Batches are annotated apart from one another, often by helpers that cannot see each other, so this is structural and not accidental: the same word glossed two ways; a headword spelt or capitalised two ways; a verb given two sets of principal parts; a name or construction explained again and again, or never, each side assuming the other did; a convention applied in some chunks and not in others (the speech dash kept in some `en` lines and dropped in others); a verb with no `\vb`. What settles a conflict:

- the book's own transliteration: two spellings of one word printed with the same transliteration cannot both be right;
- but one spelling can be two words, read two ways: refuse a form printed with two different readings and never harmonise two words into one;
- the majority form is sometimes the faulty one: count, then think;
- a change to one field that needs another to move with it (a mark and its transliteration) is made on both, chunk by chunk, and is not a sweep;
- a pass corrects the book where the book contradicts itself and does not settle what the conventions leave open. Where the book says one thing consistently and you would say another, that is a decision and not an error: decide once, write the ruling in `NOTES.md` (Decisions) and apply it everywhere.

A gap is the opposite of a repetition, and no sweep for repetition finds it: a word introduced in no batch because each side assumed the other had. Read the seams between batches, and between helpers' paragraphs, for a word or a name thinned on the strength of a neighbour.
