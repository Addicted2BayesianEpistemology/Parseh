#!/bin/sh
# Parseh on a Mac -- double-click this file in the Finder.
#
# The first time, it installs what Parseh needs (./install.sh: everything goes
# into this folder, under .runtime/, unless the Mac already has conda with an
# ilya-frank environment).  Every time, it starts the server (./serve.sh) and
# opens the browser on it.  Terminal shows what happens; closing its window
# does not stop the server -- the stop button on any page does.
#
# Linux has no double-click convention this could follow; ./install.sh and
# ./serve.sh are the same two steps there.
cd "$(dirname "$0")" || exit 1
. ./lib/env.sh
parseh_env
if [ -z "$PARSEH_PREFIX" ]; then
  echo "The first start: installing what Parseh needs.  This takes a while, once."
  echo
  if ! ./install.sh; then
    echo
    echo "The installation did not finish -- the lines above say why."
    echo "Press Return to close."
    read -r _
    exit 1
  fi
fi
./serve.sh || { echo "Press Return to close."; read -r _; exit 1; }
open "https://localhost:8765/"
