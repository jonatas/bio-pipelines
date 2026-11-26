# shellcheck shell=bash
set -euo pipefail
: "${out:?set by nix}" "${fixtures:?set by nix}"
export HOME="$TMPDIR/home" BIO_PIPELINES_STATE_DIR="$TMPDIR/state"
mkdir -p "$HOME"
# The darwin sandbox shares the host's loopback: the UI takes a free
# port rather than 8090. PostgreSQL needs none: it listens only on a
# socket in this build's own directory.
BIO_PIPELINES_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
export BIO_PIPELINES_PORT
mkdir -p "$BIO_PIPELINES_STATE_DIR/models"
cp "$fixtures"/*.pdb "$BIO_PIPELINES_STATE_DIR/models/"
status=0
bio-pipelines test || status=$?
bio-pipelines stop || true
if [ "$status" != 0 ]; then
  cat "$BIO_PIPELINES_STATE_DIR"/log/*.log >&2 || true
  exit "$status"
fi
touch "$out"
