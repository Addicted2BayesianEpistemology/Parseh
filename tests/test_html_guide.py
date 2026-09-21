"""The HTML guide's compiler (html-guide/build.py and html-guide/engine/).

    python3 -m unittest discover -s tests -p test_html_guide.py

Every test compiles a small tree of pages written here into a scratch
directory and reads the HTML that comes out: Hugo's Markdown, the Parseh
dialect drawn by the studio's own renderer, where the dialect wins, the
shortcodes, the navigation, the pictures, the warnings, the export that
builds on its own.  The browser half -- the sidebar, the themes, the Copy
button, the exercises, the search, on file:// and through the server -- is
tests/html_guide.mjs.
"""
import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "html-guide"
sys.path.insert(0, str(GUIDE))
sys.path.insert(0, str(ROOT / "lib"))
from engine import blocks, cssscope, frontmatter, highlight, qr  # noqa: E402
from engine.inline import typographer  # noqa: E402
from engine.site import Site  # noqa: E402
import guidebuild  # noqa: E402

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c63f8cfc0f01f0005000201"
                    "a5f3c1a50000000049454e44ae426082")


def write_tree(base, files):
    for rel, text in files.items():
        p = Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            p.write_bytes(text)
        else:
            p.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def compile_tree(files):
    """Pages written into a scratch markdown/ -> (the site directory, the
    report).  The scratch directory goes when the test does."""
    td = tempfile.mkdtemp(prefix="guide-test-")
    write_tree(Path(td) / "markdown", files)
    report = Site(GUIDE, src=Path(td) / "markdown").build(Path(td) / "site")
    return Path(td) / "site", report, td


def sheet(html):
    """The article's text: what is between the sheet's opening tag and the
    article's end."""
    m = re.search(r'<div class="sheet"[^>]*>(.*)</div>\s*</article>', html, re.S)
    return m.group(1) if m else ""


class Tree(unittest.TestCase):
    """One compile of a tree of pages, read by many tests."""
    FILES = {}

    @classmethod
    def setUpClass(cls):
        cls.site, cls.report, cls.td = compile_tree(cls.FILES)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.td, ignore_errors=True)

    def page(self, rel):
        return (self.site / rel).read_text(encoding="utf-8")

    def body(self, rel):
        return sheet(self.page(rel))

    def problems(self, level=None):
        return [str(p) for p in self.report.problems if level in (None, p.level)]


# ------------------------------------------------------------------ code
class CodeIsVerbatim(Tree):
    FILES = {
        "code.md": '''
            ---
            title: Code
            ---
            ```markdown
            [x]{tl} and **b** and <b>tag</b> & "quotes" -- dashes...
            {{< figure src="missing.png" >}}
            :::exercise single-choice
            - [x] a
            :::
            ```

            A span: `[x]{tl} **b** {{< ref "nowhere.md" >}}` and ``a ` tick``.

            ````text
            ```python
            print("nested")
            ```
            ````

            ```python {linenos=true,hl_lines=[2],linenostart=5}
            a = 1
            b = "two"  # marked
            ```

            ~~~
            tildes, no language
            ~~~
        ''',
    }

    def test_a_block_is_shown_exactly_as_written(self):
        b = self.body("code.html")
        block = re.search(r'<div class="g-code" data-code="markdown">.*?</pre></div>', b, re.S)
        self.assertIsNotNone(block, "the markdown block is drawn as a code block")
        text = re.sub(r"<[^>]+>", "", block.group(0).split("<pre", 1)[1])
        import html
        text = html.unescape(text.split(">", 1)[1])
        self.assertIn('[x]{tl} and **b** and <b>tag</b> & "quotes" -- dashes...', text)
        self.assertIn('{{< figure src="missing.png" >}}', text)
        self.assertIn(":::exercise single-choice", text)
        # nothing inside it was read: no mark, no figure, no exercise, no bold
        self.assertNotIn("<strong>", block.group(0))
        self.assertNotIn('class="exercise"', b)
        self.assertNotIn("<figure", b)
        self.assertIn("&lt;b&gt;tag&lt;/b&gt;", block.group(0))
        self.assertFalse(self.problems(), "a shortcode in code is never run: %s" % self.problems())

    def test_a_block_has_its_language_and_a_copy_button(self):
        b = self.body("code.html")
        self.assertEqual(b.count('class="g-copy"'), 4)
        self.assertIn('<span class="g-code-lang">Markdown</span>', b)
        self.assertIn('<span class="g-code-lang">Python</span>', b)

    def test_a_code_span_is_opaque(self):
        b = self.body("code.html")
        self.assertIn('<code>[x]{tl} **b** {{&lt; ref "nowhere.md" &gt;}}</code>', b)
        self.assertIn("<code>a ` tick</code>", b)

    def test_a_longer_fence_holds_a_shorter_one(self):
        b = self.body("code.html")
        self.assertIn("```python", b)
        self.assertIn('print("nested")', b.replace("&quot;", '"'))

    def test_line_numbers_and_marked_lines(self):
        b = self.body("code.html")
        self.assertIn('<span class="g-ln" aria-hidden="true">5</span>', b)
        self.assertIn('<span class="g-ln" aria-hidden="true">6</span>', b)
        self.assertRegex(b, r'<span class="g-line g-hl"><span class="g-ln"[^>]*>6</span>')


class ATabIsATab(Tree):
    """A code block shows, and its Copy copies, a tab as a tab: a Makefile's
    recipe line begins with one, a tab-separated table is made of them.
    (The page's structure still reads a tab as four columns.)"""
    FILES = {
        "tabs.md": "---\ntitle: Tabs\n---\n"
                   "```make\nall:\n\techo \"hi\"\n```\n\n"
                   "```text\na\tb\tc\n```\n\n"
                   "{{< highlight bash >}}\n\techo highlighted\n{{< /highlight >}}\n\n"
                   "- an item\n\n  ```make\n  in-a-list:\n  \techo listed\n  ```\n\n"
                   "> ```make\n> in-a-box:\n> \techo boxed\n> ```\n\n"
                   "- a list item\n"
                   "\t- nested by a tab\n",
    }

    def lines(self):
        return [html_mod.unescape(re.sub(r"<[^>]+>", "", x)) for x in
                re.findall(r'<span class="g-line[^"]*">(.*?)</span>(?=<span class="g-line|</code>)',
                           self.body("tabs.html"))]

    def test_a_fence_keeps_its_tabs(self):
        got = self.lines()
        self.assertIn('\techo "hi"', got)
        self.assertIn("a\tb\tc", got)

    def test_so_does_a_highlight_shortcode(self):
        self.assertIn("\techo highlighted", self.lines())

    def test_so_does_a_fence_inside_a_list_item_or_a_box(self):
        got = self.lines()
        self.assertIn("\techo listed", got)
        self.assertIn("\techo boxed", got)

    def test_the_structure_still_reads_a_tab_as_four_columns(self):
        b = self.body("tabs.html")
        self.assertRegex(b, r"<li>a list item\s*<ul><li>nested by a tab</li></ul></li>")

    def test_cutting_columns_off_a_line_as_written(self):
        cut = blocks._cut
        self.assertEqual(cut("  \tx", 0, 2), "\tx", "two spaces off, the tab kept")
        self.assertEqual(cut("\t\tx", 0, 2), "  \tx", "half a tab off: the rest of it as spaces")
        self.assertEqual(cut(">\tfoo", 0, 2), "  foo")
        self.assertEqual(cut("\tx", 2, 2), "x", "a tab at column 2 reaches column 4")
        self.assertEqual(cut("ab", 0, 5), "")


