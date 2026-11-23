-- =============================================================================
-- bio-pipelines/biochar-water-remediation/run_biochar_remediation_swarm.sql
-- In-Database Cheminformatics Adsorption Screening, Pareto Chimera Ranking &
-- 48-Hour RK4 Biochar Pore Regeneration Simulation in PostgreSQL 18 (pg_bio)
-- =============================================================================

-- 1. Cheminformatics & Biochar Adsorption Affinity Audit across 6 Emerging Contaminants
--    Uses pg_bio Rust primitives:
--      * parse_smiles()                     (Hückel 4n+2 + Salt/Tautomer Normalized Graph)
--      * compute_ligand_properties_row()    (MW, cLogP, TPSA, HBD, HBA, RotBonds, AromaticRings, Fsp3)
--      * molecule_wl_hash()                 (64-bit Weisfeiler-Lehman Canonical Hash)
--      * @>                                 (VF2 Subgraph Isomorphism for aromatic/halide motifs)
WITH contaminants(contaminant_name, class_label, smiles) AS (
    VALUES
        ('Diclofenac',      'NSAID Pharmaceutical',      'OC(=O)Cc1ccccc1Nc2c(Cl)cccc2Cl'),
        ('Paracetamol',     'Analgesic Pharmaceutical',  'CC(=O)Nc1ccc(O)cc1'),
        ('Ciprofloxacin',   'Fluoroquinolone Antibiotic','O=C(O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O'),
        ('Caffeine',        'Stimulant Tracer',          'Cn1cnc2c1c(=O)n(C)c(=O)n2C'),
        ('Atrazine',        'Chlorotriazine Herbicide',  'CCn1nc(Cl)nc(NC(C)C)n1'),
        ('Methylene Blue',  'Cationic Thiazine Dye',     'CN(C)c1ccc2nc3ccc(N(C)C)cc3s2c1')
)
SELECT c.contaminant_name,
       c.class_label,
       ROUND(lp.mw::numeric, 1) AS mw_da,
       ROUND(lp.logp::numeric, 2) AS clogp,
       ROUND(lp.tpsa::numeric, 1) AS tpsa_a2,
       lp.hbd::int AS hbd,
       lp.hba::int AS hba,
       lp.aromatic_rings::int AS arom_rings,
       parse_smiles(c.smiles) @> parse_smiles('c1ccccc1') AS has_benzene_pi_stack,
       -- Estimated Biochar Langmuir-Hinshelwood Interfacial Enrichment Boost (pi-pi + hydrophobic partitioning)
       ROUND((2.5 + GREATEST(lp.logp, 0.0) * 0.85 + lp.aromatic_rings * 1.15)::numeric, 2) AS biochar_adsorption_boost
FROM contaminants c
CROSS JOIN LATERAL compute_ligand_properties_row(c.smiles) lp
ORDER BY biochar_adsorption_boost DESC;

-- 2. Top Pareto-Optimal Biochar-Anchored Chimeras (Module 1 Anchor × Module 2 Scissor)
SELECT pipeline_id,
       candidate_rank,
       anchor_uniprot,
       linker_sequence,
       scissor_uniprot,
       sink_tag,
       host_code,
       ROUND(anchor_gravy::numeric, 3) AS anchor_gravy,
       ROUND(scissor_mw_kda::numeric, 1) AS scissor_mw_kda,
       ROUND(composite_pareto_score::numeric, 4) AS pareto_score,
       ROUND((predicted_48h_conversion * 100.0)::numeric, 1) AS rk4_48h_mineralization_pct
FROM bio_chimeric_runs
WHERE pipeline_id = 'biochar-water-remediation'
ORDER BY candidate_rank ASC;

-- 3. 3-Enzyme Consortium Stoichiometry Optimization for Mixed Effluent
--    (45% NSAIDs/Phenolics : 35% Synthetic Dyes : 20% Triazine/Quinolone Halides)
SELECT ROUND(w1_fraction::numeric, 3) AS w_laccase,
       ROUND(w2_fraction::numeric, 3) AS w_dyp_peroxidase,
       ROUND(w3_fraction::numeric, 3) AS w_chlorohydrolase,
       ROUND((predicted_48h_conversion * 100.0)::numeric, 1) AS total_48h_removal_pct,
       ROUND(balance_efficiency::numeric, 4) AS balance_index
FROM optimize_consortium_stoichiometry(0.45, 0.35, 0.20, 18.5, 21.0, 12.5, 48.0);
