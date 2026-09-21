"""engine.frontmatter -- Hugo's three front matters, read without a library.

    ---            +++            {
    title: A       title = "A"      "title": "A",
    weight: 2      weight = 2       "weight": 2
    ---            +++            }

YAML between `---` lines, TOML between `+++` lines, or a JSON object that
opens the file -- the three shapes Hugo reads.  Only the standard library is
at hand, so YAML and TOML are read here, as far as a page's front matter
ever goes: scalars (strings plain, "double" and 'single' quoted, numbers,
booleans, null), lists (`[a, b]`, or `- a` lines), nested maps by
indentation or `[table]` headers, `|` and `>` block strings, and comments.
Anchors, tags, multi-document streams and dates as objects are not read;
a date stays the string it was written as.

Keys are lower-cased at the top level, as Hugo treats them.
"""
import json
import re


class FrontMatterError(ValueError):
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line            # 1-based, in the file


def split(text):
    """text -> (front matter dict, body text, the body's first line number
    (1-based), the format name or None)."""
    text = text.replace("\r\n", "\n").lstrip("\ufeff")
    lines = text.split("\n")
    if not lines:
        return {}, text, 1, None
    first = lines[0].rstrip()
    if first in ("---", "+++"):
        for j in range(1, len(lines)):
            if lines[j].rstrip() == first:
                block = lines[1:j]
                data = read_yaml(block, 2) if first == "---" else read_toml(block, 2)
                return _lower(data), "\n".join(lines[j + 1:]), j + 2, \
                    "yaml" if first == "---" else "toml"
        raise FrontMatterError("the front matter opened by %r on line 1 is "
                               "never closed" % first, 1)
    if first.startswith("{"):
        try:
            data, end = json.JSONDecoder().raw_decode(text)
        except ValueError as e:
            raise FrontMatterError("the JSON front matter does not read: %s" % e, 1)
        if not isinstance(data, dict):
            raise FrontMatterError("JSON front matter must be an object", 1)
        rest = text[end:]
        used = text[:end].count("\n")
        # the rest of the line the object closed on belongs to it
        nl = rest.find("\n")
        body = rest[nl + 1:] if nl >= 0 else ""
        return _lower(data), body, used + 2, "json"
    return {}, text, 1, None


def _lower(d):
    return {str(k).lower(): v for k, v in d.items()}


# ------------------------------------------------------------------ scalars
_NUM = re.compile(r"^[-+]?(\d[\d_]*)(\.\d+)?([eE][-+]?\d+)?$")


def _scalar(s, line):
    s = s.strip()
    if s == "":
        return ""
    if s[0] == '"':
        try:
            end = _quoted_end(s, '"')
            return json.loads(s[:end + 1])
        except ValueError:
            raise FrontMatterError("a double-quoted string does not close", line)
    if s[0] == "'":
        end = _quoted_end(s, "'")
        if end < 0:
            raise FrontMatterError("a single-quoted string does not close", line)
        return s[1:end].replace("''", "'")
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "~"):
        return None
    if _NUM.match(s):
        t = s.replace("_", "")
        try:
            return int(t) if re.fullmatch(r"[-+]?\d+", t) else float(t)
        except ValueError:
            return s
    return s


def _quoted_end(s, q):
    i = 1
    while i < len(s):
        c = s[i]
        if q == '"' and c == "\\":
            i += 2
            continue
        if c == q:
            if q == "'" and i + 1 < len(s) and s[i + 1] == "'":
                i += 2
                continue
            return i
        i += 1
    return -1


def _strip_comment(s):
    """A `#` comment off the end of a line, outside quotes."""
    out, q = [], None
    for i, c in enumerate(s):
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        out.append(c)
    return "".join(out).rstrip()


def _flow(s, line):
    """`[a, "b", 3]` or `{k: v}` -> a list or a dict."""
    s = s.strip()
    try:
        return json.loads(s)
    except ValueError:
        pass
    if s.startswith("[") and s.endswith("]"):
        return [_flow_item(x, line) for x in _split_top(s[1:-1])]
    if s.startswith("{") and s.endswith("}"):
        out = {}
        for x in _split_top(s[1:-1]):
            k, sep, v = x.partition(":") if ":" in x else x.partition("=")
            if not sep:
                raise FrontMatterError("a {map} entry has no value: %r" % x, line)
            out[_scalar(k, line)] = _flow_item(v, line)
        return out
    raise FrontMatterError("cannot read %r" % s, line)


def _flow_item(x, line):
    x = x.strip()
    return _flow(x, line) if x[:1] in "[{" else _scalar(x, line)


def _split_top(s):
    parts, depth, q, cur = [], 0, None, []
    for c in s:
        if q:
            cur.append(c)
            if c == q:
                q = None
            continue
        if c in "\"'":
            q = c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(c)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [p for p in (x.strip() for x in parts) if p]