# ------------------------------------------------------------------ Hugo's Markdown
class HugoMarkdown(Tree):
    FILES = {
        "hugo.md": '''
            +++
            title = "Hugo"
            weight = 1
            +++
            Title one
            =========

            Title two
            ---------

            #### Four ####

            ### Custom {#my-id .fancy}

            ### Custom

            - one
              - two
                - three
            - [ ] todo
            - [x] done

            7. seven
            8. eight

            | L | C | R |
            |:--|:-:|--:|
            | a \\| b | [a link](other.md) | -- |

            ~~gone~~, _em_, __strong__, ***both***, snake_case_word.

            "Quoted" -- and --- and... it's a -> b.

            Term
            : Definition

            A [ref link][r] and [r] and <https://example.org> and https://bare.example.com.

            [r]: https://example.com/ref "The title"

            Note[^n] and ^[inline].

            [^n]: The note.

            A line{two_spaces}
            broken, and\\
            again. \\*not em\\* &copy;
        '''.replace("{two_spaces}", "  "),
        "other.md": '''
            {"title": "Other", "weight": 2}
            Other page.
        ''',
    }

    def test_headings(self):
        b = self.body("hugo.html")
        self.assertRegex(b, r'<h1 class="g-h1" id="title-one">Title one')
        self.assertRegex(b, r'<h2 class="section" id="title-two"><span class="secnum">1\.</span> Title two')
        self.assertRegex(b, r'<h4 class="g-h4" id="four">Four<a class="g-anchor"')
        self.assertRegex(b, r'<h3 class="subsection fancy" id="my-id">Custom')
        self.assertRegex(b, r'<h3 class="subsection" id="custom">Custom')

    def test_duplicate_heading_ids_are_numbered_as_hugo_numbers_them(self):
        site, _r, td = compile_tree({"d.md": "## A\n\n## A\n\n## A\n"})
        try:
            b = sheet((site / "d.html").read_text(encoding="utf-8"))
            self.assertEqual(re.findall(r'<h2 class="section" id="([^"]+)"', b), ["a", "a-1", "a-2"])
        finally:
            shutil.rmtree(td)

    def test_lists_nest_start_and_carry_tasks(self):
        b = self.body("hugo.html")
        self.assertIn("<li>one\n<ul><li>two\n<ul><li>three</li></ul></li></ul></li>", b)
        self.assertIn('<li class="g-task"><input type="checkbox" disabled aria-label="to do"> todo</li>', b)
        self.assertIn('<input type="checkbox" disabled checked aria-label="done"> done', b)
        self.assertIn('<ol start="7"><li>seven</li><li>eight</li></ol>', b)

    def test_tables_with_alignment_escaped_pipes_and_links(self):
        b = self.body("hugo.html")
        self.assertIn('<th class="a-l">L</th><th class="a-c">C</th><th class="a-r">R</th>', b)
        self.assertIn('<td class="a-l">a | b</td>', b)
        self.assertIn('<td class="a-c"><a href="other.html">a link</a></td>', b)
        self.assertIn('<td class="a-r">—</td>', b, "the studio's empty cell")

    def test_emphasis_strikethrough_and_the_typographer(self):
        b = self.body("hugo.html")
        self.assertIn("<del>gone</del>, <em>em</em>, <strong>strong</strong>, "
                      "<strong><em>both</em></strong>, snake_case_word.", b)
        self.assertIn("“Quoted” – and — and… it’s a", b)
        self.assertIn('<span class="arrow">→</span>', b, "-> stays the studio's arrow")

    def test_definition_lists(self):
        self.assertIn('<dl class="desc g-dl"><div class="di"><dt>Term</dt><dd>Definition</dd></div></dl>',
                      self.body("hugo.html"))

    def test_a_term_with_two_definitions_sets_each_on_its_own_line(self):
        # the run-on list ("desc") would draw "Term two Definition two
        # aDefinition two b": such a list is the studio's other one, "lex",
        # every term and every definition a line of its own
        site, _r, td = compile_tree({"d.md": "Term one\n: Definition one\n\n"
                                             "Term two\n: Definition two a\n: Definition two b\n\n"
                                             "Paragraph.\n\n"
                                             "Name\nAlias\n: One definition for two terms\n"})
        try:
            b = sheet((site / "d.html").read_text(encoding="utf-8"))
            self.assertIn('<dl class="lex g-dl"><div class="di"><dt>Term one</dt><dd>Definition one</dd></div>'
                          '<div class="di"><dt>Term two</dt><dd>Definition two a</dd>'
                          '<dd>Definition two b</dd></div></dl>', b)
            self.assertIn('<dl class="lex g-dl"><div class="di"><dt>Name</dt><dt>Alias</dt>'
                          '<dd>One definition for two terms</dd></div></dl>', b)
        finally:
            shutil.rmtree(td)

    def test_links_reference_auto_and_bare(self):
        b = self.body("hugo.html")
        self.assertIn('<a class="lnk" href="https://example.com/ref" title="The title" target="_blank" '
                      'rel="noopener noreferrer">ref link</a>', b)
        self.assertIn('>r</a>', b)
        self.assertIn('href="https://example.org"', b)
        self.assertIn('href="https://bare.example.com"', b)

    def test_footnotes_are_the_studio_s(self):
        b = self.body("hugo.html")
        self.assertIn('<span class="fncloud" role="tooltip" id="fn-2">The note.</span>', b)
        self.assertIn('<span class="fncloud" role="tooltip" id="fn-1">inline</span>', b)
        self.assertIn("<h4>Notes</h4>", b)

    def test_hard_breaks_escapes_and_entities(self):
        b = self.body("hugo.html")
        self.assertIn("A line<br>broken, and<br>again. *not em* ©", b)

    def test_front_matter_in_all_three_forms_orders_the_pages(self):
        nav = (self.site / "nav.js").read_text(encoding="utf-8")
        tree = json.loads(nav.split("=", 1)[1].rstrip().rstrip(";"))["tree"]
        self.assertEqual([n["t"] for n in tree], ["Hugo", "Other"])


