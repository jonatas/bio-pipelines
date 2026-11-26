-- =============================================================================
-- bio-pipelines/base/schema.sql
-- Universal 4-Module Synthetic Biology Compiler Schema for pg_bio
-- Supports:
--   1. ptfe-to-bioceramic        (PTFE/PFAS -> Fluorapatite Ca5(PO4)3F)
--   2. plastics-upcycling        (PET/PU -> Monomers / Vanillin / FDCA)
--   3. sugarcane-bagasse         (Cellulose/Xylan/Lignin -> C5/C6 & 2,5-FDCA)
--   4. corn-stover-bran          (Arabinoxylan Diferulate Bridges -> Bio-Vanillin)
--   5. habanero-spicy-fuel       (Capsicum GGPPS P80042 Isoprenoids -> Drop-In Bio-Jet Fuel)
-- =============================================================================

CREATE TABLE IF NOT EXISTS bio_substrates (
    pipeline_id VARCHAR(50) PRIMARY KEY,
    feedstock_name TEXT NOT NULL,
    target_bond VARCHAR(60) NOT NULL,
    bond_dissociation_kj_mol FLOAT8 NOT NULL,
    representative_smiles TEXT NOT NULL,
    reactor_temp_c FLOAT8 NOT NULL,
    reactor_ph FLOAT8 NOT NULL,
    equilibrium_sink_product TEXT NOT NULL,
    optical_beacon_readout TEXT NOT NULL
);

TRUNCATE bio_substrates CASCADE;

INSERT INTO bio_substrates (
    pipeline_id, feedstock_name, target_bond, bond_dissociation_kj_mol,
    representative_smiles, reactor_temp_c, reactor_ph,
    equilibrium_sink_product, optical_beacon_readout
) VALUES
(
    'ptfe-to-bioceramic',
    'PTFE / PFAS Fluoropolymers',
    'C-F (Aliphatic Fluorocarbon)',
    540.0,
    'FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F',
    37.0,
    7.4,
    'Fluorapatite Ca5(PO4)3F (via AMELX Tag)',
    'crcB Fluoride Riboswitch -> Ruby-Red Phytoene Desaturase (W9DPJ6)'
),
(
    'plastics-upcycling',
    'PET & Ester-Urethane Plastics',
    'Aromatic Ester / Urethane (C(=O)-O)',
    360.0,
    'OC(=O)c1ccc(C(=O)OCCO)cc1',
    68.0,
    8.0,
    'Ca-Terephthalate / Protocatechuate -> Vanillin or 2,5-FDCA',
    'PcaU Terephthalate Biosensor -> Violacein / Carotenoid Beacon'
),
(
    'sugarcane-bagasse',
    'Steam-Exploded Sugarcane Bagasse (42% Cellulose, 25% Xylan, 20% Lignin)',
    'beta-1,4-Glycosidic + Lignin beta-O-4 Ether',
    310.0,
    'OCC1OC(OC2C(O)C(O)C(OC2CO)O)C(O)C(O)C1O',
    55.0,
    5.0,
    'Cellobiose Phosphorylase + HMF/FDCA Oxidase -> 2,5-FDCA',
    'XylR / FerC Xylose-Ferulate Biosensor -> Lycopene Readout'
),
(
    'corn-stover-bran',
    'Corn Stover & Pericarp Bran (Arabinoxylan-Ferulate Crosslinks)',
    'Diferulate-Arabinoxylan Ester Bridge',
    335.0,
    'COc1cc(/C=C/C(=O)OCC2OC(O)C(O)C2O)ccc1O',
    50.0,
    5.5,
    'FDC1 + VpVAN Cascade -> Bio-Vanillin',
    'FerC Ferulate-Inducible Chromoprotein Beacon'
),
(
    'habanero-spicy-fuel',
    'Capsicum GGPPS (P80042) Prenyl Diphosphates (DMAPP / IPP / FPP / GGPP)',
    'Allylic Pyrophosphate Ester (C-OPP)',
    295.0,
    'CC(C)=CCCC(C)=CCCC(C)=CCCC(C)=CCOP(=O)(O)OP(=O)(O)O',
    32.0,
    6.8,
    'Terpene Synthase Cyclization + Dodecane Overlay -> Drop-In C15/C20 Bio-Jet Fuel',
    'ERG9/idi FPP-GGPP Sensor -> Capsicum PSY (P37272) + PDS (P80093) Carotenoid Beacon'
),
(
    'biochar-water-remediation',
    'Agro-Waste Biochar (Bagasse / Ouricuri / Mg-Al LDH) + Emerging Micropollutants (Diclofenac, Dyes, Atrazine)',
    'Diaryl Amine / Thiazine Chromophore / Aryl C-Cl',
    385.0,
    'OC(=O)Cc1ccccc1Nc2c(Cl)cccc2Cl',
    30.0,
    6.5,
    'Catechol 1,2-Dioxygenase + Mg/Al-LDH Chloride Sink (Biochar Pore Regeneration)',
    'DmpR / MphR Phenolic & Macrolide Sensor -> Lycopene Breakthrough Alert'
),
(
    'cyanide-mine-tailings',
    'Alkaline Gold-Mine Heap Leachate (Cyanide CN- + Persulfide GSSH / Sulfide HS-, pH 9.8, 3.0 M NaCl)',
    'Nitrile C#N + Hydrodisulfide R-S-SH',
    415.0,
    'N#CSCCc1ccc(O)c(O)c1',
    38.0,
    9.8,
    'Bifunctional MBL-Rhodanese Persulfide Dioxygenase-Sulfurtransferase (A0ABD6AX71 x M0AE48) -> Thiocyanate SCN- & Sulfate SO4(2-)',
    'ArsR / BigR Persulfide-Cyanide Sensor (A0A2S2KQG4) -> Halophilic Phytoene Desaturase CrtI (A0A0W1R8L8)'
),
(
    'desalination-brine-upcycling',
    'Hypersaline Desalination Reject Brine + Cheese-Whey Permeate (3.5 M NaCl, pH 9.5, Lactose / UDP-Glucose)',
    'Pyranose C4-OH & Pyranose-Furanose Ring',
    305.0,
    'OCC1OC(Oc2ccccc2)C(O)C(O)C1O',
    45.0,
    9.5,
    'Soda-Lake GalE 4-Epimerase (D3SWG7 x A0ABD5UZ94) + Glf Mutase (A0A1I1DB55) -> Rare UDP-Galactofuranose & Prebiotic Galacto-Oligosaccharides',
    'GalR / LacI Halophilic Sugar Sensor -> Bacterioruberin Carotenoid Beacon (A0A0W1R8L8)'
);

