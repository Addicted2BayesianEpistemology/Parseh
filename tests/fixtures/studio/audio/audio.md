---
title: Recordings
subtitle: audio lines and a flashcard made of blocks — صدا
note: a test document for recordings on the page, in a box, clipped, and on flashcards
lang: en
target: fa
---

## Recordings on the page

A recording on its own line, laid out like a picture:

![The greeting سلام, spoken](audio/greeting.mp3)

The same file clipped to a stretch, centred and narrower:

![Only the second half](audio/greeting.mp3){width=50 align=center offset=0 start=0.5 end=1.25}

> A box can hold one too, beside its text[^box]:
>
> ![In a box, from a quarter of a second](audio/greeting.mp3){width=70 align=left offset=5 start=0:00.25}

[^box]: A note inside the box that holds a recording.

A picture follows, so the layout numbering runs across both kinds:

![A small test picture](images/swatch.png){width=30 align=center offset=0}

## A card made of blocks

:::exercise flashcard
prompt: Say the word, then turn the card.
card-type: jolly
front-primary: |
  ### سلام
  ![](audio/greeting.mp3){width=80 align=center offset=0}
front-secondary: salâm
back-primary: |
  **hello**, the everyday greeting.

  | Persian | English |
  |---|---|
  | سلام | hello |
  | خداحافظ | goodbye |

  - said on arriving
  - answered with سلام too
    - or with علیک سلام
back-secondary: |
  > A box on the card, with a note[^card].

  ![A small test picture](images/swatch.png){width=40 align=center offset=0}

  [^card]: A note written inside the card.
:::

A vocabulary card with a recording on each side:

:::exercise flashcard
card-type: vocab
target: خداحافظ
transliteration: xodâhâfez
meaning: goodbye
front-audio: audio/greeting.mp3
back-audio: audio/greeting.mp3
:::

A last recording after the cards keeps its place in the numbering:

![After the cards](audio/greeting.mp3){width=60 align=right offset=0 end=1}
