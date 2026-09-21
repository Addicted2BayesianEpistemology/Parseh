#!/bin/sh
# The video player is served by the toolbox's one server, from the root:
#
#   cd .. && ./serve.sh        # then open  https://localhost:8765/youtube/
#
# This script only forwards, so an old habit still works.
cd "$(dirname "$0")/.."
echo "the video player is part of Parseh now -- running ../serve.sh $*"
exec ./serve.sh "$@"
