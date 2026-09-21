"""Shared CharacterComponentNode domain and local-only decomposition service.

Nodes have character/operator/children/source and optional variantOf, partial,
kind=unknown, status. Data packs are separate SQLite files, each with provenance
and its own licence. No external request is made by this module.
"""
import json
import sqlite3
import unicodedata
from contextlib import ExitStack, closing
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'components'
PREFERRED = {'ja': 'kanjivg', 'zh': 'makemeahanzi'}
PACKS = {
    'kanjivg': {'name': 'KanjiVG', 'languages': ['ja'], 'licence': 'CC BY-SA 3.0',
               'url': 'https://kanjivg.tagaini.net/', 'attribution': 'Ulrich Apel and KanjiVG contributors'},
    'makemeahanzi': {'name': 'Make Me a Hanzi', 'languages': ['zh'], 'licence': 'LGPL-3.0-or-later',
                   'url': 'https://github.com/skishore/makemeahanzi',
                   'attribution': 'Make Me a Hanzi contributors; derived from Unihan and CJKlib'},
    'cjkvi': {'name': 'CJKVI-IDS', 'languages': ['ja', 'zh'], 'licence': 'GPL-2.0',
             'url': 'https://github.com/cjkvi/cjkvi-ids',
             'attribution': 'CJKVI Database, based on the CHISE IDS Database'},
}
# Stop automatic expansion at familiar learning units. A user can still open
# any of these as the root to inspect the source's finer structure.
BASIC_COMPONENTS = frozenset('一丨丶丿乙亅人儿入八刀力十卜又口囗土士夕女子宀寸小山川工巾干广弓彡心手日月木目水火田金石禾竹糸言耳足車门門')
MAX_DEPTH = 7
MAX_NODES = 160


def is_han(character):
    if not isinstance(character, str) or not 1 <= len(character) <= 2:
        return False
    # Unicode names cover supplementary planes without a BMP-only range.
    name = unicodedata.name(character[0], '')
    han = name.startswith(('CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-')) or character[0] == '〇'
    return han and (len(character) == 1 or 0xFE00 <= ord(character[1]) <= 0xFE0F or
                    0xE0100 <= ord(character[1]) <= 0xE01EF)


def path_for(source):
    if source not in PACKS:
        raise ValueError('unknown decomposition source')
    return Path(DATA_DIR) / (source + '.db')


def connect(source):
    path = path_for(source)
    if not path.is_file():
        return None
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def about(source):
    try:
        conn = connect(source)
        if conn is None:
            return {}
        with closing(conn):
            return json.loads(conn.execute('SELECT value FROM meta WHERE key="manifest"').fetchone()[0])
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return {}


def packs():
    out = []
    for source, info in PACKS.items():
        meta = about(source)
        row = dict(info, source=source, have=bool(meta), entries=meta.get('entries', 0),
                   built=meta.get('built', ''), size=0)
        if meta:
            try:
                row['size'] = path_for(source).stat().st_size
            except OSError:
                pass
        out.append(row)
    return out


def available(code):
    return code in PREFERRED and any(about(s) for s in (PREFERRED[code], 'cjkvi'))


def meanings(code, characters):
    """Reuse the installed dictionary; never import meanings from component packs."""
    import lookup
    have = lookup.available(code)
    out = {}
    if have:
        for character in characters:
            result = lookup.look_up(code, character) or {}
            senses = []
            for word in result.get('words', []):
                for hit in word.get('hits', []):
                    for sense in hit.get('senses', [])[:2]:
                        if sense and sense not in senses:
                            senses.append(sense)
                if senses:
                    break
            out[character] = '; '.join(senses[:2])[:240]
    return out, lookup.about(code) if have else {}


def character_tree(code, character, include_meanings=True):
    if code not in PREFERRED:
        raise ValueError('character decomposition supports Japanese and Chinese')
    if not is_han(character):
        raise ValueError('select one kanji or hanzi')
    # Default shape for an IVS, retained as the displayed root. No claim of
    # a glyph-specific decomposition is made for an unsupported variant.
    base = character[0]
    sources = [PREFERRED[code], 'cjkvi']
    manifest = {}
    with ExitStack() as stack:
        connections = []
        for source in sources:
            conn = connect(source)
            if conn is not None:
                connections.append((source, stack.enter_context(closing(conn))))
        cache = {}

        def lookup_node(char):
            char = char[0] if is_han(char) else char
            if char in cache:
                return cache[char]
            candidate = None
            for source, conn in connections:
                row = conn.execute('SELECT tree FROM node WHERE lang=? AND character=?', (code, char)).fetchone()
                if row:
                    node = json.loads(row[0])
                    candidate = candidate or node
                    if node.get('status') != 'missing':
                        cache[char] = node
                        return node
            cache[char] = candidate
            return candidate

        count = 0

        def expand(node, ancestors=(), depth=0):
            nonlocal count
            count += 1
            node = dict(node)
            char = node.get('character')
            source = node.get('source')
            if source:
                manifest[source] = dict(PACKS[source], source=source)
            if depth >= MAX_DEPTH or count >= MAX_NODES or char in ancestors:
                node.pop('children', None)
                node['truncated'] = True
                return node
            if depth and char in BASIC_COMPONENTS:
                node.pop('children', None)
                node.pop('operator', None)
                node['status'] = 'basic'
                return node
            if char and not node.get('children') and node.get('status') != 'atomic' and not node.get('partial'):
                found = lookup_node(char)
                if found:
                    # Keep a contextual variant identity alongside its full entry.
                    node = dict(found, **{k: v for k, v in node.items() if k in ('variantOf', 'partial')})
                    source = node.get('source')
                    if source:
                        manifest[source] = dict(PACKS[source], source=source)
            if node.get('children'):
                next_ancestors = ancestors + ((char,) if char else ())
                node['children'] = [expand(c, next_ancestors, depth + 1) for c in node['children'][:12]]
            return node

        found = lookup_node(base)
        tree = expand(found) if found else {'character': base, 'status': 'missing'}
        status = 'not_installed' if not connections else tree.get('status', 'available')
        if status == 'available' and not tree.get('children'):
            status = 'atomic'
        tree['character'] = character
    chars = set()

    def collect(node):
        for field in ('character', 'variantOf'):
            if node.get(field):
                chars.add(node[field])
        for child in node.get('children', []):
            collect(child)
    collect(tree)
    definitions, dictionary = meanings(code, chars) if include_meanings else ({}, {})
    return {'ok': True, 'lang': code, 'character': character, 'status': status, 'tree': tree,
            'meanings': definitions, 'dictionary': dictionary, 'sources': list(manifest.values()),
            'variant_fallback': len(character) > 1}
