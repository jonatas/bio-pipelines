# Check fixtures

`AF-A0A1S8AT22-F1-model_v4.pdb` and `AF-A0A1H3IA37-F1-model_v4.pdb` are
AlphaFold DB predicted structures, byte for byte the model v6 files
`https://alphafold.ebi.ac.uk/files/AF-<id>-F1-model_v6.pdb` (checked
2026-11-26). They carry the `_v4` names because that is the file name the
app reads: when v4 is gone, `fetch_pdb_string` downloads v6 and saves it
under that name.

Licence: AlphaFold DB data is CC-BY-4.0, not the repository's own
licence. It may be copied and redistributed with attribution:
AlphaFold DB, EMBL-EBI and Google DeepMind; Jumper et al., Nature 2021;
Varadi et al., Nucleic Acids Research 2024.

`checks.e2e` runs offline, and `validate_swarm_web.py` calls
`/api/compare/A0A1S8AT22/A0A1H3IA37`, which needs these two models, so the
check puts them in the models directory before it starts.