-- Universal 4-Module Domain Atlas populated across the 2.34M protein space
CREATE TABLE IF NOT EXISTS bio_domain_atlas (
    id SERIAL PRIMARY KEY,
    pipeline_family VARCHAR(40) NOT NULL,
    module_role VARCHAR(40) NOT NULL,     -- 'M1_Anchor', 'M2_Scissor', 'M3_Sink', 'M4_Beacon'
    subtype VARCHAR(50) NOT NULL,         -- e.g. 'Hydrophobin', 'CBM', 'PETase_Cutinase', 'Cellulase_LPMO', 'Feruloyl_Esterase'
    uniprot_id VARCHAR(20) NOT NULL,
    organism_name TEXT NOT NULL,
    protein_description TEXT,
    seq_length INT NOT NULL,
    mw_kda FLOAT8 NOT NULL,
    isoelectric_pi FLOAT8 NOT NULL,
    gravy_hydropathy FLOAT8 NOT NULL,
    shannon_entropy FLOAT8 NOT NULL,
    UNIQUE (pipeline_family, module_role, subtype, uniprot_id)
);

CREATE INDEX IF NOT EXISTS idx_bio_domain_family_role
    ON bio_domain_atlas (pipeline_family, module_role, subtype);
CREATE INDEX IF NOT EXISTS idx_bio_domain_gravy
    ON bio_domain_atlas (gravy_hydropathy DESC);

