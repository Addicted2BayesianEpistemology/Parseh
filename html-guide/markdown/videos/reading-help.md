---
title: Reading help in the player
linkTitle: Reading help
weight: 3
description: The dictionary under a phrase nobody glossed, the definitions, the readings of Japanese and Chinese, and Decompose Kanji.
---

A phrase somebody glossed has everything a reader needs in its cloud. This
page is about the rest: the phrase **nobody has glossed yet** — a video
started empty, a caption the model skipped — and the extra help Japanese
and Chinese get with their readings.

## What can help, and where it comes from

Three things can speak for a phrase with no vocabulary line, and each is a
separate download on the dictionaries page, `/lookup/` (the **reading
help** link in the player's bar goes there):

- **a dictionary** of the video's language, which looks the words up;
- **a corpus** of sentences somebody translated, which shows real sentences
  holding the same words;
- **a translation model** from the video's language into the language its
  glosses are written in, which reads the whole caption.

None of them is a gloss, and the player never pretends otherwise: every
block is ruled off, tinted, labelled *not a gloss*, and signed with its
source and its licence. A dictionary lists every sense a word can carry and
cannot say which one is meant here — which is exactly the judgement a
written vocabulary line is. Nothing any of them says is ever written into
the video by itself; the [editor's sources](editing-a-phrase.md#the-sources-beside-the-fields)
are where you choose what goes in.

## The dictionary button

The **dictionary** button appears in the bar only once at least one of the
three is there for this video — a dictionary of its language, or a corpus
or a model for its language and its gloss language; a toolbox with none of
them shows a player exactly as it always was. It starts off, and it is
remembered.

With it on, the cloud of a phrase that has **no vocabulary line** gets a
panel under what it already says. (A written phrase looks exactly as it
did: the help is for the phrases nobody has written.) The panel holds up to
three blocks, each only if it has something to show:

**dictionary — not a gloss.** Each word of the phrase, as the caption
spells it, with the dictionary's entries: the headword, its part of
speech, its first senses. A verb shows its forms, and an arrow when the
entry is filed under another word — a German separated verb put back
together, *stehen → aufstehen*. A word the dictionary does not have says
what it tried (*not found (tried …)*), and a word found by another road
says which (*found …*): so you can tell “not in the dictionary” from “the
dictionary was never asked”. The source and its licence close the block.

**a machine's reading of the caption — not a gloss.** The model translates
the **whole caption** holding the phrase, never the phrase alone — a
fragment translated on its own comes back as a fragment, and the caption
comes back as sense. The words of the translation that seem to be this
phrase's are marked inside it, and a line under it says how sure that
guess is (*this phrase is likely: …*, or *part of this phrase is likely:
…*). The guess is made from what the dictionary says the phrase's words
mean, never from where the phrase sits in its caption. When the phrase is
the whole caption the heading is simply *a machine's reading — not a
gloss*.

**a sentence somebody translated — not this one.** Sentences from the
corpus that share words with the phrase, each with its translation and the
words it shares; **Load more** fetches more of them.

When none of the three has anything, the panel says so — *the dictionary
has nothing for these words*, or *nothing here has anything to say about
this phrase* — and while it waits it says *looking it up…*.

### Nothing set up yet

A cloud opened on a blank phrase says *nothing glossed yet*. If none of the
three is on this machine, it also says what could help — *A dictionary can
look these words up, a corpus can show a sentence somebody translated, and
a model can read the line* — with a link to set any of them up. That is the
moment you want to know the feature exists, so that is where it is said.

### Prepared before you ask

With the **dictionary** button on, the player looks ahead of the spoken
line: the unglossed phrases of the next ten captions are looked up, and
those captions translated, in the background, a little at a time, so that
the panel opens already filled. It holds off whenever you are doing
something — a click, a key, a scroll — and goes on after a moment's quiet.
Every lookup and every translation is done on this machine; nothing leaves
it.

## Definitions

Every dictionary here is the English Wiktionary's. For most languages that
means its senses are written in English. For **English itself** they are
**definitions written in the language being learned** — which are worth
reading, and which a learner may not want on every phrase. So they wait
behind a switch of their own:

- **definitions** shows the dictionary's own definitions under each word it
  finds — the first three, and a button (**2 more definitions**, say) for
  the rest. It is greyed out while **dictionary** is off.
- **in italian** (or whatever the gloss language is) puts each definition
  into the gloss language under it, with the translation model on this
  machine: a machine's reading, not a gloss. It is shown only when there is
  a model, and greyed out while **definitions** is off.

Both buttons exist only where the dictionary defines its words in their own
language. Until you have touched the first, a panel that could show
definitions says so once: *the dictionary explains these words in English:
“definitions”, in the header, shows what it says.*

## Japanese and Chinese: the reading over the words

Japanese and Chinese write no spaces, so each phrase can carry its
**words** — `今日(きょう) は 天気(てんき) が`, each word with its reading —
and the player sets that reading over each word: furigana for Japanese,
pinyin for Chinese. A Japanese phrase without its words still gets its
kana spread over its kanji, as far as the kana can be matched to them.

The cloud of such a phrase carries a button per word, or per kanji:
**天気: I know this**. Press it and that word's reading is hidden wherever
it appears in this video; the button then reads **天気: show reading**.
A word also counts as known once every kanji in it is. The choice is kept
in this browser, for this video.

**kana** (Japanese) or **pinyin** (Chinese), in the bar, turns the whole
transcript into its reading alone — each phrase as it is said, at the size
of the text — which is the way to listen and read along without the
characters. The clouds still open over it, with the text itself at their
top. It is remembered, and it does nothing to a video of another language.

The **Aa** panel has three more sliders for these two languages —
character spacing, and for Japanese the reading's contrast and its size
against the kanji ([The player](the-player.md#aa-text-and-margins)).

## Decomposing a character

A Japanese video has **Decompose Kanji** at the end of the bar, a Chinese
one **Decompose Hanzi**. Press it and the page says *Choose a kanji in the
text.*, with a **Done** button: every character of the transcript becomes
a button. Click one (or Tab to it and press Enter) and a window opens with
its **components** — the tree of parts it is built from, each part with its
meaning where the installed dictionary has one and the way the parts are
put together (*Left and right*, *Top and bottom*…). Click a part to explore
it in turn; **← Back** and **Return to 語** walk back up. The sources and
their licences are named at the foot.

Opening a character pauses the video, and turning the mode on closes any
open cloud. **Done**, the button again, or Esc leaves the mode.

The components come from a **component pack**, downloaded once from the
dictionaries page and read offline afterwards. Without one, the window
says *Install character components* and links to the setup page.
