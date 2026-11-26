#!/usr/bin/env bash
set -euo pipefail

export PGDATA="${PGDATA:-/var/lib/postgresql/data}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"
export PGDATABASE="${PGDATABASE:-bio_demo}"
export PG_BIO_URL="${PG_BIO_URL:-postgresql://${PGUSER}@127.0.0.1:${PGPORT}/${PGDATABASE}}"
export SWARM_WEB_HOST="${SWARM_WEB_HOST:-0.0.0.0}"
export SWARM_WEB_PORT="${SWARM_WEB_PORT:-8090}"

echo "================================================================================"
echo "🧬 Starting pg_bio (PostgreSQL 18 + Rust Extension) & bio-pipelines Environment"
echo "================================================================================"

# 1. Initialize & start local PostgreSQL 18 if PG_BIO_URL points to local container
if [[ "${PG_BIO_URL}" == *"127.0.0.1"* ]] || [[ "${PG_BIO_URL}" == *"localhost"* ]]; then
    mkdir -p "${PGDATA}" /var/run/postgresql
    chown -R postgres:postgres "${PGDATA}" /var/run/postgresql

    if [ ! -s "${PGDATA}/PG_VERSION" ]; then
        echo "📦 Initializing PostgreSQL 18 cluster in ${PGDATA}..."
        su - postgres -c "/usr/lib/postgresql/18/bin/initdb -D '${PGDATA}' --auth=trust --encoding=UTF8"
        echo "listen_addresses = '*'" >> "${PGDATA}/postgresql.conf"
        echo "port = ${PGPORT}" >> "${PGDATA}/postgresql.conf"
        echo "shared_buffers = 512MB" >> "${PGDATA}/postgresql.conf"
        echo "work_mem = 64MB" >> "${PGDATA}/postgresql.conf"
    fi

    # Inside the container (the app over 127.0.0.1, psql over the socket)
    # stays trusted, as initdb --auth=trust set it up. Any other client,
    # such as the host through the published port, needs a password: set
    # POSTGRES_PASSWORD to allow it; without one, remote access is off.
    # Volumes created before this change carry a trust-everyone line: drop it.
    sed -i '/^host all all 0\.0\.0\.0\/0 trust$/d' "${PGDATA}/pg_hba.conf"
    # The block below is rewritten on every start; lines outside it stay.
    sed -i '/^# bio-pipelines: remote access begin$/,/^# bio-pipelines: remote access end$/d' "${PGDATA}/pg_hba.conf"
    if [ -n "${POSTGRES_PASSWORD:-}" ]; then
        printf '%s\n' '# bio-pipelines: remote access begin' \
            'host all all 0.0.0.0/0 scram-sha-256' \
            'host all all ::/0 scram-sha-256' \
            '# bio-pipelines: remote access end' >> "${PGDATA}/pg_hba.conf"
    fi

    echo "🚀 Starting PostgreSQL 18 on port ${PGPORT}..."
    su - postgres -c "/usr/lib/postgresql/18/bin/pg_ctl -D '${PGDATA}' -l /tmp/postgres.log -w start"

    if [ -n "${POSTGRES_PASSWORD:-}" ]; then
        # \getenv reads the password inside psql, so it never appears in
        # a process's command line.
        psql -h 127.0.0.1 -p "${PGPORT}" -U postgres -d postgres -q -v ON_ERROR_STOP=1 <<'SQL'
\getenv pw POSTGRES_PASSWORD
ALTER ROLE postgres PASSWORD :'pw';
SQL
    fi

    # Ensure database & pg_bio extension exist
    su - postgres -c "psql -p ${PGPORT} -tc \"SELECT 1 FROM pg_database WHERE datname = '${PGDATABASE}'\" | grep -q 1 || createdb -p ${PGPORT} ${PGDATABASE}"
    su - postgres -c "psql -p ${PGPORT} -d ${PGDATABASE} -c 'CREATE EXTENSION IF NOT EXISTS pg_bio CASCADE;'"
else
    echo "🔗 Using external PostgreSQL cluster: ${PG_BIO_URL}"
    until pg_isready -d "${PG_BIO_URL}"; do
        echo "⏳ Waiting for PostgreSQL at ${PG_BIO_URL}..."
        sleep 2
    done
    psql "${PG_BIO_URL}" -c "CREATE EXTENSION IF NOT EXISTS pg_bio CASCADE;"
fi

cd /app/bio-pipelines

# 2. Seed database if proteins / bio_domain_atlas are empty
PROT_COUNT=$(psql "${PG_BIO_URL}" -tAc "SELECT CASE WHEN to_regclass('public.proteins') IS NOT NULL THEN (SELECT COUNT(*) FROM proteins) ELSE 0 END;" || echo "0")
if [ "${PROT_COUNT}" -eq "0" ]; then
    echo "🌱 Loading curated multi-feedstock seed dataset (base/docker_seed.sql)..."
    psql "${PG_BIO_URL}" -v ON_ERROR_STOP=1 -f base/docker_seed.sql >/dev/null
    echo "📐 Building Universal 4-Module Domain Atlas (base/schema.sql + base/swarm_pareto.sql)..."
    psql "${PG_BIO_URL}" -v ON_ERROR_STOP=1 -f base/schema.sql >/dev/null
    psql "${PG_BIO_URL}" -v ON_ERROR_STOP=1 -f base/swarm_pareto.sql >/dev/null
fi

# 3. Compile all 8 declarative feedstock pipelines & seed autonomous hypothesis ledger
echo "⚡ Running Declarative 8-Feedstock Bioprocess Compiler (base/compiler.py)..."
uv run --no-sync python base/compiler.py

echo "🧠 Running Autonomous Hypothesis & Dark-Proteome (DUF) Evolution Cycle (base/hypothesis_agent.py)..."
uv run --no-sync python base/hypothesis_agent.py

# 4. Handle execution mode (`web` default, `test` for full CI validation, or custom command)
MODE="${1:-web}"
if [ "${MODE}" = "test" ]; then
    echo "🔬 Starting background web server for end-to-end validation suite..."
    uv run --no-sync python base/swarm_web.py "${SWARM_WEB_PORT}" >/tmp/swarm_web.log 2>&1 &
    WEB_PID=$!
    sleep 3
    SWARM_WEB_URL="http://127.0.0.1:${SWARM_WEB_PORT}" uv run --no-sync python base/validate_swarm_web.py
    kill "${WEB_PID}" || true
    echo "✅ All pipelines compiled and validated!"
elif [ "${MODE}" = "web" ]; then
    echo "🌐 Launching Unified Bio-Pipelines Web UI on http://0.0.0.0:${SWARM_WEB_PORT} ..."
    echo "   Routes: /pipelines | /discovery | /telemetry | /cards | /compare | /galaxy | /tpp"
    exec uv run --no-sync python base/swarm_web.py "${SWARM_WEB_PORT}"
else
    exec "$@"
fi
