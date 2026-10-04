# SPDX-License-Identifier: GPL-3.0-or-later
"""Installation information, rendered with host-native paths on every OS."""
import platform
from pathlib import Path
import author
import settingspage

PAGE = '/settings/about/'


def page(where):
    root = Path(settingspage.ROOT)
    esc = settingspage.esc
    rows = [('Version', settingspage.parseh_version()), ('Author', author.NAME),
            ('Operating system', platform.system() + ' ' + platform.release()),
            ('Python', platform.python_version()), ('Installation folder', str(root)),
            ('serve.sh location', str(root / 'serve.sh')),
            ('Windows launcher', str(root / 'serve.bat')),
            ('Python launcher', str(root / 'serve.py')),
            ('Settings folder', str(root / 'config'))]
    table = ''.join('<dt>%s</dt><dd><code>%s</code></dd>' % (esc(k), esc(v)) for k, v in rows)
    main = '''<main class="settings tools">%s<h1 class="idx">About Parseh</h1>
<p class="sub">Read, watch and study in another language, with dictionaries, transcripts and reading help.</p>
<dl>%s</dl><p>Use serve.sh on Linux and macOS, or serve.bat on Windows. These paths belong to the computer running Parseh.</p>
<p>Free software under GNU GPL version 3 or later.</p>
<p class="footer-links"><a href="/guide/">User guide</a><a href="/licences/">Licences</a><a href="/settings/update/">Updates</a></p>
<p>%s</p></main>''' % (settingspage.settings_doors(PAGE), table, author.links())
    return settingspage.frame('About — Parseh', 'Settings', 'Settings', '/guide/', main,
        style='.tools dl{display:grid;grid-template-columns:minmax(8rem,auto) minmax(0,1fr);gap:14px 20px;margin:24px 0;padding:18px;border:1px solid var(--rule);border-radius:10px;background:var(--card)}.tools dt{font-weight:600;font-size:14px}.tools dd{margin:0;overflow-wrap:anywhere;font-size:14px}.tools dd code{font-size:13px}@media(max-width:620px){.tools dl{grid-template-columns:minmax(0,1fr);gap:4px}.tools dt:not(:first-child){margin-top:12px}}',
        extra_head='<link rel="stylesheet" href="/lib/settings-tools.css">')
