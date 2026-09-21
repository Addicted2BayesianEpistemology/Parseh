---
title: Shortcodes
weight: 6
description: Hugo's built-in shortcodes — figure, details, highlight, ref, youtube, qr and the rest.
---

A shortcode is Hugo's way of putting something into a page that Markdown
has no syntax for: `{{< name arguments >}}`, and for one that wraps
something, a closing `{{< /name >}}`. Arguments are named
(`src="x.png"`) or given in order (`"x.png"`); a value with spaces goes in
double quotes, and a long list of them may run over several lines. The
`{{% name %}}` form works the same way.

The guide has Hugo's built-in shortcodes — the ones a page that is read
without a server can honour. A shortcode it does not know is said at
compile time, with its page and line, and shows on the page as a red box,
so that it cannot go unnoticed.

## figure

A picture with a caption, a title, a link, a size:

```markdown
{{< figure src="../images/card-front.png" alt="The front of a card"
    caption="The **front**, before it is turned." link="../showcase.md" width="240" >}}
```

{{< figure src="../images/card-front.png" alt="The front of a card" caption="The **front**, before it is turned." link="../showcase.md" width="240" >}}

It takes Hugo's arguments: `src`, `alt`, `caption` (Markdown), `title`,
`link` with `target` and `rel`, `attr` and `attrlink` (a credit),
`width`, `height`, `class` and `loading`.

## details

A block that opens when its summary is clicked; Markdown inside:

```markdown
{{< details summary="What happens to an unknown shortcode?" >}}
It is said at compile time, and drawn as a **red box** where it stood.
{{< /details >}}
```

{{< details summary="What happens to an unknown shortcode?" >}}
It is said at compile time, and drawn as a **red box** where it stood.
{{< /details >}}

`open=true` shows it open; `class`, `name` and `title` are passed on.

## highlight

A code block, written as Hugo's older sites wrote one; the options are the
fence's:

```markdown
{{< highlight python "linenos=true,hl_lines=2" >}}
for word in words:
    print(word)
{{< /highlight >}}
```

{{< highlight python "linenos=true,hl_lines=2" >}}
for word in words:
    print(word)
{{< /highlight >}}

## ref and relref

The address of another page, from its file: in a link, or on its own.
Both give the same relative address here. A `ref` to a page that is not
there stops the compile with an error.

```markdown
[Code blocks]({{< ref "code-blocks.md" >}}) and
[its nested fences]({{< relref "code-blocks.md#nested-fences" >}}).
```

[Code blocks]({{< ref "code-blocks.md" >}}) and
[its nested fences]({{< relref "code-blocks.md#nested-fences" >}}).

## param

A value from the page's front matter:

```markdown
This page is called “{{< param "title" >}}”.
```

This page is called “{{< param "title" >}}”.

## youtube, vimeo

`{{< youtube id >}}` (or `id=`, with `start=` and `end=` in seconds),
`{{< vimeo id >}}`: the video, embedded the privacy-minded way. See
[Pictures and media](pictures.md#videos).

## qr

A QR code, drawn by the compiler — dark on light whatever the theme, so
that a phone can read it off the screen:

```markdown
{{< qr text="https://gohugo.io" />}}
```

{{< qr text="https://gohugo.io" />}}

`level=` sets how much of it may be damaged and still read (`low`,
`medium`, `quartile`, `high`), `scale=` its size, `alt=` what a screen
reader says.

## x, instagram, gist

Hugo fetches these from their services when it builds; the guide is built
without the network and read without it, so it draws a link to the post
instead: `{{< x user="gohugoio" id="1234567890" >}}`,
`{{< instagram "CxOWiQNP2MO" >}}`, `{{< gist user id >}}`.

## comment

Text for whoever edits the page, never shown:

```markdown
{{% comment %}} The screenshots are from version 3. {{% /comment %}}
```

## Writing a shortcode that is not run

Hugo's escape works: `{{</*` … `*/>}}` in the text of a page shows the
shortcode instead of running it — {{</* figure src="x.png" */>}} — which is
how this page writes them outside its code. Inside code, nothing is ever
run, so the plain form is enough there.
