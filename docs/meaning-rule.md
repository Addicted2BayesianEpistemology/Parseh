## The meaning (`en`) is a gloss, not a translation

The learner reads the {{LANGUAGE}} phrase by phrase, and under each phrase the
`en` says what THAT phrase says — so that, reading the `en` lines one after
another, the learner can point from each word of them to the {{LANGUAGE}} word
it renders, and see how {{LANGUAGE}} builds its sentence.

1. A chunk's `en` renders that chunk's own words and only those. Nothing in it
   comes from a neighbouring chunk; nothing of the chunk's own is left for a
   neighbour to say.
2. Follow the order of the text. The `en` lines come in the order of the
   chunks, which is the order of the {{LANGUAGE}}: never move a meaning to where
   {{GLOSS_LANGUAGE}} would put it. Read in a row they may not be good
   {{GLOSS_LANGUAGE}}. That is meant: the reader thinks it through.
3. Never translate the sentence first and then divide the translation among the
   chunks. That is the mistake this rule is for. Work chunk by chunk, from its
   words, in order.
4. Inside a chunk, write natural {{GLOSS_LANGUAGE}}: every word of it is the
   chunk's own. A fixed expression is one chunk: give its plain meaning. A word
   that means nothing by itself in {{GLOSS_LANGUAGE}} (a particle, a case
   marker, the object marker) and a word {{GLOSS_LANGUAGE}} needs that the text
   lacks (an article) are left to `voc`; a short bracket such as "(obj.)" goes
   in `en` only where the learner would otherwise be lost.
5. Lower case, except names and "I"; a comma or a stop only where the text has
   one on this chunk.{{?video}} A sentence running on into the next caption ends with
   `…`, and the next caption's first chunk picks it up.{{/video}} In a text read in
   another order than written, "the order of the text" is the order it is read.
6. `en` and `voc` agree: what `voc` says a word of the chunk means is what `en`
   says, in the same words where the grammar allows.

Before you answer, cover the {{LANGUAGE}} and read one sentence's `en` lines in
a row. If they read like a fluent translation, it was translated first. If a
chunk's `en` reads better with words from its neighbour, move them back.

An example, the Persian `چشم، | چیز دیگری | نمی‌خواهید`, with its meanings in
English (yours are written in {{GLOSS_LANGUAGE}}):

```
aligned:   certainly,      | anything else   | you do not want
           read in a row: "certainly, anything else you do not want" — stiff,
           and right: the learner sees the Persian order and the literal negative.
translated first, then cut (a constructed counter-example, not to be copied):
           certainly,      | would you like  | anything else?
           fluent, and wrong: the noun phrase now says what the verb says, and
           the verb what the noun phrase says.
```
