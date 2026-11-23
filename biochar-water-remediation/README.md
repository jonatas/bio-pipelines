# 🌱 `biochar-water-remediation` — Self-Regenerating Agro-Waste Biochar & Enzymatic Micropollutant Cascade

This pipeline models **coupled adsorption + in-situ enzymatic bioregeneration** on tropical agro-industrial biochars (**sugarcane bagasse**, **Ouricuri palm / *Syagrus coronata***, and **$\text{Mg/Al}$ Layered Double Hydroxide ($\text{LDH}$) biochar composites**) for the continuous removal and mineralization of **emerging water contaminants** (pharmaceuticals, synthetic dyes, and herbicides).

---

## 1. The Chemical Engineering Bottleneck: Fixed-Bed Pore Saturation

Pyrolyzed lignocellulosic biochars and hydrochars exhibit high specific surface area and strong $\pi\text{–}\pi$ electron-donor-acceptor (EDA), hydrogen-bonding, and hydrophobic partitioning affinity for micropollutants such as **Diclofenac**, **Paracetamol**, **Ciprofloxacin**, **Caffeine**, **Atrazine**, and **Methylene Blue**.

However, in continuous fixed-bed column operations, passive adsorption obeys Langmuir/Sips saturation ceilings ($q_{\max}$): once micropores fill, contaminant breakthrough occurs and spent biochar must undergo energy-intensive thermal reactivation ($>500\,^\circ\text{C}$) or chemical elution.

### The 4-Module "Living Biochar" Solution in `pg_bio`
By compiling a 4-module chimeric enzyme consortium directly inside PostgreSQL 18 via `pg_bio`:
1. **Module 1 (`M1_Anchor` — Biochar Graphitic Pore Anchor):** Amphiphilic Class II Hydrophobins and aromatic carbohydrate-binding modules (CBMs) adsorb irreversibly onto $sp^2$ graphitic biochar domains, immobilizing the catalytic domains inside mesopores without leaching into the treated water.
2. **Module 2 (`M2_Scissor` — 3-Enzyme Micropollutant Swarm):**
   - **Multi-Copper Laccase (` Phenolic_NSAID_Oxidizer`):** Oxidizes phenolic and diarylamine pharmaceuticals (Diclofenac, Paracetamol, $17\beta$-Estradiol).
   - **DyP-Type Peroxidase (`Chromophore_Dye_Decolorizer`):** Cleaves heterocyclic thiazine and azo chromophores (Methylene Blue, Rhodamine B).
   - **Chlorohydrolase / Dehalogenase (`Halogenated_Herbicide_Antibiotic_Cleaver`):** Dechlorinates/defluorinates triazine herbicides (Atrazine) and fluoroquinolones (Ciprofloxacin).
3. **Module 3 (`M3_Sink` — Catechol Dioxygenase + $\text{Mg/Al-LDH}$ Sink):** Cleaves quinone/catechol intermediates (preventing reversible polymerization blockages, $K_i$) while $\text{Mg/Al-LDH}$ layers intercalate liberated $\text{Cl}^-/\text{F}^-$ ions—continuously restoring free biochar adsorption sites ($q_e$).
4. **Module 4 (`M4_Beacon` — Breakthrough Optical Sensor):** `DmpR`/`MphR` transcriptional sensor coupled to a Lycopene/Carotenoid reporter to signal column exhaustion before effluent breakthrough.

---

## 2. Running the Experiment in PostgreSQL 18

```bash
# 1. Run the full multi-feedstock compiler (rebuilding the atlas to include biochar-water-remediation)
uv run python -c "from base.compiler import run_declarative_compiler; run_declarative_compiler(rebuild_atlas=True)"

# 2. Execute the standalone SQL benchmark (Cheminformatics Adsorption Boost + Pareto Ranking + Consortium Simplex)
psql postgresql://localhost:28818/bio_demo -f biochar-water-remediation/run_biochar_remediation_swarm.sql
```