-- Chimeric Swarm Optimization & Pareto Front Runs
CREATE TABLE IF NOT EXISTS bio_chimeric_runs (
    run_id SERIAL PRIMARY KEY,
    pipeline_id VARCHAR(50) NOT NULL,
    candidate_rank INT NOT NULL,
    anchor_uniprot VARCHAR(20) NOT NULL,
    linker_sequence TEXT NOT NULL,
    scissor_uniprot VARCHAR(20) NOT NULL,
    sink_tag VARCHAR(40) NOT NULL,
    host_code VARCHAR(30) NOT NULL,
    anchor_gravy FLOAT8,
    scissor_mw_kda FLOAT8,
    composite_pareto_score FLOAT8,
    predicted_48h_conversion FLOAT8,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Autonomous Multi-Agent Annotation Evolution & Hypothesis Ledger
-- =============================================================================

CREATE TABLE IF NOT EXISTS bio_annotation_evolution (
    uniprot_id VARCHAR(20) PRIMARY KEY,
    organism_name TEXT NOT NULL,
    original_annotation TEXT NOT NULL,
    evolved_annotation TEXT NOT NULL,
    inferred_ec_or_family TEXT NOT NULL,
    best_partner_uniprot VARCHAR(20) NOT NULL,
    best_partner_organism TEXT NOT NULL,
    best_edge_id BIGINT NOT NULL,
    evidence_edges_count INT NOT NULL DEFAULT 1,
    distinct_genera_count INT NOT NULL DEFAULT 1,
    vector_distance FLOAT8 NOT NULL,
    seq_identity_pct FLOAT8 NOT NULL,
    twilight_score FLOAT8 NOT NULL,
    tm_score FLOAT8,
    core_rmsd FLOAT8,
    rf_range_iou FLOAT8,
    rf_score FLOAT8,
    len_ratio FLOAT8 NOT NULL,
    gated_synergy_score FLOAT8 NOT NULL,
    evolution_version INT NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'Evolving', -- 'Evolving', '3D_Verified', 'Promoted_To_Atlas'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bio_hypothesis_ledger (
    hypothesis_id SERIAL PRIMARY KEY,
    hypothesis_code VARCHAR(40) UNIQUE NOT NULL,
    target_pipeline VARCHAR(50) NOT NULL,
    is_new_scenario BOOLEAN NOT NULL DEFAULT FALSE,
    module_role VARCHAR(40) NOT NULL,               -- 'M1_Anchor', 'M2_Scissor', 'M3_Sink', 'M4_Beacon'
    subtype VARCHAR(50) NOT NULL,
    candidate_uniprot VARCHAR(20) NOT NULL,
    candidate_organism TEXT NOT NULL,
    reference_homolog VARCHAR(20) NOT NULL,
    hypothesis_title TEXT NOT NULL,
    biological_rationale TEXT NOT NULL,
    fold_gate_tm FLOAT8,
    core_rmsd_a FLOAT8,
    rf_pocket_iou FLOAT8,
    gist_props_matched INT,
    gated_synergy_score FLOAT8 NOT NULL,
    chimera_partner_uniprot VARCHAR(20),
    chimera_flory_ratio FLOAT8,
    pareto_score FLOAT8,
    forward_flux_score FLOAT4 DEFAULT 0.0,
    backpressure_risk FLOAT4 DEFAULT 0.0,
    role_contrast_norm FLOAT4 DEFAULT 0.0,
    c_over_cstar FLOAT4 DEFAULT 0.0,
    baseline_48h_yield_pct FLOAT8,
    predicted_48h_yield_pct FLOAT8,
    yield_delta_pct FLOAT8,
    status VARCHAR(30) NOT NULL DEFAULT 'Proposed', -- 'Proposed', '3D_Verified', 'RK4_Validated', 'Promoted_To_Atlas', 'New_Scenario_Ready', 'Down_Ranked_Backpressure', 'Rejected'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE bio_hypothesis_ledger
    ADD COLUMN IF NOT EXISTS forward_flux_score FLOAT4 DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS backpressure_risk FLOAT4 DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS role_contrast_norm FLOAT4 DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS c_over_cstar FLOAT4 DEFAULT 0.0;

CREATE TABLE IF NOT EXISTS bio_agent_checkpoint (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_scanned_edge_id BIGINT NOT NULL DEFAULT 0,
    total_cycles_run INT NOT NULL DEFAULT 0,
    total_annotations_evolved INT NOT NULL DEFAULT 0,
    total_hypotheses_promoted INT NOT NULL DEFAULT 0,
    last_run_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO bio_agent_checkpoint (id, last_scanned_edge_id, total_cycles_run, total_annotations_evolved, total_hypotheses_promoted)
VALUES (1, 0, 0, 0, 0)
ON CONFLICT (id) DO NOTHING;