# ------------------------------------------------------------------ the dialect
class ParsehDialect(Tree):
    FILES = {
        "fa.md": '''
            ---
            title: Persian
            ---
            The word [کتاب]{tl} and a run کتاب here, [تند]{teal}, [آهسته]{translit:âheste}.

            ## [کتاب]{teal} | ketâb | Arabic | = *book*

            ## 3. Numbered by hand = *gloss*

            > A box with **bold**.

            :::exercise single-choice
            prompt: Choose.
            - [x] right
            - [ ] wrong
            :::

            A formula [x^2 + [0,1)]{math} and [a]{teal} then [b^2]{math}.

            A commutator [[A,B]]{math}, a [link](https://example.org/m) then [c^2]{math}, and [d]{teal} [e^2]{math}.

            :::math
            \\int_0^1 x\\,dx
            :::
        ''',
        "ja.md": '''
            ---
            title: Japanese
            target: ja
            ---
            [猫]{kana:ねこ translit:neko} = *cat*
        ''',
    }

    def test_a_target_run_carries_its_direction_and_language(self):
        b = self.body("fa.html")
        self.assertRegex(b, r'<span class="fa fa-l fa-rich" dir="rtl" lang="fa"[^>]*>کتاب</span>')
        self.assertRegex(b, r'<span class="fa" dir="rtl" lang="fa" data-fa="کتاب" data-occ="\d">کتاب</span>')
        self.assertIn('class="fac fac-teal"', b)
        self.assertIn('data-translit="âheste"', b)

    def test_a_lemma_heading(self):
        b = self.body("fa.html")
        self.assertIn('<section class="voce"', b)
        self.assertRegex(b, r'<div class="voce-fa fac fac-teal" dir="rtl" lang="fa"[^>]*>کتاب</div>')
        self.assertIn('<div class="voce-translit">ketâb</div>', b)

    def test_a_typed_number_and_a_gloss_are_taken_off_a_section(self):
        b = self.body("fa.html")
        self.assertRegex(b, r'id="numbered-by-hand"><span class="secnum">1\.</span> Numbered by hand<a')

    def test_a_box_an_exercise_and_the_check_button(self):
        b = self.body("fa.html")
        self.assertIn('<div class="box"><p>A box with <strong>bold</strong>.</p></div>', b)
        self.assertRegex(b, r'<section class="exercise" data-exercise="1" data-subtype="single-choice"')
        self.assertIn('class="btn primary ex-correct-all"', b)
        page = self.page("fa.html")
        self.assertIn("_parseh/app.js", page, "a page with exercises loads the studio's script")
        self.assertIn("_parseh/mathjax.js", page)

    def test_formulas_inline_and_on_their_own(self):
        b = self.body("fa.html")
        self.assertIn('<span class="math" data-tex="x^2 + [0,1)">', b)
        # a formula starts at its own bracket (texgen.MATH_RE, which the
        # guide reads a formula with as well): the colour mark and the link
        # before one stay themselves, and a formula that is one bracket is
        # not a blank
        self.assertIn('<span class="fac fac-teal" data-color="teal">a</span>', b)
        self.assertIn('<span class="math" data-tex="b^2">', b)
        self.assertIn('<span class="math" data-tex="[A,B]">', b)
        self.assertIn('>link</a>', b)
        self.assertIn('<span class="math" data-tex="c^2">', b)
        self.assertIn('<span class="fac fac-teal" data-color="teal">d</span>', b)
        self.assertIn('<span class="math" data-tex="e^2">', b)
        self.assertIn('<div class="math mathblock" data-tex="\\int_0^1 x\\,dx"', b)

    def test_a_formula_that_is_one_bracket_loads_mathjax(self):
        # `[[A,B]]{math}` was taken for a blank, `[[A,B]]`, which the studio
        # then read as the formula it is: drawn, but on a page that did not
        # know it had one, and so never loaded MathJax to draw it
        site, _r, td = compile_tree({"c.md": "A commutator [[A,B]]{math} alone.\n"})
        try:
            page = (site / "c.html").read_text(encoding="utf-8")
            self.assertIn('<span class="math" data-tex="[A,B]">', sheet(page))
            self.assertIn("_parseh/mathjax.js", page)
        finally:
            shutil.rmtree(td)

    def test_the_page_s_target_language(self):
        page = self.page("ja.html")
        self.assertIn('<div class="sheet" lang="en" data-lang="ja" style="--fa-scale:1.20">', page)
        self.assertIn('data-kana="ねこ"', sheet(page))
        self.assertNotIn("app.js", page, "no exercises, no studio script")


# ------------------------------------------------------------------ where Parseh wins
class ParsehWins(Tree):
    FILES = {
        "wins.md": '''
            ---
            title: Wins
            ---
            > quoted?

            ## word | translit | etym

            The mark [text]{teal} and [*not em* `x`]{tl} and `[x]{tl}` and *em* and **b**.

            ![cap](pic.png){width=50 align=center}

            ![plain](pic.png)

            <b>html</b> <!-- gone --> kept

                indented is text

            | a | b |
            |---|---|
            | [link](wins.md) | `c` |
        ''',
        "pic.png": PNG,
    }

    def test_a_quote_is_a_box(self):
        b = self.body("wins.html")
        self.assertIn('<div class="box"><p>quoted?</p></div>', b)
        self.assertNotIn("<blockquote", b)

    def test_a_heading_with_pipes_is_a_lemma_for_a_script_language_only_when_it_starts_so(self):
        # Persian target, Latin headword: not a lemma (the studio's rule)
        self.assertRegex(self.body("wins.html"), r'<h2 class="section" id="word--translit--etym">')

    def test_braces_after_brackets_are_parseh_marks(self):
        b = self.body("wins.html")
        self.assertIn('<span class="fac fac-teal" data-color="teal">text</span>', b)
        self.assertRegex(b, r'<span class="fa fa-l fa-rich"[^>]*>\*not em\* `x`</span>')
        self.assertIn("<code>[x]{tl}</code>", b)
        self.assertIn("<em>em</em> and <strong>b</strong>", b)

    def test_a_picture_with_the_studio_s_braces_is_the_studio_s_figure(self):
        b = self.body("wins.html")
        self.assertRegex(b, r'<figure class="img align-center" data-width="50"[^>]*style="width:50%;'
                            r'margin-left:25\.00%"><img loading="lazy" decoding="async" src="pic.png"')
        self.assertIn('<p><img loading="lazy" decoding="async" class="g-img" src="pic.png" alt="plain"></p>', b)

    def test_raw_html_is_shown_and_comments_dropped(self):
        b = self.body("wins.html")
        self.assertIn("&lt;b&gt;html&lt;/b&gt;  kept", b)
        self.assertNotIn("gone", b)

    def test_indentation_is_not_code(self):
        b = self.body("wins.html")
        self.assertIn("<p>indented is text</p>", b)
        self.assertNotIn("<pre", b)

    def test_a_hugo_link_inside_a_table_cell(self):
        self.assertIn('<td class="a-l"><a href="wins.html">link</a></td><td class="a-l"><code>c</code></td>',
                      self.body("wins.html"))


