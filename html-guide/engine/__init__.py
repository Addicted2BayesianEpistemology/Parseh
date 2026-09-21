"""The Parseh guide's engine: Hugo's Markdown and the Parseh studio's dialect,
compiled into a static site.  html-guide/build.py is the command; README.md
beside it says how to write a page.

    engine.site      markdown/ in, site/ out: pages, navigation, search, runtime
    engine.render    one page: the blocks, the headings, the code
    engine.blocks    the block parser (Hugo's blocks and the dialect's)
    engine.inline    Hugo's inline Markdown, in front of the studio's
    engine.studio    where the studio's renderer is imported from
    engine.shortcodes, engine.highlight, engine.qr, engine.frontmatter,
    engine.cssscope, engine.export, engine.fingerprint, engine.manifest
"""
