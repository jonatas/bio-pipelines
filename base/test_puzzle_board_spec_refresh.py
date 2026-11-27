import os
import sys

import psycopg
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hypothesis_agent import DB_URL, evaluate_and_advance_open_puzzles

PUZZLE = "smorf-hla-immunopeptidomics"

# Every spec column of bio_pipeline_puzzles, with a value the spec never uses.
STALE = {
    "temp_c": -1.0,
    "ph": -1.0,
    "kcat1": -1.0,
    "km1": -1.0,
    "kcat2": -1.0,
    "km2": -1.0,
    "ki": -1.0,
    "boost": -1.0,
    "substrate_smiles": "stale",
    "intermediate_smiles": "stale",
    "sub_label": "stale",
    "int_label": "stale",
    "prod_label": "stale",
    "target_bond": "stale",
    "linker_name": "stale",
    "sink_name": "stale",
    "beacon_name": "stale",
    "slots_total": -1,
}


@pytest.fixture
def cur():
    """One transaction per test, rolled back, so the database is left as it was."""
    conn = psycopg.connect(DB_URL)
    try:
        with conn.cursor() as c:
            yield c
    finally:
        conn.rollback()
        conn.close()


@pytest.mark.parametrize("column", sorted(STALE))
def test_rerun_writes_the_spec_value_over_an_old_row(cur, column):
    """
    An edited puzzle spec must reach a row written by an earlier run:
    ON CONFLICT ... DO UPDATE has to refresh every spec column.
    """
    evaluate_and_advance_open_puzzles(cur)
    cur.execute(f"SELECT {column} FROM bio_pipeline_puzzles WHERE puzzle_id = %s", (PUZZLE,))
    (expected,) = cur.fetchone()

    cur.execute(
        f"UPDATE bio_pipeline_puzzles SET {column} = %s WHERE puzzle_id = %s",
        (STALE[column], PUZZLE),
    )
    evaluate_and_advance_open_puzzles(cur)
    cur.execute(f"SELECT {column} FROM bio_pipeline_puzzles WHERE puzzle_id = %s", (PUZZLE,))
    (actual,) = cur.fetchone()

    assert actual == expected, f"{column} stayed {actual!r} after a rerun; the spec says {expected!r}"
