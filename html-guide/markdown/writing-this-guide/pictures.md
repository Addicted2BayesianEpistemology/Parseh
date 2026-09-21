---
title: Pictures, recordings and videos
linkTitle: Pictures and media
weight: 5
description: Screenshots, GIFs, figures laid out as in the studio, players and videos.
---

## Where a picture lives

Put the file under `html-guide/markdown/`, anywhere — beside the page that
shows it, or in a folder of pictures — and name it by its path from the
page. The compile copies it to the same place in the compiled site, and
says so, with the page and the line, when a page names a file that is not
there.

```text
markdown/
  images/flashcard.gif
  writing-this-guide/pictures.md    ->  ![A card](../images/flashcard.gif)
```

A picture from another site is named by its whole address,
`https://…`, and is not copied.

## A picture in the text

Hugo's picture, `![what it shows](path "a title")`, sits in the line like a
word, as wide as it is — never wider than the column, so a large GIF does
not break a page on a phone. Click it to see it large; Escape, or a click
anywhere, closes it.

```markdown
A card, turned: ![A flashcard being turned over](../images/flashcard.gif "Click a card to turn it")
```

A card, turned: ![A flashcard being turned over](../images/flashcard.gif "Click a card to turn it")

Every picture is loaded only when the page scrolls near it.

## A figure, laid out as in the studio

A picture alone on its line with the studio's braces after it is the
studio's figure: `width=` in percent of the column, `align=left`, `center`
or `right`, `offset=` to push it sideways, and the text in brackets as its
caption.

```markdown
![The front of the card](../images/card-front.png){width=45 align=center}
```

![The front of the card](../images/card-front.png){width=45 align=center}

Without the braces a picture alone on its line is Hugo's plain picture, as
wide as it is.

## A figure with a caption: the shortcode

Hugo's `figure` shortcode takes a caption, a title, a link and a size:

```markdown
{{< figure src="../images/card-back.png" alt="The back of the card"
    title="The back" caption="What the learner sees *after* turning it." width="300" >}}
```

{{< figure src="../images/card-back.png" alt="The back of the card" title="The back" caption="What the learner sees *after* turning it." width="300" >}}

## Recordings

A picture line whose file is a recording — `.mp3`, `.m4a`, `.aac`, `.ogg`,
`.oga`, `.opus`, `.wav`, `.flac`, `.webm` — is a player, laid out like a
figure. `start=` and `end=` play a stretch of it: `90`, `1:30`,
`1:05.25`.

```markdown
![The word, read aloud](sounds/ketab.mp3){width=60 start=0:01.5 end=0:03}
```

## Videos

A YouTube video goes in on a line of its own, the studio's way —
`@[caption](address){width= align= start= end=}` — or with Hugo's
`youtube` shortcode. Vimeo has a shortcode too.

```markdown
@[A lesson](https://www.youtube.com/watch?v=aqz-KE-bpKQ){width=80 align=center start=30}

{{< youtube id="aqz-KE-bpKQ" start="30" >}}
{{< vimeo 55073825 >}}
```

Both are the privacy-minded embeds: `youtube-nocookie.com`, and Vimeo with
`dnt=1`.

A YouTube video plays in the page only when the guide is **served** — by
Parseh, or on the web. YouTube's player refuses a page opened straight from
the disk, so there the guide puts a card in its place: the video's still and
**Watch on YouTube**, from the clip's start, which opens it on YouTube, with
a line under it saying that the player works when the guide is served. A
narrow card, as on a phone, says only **YouTube** and the start time.
Vimeo's player plays from the disk too.

## Making a GIF

A GIF shows a thing being done better than a paragraph does. Record the
screen with any tool, keep it short and narrow — the column is some 800
pixels wide, and a phone half that — and cut the colours down: a
screenshot needs a few dozen. With ImageMagick, from a folder of frames:

```bash
magick -delay 80 frame-*.png -loop 0 -layers Optimize -colors 64 demo.gif
```

The card above is nine frames, 480 × 220 pixels, 29 kilobytes.
