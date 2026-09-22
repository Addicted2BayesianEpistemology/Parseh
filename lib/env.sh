# SPDX-License-Identifier: GPL-3.0-or-later
# Sourced, never run: the environment serve.sh, build.sh and install.sh work in.
#
#   . lib/env.sh && parseh_env
#
# sets PARSEH_PY (the python3 to run) and PARSEH_PREFIX (the environment's
# directory, empty where there is none) and puts the environment's programs
# first on the PATH, which is all activating it does as far as anything here
# is concerned -- and what every tool serve.py and build.sh start inherits.
#
# The search is lib/runtime.py's find_env(), in sh because it has to work
# before any Python is known to: $PARSEH_PYTHON; the checkout's own
# .runtime/env (./install.sh makes it); an environment called ilya-frank
# wherever a conda, a mamba or a micromamba keeps them; else the machine's
# python3.  PARSEH_ROOT is the checkout, the current directory by default.
parseh_env() {
  PARSEH_PREFIX=""
  PARSEH_PY=""
  _pr="${PARSEH_ROOT:-$(pwd)}"
  if [ -n "${PARSEH_PYTHON:-}" ] && [ -x "$PARSEH_PYTHON" ]; then
    PARSEH_PY="$PARSEH_PYTHON"
    PARSEH_PREFIX="$(dirname "$(dirname "$PARSEH_PYTHON")")"
  else
    _conda_base=""
    if [ -n "${CONDA_EXE:-}" ]; then _conda_base="$(dirname "$(dirname "$CONDA_EXE")")"; fi
    for _p in "$_pr/.runtime/env" \
              ${MAMBA_ROOT_PREFIX:+"$MAMBA_ROOT_PREFIX/envs/ilya-frank"} \
              ${_conda_base:+"$_conda_base/envs/ilya-frank"} \
              "$HOME/miniconda3/envs/ilya-frank" "$HOME/anaconda3/envs/ilya-frank" \
              "$HOME/miniforge3/envs/ilya-frank" "$HOME/mambaforge/envs/ilya-frank" \
              "$HOME/micromamba/envs/ilya-frank" "$HOME/.local/share/mamba/envs/ilya-frank" \
              "$HOME/.conda/envs/ilya-frank" \
              /opt/miniconda3/envs/ilya-frank /opt/anaconda3/envs/ilya-frank \
              /opt/miniforge3/envs/ilya-frank /opt/mambaforge/envs/ilya-frank \
              /opt/homebrew/Caskroom/miniconda/base/envs/ilya-frank \
              /opt/homebrew/Caskroom/miniforge/base/envs/ilya-frank \
              /usr/local/Caskroom/miniconda/base/envs/ilya-frank \
              /usr/local/Caskroom/miniforge/base/envs/ilya-frank; do
      if [ -x "$_p/bin/python3" ]; then
        PARSEH_PREFIX="$_p"
        PARSEH_PY="$_p/bin/python3"
        break
      fi
    done
    if [ -z "$PARSEH_PY" ] && command -v conda >/dev/null 2>&1; then
      _conda_base="$(conda info --base 2>/dev/null || true)"
      if [ -n "$_conda_base" ] && [ -x "$_conda_base/envs/ilya-frank/bin/python3" ]; then
        PARSEH_PREFIX="$_conda_base/envs/ilya-frank"
        PARSEH_PY="$PARSEH_PREFIX/bin/python3"
      fi
    fi
  fi
  if [ -n "$PARSEH_PREFIX" ]; then
    case ":$PATH:" in
      *":$PARSEH_PREFIX/bin:"*) ;;
      *) PATH="$PARSEH_PREFIX/bin:$PATH"; export PATH ;;
    esac
  else
    PARSEH_PY="$(command -v python3 2>/dev/null || echo python3)"
  fi
  export PARSEH_PY PARSEH_PREFIX
}
