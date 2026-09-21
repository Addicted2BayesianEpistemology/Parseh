"""engine.highlight -- a small syntax highlighter, standard library only.

A language is an ordered list of (token class, regex); the first rule that
matches at a position wins, and anything no rule claims is plain text.  That
is all a guide's code blocks need to be readable -- keywords, strings,
comments, numbers, tags -- and it keeps the output tiny and predictable:
one <span class="t-CLASS"> per token, coloured by guide.css from the
palette, so every theme colours code the same way it colours the page.

The Markdown lexer knows the Parseh dialect as well as Hugo's: a
`[text]{tl}` mark, `:::exercise`, `{translit:…}`, a lemma heading with its
`|` fields, `✗`/`✅`/`→`/`⏎` and the rest are coloured as the marks they are,
so a page explaining the dialect shows what each piece of syntax is.

    lex(code, lang) -> [(class or "", text), ...]    the tokens, in order
    render_lines(code, lang) -> [html of line 1, html of line 2, ...]
"""
import html
import re

_ESC = lambda s: html.escape(s, quote=False)  # noqa: E731


def _kw(words):
    return r"\b(?:%s)\b" % "|".join(sorted(words.split(), key=len, reverse=True))


# Token classes (guide.css colours each): com comment, str string, kw keyword,
# num number, lit literal (true/null), fn function or command, tag, attr,
# var variable, op punctuation that matters, head a heading, mark a Parseh
# mark, meta a fence, shortcode or directive, em/strong emphasis, link.
LANGS = {}

LANGS["python"] = [
    ("com", r"#[^\n]*"),
    ("str", r"(?i:[rbuf]{0,2})(?:'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")"),
    ("str", r"(?i:[rbuf]{0,2})(?:'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\")"),
    ("meta", r"@[\w.]+"),
    ("kw", _kw("and as assert async await break class continue def del elif else except "
               "finally for from global if import in is lambda nonlocal not or pass raise "
               "return try while with yield match case")),
    ("lit", _kw("True False None self")),
    ("fn", r"\b[A-Za-z_]\w*(?=\()"),
    ("num", r"\b(?:0[xob][\da-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][-+]?\d+)?)\b"),
]

LANGS["bash"] = [
    ("com", r"(?<![\w$])#[^\n]*"),
    ("str", r"'[^']*'"),
    ("str", r"\"(?:[^\"\\]|\\.)*\""),
    ("var", r"\$(?:\{[^}\n]*\}|\w+|[@*#?$!0-9-])"),
    ("kw", _kw("if then else elif fi for in do done case esac while until function "
               "return local export set unset shift exit break continue source")),
    ("fn", r"(?:^|(?<=[;&|] )|(?<=\|)|(?<=&& ))[ \t]*[A-Za-z_./][\w./-]*"),
    ("op", r"(?<=[ \t])--?[A-Za-z][\w-]*"),
    ("num", r"\b\d+\b"),
]

LANGS["json"] = [
    ("attr", r"\"(?:[^\"\\\n]|\\.)*\"(?=\s*:)"),
    ("str", r"\"(?:[^\"\\\n]|\\.)*\""),
    ("lit", r"\b(?:true|false|null)\b"),
    ("num", r"-?\b\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\b"),
]

LANGS["yaml"] = [
    ("com", r"(?:(?<=\s)|^)#[^\n]*"),
    ("meta", r"^(?:---|\.\.\.)[ \t]*$"),
    ("attr", r"(?:^|(?<=[ \t-]))[\w./-]+(?=[ \t]*:(?:[ \t]|$))"),
    ("str", r"\"(?:[^\"\\\n]|\\.)*\"|'[^'\n]*'"),
    ("lit", r"\b(?:true|false|yes|no|null|on|off)\b|~"),
    ("num", r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])"),
    ("op", r"^[ \t]*-(?=[ \t])|[|>][-+]?(?=[ \t]*$)"),
]

