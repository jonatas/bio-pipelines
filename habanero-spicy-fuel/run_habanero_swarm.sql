-- =============================================================================
-- bio-pipelines/habanero-spicy-fuel/run_habanero_swarm.sql
-- Swarm & Pareto Search for Capsicum GGPPS (P80042) & Extremophile Prenyl
-- Synthases Coupled to Lipid-Droplet Anchors and Terpene Cyclase Biofuel Sinks
-- =============================================================================

SELECT pipeline_id,
       candidate_rank,
       anchor_uniprot,
       linker_sequence,
       scissor_uniprot,
       sink_tag,
       host_code,
       anchor_gravy,
       scissor_mw_kda,
       composite_pareto_score,
       predicted_48h_conversion
FROM bio_chimeric_runs
WHERE pipeline_id = 'habanero-spicy-fuel'
ORDER BY candidate_rank ASC;
