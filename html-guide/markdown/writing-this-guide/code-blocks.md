---
title: Code blocks
weight: 4
description: Verbatim code with a Copy button, highlighting, line numbers, nested fences, and parseh-example.
---

## Fenced code

Three backticks (or three tildes) open a block of code and three more
close it; the word after the opening ones names the language:

````markdown
```python
def greet(name):
    return "سلام, " + name
```
````

```python
def greet(name):
    return "سلام, " + name
```

What is inside is shown **exactly as written**: nothing in it is read as
Markdown, as the Parseh dialect or as a shortcode. That is what lets a page
explain the dialect: `[x]{tl}`, `**bold**`, `:::exercise` and
`{{< figure >}}` inside a block stay what they are:

```markdown
## کتاب | ketâb | Arabic *kitāb*

The word [کتاب]{tl} = *book*, and **bold** stays two stars.

:::exercise yes-no
- [کتاب]{tl} means book => yes
:::

{{< figure src="shots/editor.png" >}}
```

Every block has its language named above it and a **Copy** button in the
corner, which copies the block exactly — every character, every line, no
line numbers — and says **Copied**. It works on a page opened from the
disk as well as on one served.

A tab stays a tab: shown four columns wide, and copied as the tab it is —
so a Makefile, whose every command line begins with one, still runs when
it is copied from a page:

```make
guide:
	python3 html-guide/build.py --check
```

## Languages

The guide colours Markdown (with the Parseh dialect's marks), `bash` or
`sh`, `python`, `json`, `yaml`, `toml`, `html` or `xml`, `css`,
`javascript`, `latex` or `tex`, and leaves `text` — or a block with no
language — plain. Any other name is shown above the block and the code is
left plain.

```yaml
title: A page
weight: 3
aliases: [old/page.md]   # an old address
```

```bash
# compile the guide, and check it
python3 html-guide/build.py --check && echo "all good"
```

```json
{"title": "A page", "weight": 3, "draft": false}
```

```html
<figure class="img"><img src="x.png" alt="A picture"></figure>
```

```latex
\section{Books} The reader is built with \texttt{tex2html.py}. % a comment
```

## Line numbers and highlighted lines

Hugo's options go in braces after the language: `linenos=true` numbers
the lines, `linenostart=` starts somewhere else, and `hl_lines=` marks lines
— counted from the block's first line, one by one or as ranges:

````markdown
```python {linenos=true,hl_lines=[2,"4-5"],linenostart=10}
def f(x):
    y = x * 2        # marked
    z = y + 1
    return z         # marked
                     # and this one
```
````

```python {linenos=true,hl_lines=[2,"4-5"],linenostart=10}
def f(x):
    y = x * 2        # marked
    z = y + 1
    return z         # marked
                     # and this one
```

The line numbers are never copied.

## Nested fences

A fence closes only on a fence of the same kind and at least as long, so a
block that shows a code block is written with a longer fence round it —
four backticks round three, or tildes round backticks:

`````markdown
````markdown
```python
print("a code block, shown in a code block")
```
````
`````

````markdown
```python
print("a code block, shown in a code block")
```
````

## Code inside a line

`` `code` `` inside a sentence is shown as written, whatever it holds:
`[x]{tl}`, `**b**`, `{{< ref "x.md" >}}`. Two backticks round it let it
hold one: ``a ` backtick``.

## Showing Markdown and what it becomes {#showing-markdown-and-what-it-becomes}

A block whose language is `parseh-example` is shown twice: as the code it
is, with its Copy button, and below it as what the studio draws from it —
the best way to explain a piece of the dialect.

````markdown
```parseh-example
The word [کتاب]{teal} = *book*, **bold**, and a formula [a^2]{math}.
```
````

```parseh-example
The word [کتاب]{teal} = *book*, **bold**, and a formula [a^2]{math}.
```

The example is drawn as a document of its own: its footnotes are its own,
its headings are not in the page's contents, and it may start with a front
matter of its own — a `title:`, and a `target:` for a language other than
the page's:

```parseh-example
---
title: A small Japanese lesson
target: ja
---
[猫]{kana:ねこ translit:neko} = *cat*^[A footnote of the example's own.]
```

Its exercises work like any other, and **Check exercises** at the end of
the page marks them with the rest.
