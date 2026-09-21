MathJax 3.2.2, the `tex-svg` bundle, vendored whole.

    https://github.com/mathjax/MathJax  ·  Apache-2.0 (LICENSE beside this)
    es5/tex-svg.js, byte for byte as npm ships it

WHY IT IS HERE AND NOT FETCHED.  Nothing in this toolbox reaches the
network while it runs -- a reader on a train is the point -- so the one
copy that is ever needed sits beside the fonts it is filed with
(lib/fonts/), served by the same static prefix, and is as old or as new as
the checkout is.  It is 2 MB, which is half a demo gif.

WHY tex-svg AND NOT tex-mml-chtml.  Two reasons, and the second is the
one that decides it.  CHTML is smaller but arrives as a bundle PLUS a tree
of web fonts, and this way there is one file and no second thing to serve.
And an Anki card leaves this toolbox for good: it cannot ask us to render
anything, so its maths has to be drawn BEFORE it goes, and an <svg> can be
written into a card where CHTML would be a reference to fonts that are not
there.  The same drawing serves the page, the card and the print.

UPGRADING.  Replace tex-svg.js with the same file from a later release and
replace LICENSE beside it; nothing here reads a version number, and
lib/mathjax.js asks only for MathJax.tex2svg, which has been the entry
point since 3.0.
