#!/usr/bin/env bash
# bio-pipelines: run bio-pipelines on a private PostgreSQL 18 with pg_bio,
# hands off.
#
# Usage: bio-pipelines [web|test|seed|psql|stop|status]
#   web     (default) start the database, seed it once, compile the
#           pipelines, run the hypothesis cycle, serve the UI
#   test    the same, then upstream's validate_swarm_web.py against it
#   seed    start the database and seed it, nothing else
#   psql    open psql on the database
#   stop    stop the database
#   status  print the paths and whether the database runs
#
# The database listens on a unix socket only (no TCP), with peer auth for
# the user who runs this. The UI binds 127.0.0.1.
#
# Env seams:
#   BIO_PIPELINES_SHARE      the app tree in the store (set by the wrapper)
#   BIO_PIPELINES_STATE_DIR  state root; default
#                            ${XDG_STATE_HOME:-$HOME/.local/state}/bio-pipelines
#   BIO_PIPELINES_PORT       UI port; default 8090
#   BIO_PIPELINES_PGPORT     socket port number; default 28818
#   BIO_PIPELINES_DB         database name; default bio_demo
#   BIO_PIPELINES_SOCKET_DIR socket directory; default $state/run (a unix
#                            socket path must stay under 104 bytes)
#   BIO_PIPELINES_MODELS_DIR AlphaFold models the app reads and writes;
#                            default $state/models
set -euo pipefail

info() { printf 'bio-pipelines: %s\n' "$*" >&2; }
fatal() {
  printf 'bio-pipelines: error: %s\n' "$*" >&2
  exit 1
}

mode="${1:-web}"
share="${BIO_PIPELINES_SHARE:?set by the package wrapper}"
state="${BIO_PIPELINES_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/bio-pipelines}"
web_port="${BIO_PIPELINES_PORT:-8090}"
pg_port="${BIO_PIPELINES_PGPORT:-28818}"
db="${BIO_PIPELINES_DB:-bio_demo}"
case "$db" in
"" | [!A-Za-z_]* | *[!A-Za-z0-9_]*)
  printf 'bio-pipelines: error: BIO_PIPELINES_DB must be a plain identifier, got: %s\n' "$db" >&2
  exit 1
  ;;
esac

pgdata="$state/pgdata"
run="${BIO_PIPELINES_SOCKET_DIR:-$state/run}"
app="$state/app"
log="$state/log"
socket="$run/.s.PGSQL.$pg_port"
if [ "${#socket}" -gt 103 ]; then
  fatal "socket path is ${#socket} bytes, over the 103-byte limit: $socket; set BIO_PIPELINES_SOCKET_DIR to a shorter directory"
fi
mkdir -p "$state" "$run" "$log"
chmod 700 "$state" "$run"

export PGHOST="$run" PGPORT="$pg_port" PGDATABASE="$db"
export PG_BIO_URL="postgresql:///$db?host=$run&port=$pg_port"
export SWARM_WEB_HOST=127.0.0.1 SWARM_WEB_PORT="$web_port"
export SWARM_WEB_URL="http://127.0.0.1:$web_port"
export BIO_PIPELINES_MODELS_DIR="${BIO_PIPELINES_MODELS_DIR:-$state/models}"
mkdir -p "$BIO_PIPELINES_MODELS_DIR/aligned"

modes="web test seed psql stop status"
case " $modes " in
*" $mode "*) ;;
*) fatal "unknown mode '$mode' ($modes)" ;;
esac

if [ "$mode" = status ]; then
  printf 'state     %s\napp       %s\nPG_BIO_URL %s\nUI        %s\n' \
    "$state" "$app" "$PG_BIO_URL" "$SWARM_WEB_URL"
  pg_ctl -D "$pgdata" status || true
  exit 0
fi

if [ "$mode" = stop ]; then
  pg_ctl -D "$pgdata" -m fast stop
  exit 0
fi

# The app writes beside its own sources (structures/ downloads, output/
# plots), so it runs from a writable copy, refreshed when the package
# changes.
# The copy is made beside it and swapped in whole, so an interrupted copy
# never leaves a half tree behind.
if [ "$(cat "$app/.store-path" 2>/dev/null || true)" != "$share" ]; then
  info "copying the app to $app"
  tmp="$app.new.$$"
  rm -rf "$tmp"
  cp -R "$share" "$tmp"
  chmod -R u+w "$tmp"
  printf '%s\n' "$share" >"$tmp/.store-path"
  # Downloads (structures/) and plots (output/) live in $state and are
  # linked in, so a package update keeps them. Files the package ships
  # there are added once, never over the top of what the app wrote.
  for d in structures output; do
    mkdir -p "$state/$d"
    if [ -d "$tmp/$d" ]; then
      cp -Rn "$tmp/$d/." "$state/$d/"
      rm -rf "${tmp:?}/$d"
    fi
    ln -s "$state/$d" "$tmp/$d"
  done
  if [ -e "$app" ]; then
    chmod -R u+w "$app"
    rm -rf "$app"
  fi
  mv "$tmp" "$app"
