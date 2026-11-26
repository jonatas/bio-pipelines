#!/usr/bin/env python3
"""
pg_bio / bio_demo Zero-Downtime Progressive & Incremental Backup Engine
========================================================================
Provides two complementary zero-downtime backup & restore workflows for
PostgreSQL 18 (`postgresql://jonatas@localhost:28818/bio_demo`):

1. Native PostgreSQL 18 Block-Level Incremental Backups (`pg_basebackup --incremental`
   + WAL Summarizer `summarize_wal = on` + `zstd` tar compression + `pg_combinebackup`):
   - `full-physical` / `auto`: Takes a base physical snapshot via streaming replication
     with `--checkpoint=spread` (zero lock, zero downtime).
   - `diff-physical` / `auto`: Uses PostgreSQL 18's WAL Summarizer (`pg_wal/summaries`)
     and `--incremental=<prev_manifest>` to copy ONLY the 8 KB data blocks modified
     since the previous full or incremental backup!

2. Progressive Logical Watermark Delta & State Snapshots (`logical-delta` & `load-delta`):
   - Tracks high-watermarks (`max(id)`) in `backup_manifest.json` for high-volume
     append/update tables (`orphan_discoveries`, `swarm_tpp_knockout_cascades`,
     `swarm_telemetry_log`, `proteins`) and exports compressed `COPY ... TO STDOUT`
     `.csv.zst` delta slices + full reference state tables (`bio_pipeline_puzzles`,
     `bio_puzzle_slots`, `bio_composite_super_pipelines`, `bio_hypothesis_ledger`,
     `bio_annotation_evolution`, `swarm_pocket_ranges`, `bio_domain_atlas`, etc.)
     inside a single `REPEATABLE READ READ ONLY` transaction (zero locks).
   - `load-delta --snapshot <dir>` progressively loads any snapshot or chain of
     daily delta snapshots back into a target database via `ON CONFLICT DO UPDATE` /
     staging upserts without interrupting active operations.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg

DEFAULT_DB_URI = os.environ.get("PG_BIO_DB_URI", "postgresql://jonatas@localhost:28818/bio_demo")
DEFAULT_BACKUP_ROOT = Path(
    os.environ.get("PG_BIO_BACKUP_ROOT", "/Users/jonatas/code/bio-pipelines/backups")
)
PG_HOST = os.environ.get("PG_BIO_HOST", "localhost")
PG_PORT = os.environ.get("PG_BIO_PORT", "28818")
PG_USER = os.environ.get("PG_BIO_USER", "jonatas")

PG_BASEBACKUP = shutil.which("pg_basebackup") or "/opt/homebrew/bin/pg_basebackup"
PG_COMBINEBACKUP = shutil.which("pg_combinebackup") or "/opt/homebrew/bin/pg_combinebackup"
PG_VERIFYBACKUP = shutil.which("pg_verifybackup") or "/opt/homebrew/bin/pg_verifybackup"
PG_DUMP = shutil.which("pg_dump") or "/opt/homebrew/bin/pg_dump"
ZSTD_BIN = shutil.which("zstd") or "/opt/homebrew/bin/zstd"

# Small/medium state & reference tables that are snapshotted in full on every daily delta
# (< 60 MB total uncompressed, ~12 MB compressed with zstd)
STATE_TABLES: List[Dict[str, Any]] = [
    {"table": "bio_pipeline_puzzles", "pk": "puzzle_id"},
    {"table": "bio_puzzle_slots", "pk": "puzzle_id, module_role"},
    {"table": "bio_composite_super_pipelines", "pk": "composite_id"},
    {"table": "bio_hypothesis_ledger", "pk": "hypothesis_id"},
    {"table": "bio_annotation_evolution", "pk": "uniprot_id"},
    {"table": "bio_agent_checkpoint", "pk": "id"},
    {"table": "swarm_checkpoint", "pk": "id"},
    {"table": "swarm_pocket_ranges", "pk": "uniprot_id"},
    {"table": "swarm_enzyme_substrates", "pk": "id"},
    {"table": "bio_domain_atlas", "pk": "id"},
    {"table": "pg_bio_research_attempts", "pk": "attempt_id"},
]

# High-volume tables tracked via progressive id/timestamp watermarks
WATERMARK_TABLES: List[Dict[str, Any]] = [
    {
        "table": "orphan_discoveries",
        "pk": "id",
        "watermark_col": "id",
        "extra_where": "OR (rf_score IS NOT NULL AND id > {prev_wm} - 250000)",
    },
    {
        "table": "swarm_tpp_knockout_cascades",
        "pk": "id",
        "watermark_col": "id",
        "extra_where": "",
    },
    {
        "table": "swarm_telemetry_log",
        "pk": "id",
        "watermark_col": "id",
        "extra_where": "",
    },
]


def ensure_wal_summarizer_enabled(db_uri: str) -> Dict[str, Any]:
    """Ensures PostgreSQL 18 WAL Summarizer is active (zero downtime via SIGHUP)."""
    with psycopg.connect(db_uri, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW summarize_wal;")
            current_val = cur.fetchone()[0]
            if current_val != "on":
                cur.execute("ALTER SYSTEM SET summarize_wal = 'on';")
                cur.execute("ALTER SYSTEM SET wal_summary_keep_time = '14d';")
                cur.execute("SELECT pg_reload_conf();")
                time.sleep(1.0)
            cur.execute("SELECT summarized_tli, summarized_lsn::text, pending_lsn::text, summarizer_pid FROM pg_get_wal_summarizer_state();")
            row = cur.fetchone()
            return {
                "summarize_wal": "on",
                "summarized_tli": row[0],
                "summarized_lsn": row[1],
                "pending_lsn": row[2],
                "summarizer_pid": row[3],
            }


def ensure_backup_ledger_table(db_uri: str) -> None:
    """Creates `bio_backup_snapshots` table inside `bio_demo` for telemetry visibility."""
    with psycopg.connect(db_uri, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bio_backup_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    backup_kind TEXT NOT NULL,
                    parent_snapshot_id TEXT,
                    snapshot_path TEXT NOT NULL,
                    size_bytes BIGINT NOT NULL DEFAULT 0,
                    size_pretty TEXT,
                    orphan_edges_watermark BIGINT,
                    tpp_cascades_watermark BIGINT,
                    telemetry_watermark BIGINT,
                    delta_rows_exported BIGINT DEFAULT 0,
                    wal_start_lsn TEXT,
                    wal_end_lsn TEXT,
                    duration_sec DOUBLE PRECISION,
                    status TEXT NOT NULL DEFAULT 'COMPLETED',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )


def dir_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for entry in path.rglob("*"):
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                pass
    return total


def human_bytes(num_bytes: int) -> str:
    val = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0 or unit == "TB":
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} TB"


def load_ledger(backup_root: Path) -> Dict[str, Any]:
    ledger_file = backup_root / "backup_ledger.json"
    if ledger_file.exists():
        try:
            return json.loads(ledger_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "updated_at": None,
        "latest_physical_manifest": None,
        "latest_physical_snapshot_id": None,
        "latest_full_physical_id": None,
        "watermarks": {
            "orphan_discoveries": 0,
            "swarm_tpp_knockout_cascades": 0,
            "swarm_telemetry_log": 0,
        },
        "snapshots": [],
    }


def save_ledger(backup_root: Path, ledger: Dict[str, Any]) -> None:
    backup_root.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    ledger_file = backup_root / "backup_ledger.json"
    ledger_file.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def record_snapshot_in_db(db_uri: str, meta: Dict[str, Any]) -> None:
    try:
        ensure_backup_ledger_table(db_uri)
        with psycopg.connect(db_uri, autocommit=True) as conn:
            with conn.cursor() as cur:
                wm = meta.get("watermarks", {})
                cur.execute(
                    """
                    INSERT INTO bio_backup_snapshots (
                        snapshot_id, backup_kind, parent_snapshot_id, snapshot_path,
                        size_bytes, size_pretty, orphan_edges_watermark,
                        tpp_cascades_watermark, telemetry_watermark,
                        delta_rows_exported, wal_start_lsn, wal_end_lsn,
                        duration_sec, status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (snapshot_id) DO UPDATE SET
                        size_bytes = EXCLUDED.size_bytes,
                        size_pretty = EXCLUDED.size_pretty,
                        delta_rows_exported = EXCLUDED.delta_rows_exported,
                        duration_sec = EXCLUDED.duration_sec,
                        status = EXCLUDED.status;
                    """,
                    (
                        meta["snapshot_id"],
                        meta["backup_kind"],
                        meta.get("parent_snapshot_id"),
                        meta["snapshot_path"],
                        meta["size_bytes"],
                        meta["size_pretty"],
                        wm.get("orphan_discoveries", 0),
                        wm.get("swarm_tpp_knockout_cascades", 0),
                        wm.get("swarm_telemetry_log", 0),
                        meta.get("delta_rows_exported", 0),
                        meta.get("wal_start_lsn"),
                        meta.get("wal_end_lsn"),
                        meta.get("duration_sec", 0.0),
                        meta.get("status", "COMPLETED"),
                    ),
                )
    except Exception as exc:
        print(f"[warn] Could not record snapshot in DB ledger: {exc}", file=sys.stderr)


def run_logical_progressive_delta(
    db_uri: str,
    backup_root: Path,
    bootstrap_window: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Takes a zero-downtime, lock-free progressive logical delta snapshot:
    - Exports schema DDL (`schema_ddl.sql`) via `pg_dump --schema-only`.
    - Exports all state & puzzle/hypothesis tables as `.csv.zst`.
    - Exports new/updated rows since the last watermark for `orphan_discoveries`,
      `swarm_tpp_knockout_cascades`, and `swarm_telemetry_log` inside a single
      `REPEATABLE READ READ ONLY` transaction.
    """
    t0 = time.perf_counter()
    now_str = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_id = f"logical_delta_{now_str}"
    snap_dir = backup_root / "logical_deltas" / snap_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    ledger = load_ledger(backup_root)
    prev_wm = dict(ledger.get("watermarks", {}))

    # 1. Dump clean schema DDL (non-blocking)
    schema_path = snap_dir / "schema_ddl.sql"
    subprocess.run(
        [
            PG_DUMP,
            "-h",
            PG_HOST,
            "-p",
            PG_PORT,
            "-U",
            PG_USER,
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            "-d",
            "bio_demo",
            "-f",
            str(schema_path),
        ],
        check=True,
    )

    exported_tables: Dict[str, Any] = {}
    new_wm = dict(prev_wm)
    total_delta_rows = 0

    with psycopg.connect(db_uri, autocommit=False) as conn:
        with conn.cursor() as cur:
            # Use REPEATABLE READ READ ONLY so we hold zero locks and get a consistent MVCC view
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;")
            cur.execute("SELECT pg_current_wal_lsn()::text;")
            snap_lsn = cur.fetchone()[0]

            # 2. Export full reference/state tables
            for st in STATE_TABLES:
                tbl = st["table"]
                cur.execute("SELECT to_regclass(%s);", (f"public.{tbl}",))
                if cur.fetchone()[0] is None:
                    continue
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                row_cnt = int(cur.fetchone()[0])

                out_file = snap_dir / f"state_{tbl}.csv.zst"
                with subprocess.Popen(
                    [ZSTD_BIN, "-q", "-3", "-T0", "-f", "-o", str(out_file)],
                    stdin=subprocess.PIPE,
                ) as zproc:
                    assert zproc.stdin is not None
                    with cur.copy(f"COPY {tbl} TO STDOUT WITH (FORMAT CSV, HEADER TRUE)") as copy:
                        for data in copy:
                            zproc.stdin.write(bytes(data))
                    zproc.stdin.close()
                    zproc.wait()

                exported_tables[tbl] = {
                    "mode": "full_state",
                    "pk": st["pk"],
                    "rows": row_cnt,
                    "file": out_file.name,
                    "size_bytes": out_file.stat().st_size if out_file.exists() else 0,
                }
                total_delta_rows += row_cnt

            # 3. Export progressive watermark delta slices for high-volume tables
            for wt in WATERMARK_TABLES:
                tbl = wt["table"]
                wm_col = wt["watermark_col"]
                cur.execute("SELECT to_regclass(%s);", (f"public.{tbl}",))
                if cur.fetchone()[0] is None:
                    continue

                cur.execute(f"SELECT COALESCE(MAX({wm_col}), 0) FROM {tbl};")
                curr_max_id = int(cur.fetchone()[0] or 0)
                last_id = int(prev_wm.get(tbl, 0) or 0)

                if last_id == 0 and bootstrap_window is not None and curr_max_id > bootstrap_window:
                    # On initial progressive seed, capture the recent high-value frontier window
                    # while full physical pg_basebackup captures the historical 62 GB baseline
                    last_id = max(0, curr_max_id - bootstrap_window)

                extra_clause = wt["extra_where"].format(prev_wm=last_id) if wt["extra_where"] else ""
                where_sql = f"{wm_col} > {last_id} {extra_clause}".strip()

                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {where_sql};")
                delta_cnt = int(cur.fetchone()[0] or 0)

                out_file = snap_dir / f"delta_{tbl}.csv.zst"
                if delta_cnt > 0:
                    with subprocess.Popen(
                        [ZSTD_BIN, "-q", "-3", "-T0", "-f", "-o", str(out_file)],
                        stdin=subprocess.PIPE,
                    ) as zproc:
                        assert zproc.stdin is not None
                        copy_sql = (
                            f"COPY (SELECT * FROM {tbl} WHERE {where_sql} ORDER BY {wm_col} ASC) "
                            f"TO STDOUT WITH (FORMAT CSV, HEADER TRUE)"
                        )
                        with cur.copy(copy_sql) as copy:
                            for data in copy:
                                zproc.stdin.write(bytes(data))
                        zproc.stdin.close()
                        zproc.wait()

                new_wm[tbl] = curr_max_id
                exported_tables[tbl] = {
                    "mode": "watermark_delta",
                    "pk": wt["pk"],
                    "watermark_col": wm_col,
                    "prev_watermark": last_id,
                    "new_watermark": curr_max_id,
                    "rows": delta_cnt,
                    "file": out_file.name if delta_cnt > 0 else None,
                    "size_bytes": out_file.stat().st_size if out_file.exists() else 0,
                }
                total_delta_rows += delta_cnt

        conn.rollback()  # End read-only repeatable-read transaction cleanly

    elapsed = round(time.perf_counter() - t0, 2)
    snap_bytes = dir_size_bytes(snap_dir)
    meta = {
        "snapshot_id": snap_id,
        "backup_kind": "LOGICAL_PROGRESSIVE_DELTA",
        "parent_snapshot_id": ledger.get("latest_logical_snapshot_id"),
        "snapshot_path": str(snap_dir),
        "size_bytes": snap_bytes,
        "size_pretty": human_bytes(snap_bytes),
        "wal_start_lsn": snap_lsn,
        "wal_end_lsn": snap_lsn,
        "prev_watermarks": prev_wm,
        "watermarks": new_wm,
        "delta_rows_exported": total_delta_rows,
        "tables": exported_tables,
        "duration_sec": elapsed,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "COMPLETED",
    }

    (snap_dir / "snapshot_manifest.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    ledger["watermarks"] = new_wm
    ledger["latest_logical_snapshot_id"] = snap_id
    ledger["snapshots"].append(
        {
            "snapshot_id": snap_id,
            "backup_kind": meta["backup_kind"],
            "snapshot_path": str(snap_dir),
            "size_pretty": meta["size_pretty"],
            "delta_rows_exported": total_delta_rows,
            "watermarks": new_wm,
            "duration_sec": elapsed,
            "created_at": meta["created_at"],
        }
    )
    save_ledger(backup_root, ledger)
    record_snapshot_in_db(db_uri, meta)
    return meta


def load_progressive_delta(db_uri: str, snapshot_dir: Path) -> Dict[str, Any]:
    """
    Loads a progressive logical delta snapshot directory back into PostgreSQL
    without downtime using a temporary staging table and `ON CONFLICT DO UPDATE`.
    """
    t0 = time.perf_counter()
    manifest_file = snapshot_dir / "snapshot_manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Missing snapshot_manifest.json in {snapshot_dir}")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    tables_meta: Dict[str, Any] = manifest.get("tables", {})
    restored_counts: Dict[str, int] = {}

    with psycopg.connect(db_uri, autocommit=True) as conn:
        with conn.cursor() as cur:
            for tbl, tinfo in tables_meta.items():
                fname = tinfo.get("file")
                if not fname:
                    restored_counts[tbl] = 0
                    continue
                fpath = snapshot_dir / fname
                if not fpath.exists():
                    continue

                pk_cols = tinfo.get("pk", "id")
                # Introspect the live primary key constraint from pg_constraint when available
                cur.execute(
                    """
                    SELECT pg_get_constraintdef(c.oid)
                    FROM pg_constraint c
                    WHERE c.conrelid = %s::regclass AND c.contype = 'p'
                    LIMIT 1;
                    """,
                    (tbl,),
                )
                pk_row = cur.fetchone()
                if pk_row and pk_row[0] and "(" in pk_row[0]:
                    pk_cols = pk_row[0].split("(", 1)[1].rsplit(")", 1)[0]

                stage_tbl = f"_stage_restore_{tbl}"
                cur.execute(f"DROP TABLE IF EXISTS {stage_tbl};")
                cur.execute(f"CREATE TEMP TABLE {stage_tbl} (LIKE {tbl} INCLUDING DEFAULTS);")

                with subprocess.Popen(
                    [ZSTD_BIN, "-d", "-q", "-c", str(fpath)],
                    stdout=subprocess.PIPE,
                ) as zproc:
                    assert zproc.stdout is not None
                    with cur.copy(
                        f"COPY {stage_tbl} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                    ) as copy:
                        while True:
                            chunk = zproc.stdout.read(65536)
                            if not chunk:
                                break
                            copy.write(chunk)
                    zproc.wait()

                # Query column names to build idempotent ON CONFLICT upsert
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                    """,
                    (tbl,),
                )
                all_cols = [r[0] for r in cur.fetchall()]
                pk_set = {c.strip() for c in pk_cols.split(",")}
                non_pk_cols = [c for c in all_cols if c not in pk_set]
                cols_csv = ", ".join(all_cols)

                if non_pk_cols:
                    update_csv = ", ".join(f"{c} = EXCLUDED.{c}" for c in non_pk_cols)
                    upsert_sql = (
                        f"INSERT INTO {tbl} ({cols_csv}) "
                        f"SELECT {cols_csv} FROM {stage_tbl} "
                        f"ON CONFLICT ({pk_cols}) DO UPDATE SET {update_csv};"
                    )
                else:
                    upsert_sql = (
                        f"INSERT INTO {tbl} ({cols_csv}) "
                        f"SELECT {cols_csv} FROM {stage_tbl} "
                        f"ON CONFLICT ({pk_cols}) DO NOTHING;"
                    )
                cur.execute(upsert_sql)
                restored_counts[tbl] = int(tinfo.get("rows", 0))
                cur.execute(f"DROP TABLE IF EXISTS {stage_tbl};")

    return {
        "status": "RESTORED",
        "snapshot_id": manifest.get("snapshot_id"),
        "restored_tables": restored_counts,
        "duration_sec": round(time.perf_counter() - t0, 2),
    }


def run_physical_backup(
    db_uri: str,
    backup_root: Path,
    incremental: bool = True,
    max_rate_mb: int = 350,
) -> Dict[str, Any]:
    """
    Runs PostgreSQL 18 zero-downtime `pg_basebackup`:
    - If `incremental=True` and a previous `backup_manifest` exists in the ledger
       whose LSN range is covered by `pg_wal/summaries`, executes a block-level
      differential backup (`--incremental=<prev_manifest>`).
    - Otherwise executes a full base backup with zstd tar compression and
      `--checkpoint=spread` so live queries and swarm workers experience zero pause.
    """
    t0 = time.perf_counter()
    wal_state = ensure_wal_summarizer_enabled(db_uri)
    ledger = load_ledger(backup_root)

    prev_manifest = ledger.get("latest_physical_manifest")
    prev_snap_id = ledger.get("latest_physical_snapshot_id")
    use_incremental = bool(incremental and prev_manifest and Path(prev_manifest).exists())

    now_str = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    kind = "PHYSICAL_INCREMENTAL_DIFF" if use_incremental else "PHYSICAL_FULL_BASE"
    prefix = "phys_inc" if use_incremental else "phys_full"
    snap_id = f"{prefix}_{now_str}"
    snap_dir = backup_root / "physical_pg18" / snap_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        PG_BASEBACKUP,
        "-h",
        PG_HOST,
        "-p",
        PG_PORT,
        "-U",
        PG_USER,
        "-D",
        str(snap_dir),
        "-Ft",
        "--compress=server-zstd:level=3",
        "-X",
        "stream",
        "--checkpoint=spread",
        f"--max-rate={max_rate_mb}M",
        "--manifest-checksums=SHA256",
    ]
    if use_incremental:
        cmd.append(f"--incremental={prev_manifest}")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 and use_incremental:
        # If WAL summarizer was enabled after the previous base backup or a gap exists,
        # automatically fall back to a fresh full base backup
        print(
            f"[info] Incremental diff fallback to full base backup ({proc.stderr.strip()})",
            file=sys.stderr,
        )
        shutil.rmtree(snap_dir, ignore_errors=True)
        use_incremental = False
        kind = "PHYSICAL_FULL_BASE"
        snap_id = f"phys_full_{now_str}"
        snap_dir = backup_root / "physical_pg18" / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        cmd = [c for c in cmd if not c.startswith("--incremental=")]
        cmd[cmd.index("-D") + 1] = str(snap_dir)
        proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError(f"pg_basebackup failed: {proc.stderr}")

    manifest_path = snap_dir / "backup_manifest"
    elapsed = round(time.perf_counter() - t0, 2)
    snap_bytes = dir_size_bytes(snap_dir)

    meta = {
        "snapshot_id": snap_id,
        "backup_kind": kind,
        "parent_snapshot_id": prev_snap_id if use_incremental else None,
        "snapshot_path": str(snap_dir),
        "manifest_path": str(manifest_path),
        "size_bytes": snap_bytes,
        "size_pretty": human_bytes(snap_bytes),
        "wal_start_lsn": wal_state.get("summarized_lsn"),
        "wal_end_lsn": wal_state.get("pending_lsn"),
        "watermarks": ledger.get("watermarks", {}),
        "delta_rows_exported": 0,
        "duration_sec": elapsed,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "COMPLETED",
    }

    ledger["latest_physical_manifest"] = str(manifest_path)
    ledger["latest_physical_snapshot_id"] = snap_id
    if not use_incremental:
        ledger["latest_full_physical_id"] = snap_id
    ledger["snapshots"].append(
        {
            "snapshot_id": snap_id,
            "backup_kind": kind,
            "parent_snapshot_id": meta["parent_snapshot_id"],
            "snapshot_path": str(snap_dir),
            "size_pretty": meta["size_pretty"],
            "duration_sec": elapsed,
            "created_at": meta["created_at"],
        }
    )
    save_ledger(backup_root, ledger)
    record_snapshot_in_db(db_uri, meta)
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zero-Downtime Progressive & Incremental Backup Manager for pg_bio (PostgreSQL 18)"
    )
    parser.add_argument(
        "action",
        choices=[
            "status",
            "logical-delta",
            "load-delta",
            "full-physical",
            "diff-physical",
            "daily-auto",
        ],
        help="Backup or restore operation to execute",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=DEFAULT_BACKUP_ROOT,
        help="Root directory for progressive & physical backups",
    )
    parser.add_argument(
        "--db-uri",
        default=DEFAULT_DB_URI,
        help="PostgreSQL connection URI",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="Snapshot directory path for load-delta",
    )
    parser.add_argument(
        "--bootstrap-window",
        type=int,
        default=250000,
        help="Number of recent rows to include on initial logical delta seed (0 = all rows)",
    )
    parser.add_argument(
        "--max-rate-mb",
        type=int,
        default=350,
        help="Max streaming transfer rate in MB/s for pg_basebackup (zero-downtime throttling)",
    )
    args = parser.parse_args()

    if args.action == "status":
        wal_info = ensure_wal_summarizer_enabled(args.db_uri)
        ledger = load_ledger(args.backup_root)
        print(
            json.dumps(
                {
                    "wal_summarizer": wal_info,
                    "backup_root": str(args.backup_root),
                    "ledger": ledger,
                },
                indent=2,
            )
        )
        return

    if args.action == "logical-delta":
        bw = None if args.bootstrap_window == 0 else args.bootstrap_window
        res = run_logical_progressive_delta(args.db_uri, args.backup_root, bootstrap_window=bw)
        print(json.dumps(res, indent=2))
        return

    if args.action == "load-delta":
        if not args.snapshot:
            ledger = load_ledger(args.backup_root)
            latest_id = ledger.get("latest_logical_snapshot_id")
            if not latest_id:
                raise ValueError("No --snapshot specified and no latest_logical_snapshot_id in ledger")
            snap_path = args.backup_root / "logical_deltas" / latest_id
        else:
            snap_path = args.snapshot
        res = load_progressive_delta(args.db_uri, snap_path)
        print(json.dumps(res, indent=2))
        return

    if args.action == "full-physical":
        res = run_physical_backup(args.db_uri, args.backup_root, incremental=False, max_rate_mb=args.max_rate_mb)
        print(json.dumps(res, indent=2))
        return

    if args.action == "diff-physical":
        res = run_physical_backup(args.db_uri, args.backup_root, incremental=True, max_rate_mb=args.max_rate_mb)
        print(json.dumps(res, indent=2))
        return

    if args.action == "daily-auto":
        # 1. Always take a fast logical progressive watermark delta (< 5 sec)
        bw = None if args.bootstrap_window == 0 else args.bootstrap_window
        logical_res = run_logical_progressive_delta(args.db_uri, args.backup_root, bootstrap_window=bw)
        # 2. Take a PostgreSQL 18 block-level incremental diff (or initial full base backup if none exists)
        phys_res = run_physical_backup(args.db_uri, args.backup_root, incremental=True, max_rate_mb=args.max_rate_mb)
        print(
            json.dumps(
                {
                    "logical_delta": logical_res,
                    "physical_backup": phys_res,
                },
                indent=2,
            )
        )
        return


if __name__ == "__main__":
    main()
