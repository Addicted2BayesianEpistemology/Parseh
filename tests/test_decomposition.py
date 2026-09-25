# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline component import/domain/API regression tests. python -m unittest discover -s tests -p test_decomposition.py"""
import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT))
import decomposition as domain
import decomposition_sources as sources
import getdecomposition as installer


def svg(body, namespace='http://kanjivg.tagaini.net'):
    return ('<svg xmlns:kvg="%s"><g id="paths">%s</g><g id="numbers"><text>1</text></g></svg>' % (namespace, body)).encode()


class ImportTests(unittest.TestCase):
    def test_ids_operators_unicode_and_unknowns(self):
        for operator, arity in sources.IDS_ARITY.items():
            node = sources.parse_ids(operator + '木' * arity, 'cjkvi')
            self.assertEqual(len(node['children']), arity)
        tree = sources.parse_ids('⿰𠮷\U000E0100⿱木？', 'makemeahanzi')
        self.assertEqual(tree['children'][0]['character'], '𠮷\U000E0100')
        self.assertEqual(tree['children'][1]['children'][1]['kind'], 'unknown')
        self.assertEqual(sources.parse_ids('&CDP-ABCD;', 'cjkvi')['kind'], 'unknown')
        for invalid in ['⿱木', '⿰木木木', '⿿' * 34 + '木']:
            with self.assertRaises(ValueError):
                sources.parse_ids(invalid, 'cjkvi')
        self.assertEqual(sources.ids_record('木', '木', 'cjkvi')['status'], 'atomic')
        self.assertEqual(sources.ids_record('木', '？', 'makemeahanzi')['status'], 'missing')

    def test_kanjivg_hierarchy_and_namespaces(self):
        body = '<g kvg:element="想"><g kvg:element="相" kvg:position="top"><g kvg:element="木" kvg:position="left"><path/></g><g kvg:element="目" kvg:position="right"><path/></g></g><g kvg:element="心" kvg:position="bottom"><path/></g></g>'
        for namespace in ['http://kanjivg.tagaini.net', 'https://kanjivg.tagaini.net/']:
            tree = sources.kanjivg_svg(svg(body, namespace))
            self.assertEqual(tree['operator'], '⿱')
            self.assertEqual([c['character'] for c in tree['children']], ['相', '心'])
            self.assertEqual(tree['children'][0]['operator'], '⿰')
            self.assertNotIn('path', json.dumps(tree))

    def test_graphical_wrappers_parts_and_partial_variants(self):
        tree = sources.kanjivg_svg(svg('<g kvg:element="回"><g><g kvg:element="囗" kvg:part="1"><path/></g><g kvg:element="口"><path/></g><g kvg:element="囗" kvg:part="2"><path/></g></g></g>'))
        self.assertEqual([c['character'] for c in tree['children']], ['囗', '口'])
        tree = sources.kanjivg_svg(svg('<g kvg:element="仮"><g kvg:element="亻" kvg:original="人" kvg:partial="true"/><path/></g>'))
        self.assertEqual(tree['children'][0]['variantOf'], '人')
        self.assertTrue(tree['children'][0]['partial'])
        self.assertEqual(tree['children'][1]['kind'], 'unknown')
        wrapper = sources.kanjivg_svg(svg('<g kvg:element="木"><g kvg:element="木"><path/></g></g>'))
        self.assertNotIn('children', wrapper)

    def test_cjkvi_locale_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ids.txt'
            path.write_text('U+4E0E\t与\t⿹②一[GTKV]\t⿻②一[J]\nU+20000\t𠀀\t⿱一木\n')
            records = {(lang, char): tree for lang, char, tree in sources.cjkvi(path)}
            self.assertEqual(records['ja', '与']['operator'], '⿻')
            self.assertEqual(records['zh', '与']['operator'], '⿹')
            self.assertIn(('ja', '𠀀'), records)


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = patch.object(domain, 'DATA_DIR', self.root / 'packs')
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def pack(self, source, records):
        path = domain.path_for(source)
        path.parent.mkdir(exist_ok=True)
        with sqlite3.connect(path) as conn:
            conn.executescript('CREATE TABLE node(lang TEXT,character TEXT,tree TEXT,PRIMARY KEY(lang,character)); CREATE TABLE meta(key TEXT,value TEXT);')
            for lang, char, tree in records:
                conn.execute('INSERT INTO node VALUES(?,?,?)', (lang, char, json.dumps(tree)))
            conn.execute('INSERT INTO meta VALUES(?,?)', ('manifest', json.dumps({'entries':len(records)})))

    def test_build_atomic_replace_and_component_only_import(self):
        data = self.root / 'dictionary.txt'
        data.write_text(json.dumps({'character':'想','decomposition':'⿱相心','definition':'DO NOT IMPORT THIS DEFINITION','pinyin':['xiang3']}) + '\n')
        installer.build('makemeahanzi', data, say=lambda _: None)
        path = domain.path_for('makemeahanzi')
        old = path.read_bytes()
        self.assertNotIn(b'DO NOT IMPORT THIS DEFINITION', old)
        self.assertNotIn(b'xiang3', old)
        self.assertEqual(domain.about('makemeahanzi')['revision'], 'local import')
        self.assertEqual(domain.about('makemeahanzi')['entries'], 1)
        data.write_text('not json')
        with self.assertRaises(ValueError):
            installer.build('makemeahanzi', data, say=lambda _: None)
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(list(path.parent.glob('.build-*')), [])

    def test_kanjivg_offline_archive_import(self):
        data = self.root / 'data.zip'
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('source/kanji/06728.svg', svg('<g kvg:element="木"><path/></g>'))
            archive.writestr('source/kanji/06728-variant.svg', svg('<g kvg:element="別"/>'))
            archive.writestr('source/COPYING', 'Fixture licence')
        self.assertEqual(installer.build('kanjivg', data, say=lambda _: None), 1)
        self.assertEqual(domain.about('kanjivg')['notices']['COPYING'], 'Fixture licence')

    def test_preferred_recursive_fallback_atomic_and_missing(self):
        self.assertEqual(domain.character_tree('ja', '想', False)['status'], 'not_installed')
        self.pack('kanjivg', [('ja', '想', sources.ids_record('想', '⿱相心', 'kanjivg')),
                             ('ja', '木', {'character':'木','source':'kanjivg','status':'atomic'})])
        self.pack('cjkvi', [('ja', '想', sources.ids_record('想', '⿰心相', 'cjkvi')),
                           ('ja', '相', sources.ids_record('相', '⿰木目', 'cjkvi')),
                           ('ja', '木', sources.ids_record('木', '⿱十人', 'cjkvi')),
                           ('zh', '𠮷', sources.ids_record('𠮷', '⿱土口', 'cjkvi'))])
        result = domain.character_tree('ja', '想', False)
        self.assertEqual(result['tree']['operator'], '⿱')
        self.assertEqual(result['tree']['children'][0]['children'][0]['character'], '木')
        self.assertEqual({s['source'] for s in result['sources']}, {'kanjivg', 'cjkvi'})
        self.assertEqual(domain.character_tree('ja', '木', False)['status'], 'atomic')
        self.assertEqual(domain.character_tree('ja', '未', False)['status'], 'missing')
        self.assertEqual(domain.character_tree('zh', '𠮷', False)['tree']['source'], 'cjkvi')
        variant = domain.character_tree('ja', '想\U000E0100', False)
        self.assertTrue(variant['variant_fallback'])
        self.assertEqual(variant['tree']['character'], '想\U000E0100')

    def test_recursion_cycles_are_bounded_and_dictionary_is_reused(self):
        self.pack('kanjivg', [('ja','想',sources.ids_record('想','⿱相心','kanjivg')),
                             ('ja','相',sources.ids_record('相','⿱想木','kanjivg'))])
        import lookup
        with patch.object(lookup, 'available', return_value=True), patch.object(lookup, 'about', return_value={'source':'existing dictionary'}), patch.object(lookup, 'look_up', return_value={'words':[{'hits':[{'senses':['existing meaning']}]}]}) as look:
            result = domain.character_tree('ja', '想')
        self.assertTrue(result['tree']['children'][0]['children'][0]['truncated'])
        self.assertEqual(result['meanings']['想'], 'existing meaning')
        self.assertEqual(look.call_count, len(result['meanings']))

    def test_validation_and_api_routes(self):
        for text in ['あ', 'AB', '', '想木', '\U0001F600']:
            self.assertFalse(domain.is_han(text))
        for text in ['想', '𠮷', '𠀀', '﨑', '想\U000E0100']:
            self.assertTrue(domain.is_han(text))
        import serve
        handler = object.__new__(serve.Handler)
        # THE COMPUTER ITSELF asks: every POST now goes through
        # lib/settingspage.py's table, which asks where the knock came from,
        # and a Handler made by hand has no address unless it is given one.
        handler.client_address = ("127.0.0.1", 0)
        def call(action, body):
            handler._json_body = lambda: body
            handler.send_json = lambda payload, status=200: (status, payload)
            return handler._lookup_api(action)
        self.assertEqual(call('decompose', {'code':'ja','character':'あ'})[0], 400)
        self.assertEqual(call('getdecomposition', {'source':'../../elsewhere'})[0], 400)
        self.assertEqual(len(call('decompositions', {})[1]['packs']), 3)
        self.assertEqual(call('decompose', {'code':'ja','character':'想'})[1]['status'], 'not_installed')
        self.pack('kanjivg', [('ja','木',{'character':'木','source':'kanjivg','status':'atomic'})])
        with patch.dict(serve.DECOMPOSITION_JOBS, {'kanjivg':{'running':True}}):
            self.assertEqual(call('dropdecomposition', {'source':'kanjivg'})[0], 409)
        self.assertEqual(call('dropdecomposition', {'source':'kanjivg'})[0], 200)
        self.assertFalse(domain.path_for('kanjivg').exists())


if __name__ == '__main__':
    unittest.main()