fi

if [ ! -s "$pgdata/PG_VERSION" ]; then
  info "initialising PostgreSQL 18 in $pgdata"
  initdb -D "$pgdata" --auth-local=peer --auth-host=reject \
    --encoding=UTF8 --no-instructions >"$log/initdb.log"
  {
    printf "listen_addresses = ''\n"
    printf 'shared_buffers = 512MB\n'
    printf 'work_mem = 64MB\n'
  } >>"$pgdata/postgresql.conf"
fi

# Socket directory and port are given at each start, not written to
# postgresql.conf, so changing BIO_PIPELINES_SOCKET_DIR or
# BIO_PIPELINES_PGPORT takes effect on the next start. A server already
# running elsewhere is reported, not silently missed.
if pg_ctl -D "$pgdata" status >/dev/null 2>&1; then
  running_port="$(sed -n 4p "$pgdata/postmaster.pid")"
  running_run="$(sed -n 5p "$pgdata/postmaster.pid")"
  if [ "$running_port" != "$pg_port" ] || [ "$running_run" != "$run" ]; then
    fatal "the database runs on $running_run port $running_port, not $run port $pg_port; run 'bio-pipelines stop' first"
  fi
else
  info "starting PostgreSQL (socket $run, port $pg_port)"
  pg_ctl -D "$pgdata" -l "$log/postgresql.log" -w \
    -o "-k '$run' -p $pg_port" start >/dev/null
fi

if [ "$mode" = psql ]; then
  exec psql "$PG_BIO_URL"
fi

if [ "$(psql -X -d postgres -tA -v db="$db" <<<"SELECT 1 FROM pg_database WHERE datname = :'db';")" != 1 ]; then
  createdb "$db"
fi
psql -q -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION IF NOT EXISTS pg_bio CASCADE;' >/dev/null

# Two queries: a single CASE fails on a fresh database, because
# PostgreSQL resolves `FROM proteins` before the CASE runs.
proteins_table="$(psql -XtAc "SELECT to_regclass('public.proteins') IS NOT NULL")"
proteins=0
if [ "$proteins_table" = t ]; then
  proteins="$(psql -XtAc 'SELECT count(*) FROM public.proteins')"
fi
# The three files run as one transaction: a failure part way leaves
# nothing, so the next start seeds again instead of finding proteins and
# skipping an atlas that was never built.
if [ "$proteins" = 0 ]; then
  info "loading the seed dataset and building the domain atlas"
  psql -X -q -1 -v ON_ERROR_STOP=1 \
    -f "$app/base/docker_seed.sql" \
    -f "$app/base/schema.sql" \
    -f "$app/base/swarm_pareto.sql" >"$log/seed.log"
fi

if [ "$mode" = seed ]; then
  info "seeded; database left running ($PG_BIO_URL)"
  exit 0
fi

# Before the compile and the cycle, which take a while.
if curl -s -o /dev/null --max-time 2 "$SWARM_WEB_URL/"; then
  fatal "port $web_port already answers on 127.0.0.1; set BIO_PIPELINES_PORT"
fi

cd "$app"
info "compiling the feedstock pipelines (base/compiler.py)"
python3 base/compiler.py
info "running the hypothesis cycle (base/hypothesis_agent.py)"
python3 base/hypothesis_agent.py

if [ "$mode" = web ]; then
  info "UI on $SWARM_WEB_URL (database stays up; 'bio-pipelines stop' stops it)"
  exec python3 base/swarm_web.py "$web_port"
fi

info "starting the UI for the validation suite"
python3 base/swarm_web.py "$web_port" >"$log/swarm_web.log" 2>&1 &
web_pid=$!
trap 'kill "$web_pid" 2>/dev/null || true' EXIT
ready=
for _ in $(seq 1 60); do
  if curl -fs -o /dev/null "$SWARM_WEB_URL/api/meta" 2>/dev/null; then
    ready=1
    break
  fi
  kill -0 "$web_pid" 2>/dev/null || fatal "the UI exited; see $log/swarm_web.log"
  sleep 1
done
[ -n "$ready" ] || fatal "the UI did not answer on $SWARM_WEB_URL/api/meta within 60s; see $log/swarm_web.log"
python3 base/validate_swarm_web.py

# The puzzle board tests, where the tree has them: each runs in one
# transaction and rolls back, so the database is left as it was. A tree
# without them is not an error.
puzzle_tests=$(find base -maxdepth 1 -name 'test_puzzle_board_*.py' | sort)
if [ -n "$puzzle_tests" ]; then
  # shellcheck disable=SC2086
  python3 -m pytest -q -p no:cacheprovider $puzzle_tests
else
  info "no base/test_puzzle_board_*.py in this tree; skipped"
fi
info "all pipelines compiled and validated"