LANGS["toml"] = [
    ("com", r"#[^\n]*"),
    ("head", r"^[ \t]*\[\[?[^\]\n]+\]\]?"),
    ("attr", r"^[ \t]*[\w.\"'-]+(?=[ \t]*=)"),
    ("str", r"\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"(?:[^\"\\\n]|\\.)*\"|'[^'\n]*'"),
    ("lit", r"\b(?:true|false)\b"),
    ("num", r"(?<![\w.])[-+]?\d[\d_]*(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])"),
]

LANGS["html"] = [
    ("com", r"<!--[\s\S]*?-->"),
    ("meta", r"<![A-Za-z][^>]*>"),
    ("tag", r"</?[A-Za-z][\w:-]*|/?>"),
    ("attr", r"(?<=\s)[A-Za-z_:][\w:.-]*(?=\s*=)"),
    ("str", r"\"[^\"]*\"|'[^']*'"),
    ("lit", r"&(?:#\d+|#x[\da-fA-F]+|\w+);"),
]

LANGS["css"] = [
    ("com", r"/\*[\s\S]*?\*/"),
    ("str", r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'"),
    ("meta", r"@[\w-]+"),
    ("attr", r"(?<![\w-])--?[A-Za-z][\w-]*(?=\s*:)"),
    ("num", r"#[\da-fA-F]{3,8}\b|(?<![\w-])-?\d*\.?\d+(?:px|em|rem|%|vh|vw|s|ms|deg|fr|ch|ex)?\b"),
    ("fn", r"\b[\w-]+(?=\()"),
    ("tag", r"[.#]?[A-Za-z][\w-]*(?=[^{};:]*\{)"),
]

LANGS["javascript"] = [
    ("com", r"//[^\n]*|/\*[\s\S]*?\*/"),
    ("str", r"`(?:[^`\\]|\\.)*`|'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\""),
    ("kw", _kw("async await break case catch class const continue debugger default delete do "
               "else export extends finally for function if import in instanceof let new of "
               "return static super switch this throw try typeof var void while with yield")),
    ("lit", _kw("true false null undefined NaN Infinity")),
    ("fn", r"\b[A-Za-z_$][\w$]*(?=\()"),
    ("num", r"\b(?:0[xob][\da-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][-+]?\d+)?)\b"),
]

LANGS["latex"] = [
    ("com", r"(?<!\\)%[^\n]*"),
    ("fn", r"\\(?:[A-Za-z@]+\*?|.)"),
    ("str", r"\$\$[\s\S]*?\$\$|\$(?:[^$\\\n]|\\.)+\$"),
    ("op", r"[{}\[\]&]"),
    ("num", r"\b\d+(?:\.\d+)?(?:pt|mm|cm|in|em|ex|bp)?\b"),
]

# The markdown the guide is written in: Hugo's, and the Parseh dialect's
# marks on top.  Rules that belong to a whole line come first and are
# anchored with ^ (the patterns are compiled with re.M).
LANGS["markdown"] = [
    ("com", r"<!--[\s\S]*?-->"),
    ("meta", r"^[ \t]*(?:`{3,}|~{3,})[^\n]*"),
    ("meta", r"^(?:---|\+\+\+)[ \t]*$"),
    ("meta", r"\{\{[<%][\s\S]*?[>%]\}\}"),
    ("mark", r"^[ \t]*:::(?i:exercise|math)?[^\n]*"),
    ("head", r"^#{1,6}[ \t][^\n]*"),
    ("head", r"^[ \t]*(?:=+|-+)[ \t]*$"),
    ("op", r"^[ \t]*>"),
    ("op", r"^[ \t]*(?:[-*+]|\d{1,9}[.)])(?=[ \t])"),
    ("attr", r"^[ \t]*[a-z][a-z0-9-]*:(?=[ \t]|$)"),
    ("str", r"(?P<bt>`+)[\s\S]*?(?P=bt)"),
    ("mark", r"\[\^[^\]\s]+\]|\^\[(?:[^\[\]]|\[[^\[\]]*\])*\]"),
    ("mark", r"\[\[[^\[\]]+\]\]"),
    ("mark", r"!?\[(?:[^\[\]\n]|\[[^\[\]\n]*\])*\]\{[^{}\n]*\}"),
    ("mark", r"@\[[^\[\]\n]*\]\([^()\s]*\)(?:\{[^{}\n]*\})?"),
    ("link", r"!?\[(?:[^\[\]\n]|\[[^\[\]\n]*\])*\](?:\([^()\n]*(?:\([^()\n]*\)[^()\n]*)*\)|\[[^\[\]\n]*\])"),
    ("link", r"<(?:https?|mailto):[^>\s]*>|\bhttps?://[^\s<>()]+"),
    ("strong", r"\*\*(?=\S)[^*\n]+?\*\*|__(?=\S)[^_\n]+?__"),
    ("em", r"(?<![\w*])\*(?=\S)[^*\n]+?\*(?!\*)|(?<![\w_])_(?=\S)[^_\n]+?_(?![\w_])"),
    ("mark", r"~~[^~\n]+~~"),
    ("mark", r"[✗❌✅→⏎]|->|=>|\|"),
    ("lit", r"\{[#.][^{}\n]*\}"),
]
LANGS["parseh"] = LANGS["markdown"]

LANGS["text"] = []

ALIASES = {"py": "python", "python3": "python", "sh": "bash", "shell": "bash",
           "zsh": "bash", "console": "bash", "shell-session": "bash",
           "bat": "text", "yml": "yaml", "xml": "html", "svg": "html", "htm": "html",
           "js": "javascript", "mjs": "javascript", "jsonc": "json",
           "tex": "latex", "md": "markdown", "hugo": "markdown",
           "parseh-markdown": "parseh", "parseh-example": "parseh",
           "plain": "text", "plaintext": "text", "txt": "text", "": "text", "none": "text"}

# what the bar above a block calls each language
LABELS = {"python": "Python", "bash": "shell", "json": "JSON", "yaml": "YAML",
          "toml": "TOML", "html": "HTML", "css": "CSS", "javascript": "JavaScript",
          "latex": "LaTeX", "markdown": "Markdown", "parseh": "Parseh Markdown",
          "text": "text"}

_COMPILED = {}


def canonical(lang):
    """A fence's language name -> the lexer's (unknown names -> 'text')."""
    lang = (lang or "").strip().lower()
    lang = ALIASES.get(lang, lang)
    return lang if lang in LANGS else "text"


def _master(lang):
    rx = _COMPILED.get(lang)
    if rx is None:
        rules = LANGS[lang]
        parts = []
        for k, (_cls, pat) in enumerate(rules):
            parts.append("(?P<r%d>%s)" % (k, pat))
        # one pattern for the lot, line anchors on: every rule written with
        # ^ or $ means the start or end of a source line
        rx = re.compile("|".join(parts), re.M) if parts else None
        _COMPILED[lang] = rx
    return rx


def lex(code, lang):
    """code -> [(class, text), ...]: the classes of `lang`'s rules, "" for
    text none of them claims."""
    lang = canonical(lang)
    rx = _master(lang)
    if rx is None:
        return [("", code)] if code else []
    rules = LANGS[lang]
    out, at = [], 0
    for m in rx.finditer(code):
        if m.end() == m.start():
            continue
        if m.start() > at:
            out.append(("", code[at:m.start()]))
        # the rule whose group matched (a rule may hold a group of its own,
        # so lastgroup is not relied on)
        k = next(int(name[1:]) for name, v in m.groupdict().items()
                 if v is not None and name[0] == "r" and name[1:].isdigit())
        out.append((rules[k][0], m.group(0)))
        at = m.end()
    if at < len(code):
        out.append(("", code[at:]))
    return out


def render_lines(code, lang):
    """code -> one HTML string per source line.  A token that spans lines (a
    block comment, a triple-quoted string) is closed at each line's end and
    opened again on the next, so every line stands alone -- which is what
    lets a line be numbered or highlighted by itself."""
    lines = [[]]
    for cls, text in lex(code, lang):
        pieces = text.split("\n")
        for n, piece in enumerate(pieces):
            if n:
                lines.append([])
            if piece:
                lines[-1].append(('<span class="t-%s">%s</span>' % (cls, _ESC(piece)))
                                 if cls else _ESC(piece))
    return ["".join(parts) for parts in lines]
