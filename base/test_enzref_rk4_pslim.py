import os
import sys
import psycopg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from hypothesis_agent import (
    DB_URL,
    evaluate_m3_sink_candidate_with_enzref_rk4,
    discover_disordered_dual_slim_tethers,
)


def test_split_reaction_roles_and_enzref_antisymmetry():
    """
    Verifies Phase 1 & 4 requirements in PostgreSQL 18:
    - `bio_split_reaction_roles` handles `A.B>>C.D` and agent stripping `A>agent>B`.
    - `bio_enzref_flux_rank` is strictly antisymmetric under `swap(reactant, product)`.
    """
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT reactants_smiles, products_smiles FROM bio_split_reaction_roles('CC(=O)Oc1ccccc1C(=O)O.O>[Zn+2]>CC(=O)O.O=C(O)c1ccccc1O');"
            )
            r_s, p_s = cur.fetchone()
            assert r_s == "CC(=O)Oc1ccccc1C(=O)O.O"
            assert p_s == "CC(=O)O.O=C(O)c1ccccc1O"

            enz_bg = [1.0, 0.0, 0.0, 0.0, 0.5, -0.5, 0.2, 0.1]
            react_v = [2.0, 1.0, 0.0, 0.0, 0.5, -0.5, 0.2, 0.1]
            prod_v = [3.5, 2.5, 0.0, 0.0, 0.5, -0.5, 0.2, 0.1]

            cur.execute(
                """
                SELECT
                    bio_enzref_flux_rank(%s::real[], %s::real[], %s::real[]) AS fwd,
                    bio_enzref_flux_rank(%s::real[], %s::real[], %s::real[]) AS rev;
                """,
                (enz_bg, react_v, prod_v, enz_bg, prod_v, react_v),
            )
            fwd, rev = cur.fetchone()
            assert fwd > 0.25, f"Expected positive forward flux rank, got {fwd}"
            assert abs(fwd + rev) < 1e-5, f"Expected exact antisymmetry fwd == -rev, got {fwd} vs {rev}"


def test_m3_sink_backpressure_depresses_rk4_yield_and_downranks_candidate():
    """
    Verifies Phase 3 & 4 requirement:
    High `backpressure_risk` on an `M3_Sink` candidate depresses 48h RK4 net yield
    and gets down-ranked (`status == 'Down_Ranked_Backpressure'`, `promoted == False`)
    before ledger promotion.
    """
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            enz_bg = [1.0, 0.0, 0.0, 0.0, 0.5, -0.5, 0.2, 0.1]
            react_v = [2.0, 1.0, 0.0, 0.0, 0.5, -0.5, 0.2, 0.1]
            # Productive forward M3_Sink product shift (low backpressure_risk)
            prod_forward = [3.5, 2.5, 0.0, 0.0, 0.5, -0.5, 0.2, 0.1]
            # Product-retention / inhibitory M3_Sink shift (high backpressure_risk)
            prod_backpressure = [0.5, -0.5, 0.0, 0.0, 0.5, -0.5, 0.2, 0.1]

            rxn = "CC(=O)NC1C(O)OC(CO)C(O)C1O>O>NC1C(O)OC(CO)C(O)C1O.CC(=O)O"

            good_sink = evaluate_m3_sink_candidate_with_enzref_rk4(
                cur,
                enzyme_bg_vec=enz_bg,
                rxn_smiles=rxn,
                reactant_vec_override=react_v,
                product_vec_override=prod_forward,
            )
            stalled_sink = evaluate_m3_sink_candidate_with_enzref_rk4(
                cur,
                enzyme_bg_vec=enz_bg,
                rxn_smiles=rxn,
                reactant_vec_override=react_v,
                product_vec_override=prod_backpressure,
            )

            assert stalled_sink["backpressure_risk"] > good_sink["backpressure_risk"] + 0.5, (
                f"Expected stalled M3_Sink to have higher backpressure_risk: {stalled_sink} vs {good_sink}"
            )
            assert stalled_sink["predicted_48h_yield_pct"] < good_sink["predicted_48h_yield_pct"] - 10.0, (
                f"Expected high backpressure_risk to depress 48h RK4 net yield by >10%: "
                f"{stalled_sink['predicted_48h_yield_pct']}% vs {good_sink['predicted_48h_yield_pct']}%"
            )
            assert stalled_sink["composite_rank"] < good_sink["composite_rank"], (
                "Stalled M3_Sink must have a strictly lower composite rank than productive M3_Sink"
            )
            assert good_sink["promoted"] is True
            assert good_sink["status"] == "Promoted_To_Atlas"
            assert stalled_sink["promoted"] is False
            assert stalled_sink["status"] == "Down_Ranked_Backpressure"


def test_pslim_window_pool_and_dual_slim_tether_junction_sanity():
    """
    Verifies Phase 2 & 3 Disordered Microprotein SLiM Window Indexing (`bio_pslim_window_pool`)
    and `L0JP89`-style dual-SLiM metabolon couplers (`bio_match_dual_slim_tether` + junction sanity check).
    """
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            couplers = discover_disordered_dual_slim_tethers(cur, limit=5)
            assert len(couplers) >= 3, f"Expected >= 3 disordered dual-SLiM couplers, got {len(couplers)}"
            l0jp89 = next(c for c in couplers if c["microprotein_id"] == "L0JP89")
            assert l0jp89["microprotein_len"] <= 110
            assert l0jp89["end_a"] + 6 <= l0jp89["start_b"], (
                f"Expected non-overlapping SLiM windows on L0JP89: {l0jp89['end_a']} + 6 <= {l0jp89['start_b']}"
            )
            assert l0jp89["junction_sanity_pass"] is True
            assert l0jp89["recommended_operon_mode"] == "Single_Polypeptide_Fusion"

            # Verify split hydrophobic core across linker is rejected for Single_Polypeptide_Fusion
            cur.execute(
                """
                SELECT junction_sanity_pass, recommended_operon_mode
                FROM bio_audit_fusion_junction_sanity(
                    'DKTKREEVDDDDIVLFWVIVLFWVVVLLFIIVLFWVGSAQAPVGRDTV',
                    8,
                    40
                );
                """
            )
            j_pass, j_mode = cur.fetchone()
            assert j_pass is False
            assert "Bicistronic_Operon_Required" in j_mode
