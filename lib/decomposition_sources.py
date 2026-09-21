"""Import component structure only; no definitions, readings, paths or SVG reach the UI."""
import json
import re
import xml.etree.ElementTree as ET
import zipfile

# IDS arity, including the newer unary reflection/rotation operators.
IDS_ARITY = {c: 2 for c in '⿰⿱⿴⿵⿶⿷⿸⿹⿺⿻⿼⿽㇯'}
IDS_ARITY.update({'⿲': 3, '⿳': 3, '⿾': 1, '⿿': 1})
KVG = '{http://kanjivg.tagaini.net}'


def parse_ids(text, source):
    """Strict prefix parser. Unknown/unencoded components remain explicit leaves."""
    tokens = re.findall(r'&[^;]+;|[^\s]', text)
    pos = 0

    def node(depth=0):
        nonlocal pos
        if depth > 32 or pos >= len(tokens):
            raise ValueError('incomplete or excessively deep IDS')
        t = tokens[pos]
        pos += 1
        if t in IDS_ARITY:
            return {'operator': t, 'children': [node(depth + 1) for _ in range(IDS_ARITY[t])],
                    'source': source}
        if t in '?？' or t.startswith('&') or '①' <= t <= '⑳' or 0xE000 <= ord(t[0]) <= 0xF8FF:
            return {'kind': 'unknown', 'source': source}
        if t in '[]()':
            raise ValueError('unexpected IDS annotation')
        # Keep an ideographic variation selector attached to its base character.
        if pos < len(tokens) and (0xFE00 <= ord(tokens[pos][0]) <= 0xFE0F or
                                  0xE0100 <= ord(tokens[pos][0]) <= 0xE01EF):
            t += tokens[pos]
            pos += 1
        return {'character': t, 'source': source}

    result = node()
    if pos != len(tokens):
        raise ValueError('trailing IDS tokens')
    return result


def ids_record(character, ids, source):
    if not ids or ids.startswith(('？', '?')):
        return {'character': character, 'source': source, 'status': 'missing'}
    try:
        tree = parse_ids(ids, source)
    except ValueError:
        return {'character': character, 'source': source, 'status': 'missing'}
    if tree.get('character') == character:
        tree['status'] = 'atomic'
        return tree
    if tree.get('operator'):
        return dict(tree, character=character)
    return {'character': character, 'children': [tree], 'source': source}


def makemeahanzi(path):
    with open(path, encoding='utf-8') as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            character = row.get('character', '')
            if len(character) == 1:
                yield 'zh', character, ids_record(character, row.get('decomposition', ''), 'makemeahanzi')


def cjkvi(path):
    with open(path, encoding='utf-8') as stream:
        for line in stream:
            fields = line.rstrip().split('\t')
            if len(fields) < 3 or line.startswith('#'):
                continue
            character = fields[1]
            if len(character) != 1:
                continue
            candidates = []
            for field in fields[2:]:
                m = re.fullmatch(r'([^\[]+)(?:\[([A-Z]+)\])?', field)
                if m:
                    candidates.append((m[1], m[2] or ''))
            for lang, locale in [('ja', 'J'), ('zh', 'G')]:
                # Locale-specific shapes first, then neutral, then traditional
                # Chinese. Never use a Japanese-only shape as the Chinese default.
                usable = [(0 if locale in tags else 1 if not tags else 2, ids)
                          for ids, tags in candidates
                          if locale in tags or not tags or (lang == 'zh' and 'T' in tags)]
                if usable:
                    ids = min(enumerate(usable), key=lambda x: (x[1][0], x[0]))[1][1]
                    yield lang, character, ids_record(character, ids, 'cjkvi')


def kanjivg_svg(data):
    """Named component groups; flatten anonymous graphics and coalesce stroke-order parts."""
    root = ET.fromstring(data)
    # Current releases use https + trailing slash; older ones used http.
    for element in root.iter():
        for name, value in list(element.attrib.items()):
            if name.startswith(('{https://kanjivg.tagaini.net/}', '{https://kanjivg.tagaini.net}',
                                '{http://kanjivg.tagaini.net/}')):
                element.set(KVG + name.split('}', 1)[1], value)
    groups = [g for g in root.iter() if g.tag.rsplit('}', 1)[-1] == 'g']
    outer = next((g for g in groups if g.get(KVG + 'element')), None)
    if outer is None:
        return None

    def convert(group):
        children = []
        seen_parts = {}
        positions = []
        for child in group:
            if child.tag.rsplit('}', 1)[-1] != 'g':
                continue
            part = child.get(KVG + 'part')
            key = (child.get(KVG + 'element'), child.get(KVG + 'number', ''))
            if part and key[0] and key in seen_parts:
                # A split element is one component, not two copies of its shape.
                continue
            converted = convert(child)
            if part and key[0]:
                converted = {'character': key[0], 'source': 'kanjivg'}
                seen_parts[key] = True
            if converted:
                if not converted.get('character') and not converted.get('operator'):
                    children.extend(converted.get('children', []))
                else:
                    children.append(converted)
                positions.append(child.get(KVG + 'position', ''))
        character = group.get(KVG + 'element')
        out = {'source': 'kanjivg'}
        if character:
            out['character'] = character
        if group.get(KVG + 'original') and group.get(KVG + 'original') != character:
            out['variantOf'] = group.get(KVG + 'original')
        if group.get(KVG + 'partial') == 'true':
            out['partial'] = True
        # Wrappers naming the same glyph do not add a level to the learner tree.
        if len(children) == 1 and children[0].get('character') == character:
            child = children[0]
            out.update({k: v for k, v in child.items() if k != 'character'})
            return out
        if children:
            out['children'] = children
            # Only infer layouts explicitly supported by positional metadata.
            layout = {('left', 'right'): '⿰', ('top', 'bottom'): '⿱',
                      ('left', 'middle', 'right'): '⿲', ('top', 'middle', 'bottom'): '⿳',
                      ('tare', 'tarec'): '⿸', ('nyo', 'nyoc'): '⿺',
                      ('⿵A', '⿵B'): '⿵'}
            operator = layout.get(tuple(positions))
            if operator and len(children) == IDS_ARITY[operator]:
                out['operator'] = operator
            # Ungrouped strokes are represented once, never as individual paths.
            if any(c.tag.rsplit('}', 1)[-1] == 'path' for c in group):
                out.pop('operator', None)
                out['children'].append({'kind': 'unknown', 'source': 'kanjivg'})
        return out if character or children else None

    tree = convert(outer)
    if tree and not tree.get('children'):
        tree['status'] = 'atomic'
    return tree


def kanjivg(path):
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not re.search(r'(?:^|/)kanji/[0-9a-f]{5,6}\.svg$', name):
                continue
            info = archive.getinfo(name)
            if info.file_size > 2_000_000:
                raise ValueError('unexpectedly large KanjiVG entry')
            tree = kanjivg_svg(archive.read(name))
            if tree:
                yield 'ja', tree['character'], tree
