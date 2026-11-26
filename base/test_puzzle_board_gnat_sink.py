import os
import sys

import psycopg
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hypothesis_agent import DB_URL, evaluate_and_advance_open_puzzles

PUZZLE = "soda-lake-acetyl-chitin-upcycling"


@pytest.fixture
def cur():
    """One transaction per test, rolled back, so the database is left as it was."""
    conn = psycopg.connect(DB_URL)
    try:
        with conn.cursor() as c:
            c.execute("TRUNCATE bio_annotation_evolution")
            yield c
    finally:
        conn.rollback()
        conn.close()


def add_gnat_candidate(cur, rf_range_iou, uid="TESTGNAT01", gated_synergy_score=0.9):
    cur.execute(
        """
        INSERT INTO bio_annotation_evolution (
            uniprot_id, organism_name, original_annotation, evolved_annotation,
            inferred_ec_or_family, best_partner_uniprot, best_partner_organism,
            best_edge_id, vector_distance, seq_identity_pct, twilight_score,
            rf_range_iou, len_ratio, gated_synergy_score)
        VALUES (%s, 'Natrialba magadii', 'DUF5816', 'GNAT family acetyltransferase',
                'GNAT', 'TESTGNAT02', 'Natrialba magadii',
                0, 0.1, 30.0, 0.5,
                %s, 1.0, %s)
        """,
        (uid, rf_range_iou, gated_synergy_score),
    )


def m3_slot(cur):
    evaluate_and_advance_open_puzzles(cur)
    cur.execute(
        """
        SELECT s.assigned_uniprot, s.is_locked, s.gate_metric_summary, p.slots_filled
        FROM bio_puzzle_slots s JOIN bio_pipeline_puzzles p USING (puzzle_id)
        WHERE s.puzzle_id = %s AND s.module_role = 'M3_Sink'
        """,
        (PUZZLE,),
    )
    return cur.fetchone()


def test_no_discovery_leaves_the_sink_open(cur):
    uid, locked, metric, filled = m3_slot(cur)
    assert (uid, locked, filled) == (None, False, 3), metric


def test_unmeasured_iou_leaves_the_sink_open(cur):
    add_gnat_candidate(cur, None)
    uid, locked, metric, filled = m3_slot(cur)
    assert (uid, locked, filled) == (None, False, 3), metric
    assert "unmeasured" in metric, metric
    assert "95.5%" not in metric, metric


def test_measured_iou_below_the_gate_leaves_the_sink_open(cur):
    add_gnat_candidate(cur, 0.94)
    uid, locked, metric, filled = m3_slot(cur)
    assert (uid, locked, filled) == (None, False, 3), metric
    assert "94.0%" in metric, metric


def test_an_iou_that_rounds_up_to_the_gate_does_not_lock(cur):
    # The gate is 0.95 on the stored value; 0.9495 shows as 95.0% but misses it.
    add_gnat_candidate(cur, 0.9495)
    uid, locked, metric, filled = m3_slot(cur)
    assert (uid, locked, filled) == (None, False, 3), metric


def test_measured_iou_above_the_gate_locks_the_sink(cur):
    add_gnat_candidate(cur, 0.962)
    uid, locked, metric, filled = m3_slot(cur)
    assert (uid, locked, filled) == ("TESTGNAT01", True, 4), metric
    assert "96.2% Pocket IoU" in metric, metric


def test_a_candidate_with_no_iou_does_not_hide_one_that_passes(cur):
    add_gnat_candidate(cur, None, uid="TESTGNAT03", gated_synergy_score=0.99)
    add_gnat_candidate(cur, 0.97, uid="TESTGNAT01", gated_synergy_score=0.10)
    uid, locked, metric, filled = m3_slot(cur)
    assert (uid, locked, filled) == ("TESTGNAT01", True, 4), metric