class ListsReadAsTheStudioReadsThem(Tree):
    """A line under a list item carries its text on only when it is
    indented, as in the studio; one at the margin ends the list (Hugo would
    take it in, a "lazy" line).  A blank line between items keeps Hugo's
    reading, one loose list -- the documented exception."""
    CASES = {
        "margin": "- one\n- two\na line at the margin\n",
        "indented": "1. a\n  carried on by two spaces\n",
        "nested": "- a\n  - b\n  carried on under b\n",
        "box": "> - in a box\n> at the margin of the box\n",
    }
    FILES = dict({"%s.md" % k: "---\ntitle: %s\n---\n%s" % (k, v) for k, v in CASES.items()},
                 **{"blank.md": "---\ntitle: blank\n---\n1. a\n\n1. b\n"})

    @staticmethod
    def shape(html_text):
        html_text = re.sub(r' data-src-line="\d+"', "", html_text)
        html_text = re.sub(r'<footer class="colophon">.*?</footer>', "", html_text, flags=re.S)
        return re.sub(r"\s*\n\s*", "", html_text).strip()

    def test_the_guide_draws_the_studio_s_list(self):
        from engine.studio import htmlgen
        for name, text in self.CASES.items():
            guide = self.shape(self.body(name + ".html").split("</header>", 1)[1])
            studio = self.shape(htmlgen.render_document(text)["html"])
            self.assertEqual(guide, studio, name)

    def test_a_line_at_the_margin_is_a_paragraph_after_the_list(self):
        self.assertIn("<ul><li>one</li><li>two</li></ul>\n<p>a line at the margin</p>", self.body("margin.html"))

    def test_a_blank_line_between_items_is_one_loose_list(self):
        self.assertIn("<ol><li><p>a</p></li><li><p>b</p></li></ol>", self.body("blank.html"))


# ------------------------------------------------------------------ shortcodes
class Shortcodes(Tree):
    FILES = {
        "sec/_index.md": "---\ntitle: Section\n---\nThe section.\n",
        "sec/page.md": '''
            ---
            title: Page
            answer: 42
            ---
            {{< figure src="../shots/a.png" alt="A" caption="The *caption*" title="T" link="../top.md" >}}

            {{< details summary="Open me" open=true >}}
            Inside **bold**.

            - a list
            {{< /details >}}

            See [top]({{< ref "top.md" >}}), [the heading]({{< relref "/top.md#h" >}}) and {{< param "answer" >}}.

            {{< youtube id="aqz-KE-bpKQ" start="30" title="Big Buck Bunny" >}}

            {{< vimeo 55073825 >}}

            {{< qr text="https://example.org" >}}

            {{< highlight python "linenos=true" >}}
            x = 1
            {{< /highlight >}}

            {{< nosuch a="b" >}}

            Shown, not run: {{</* figure src="x.png" */>}}.

            {{% comment %}} for the editors only {{% /comment %}}

            {{< figure src="../shots/a.png"
                alt="Over two lines" >}}
        ''',
        "top.md": "---\ntitle: Top\n---\n## H\n",
        "shots/a.png": PNG,
        "broken.md": "---\ntitle: Broken\n---\n{{< ref \"nowhere.md\" >}}\n",
    }

    def test_figure(self):
        b = self.body("sec/page.html")
        self.assertIn('<figure class="g-figure"><a href="../top.html"><img loading="lazy" decoding="async" '
                      'src="../shots/a.png" alt="A"></a><figcaption><h4>T</h4><p>The <em>caption</em></p>'
                      '</figcaption></figure>', b)
        self.assertTrue((self.site / "shots" / "a.png").is_file(), "the picture is copied")
        self.assertIn('alt="Over two lines"', b, "a shortcode may run over several lines")

    def test_details(self):
        b = self.body("sec/page.html")
        self.assertIn('<details class="g-details" open><summary>Open me</summary>'
                      '<p>Inside <strong>bold</strong>.</p>\n<ul><li>a list</li></ul></details>', b)

    def test_ref_relref_and_param(self):
        b = self.body("sec/page.html")
        self.assertIn('<a href="../top.html">top</a>', b)
        self.assertIn('<a href="../top.html#h">the heading</a>', b)
        self.assertIn(" and 42.", b)

    def test_youtube_vimeo_qr_highlight(self):
        b = self.body("sec/page.html")
        self.assertIn("https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ?rel=0&amp;start=30", b)
        self.assertIn('title="Big Buck Bunny"', b)
        self.assertNotIn("<figcaption>Big Buck Bunny", b)
        self.assertIn("https://player.vimeo.com/video/55073825?dnt=1", b)
        self.assertRegex(b, r'<figure class="g-qr"[^>]*><svg xmlns="http://www.w3.org/2000/svg"')
        self.assertRegex(b, r'<div class="g-code g-numbered" data-code="python">')

    def test_an_unknown_shortcode_is_said_and_shown(self):
        b = self.body("sec/page.html")
        self.assertIn('<div class="g-error" role="note">Unknown shortcode <code>{{&lt; nosuch', b)
        self.assertTrue(any("markdown/sec/page.md:" in p and "unknown shortcode {{< nosuch >}}" in p
                            for p in self.problems("warning")), self.problems())

    def test_the_comment_escape_and_comment(self):
        b = self.body("sec/page.html")
        self.assertIn('Shown, not run: {{&lt; figure src="x.png" &gt;}}.', b)
        self.assertNotIn("for the editors only", b)

    def test_a_ref_to_no_page_is_an_error(self):
        self.assertTrue(any(p.startswith("error: markdown/broken.md:4: ref: no page 'nowhere.md'")
                            for p in self.problems("error")), self.problems())


