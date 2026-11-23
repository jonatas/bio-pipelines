# =============================================================================
# Stage 1: Compile the pg_bio Rust (pgrx 0.17.0) extension against PostgreSQL 18
# =============================================================================
FROM postgres:18-bookworm AS pg_bio_builder

ARG PG_BIO_GIT_URL="https://github.com/jonatas/pg_bio.git"
ARG PG_BIO_GIT_REF="main"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    build-essential \
    libclang-dev \
    clang \
    pkg-config \
    libssl-dev \
    postgresql-server-dev-18 \
    postgresql-18-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain & cargo-pgrx 0.17.0
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

RUN cargo install --locked cargo-pgrx --version 0.17.0
RUN cargo pgrx init --pg18 /usr/lib/postgresql/18/bin/pg_config

WORKDIR /usr/src/pg_bio
RUN git clone --depth 1 --branch "${PG_BIO_GIT_REF}" "${PG_BIO_GIT_URL}" .
RUN cargo pgrx install --pg18 --release --no-default-features --features pg18

# =============================================================================
# Stage 2: Unified Runtime (PostgreSQL 18 + pg_bio + Python 3 / uv + bio-pipelines)
# =============================================================================
FROM postgres:18-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    python3 \
    python3-venv \
    python3-dev \
    postgresql-18-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled pg_bio extension artifacts from builder stage
COPY --from=pg_bio_builder /usr/lib/postgresql/18/lib/pg_bio.so /usr/lib/postgresql/18/lib/
COPY --from=pg_bio_builder /usr/share/postgresql/18/extension/pg_bio* /usr/share/postgresql/18/extension/

# Install uv for fast, reproducible Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/bio-pipelines
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . /app/bio-pipelines
RUN chmod +x /app/bio-pipelines/docker-entrypoint.sh

ENV PGDATA="/var/lib/postgresql/data" \
    PGPORT="5432" \
    PGUSER="postgres" \
    PGDATABASE="bio_demo" \
    PG_BIO_URL="postgresql://postgres@127.0.0.1:5432/bio_demo" \
    SWARM_WEB_HOST="0.0.0.0" \
    SWARM_WEB_PORT="8090"

EXPOSE 8090 5432

ENTRYPOINT ["/app/bio-pipelines/docker-entrypoint.sh"]
CMD ["web"]