# ------------------------------------------------------------------ YAML
def read_yaml(lines, first_line=1):
    """The YAML a front matter is written in -> a dict.  `first_line` is the
    file line of lines[0], for the errors."""
    rows = []
    for k, raw in enumerate(lines):
        rows.append((first_line + k, raw))
    value, _ = _yaml_block(rows, 0, 0)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise FrontMatterError("front matter must be a map of keys", first_line)
    return value


def _indent(s):
    return len(s) - len(s.lstrip(" "))


def _yaml_block(rows, i, indent):
    """The node starting at rows[i], all of whose lines are indented at
    least `indent` -> (value, next index)."""
    # skip blanks and comments
    while i < len(rows) and not _strip_comment(rows[i][1]).strip():
        i += 1
    if i >= len(rows):
        return None, i
    line_no, raw = rows[i]
    ind = _indent(raw)
    if ind < indent:
        return None, i
    text = _strip_comment(raw).strip()
    if text.startswith("- ") or text == "-":
        out = []
        while i < len(rows):
            line_no, raw = rows[i]
            t = _strip_comment(raw).strip()
            if not t:
                i += 1
                continue
            if _indent(raw) != ind or not (t.startswith("- ") or t == "-"):
                break
            item = t[1:].strip()
            if not item:
                v, i = _yaml_block(rows, i + 1, ind + 1)
                out.append(v)
                continue
            if re.match(r"^[^\s\"'\[{][^:]*:(\s|$)", item) and not item.startswith(("http:", "https:")):
                # `- key: value` starts a map inside the list: its other keys
                # are indented to where `key` begins
                sub = [(line_no, " " * (ind + 2) + item)]
                j = i + 1
                while j < len(rows) and (not rows[j][1].strip()
                                         or _indent(rows[j][1]) > ind):
                    sub.append(rows[j])
                    j += 1
                v, _ = _yaml_block(sub, 0, ind + 2)
                out.append(v)
                i = j
                continue
            out.append(_flow_item(item, line_no) if item[:1] in "[{" else _scalar(item, line_no))
            i += 1
        return out, i
    out = {}
    while i < len(rows):
        line_no, raw = rows[i]
        t = _strip_comment(raw)
        if not t.strip():
            i += 1
            continue
        if _indent(raw) < ind:
            break
        if _indent(raw) > ind:
            raise FrontMatterError("this line is indented more than the key above "
                                   "it expects", line_no)
        m = re.match(r'^\s*("(?:[^"\\]|\\.)*"|\'[^\']*\'|[^:#][^:]*?)\s*:(?:\s+(.*)|\s*)$', t)
        if not m:
            raise FrontMatterError("expected `key: value`, found %r" % t.strip(), line_no)
        key = _scalar(m.group(1), line_no)
        rest = (m.group(2) or "").strip()
        i += 1
        if rest in ("|", "|-", "|+", ">", ">-", ">+"):
            body, block_ind = [], None
            while i < len(rows):
                r = rows[i][1]
                if r.strip() and _indent(r) <= ind:
                    break
                if r.strip() and block_ind is None:
                    block_ind = _indent(r)
                body.append(r[block_ind:] if block_ind is not None and r.strip() else "")
                i += 1
            while body and not body[-1]:
                body.pop()
            if rest.startswith(">"):
                value = re.sub(r"(?<!\n)\n(?!\n)", " ", "\n".join(body))
            else:
                value = "\n".join(body)
            if not rest.endswith("-"):
                value += "\n"
            out[key] = value
        elif rest == "":
            v, i = _yaml_block(rows, i, ind + 1)
            out[key] = v
        elif rest[:1] in "[{":
            out[key] = _flow(rest, line_no)
        else:
            out[key] = _scalar(rest, line_no)
    return out, i


# ------------------------------------------------------------------ TOML
def read_toml(lines, first_line=1):
    out, table = {}, None
    table = out
    for k, raw in enumerate(lines):
        line_no = first_line + k
        t = _strip_comment(raw).strip()
        if not t:
            continue
        m = re.match(r"^\[\s*([^\[\]]+?)\s*\]$", t)
        if m:
            table = out
            for part in m.group(1).split("."):
                part = _scalar(part, line_no) if part.strip()[:1] in "\"'" else part.strip()
                table = table.setdefault(part, {})
                if not isinstance(table, dict):
                    raise FrontMatterError("[%s] names a value, not a table" % m.group(1), line_no)
            continue
        key, sep, value = t.partition("=")
        if not sep:
            raise FrontMatterError("expected `key = value`, found %r" % t, line_no)
        key = key.strip()
        key = _scalar(key, line_no) if key[:1] in "\"'" else key
        value = value.strip()
        table[key] = _flow(value, line_no) if value[:1] in "[{" else _scalar(value, line_no)
    return out
