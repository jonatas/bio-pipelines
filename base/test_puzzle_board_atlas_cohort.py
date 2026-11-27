import os
import sys

import psycopg
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hypothesis_agent import DB_URL, evaluate_and_advance_open_puzzles

PUZZLE = "smorf-hla-immunopeptidomics"


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


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason='a compiled puzzle copies the atlas of "ptfe-to-bioceramic" if it is '
    'smorf-hla-immunopeptidomics, else "desalination-brine-upcycling"; '
    "which cohort, if any, should an immunopeptidomics puzzle inherit?",
)
def test_immunopeptidomics_atlas_holds_only_its_own_slots(cur):
    cur.execute("DELETE FROM bio_domain_atlas WHERE pipeline_family = %s", (PUZZLE,))
    evaluate_and_advance_open_puzzles(cur)
    cur.execute(
        """
        SELECT subtype, count(*) FROM bio_domain_atlas
        WHERE pipeline_family = %s AND subtype <> 'Puzzle_Locked_Domain'
        GROUP BY 1 ORDER BY 2 DESC
        """,
        (PUZZLE,),
    )
    copied = cur.fetchall()
    assert copied == [], f"{PUZZLE} atlas holds rows copied from another pipeline: {copied}"
