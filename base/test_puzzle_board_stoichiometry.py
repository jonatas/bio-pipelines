import os
import sys

import psycopg
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hypothesis_agent import DB_URL, evaluate_and_advance_open_puzzles


class RecordingCursor:
    """A cursor that keeps every statement it runs, with its parameters."""

    def __init__(self, cur):
        self._cur = cur
        self.statements = []

    def execute(self, query, params=None, **kwargs):
        self.statements.append((str(query), params))
        return self._cur.execute(query, params, **kwargs)

    def __getattr__(self, name):
        return getattr(self._cur, name)


@pytest.fixture
def cur():
    """One transaction per test, rolled back, so the database is left as it was."""
    conn = psycopg.connect(DB_URL)
    try:
        with conn.cursor() as c:
            yield RecordingCursor(c)
    finally:
        conn.rollback()
        conn.close()


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="optimize_consortium_stoichiometry(0.45, 0.35, 0.20, 14.0, 18.0, 10.5, 48.0) "
    "is the same call for every puzzle; which puzzle values should feed f1-f3 and kcat3?",
)
def test_each_puzzle_gets_its_own_stoichiometry(cur):
    rows = evaluate_and_advance_open_puzzles(cur)
    calls = {q + repr(p) for q, p in cur.statements if "optimize_consortium_stoichiometry" in q}
    assert len(calls) == len(rows), (
        f"{len(rows)} puzzles, {len(calls)} distinct stoichiometry call(s): {sorted(calls)}"
    )
