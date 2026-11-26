import os
import sys

import psycopg
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hypothesis_agent import DB_URL, evaluate_and_advance_open_puzzles

PUZZLE = "human-gut-nitrite-ammonia-detox"


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


def add_candidate(cur, uid, annotation, rf_range_iou, tm_score, gated_synergy_score=0.9):
    cur.execute(
        """
        INSERT INTO bio_annotation_evolution (
            uniprot_id, organism_name, original_annotation, evolved_annotation,
            inferred_ec_or_family, best_partner_uniprot, best_partner_organism,
            best_edge_id, vector_distance, seq_identity_pct, twilight_score,
            tm_score, rf_range_iou, len_ratio, gated_synergy_score)
        VALUES (%s, 'Escherichia coli', 'DUF0000', %s,
                'unknown', 'TESTPART01', 'Escherichia coli',
                0, 0.9, 5.0, 0.0,
                %s, %s, 1.0, %s)
        """,
        (uid, annotation, tm_score, rf_range_iou, gated_synergy_score),
    )


def m4_slot(cur):
    evaluate_and_advance_open_puzzles(cur)
    cur.execute(
        """
        SELECT s.assigned_uniprot, s.gate_metric_summary, p.missing_slot_hint
        FROM bio_puzzle_slots s JOIN bio_pipeline_puzzles p USING (puzzle_id)
        WHERE s.puzzle_id = %s AND s.module_role = 'M4_Beacon'
        """,
        (PUZZLE,),
    )
    return cur.fetchone()


def test_unmeasured_candidate_shows_no_invented_numbers(cur):
    add_candidate(cur, "TESTREG001", "ArsR family transcriptional regulator", None, None)
    uid, metric, hint = m4_slot(cur)
    assert uid == "TESTREG001"
    for text in (metric, hint):
        assert "96.9" not in text, text
        assert "0.921" not in text, text
    assert "IoU unmeasured" in metric and "TM unmeasured" in metric, metric


def test_measured_candidate_shows_its_own_numbers(cur):
    add_candidate(cur, "TESTREG001", "ArsR family transcriptional regulator", 0.934, 0.877)
    uid, metric, hint = m4_slot(cur)
    # The TM of this candidate, not the constant 0.921 the slot used to print.
    assert "TM 0.877" in metric, metric
    assert "0.921" not in metric, metric
    assert "IoU 93.4%" in metric, metric
    assert "IoU 93.4%" in hint, hint


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="candidates match on annotation text (ILIKE '%regulator%'); "
    "what should a regulator match on instead (family, EC, domain)?",
)
def test_annotation_that_denies_the_word_is_not_a_candidate(cur):
    # A genuine regulator is present too, with a lower synergy score, so a
    # query that stops matching on the word still has a candidate to pick:
    # only the annotation-text property can make this test pass.
    add_candidate(
        cur, "TESTREG001", "ArsR family transcriptional regulator", 0.93, 0.88,
        gated_synergy_score=0.10,
    )
    add_candidate(
        cur, "TESTDEREG1", "not a regulator: deregulator-like domain of unknown function",
        0.99, 0.99, gated_synergy_score=0.90,
    )
    uid, metric, _ = m4_slot(cur)
    assert uid == "TESTREG001", metric