# ------------------------------------------------------------------ the site
class TheSite(Tree):
    FILES = {
        "_index.md": "---\ntitle: My guide\n---\n",
        "b.md": "---\ntitle: Bee\n---\nNo weight.\n",
        "a.md": "---\ntitle: Ay\nweight: 5\n---\nWeight 5.\n",
        "z.md": "---\ntitle: Zed\nweight: 1\n---\nWeight 1. [Dead](doc:Nobody) [Live](doc:Bee) "
                "[Up](sec/deep/leaf.md) ![gone](nothere.png)\n",
        "draft.md": "---\ntitle: Draft\ndraft: true\n---\nHidden.\n",
        "sec/_index.md": "---\ntitle: The Section\nweight: 3\n---\nIntro.\n",
        "sec/deep/leaf.md": "---\ntitle: Leaf\naliases: [old/leaf.md]\n---\n"
                            "Back [home](../../z.md), a picture ![p](../../img/p.png).\n",
        "img/p.png": PNG,
    }

    def nav(self):
        text = (self.site / "nav.js").read_text(encoding="utf-8")
        return json.loads(text.split("=", 1)[1].rstrip().rstrip(";"))

    def test_the_order_is_by_weight_then_title_and_drafts_are_left_out(self):
        nav = self.nav()
        self.assertEqual(nav["title"], "My guide")
        self.assertEqual([n["t"] for n in nav["tree"]], ["Zed", "The Section", "Ay", "Bee"])
        self.assertFalse((self.site / "draft.html").exists())
        sec = nav["tree"][1]
        self.assertEqual(sec["u"], "site/sec/index.html")
        self.assertEqual(sec["c"][0]["t"], "Deep")
        self.assertEqual(sec["c"][0]["c"][0]["u"], "site/sec/deep/leaf.html")

    def test_relative_addresses_from_a_nested_page(self):
        page = self.page("sec/deep/leaf.html")
        self.assertIn('<a href="../../z.html">home</a>', page)
        self.assertIn('src="../../img/p.png"', page)
        self.assertIn('<link rel="stylesheet" href="../../../assets/guide.css">', page)
        self.assertIn('<link rel="stylesheet" href="../../_parseh/studio.css">', page)
        self.assertIn('<a class="g-link g-home" href="../../../index.html">Home</a>', page)
        # the manual's button, which a phone shortens to "PDF" (the words
        # after it are hidden there, not the button)
        self.assertIn('<a class="g-pdf" data-guide-manual href="../../_parseh/manual.pdf" target="_blank" '
                      'rel="noopener" title="The PDF manual">PDF<span class="g-pdf-more"> manual</span></a>', page)
        self.assertIn('aria-current="page">Leaf</a>', page)
        self.assertIn('<html lang="en" data-guide-root="../../../">', page)
        # no address the engine wrote starts with / or ends at a folder
        for href in re.findall(r'(?:href|src)="([^"]+)"', page):
            if href.startswith(("http", "#", "mailto:")) or href == "/":
                continue
            self.assertFalse(href.startswith("/"), href)
            self.assertFalse(href.endswith("/"), href)

    def test_prev_next_follow_the_list(self):
        page = self.page("sec/index.html")
        self.assertIn('<a class="g-prev" href="../z.html"><span>Previous</span>Zed</a>', page)
        self.assertIn('<a class="g-next" href="deep/leaf.html"><span>Next</span>Leaf</a>', page)
        self.assertIn('<nav class="g-children"', page, "a section's page lists what is in it")

    def test_doc_links_by_title(self):
        b = self.body("z.html")
        self.assertIn('<a class="doclink" href="b.html">Live</a>', b)
        self.assertIn('<span class="doclink-dead" title="No page of this guide is called “Nobody”">Dead</span>', b)

    def test_pictures_are_copied_and_a_missing_one_is_said_with_its_line(self):
        self.assertTrue((self.site / "img" / "p.png").is_file())
        self.assertTrue(any(p.startswith("warning: markdown/z.md:5: no such file: nothere.png")
                            for p in self.problems()), self.problems())
        self.assertTrue(any("markdown/z.md:5: doc: link to a page that is not there: 'Nobody'" in p
                            for p in self.problems()))

    def test_an_alias_goes_on_to_the_page(self):
        text = (self.site / "old" / "leaf.html").read_text(encoding="utf-8")
        self.assertIn('content="0; url=../sec/deep/leaf.html"', text)

    def test_search_index_and_build_info(self):
        text = (self.site / "search-index.js").read_text(encoding="utf-8")
        index = json.loads(text.split("=", 1)[1].rstrip().rstrip(";"))
        leaf = next(e for e in index if e["t"] == "Leaf")
        self.assertEqual(leaf["u"], "site/sec/deep/leaf.html")
        self.assertIn("Back home, a picture", leaf["x"])
        info = json.loads((self.site / "build.json").read_text(encoding="utf-8"))
        self.assertEqual(info["pages"], 5, "the root _index.md and the draft are not pages")
        self.assertEqual(len(info["fingerprint"]), 64)

    def test_the_runtime_the_pages_draw_with(self):
        run = self.site / "_parseh"
        for name in ("studio.css", "langs.css", "app.js", "mathjax.js", "mathjax/tex-svg.js"):
            self.assertTrue((run / name).is_file(), name)
        js = (run / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("__FOLD__", js, "the case fold is spliced in, as the studio's server does")
        self.assertTrue((run / "fonts" / "Vazirmatn-Regular.ttf").is_file())

    def test_the_output_is_the_same_every_time(self):
        site2, _r, td2 = compile_tree(self.FILES)
        try:
            for p in sorted(self.site.rglob("*")):
                if p.is_file():
                    self.assertEqual(p.read_bytes(), (site2 / p.relative_to(self.site)).read_bytes(), p)
        finally:
            shutil.rmtree(td2)


class AWarningNamesItsOwnLine(Tree):
    """A warning inside a table names its row's line, one inside a list its
    item's, one in a definition list its term's or definition's -- not the
    first line of the block (a real document's 21 dead links were all said
    to be on the table's first line)."""
    FILES = {"lines.md": "---\ntitle: Lines\n---\n"      # lines 1-3
                         "| a | b |\n"                     # 4
                         "|---|---|\n"                     # 5
                         "| [x](doc:Nope1) | y |\n"        # 6
                         "| z | [w](doc:Nope2) |\n"        # 7
                         "| [x](doc:Nope1) | y |\n"        # 8: the same cell again
                         "\n"
                         "- [l](doc:Nope3)\n"              # 10
                         "- [m](doc:Nope4)\n"              # 11
                         "\n"
                         "Term [t](doc:Nope5)\n"           # 13
                         ": [d](doc:Nope6)\n"              # 14
                         ": [e](doc:Nope7)\n"}             # 15

    def test_rows_items_terms_and_definitions(self):
        got = sorted((int(re.search(r"lines\.md:(\d+):", p).group(1)),
                      re.search(r"'(\w+)'", p).group(1)) for p in self.problems())
        self.assertEqual(got, [(6, "Nope1"), (7, "Nope2"), (8, "Nope1"), (10, "Nope3"), (11, "Nope4"),
                               (13, "Nope5"), (14, "Nope6"), (15, "Nope7")])


class TheSearchIndexHoldsEveryWord(Tree):
    """The search box finds a word only if the index has it: a long page is
    indexed to its last word (the index once stopped at 20,000 characters)."""
    FILES = {"long.md": "---\ntitle: Long\n---\n" + "Filler words for the index. " * 1200
                        + "\n\nThe very last word is zymurgy.\n"}

    def test_a_long_page_is_indexed_whole(self):
        text = (self.site / "search-index.js").read_text(encoding="utf-8")
        page = json.loads(text.split("=", 1)[1].rstrip().rstrip(";"))[0]
        self.assertGreater(len(page["x"]), 30000)
        self.assertTrue(page["x"].endswith("The very last word is zymurgy."), page["x"][-60:])


# ------------------------------------------------------------------ the parts
class Parts(unittest.TestCase):
    def test_front_matter_yaml_toml_json(self):
        fm, body, line, kind = frontmatter.split(
            "---\ntitle: \"A: b\"\nweight: 3\ndraft: false\ntags: [a, 'b c']\nparams:\n"
            "  x: 1\n  y:\n    - one\n    - two\ntext: |\n  line one\n  line two\n---\nBody\n")
        self.assertEqual((kind, line, body), ("yaml", 15, "Body\n"))
        self.assertEqual(fm["title"], "A: b")
        self.assertEqual(fm["tags"], ["a", "b c"])
        self.assertEqual(fm["params"], {"x": 1, "y": ["one", "two"]})
        self.assertEqual(fm["text"], "line one\nline two\n")
        self.assertIs(fm["draft"], False)
        fm, _b, _l, kind = frontmatter.split('+++\ntitle = "T"\nweight = 2\n[params]\nk = [1, 2]\n+++\n')
        self.assertEqual((kind, fm), ("toml", {"title": "T", "weight": 2, "params": {"k": [1, 2]}}))
        fm, body, _l, kind = frontmatter.split('{"Title": "J", "weight": 4}\nbody')
        self.assertEqual((kind, fm, body), ("json", {"title": "J", "weight": 4}, "body"))
        with self.assertRaises(frontmatter.FrontMatterError):
            frontmatter.split("---\ntitle: never closed\n")

    def test_the_typographer_leaves_the_arrow_alone(self):
        self.assertEqual(typographer('"a" -- b --- c... -> d --> e'), "“a” – b — c… -> d --> e")

    def test_the_highlighter_knows_the_dialect(self):
        lines = highlight.render_lines("## کتاب | ketâb\n[x]{tl} and **b**", "markdown")
        self.assertIn('<span class="t-head">## کتاب | ketâb</span>', lines[0])
        self.assertIn('<span class="t-mark">[x]{tl}</span>', lines[1])
        self.assertIn('<span class="t-strong">**b**</span>', lines[1])
        # every line stands alone, so a token over two lines is closed and reopened
        py = highlight.render_lines('x = """a\nb"""', "python")
        self.assertEqual(py[1], '<span class="t-str">b"""</span>')
        self.assertEqual(highlight.render_lines("<a & b>", "nosuchlanguage"), ["&lt;a &amp; b&gt;"])

    def test_the_block_parser_keeps_line_numbers(self):
        nodes, _f, _d, problems = blocks.parse(["", "para", "", "```", "open"], 10)
        self.assertEqual([(n["kind"], n["line"]) for n in nodes], [("para", 11), ("code", 13)])
        self.assertEqual(problems[0][0], 13)

    def test_the_studio_s_stylesheet_is_confined_to_the_article(self):
        s = cssscope.scope(':root{--a:1}\nbody{margin:0}\nhtml{height:100%}\n'
                           'body[data-theme="dark"]{--a:2}\n.sheet p,a:hover{color:red}\n'
                           '@media (max-width:600px){.x{top:0}}\n@font-face{font-family:F;src:url(fonts/f.woff2)}\n'
                           '.modal-overlay{z-index:9}\nbody.barhidden .topbar{top:0}')
        self.assertIn(":is(.pz,.modal-overlay){--a:1}", s)
        self.assertIn(":is(.pz,.modal-overlay){margin:0}", s)
        self.assertNotIn("height:100%", s)
        self.assertIn('html[data-sheet="dark"] :is(.pz,.modal-overlay){--a:2}', s)
        self.assertIn(":is(.pz,.modal-overlay) .sheet p,:is(.pz,.modal-overlay) a:hover{color:red}", s)
        self.assertIn("@media (max-width:600px){\n:is(.pz,.modal-overlay) .x{top:0}", s)
        self.assertIn("@font-face{font-family:F;src:url(fonts/f.woff2)}", s)
        self.assertIn(".modal-overlay{z-index:9}", s)
        self.assertIn("body.barhidden :is(.pz,.modal-overlay) .topbar{top:0}", s)

    def test_a_qr_code_is_a_qr_code(self):
        m = qr.matrix("hello", "medium")
        self.assertEqual(len(m), 21, "five bytes fit version 1")
        finder = [[True] * 7, [True] + [False] * 5 + [True]]
        for x0, y0 in ((0, 0), (14, 0), (0, 14)):
            self.assertEqual(m[y0][x0:x0 + 7], finder[0])
            self.assertEqual(m[y0 + 1][x0:x0 + 7], finder[1])
        self.assertTrue(m[21 - 8][8], "the dark module")
        self.assertEqual(len(qr.matrix("x" * 300, "low")), 4 * 11 + 17, "300 bytes need version 11")
        with self.assertRaises(ValueError):
            qr.matrix("x" * 3000, "high")


class TheTokensAreTheToolbox_s(unittest.TestCase):
    """assets/guide.css copies lib/parseh.css's palette verbatim, theme by
    theme: the two must not drift apart."""

    def blocks(self, css):
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        out = {}
        for sel, body in re.findall(r"(:root(?:\[data-theme=\w+\])?(?::not\([^)]*\))*)\{([^{}]*)\}", css):
            toks = dict(re.findall(r"(--[\w-]+):\s*([^;]+);", body))
            toks = {k: v.strip().lower() for k, v in toks.items() if not k.startswith("--g-")}
            if toks:
                out.setdefault(sel, {}).update(toks)
        return out

    def test_same_tokens_same_values(self):
        ours = self.blocks((GUIDE / "assets" / "guide.css").read_text(encoding="utf-8"))
        theirs = self.blocks((ROOT / "lib" / "parseh.css").read_text(encoding="utf-8"))
        for sel in (":root", ":root[data-theme=dark]", ":root[data-theme=sepia]",
                    ":root:not([data-theme=light]):not([data-theme=sepia])"):
            self.assertEqual(ours.get(sel), theirs.get(sel), sel)

    def test_the_theme_key_and_order_are_parseh_js_s(self):
        ours = (GUIDE / "assets" / "guide.js").read_text(encoding="utf-8")
        theirs = (ROOT / "lib" / "parseh.js").read_text(encoding="utf-8")
        for pat in (r"var KEY = '(\w+)'", r"var ORDER = (\[[^\]]+\])", r"var GLYPH = (\{[^}]+\})"):
            self.assertEqual(re.search(pat, ours).group(1), re.search(pat, theirs).group(1), pat)


# ------------------------------------------------------------------ the real guide, and its copy
class TheGuideItself(unittest.TestCase):
    def test_the_guide_s_own_pages_compile_clean(self):
        with tempfile.TemporaryDirectory() as td:
            report = Site(GUIDE).build(Path(td) / "site")
            self.assertEqual([str(p) for p in report.problems], [])
            self.assertTrue((Path(td) / "site" / "showcase.html").is_file())
            self.assertTrue((Path(td) / "site" / "images" / "flashcard.gif").is_file())

    def test_the_sidebar_and_the_walk_follow_the_front_page_s_map(self):
        """The front page's map is written by hand; the sidebar (nav.js) and
        Previous/Next come from the weights.  They must agree: the reader's
        sections first, and the guide's own pages -- how it is written, the
        showcase -- after the reference, not between Getting started and
        Books."""
        front = (GUIDE / "index.html").read_text(encoding="utf-8")
        doors = re.search(r'<ul class="g-doors">(.*?)</ul>', front, re.S).group(1)
        want = re.findall(r'<a href="([^"]+)"', doors)
        site = Site(GUIDE)
        site.discover()
        root = site.tree()
        self.assertEqual([n["u"] for n in site._nav_data(root)], want)
        # the walk: a section's own page, then its pages, then the next
        # section -- so the tops of the sections come in the same order
        tops = []
        for page in site.reading_order(root):
            top = page.rel.split("/")[0]
            top = top[:-3] if top.endswith(".md") else top
            if not tops or tops[-1] != top:
                tops.append(top)
        self.assertEqual(["site/%s" % (t + ".html" if t == "showcase" else t + "/index.html") for t in tops],
                         want)

    def test_the_workflow_publishes_the_pages_mode(self):
        wf = (ROOT / ".github" / "workflows" / "guide-pages.yml").read_text(encoding="utf-8")
        for said in ("python3 html-guide/build.py --pages _site", "actions/upload-pages-artifact",
                     "actions/deploy-pages", "pages: write", "id-token: write", "workflow_dispatch",
                     "chmod -c -R +rX _site",
                     # the one-time setting that publishes the committed pages
                     "Source: Deploy from a", "Branch: main, folder / (root)"):
            self.assertIn(said, wf)
        # a push only compiles, as a check: the committed pages are what
        # GitHub Pages publishes, and only a run by hand publishes instead
        self.assertRegex(wf, r"(?m)^  deploy:\n    needs: build\n(?:    #.*\n)*"
                             r"    if: github\.event_name == 'workflow_dispatch' && github\.ref_name == 'main'$")
        from engine.export import WORKFLOW
        self.assertIn("chmod -c -R +rX _site", WORKFLOW)
        try:
            import yaml
        except ImportError:
            return
        doc = yaml.safe_load(wf)
        self.assertEqual(doc[True]["push"]["branches"], ["main"])     # `on:` reads as True
        self.assertEqual(doc["jobs"]["deploy"]["needs"], "build")
        self.assertEqual(doc["jobs"]["deploy"]["if"],
                         "github.event_name == 'workflow_dispatch' && github.ref_name == 'main'")
        steps = doc["jobs"]["build"]["steps"]
        publishing = [st for st in steps if "uses" in st and ("configure-pages" in st["uses"]
                                                              or "upload-pages-artifact" in st["uses"])]
        self.assertEqual([st.get("if") for st in publishing], ["github.event_name == 'workflow_dispatch'"] * 2)
        self.assertEqual(doc["permissions"], {"contents": "read", "pages": "write", "id-token": "write"})

    def test_the_repository_root_serves_the_committed_guide(self):
        # GitHub Pages "Deploy from a branch" serves the repository's root:
        # an index.html there sends a visitor to the guide, and .nojekyll
        # keeps site/_parseh/ (a folder Jekyll would drop) in the site
        self.assertTrue((ROOT / ".nojekyll").is_file())
        front = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('content="0; url=html-guide/index.html"', front)
        self.assertIn('href="html-guide/index.html"', front)

    def test_pages_mode_lays_out_a_deployable_folder(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "_site"
            r = subprocess.run([sys.executable, str(GUIDE / "build.py"), "--pages", str(out), "-q"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for name in (".nojekyll", "index.html", "assets/guide.js", "site/nav.js",
                         "site/_parseh/studio.css", "site/showcase.html"):
                self.assertTrue((out / name).is_file(), name)

    def test_an_export_builds_on_its_own_into_the_same_pages(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "website"
            r = subprocess.run([sys.executable, str(GUIDE / "build.py"), "--export", str(dest)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in ("engine/vendor/markdown/app/htmlgen.py", "engine/vendor/lib/languages.json",
                        "engine/vendor/markdown/app/static/app.js", ".github/workflows/pages.yml"):
                self.assertTrue((dest / rel).is_file(), rel)
            self.assertIn("site/", (dest / ".gitignore").read_text(encoding="utf-8"))
            # the copy, built with nothing of Parseh around it and no environment
            env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", td)}
            r = subprocess.run([sys.executable, str(dest / "build.py")], capture_output=True,
                               text=True, env=env, cwd=td)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("the snapshot in engine/vendor/", r.stdout)
            here = Path(td) / "here"
            Site(GUIDE).build(here)
            theirs = dest / "site"
            ours = sorted(p.relative_to(here) for p in here.rglob("*") if p.is_file())
            self.assertEqual(ours, sorted(p.relative_to(theirs) for p in theirs.rglob("*") if p.is_file()))
            for rel in ours:
                self.assertEqual((here / rel).read_bytes(), (theirs / rel).read_bytes(), rel)


# ------------------------------------------------------------------ the folders a compile may take
def snapshot(folder):
    """Every file under `folder` -> its bytes, by its relative path."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p.read_bytes()
            for p in sorted(folder.rglob("*")) if p.is_file()}


class OnlyItsOwnFolders(unittest.TestCase):
    """A compile replaces its folder whole, so it must never be given one
    that holds anything else: `--out ~/Documents` once emptied the folder,
    and `--pages` a website's repository, .git and all."""

    def build(self, *args):
        return subprocess.run([sys.executable, str(GUIDE / "build.py"), *args, "-q"],
                              capture_output=True, text=True)

    def assertRefused(self, r, folder, before):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("nothing was touched", r.stderr)
        self.assertEqual(snapshot(folder), before, "the folder is exactly as it was")

    def test_out_refuses_a_folder_that_holds_something_else(self):
        with tempfile.TemporaryDirectory() as td:
            docs = Path(td) / "Documents"
            write_tree(docs, {"thesis.txt": "four years", "notes/a.md": "# mine\n"})
            before = snapshot(docs)
            self.assertRefused(self.build("--out", str(docs)), docs, before)
            self.assertEqual(os.listdir(td), ["Documents"], "and nothing is left beside it")
            from engine.site import NotOurs
            with self.assertRaises(NotOurs):
                Site(GUIDE).build(docs)
            self.assertEqual(snapshot(docs), before)

    def test_out_takes_a_new_or_empty_folder_and_its_own_earlier_compile(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            for _ in range(2):          # empty, then an earlier compile
                r = self.build("--out", str(out))
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertTrue((out / "showcase.html").is_file())
            self.assertEqual(os.listdir(td), ["out"], "no scratch folder is left beside it")

    def test_pages_refuses_a_website_s_folder(self):
        with tempfile.TemporaryDirectory() as td:
            web = Path(td) / "website"
            write_tree(web, {".git/HEAD": "ref: refs/heads/main\n", ".nojekyll": "",
                             "about.html": "<p>about</p>\n"})
            before = snapshot(web)
            self.assertRefused(self.build("--pages", str(web)), web, before)

    def test_pages_lays_out_again_into_the_folder_it_laid_out(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "_site"
            for _ in range(2):
                r = self.build("--pages", str(out))
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((out / ".parseh-guide-pages").is_file())
            self.assertTrue((out / "site" / "showcase.html").is_file())

    def test_export_refuses_a_project_that_merely_has_a_build_py(self):
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td) / "project"
            write_tree(proj, {"build.py": "print('mine')\n", "engine/core.py": "x = 1\n",
                              "markdown/notes.md": "# mine\n", "README.md": "mine\n"})
            before = snapshot(proj)
            self.assertRefused(self.build("--export", str(proj)), proj, before)

    def test_every_folder_of_a_published_site_is_readable_by_all(self):
        # GitHub Pages refuses a site with a folder others cannot read and
        # enter (deployment_perms_error), and so does a web server running
        # as another user: the compile's temporary folder was 0700
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "_site"
            was = os.umask(0o022)
            try:
                r = self.build("--pages", str(out))
            finally:
                os.umask(was)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            closed = [str(p.relative_to(out)) or "." for p in [out, *out.rglob("*")]
                      if (p.stat().st_mode & (0o005 if p.is_dir() else 0o004))
                      != (0o005 if p.is_dir() else 0o004)]
            self.assertEqual(closed, [], "folders o+rx, files o+r")


# ------------------------------------------------------------------ served by Parseh
class Served(unittest.TestCase):
    def test_only_the_front_page_the_assets_and_the_site_are_served(self):
        with tempfile.TemporaryDirectory() as td:
            g = Path(td)
            write_tree(g, {"index.html": "front", "assets/guide.css": "x", "site/index.html": "sec",
                           "site/a/b.html": "b", "engine/site.py": "secret", "markdown/p.md": "src",
                           "site/.hidden": "no", "build.py": "no"})
            ok = lambda rel: guidebuild.file_for(rel, guide=str(g))  # noqa: E731
            self.assertEqual(Path(ok("")).name, "index.html")
            self.assertEqual(Path(ok("index.html")).read_text(), "front")
            self.assertTrue(ok("assets/guide.css"))
            self.assertEqual(Path(ok("site/a/b.html")).read_text(), "b")
            self.assertEqual(Path(ok("site/")).read_text(), "sec", "a folder answers with its index.html")
            for bad in ("engine/site.py", "markdown/p.md", "build.py", "site/.hidden",
                        "site/../engine/site.py", "assets/../build.py", "../serve.py", "site/nope.html"):
                self.assertIsNone(ok(bad), bad)

    def test_the_compile_job_and_whether_the_site_is_up_to_date(self):
        # a copy of html-guide beside the live studio (symlinked), so the
        # compile is the real one and the sources can be changed
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(GUIDE, root / "html-guide",
                            ignore=shutil.ignore_patterns("site", "vendor", "__pycache__"))
            (root / "markdown").mkdir()
            for d in ("markdown/exlex", "markdown/app", "lib"):
                os.symlink(ROOT / d, root / d)
            shutil.copyfile(ROOT / "HOW TO USE THIS TOOLBOX.pdf", root / "HOW TO USE THIS TOOLBOX.pdf")
            g = str(root / "html-guide")
            st = guidebuild.status(g)
            self.assertEqual((st["parseh"], st["built"], st["stale"]), (True, False, None))
            r = subprocess.run(guidebuild.command(g), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            st = guidebuild.status(g)
            self.assertEqual((st["built"], st["stale"], st["errors"]), (True, False, 0))
            with open(root / "html-guide" / "markdown" / "showcase.md", "a", encoding="utf-8") as f:
                f.write("\nOne more line.\n")
            self.assertTrue(guidebuild.status(g)["stale"], "a changed page makes the site stale")

            import time
            said = []
            job, started = guidebuild.start(g, runner=lambda cmd, say: (said.append(cmd), say("ok"), 0)[2])
            self.assertTrue(started)
            for _ in range(200):
                if guidebuild.status(g)["state"] != "running":
                    break
                time.sleep(0.01)
            st = guidebuild.status(g)
            self.assertEqual((st["state"], st["ok"], st["log"]), ("done", True, ["ok"]))
            self.assertEqual(said[0][-1], os.path.join(g, "build.py"))


if __name__ == "__main__":
    unittest.main()
