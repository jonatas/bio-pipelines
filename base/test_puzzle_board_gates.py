import os
import sys

import psycopg
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hypothesis_agent import DB_URL, evaluate_and_advance_open_puzzles

# Each slot of the puzzle board has a condition, an embedded SQL gate and a
# verdict. Today the verdicts g1, g2 and g4 are bool(slot["locked"]), a
# literal in the spec; only g3 also checks a computed value
# (rk4_yield_delta_pct >= 25). The gate strings are stored and shown but
# never run, and the metric text, "PASS" included, is written by hand.
#
# These tests say what a computed verdict would satisfy. They are marked
# xfail(strict=True): they document the gap without breaking the suite, and
# the change that computes the verdicts must remove the markers.
REASON = "slot verdicts are spec literals; embedded_sql_gate is never run"


class RecordingCursor:
    """A cursor that keeps the text of every statement it runs."""

    def __init__(self, cur):
        self._cur = cur
        self.statements = []

    def execute(self, query, params=None, **kwargs):
        self.statements.append(str(query))
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


def remove_evidence(cur):
    cur.execute("TRUNCATE bio_annotation_evolution")
    cur.execute("DELETE FROM proteins")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=REASON)
def test_no_gate_passes_without_evidence(cur):
    remove_evidence(cur)
    evaluate_and_advance_open_puzzles(cur)
    cur.execute(
        """
        SELECT puzzle_id, phase1_gate_passed, phase2_gate_passed,
               phase3_gate_passed, phase4_gate_passed
        FROM bio_pipeline_puzzles
        WHERE phase1_gate_passed OR phase2_gate_passed
           OR phase3_gate_passed OR phase4_gate_passed
        ORDER BY 1
        """
    )
    passing = cur.fetchall()
    assert passing == [], f"gates pass with no proteins and no annotations: {passing}"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=REASON)
def test_no_slot_reports_pass_without_evidence(cur):
    remove_evidence(cur)
    evaluate_and_advance_open_puzzles(cur)
    cur.execute(
        """
        SELECT puzzle_id, module_role FROM bio_puzzle_slots
        WHERE gate_metric_summary LIKE '%PASS%' ORDER BY 1, 2
        """
    )
    passing = cur.fetchall()
    assert passing == [], f"slots report PASS with no proteins and no annotations: {passing}"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=REASON)
def test_every_gate_is_valid_sql(cur):
    evaluate_and_advance_open_puzzles(cur)
    cur.execute("SELECT puzzle_id, module_role, embedded_sql_gate FROM bio_puzzle_slots ORDER BY 1, 2")
    broken = []
    for puzzle_id, role, gate in cur.fetchall():
        cur.execute("SAVEPOINT gate")
        try:
            # Names such as seq or p resolve only where the gate runs; a
            # syntax error is wrong anywhere.
            cur.execute(f"EXPLAIN SELECT 1 WHERE ({gate})")
        except psycopg.errors.SyntaxError as e:
            broken.append((puzzle_id, role, str(e).splitlines()[0]))
        except psycopg.Error:
            pass
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT gate")
    assert broken == [], f"gates that are not valid SQL: {broken}"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=REASON)
def test_every_gate_runs_during_evaluation(cur):
    evaluate_and_advance_open_puzzles(cur)
    ran = list(cur.statements)
    cur.execute("SELECT puzzle_id, module_role, embedded_sql_gate FROM bio_puzzle_slots ORDER BY 1, 2")
    never_ran = [(p, r) for p, r, gate in cur.fetchall() if not any(gate in q for q in ran)]
    assert never_ran == [], f"gates never executed during evaluation: {never_ran}"
