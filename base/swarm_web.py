import os
import json
import time
import urllib.request
from flask import Flask, render_template_string, jsonify, request
import psycopg

try:
    from base.discovery_routes import app
except ImportError:
    from discovery_routes import app

DB_URI = os.getenv("PG_BIO_URL", "postgresql://localhost:28818/bio_demo")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = "/Users/jonatas/code/ideia.me/assets/models"
STRUCTURES_DIR = os.path.join(REPO_ROOT, "structures")

PIPELINE_PRESETS = {
    "ptfe-to-bioceramic": {
        "title": "PTFE / PFAS -> Fluorapatite Bioceramic (37°C, pH 7.4)",
        "temp_c": 37.0,
        "ph": 7.4,
        "smiles": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
        "ref_smiles": "FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(=O)O",
        "sub_label": "Surface C-F Sites (µM)",
        "int_label": "Free Fluoride [F⁻] (µM)",
        "prod_label": "Fluorapatite Ca₅(PO₄)₃F (µM eq)",
        "kcat1": 24.0,
        "km1": 380.0,
        "kcat2": 42.0,
        "km2": 30.0,
        "ki": 22.0,
        "boost": 8.5,
        "f1": 0.50,
        "f2": 0.30,
        "f3": 0.20,
        "target_bond": "Aliphatic C–F Bond (540 kJ/mol)",
        "linker_name": "GGGGS ×3 Flexible Linker (28.0 Å Separation)",
        "sink_name": "AMELX C-Terminal Mineral Tag (WPSTDKTKREEVD)",
        "beacon_name": "crcB Fluoride Riboswitch → Ruby-Red PDS (W9DPJ6)",
    },
    "plastics-upcycling": {
        "title": "PET & Ester-Urethane -> PCA / Bio-Monomer Sink (68°C, pH 8.0)",
        "temp_c": 68.0,
        "ph": 8.0,
        "smiles": "OC(=O)c1ccc(C(=O)OCCO)cc1",
        "ref_smiles": "OC(=O)c1ccc(C(=O)O)cc1",
        "sub_label": "PET Ester Bonds (µM)",
        "int_label": "MHET / Acidic Monomer (µM)",
        "prod_label": "Upcycled Sink Product (µM)",
        "kcat1": 25.5,
        "km1": 420.0,
        "kcat2": 38.0,
        "km2": 35.0,
        "ki": 18.0,
        "boost": 7.2,
        "f1": 0.65,
        "f2": 0.20,
        "f3": 0.15,
        "target_bond": "Aromatic Ester / Urethane C(=O)–O (360 kJ/mol)",
        "linker_name": "Rigid Helical EAAAK ×3 Linker (28.0 Å Separation)",
        "sink_name": "Protocatechuate 3,4-Dioxygenase + Ca-TPA Sink",
        "beacon_name": "PcaU Terephthalate Sensor → Violacein Beacon",
    },
    "sugarcane-bagasse": {
        "title": "Sugarcane Bagasse (42% Cellulose, 25% Xylan, 20% Lignin) -> 2,5-FDCA (55°C, pH 5.0)",
        "temp_c": 55.0,
        "ph": 5.0,
        "smiles": "OCC1OC(OC2C(O)C(O)C(OC2CO)O)C(O)C(O)C1O",
        "ref_smiles": "OCC1OC(O)C(O)C(O)C1O",
        "sub_label": "Cellulose/Xylan Chains (µM)",
        "int_label": "Cellobiose Intermediate (µM)",
        "prod_label": "G1P + 2,5-FDCA Sink (µM)",
        "kcat1": 23.0,
        "km1": 450.0,
        "kcat2": 40.0,
        "km2": 32.0,
        "ki": 15.0,
        "boost": 8.0,
        "f1": 0.42,
        "f2": 0.25,
        "f3": 0.20,
        "target_bond": "β-1,4-Glycosidic + Lignin β-O-4 Ether (310 kJ/mol)",
        "linker_name": "Cellulosomal Cohesin–Dockerin Bridge (28.0 Å)",
        "sink_name": "Cellobiose Phosphorylase + HMF Oxidase → 2,5-FDCA",
        "beacon_name": "XylR / FerC Xylose-Ferulate Sensor → Lycopene",
    },
    "corn-stover-bran": {
        "title": "Corn Stover Diferulate Bridges -> Bio-Vanillin (50°C, pH 5.5)",
        "temp_c": 50.0,
        "ph": 5.5,
        "smiles": "COc1cc(/C=C/C(=O)OCC2OC(O)C(O)C2O)ccc1O",
        "ref_smiles": "COc1cc(/C=C/C(=O)O)ccc1O",
        "sub_label": "Diferulate Ester Bridges (µM)",
        "int_label": "Free Ferulic Acid (µM)",
        "prod_label": "Bio-Vanillin Sink (µM)",
        "kcat1": 24.5,
        "km1": 390.0,
        "kcat2": 41.0,
        "km2": 30.0,
        "ki": 20.0,
        "boost": 7.8,
        "f1": 0.36,
        "f2": 0.28,
        "f3": 0.18,
        "target_bond": "Diferulate–Arabinoxylan Ester Bridge (335 kJ/mol)",
        "linker_name": "GGGGSEAAAKGGGGS Chimeric Bridge (28.0 Å)",
        "sink_name": "Ferulic Acid Decarboxylase (FDC1) + VpVAN → Vanillin",
        "beacon_name": "FerC Ferulate-Inducible Chromoprotein Beacon",
    },
    "habanero-spicy-fuel": {
        "title": "Habanero Capsicum GGPPS (P80042) -> Drop-In Bio-Aviation Jet Fuel (32°C, pH 6.8)",
        "temp_c": 32.0,
        "ph": 6.8,
        "smiles": "CC(C)=CCCC(C)=CCCC(C)=CCCC(C)=CCOP(=O)(O)OP(=O)(O)O",
        "ref_smiles": "CC(C)=CCCC(C)=CCCC(C)=CC=C",
        "sub_label": "Prenyl Precursors IPP/DMAPP (µM)",
        "int_label": "Transient GGPP / FPP Pool (µM)",
        "prod_label": "Drop-In C15/C20 Bio-Jet Terpene (µM)",
        "kcat1": 26.0,
        "km1": 360.0,
        "kcat2": 44.0,
        "km2": 28.0,
        "ki": 16.0,
        "boost": 8.8,
        "f1": 0.48,
        "f2": 0.32,
        "f3": 0.20,
        "target_bond": "Allylic Prenyl Pyrophosphate C–OPP (295 kJ/mol)",
        "linker_name": "Plastoglobule GGGGS ×3 Tether (28.0 Å Separation)",
        "sink_name": "Terpene Cyclase + Dodecane Overlay → Bio-Jet Terpene",
        "beacon_name": "ERG9/idi Sensor → Capsicum PSY (P37272) + PDS (P80093)",
    },
    "biochar-water-remediation": {
        "title": "Self-Regenerating Agro-Waste Biochar -> Micropollutant Mineralization (30°C, pH 6.5)",
        "temp_c": 30.0,
        "ph": 6.5,
        "smiles": "OC(=O)Cc1ccccc1Nc2c(Cl)cccc2Cl",
        "ref_smiles": "CC(=O)Nc1ccc(O)cc1",
        "sub_label": "Adsorbed Diclofenac / Micropollutant (µM)",
        "int_label": "Chlorinated / Quinone Intermediate (µM)",
        "prod_label": "Mineralized Ring-Cleaved + LDH-Cl⁻ Sink (µM)",
        "kcat1": 25.0,
        "km1": 370.0,
        "kcat2": 43.0,
        "km2": 30.0,
        "ki": 19.0,
        "boost": 8.4,
        "f1": 0.45,
        "f2": 0.35,
        "f3": 0.20,
        "target_bond": "Diaryl Amine / Thiazine Chromophore / Aryl C–Cl (385 kJ/mol)",
        "linker_name": "GGGGS ×3 Biochar-Pore Tether (28.0 Å Separation)",
        "sink_name": "Catechol 1,2-Dioxygenase + Mg/Al-LDH Chloride Sink (Regenerates q_e)",
        "beacon_name": "DmpR / MphR Phenolic & Macrolide Sensor → Lycopene Breakthrough Alert",
    },
    "cyanide-mine-tailings": {
        "title": "Alkaline Gold-Mine Cyanide & Sulfide Tailings -> MBL-Rhodanese Detoxification (38°C, pH 9.8)",
        "temp_c": 38.0,
        "ph": 9.8,
        "smiles": "N#CCc1ccccc1",
        "ref_smiles": "N#CS",
        "sub_label": "Free Cyanide [CN⁻] & Persulfide [GSSH] (µM)",
        "int_label": "Reactive Sulfane / Thiosulfate Pool (µM)",
        "prod_label": "Non-Toxic Thiocyanate [SCN⁻] + Sulfate Sink (µM)",
        "kcat1": 26.5,
        "km1": 340.0,
        "kcat2": 55.0,
        "km2": 26.0,
        "ki": 22.0,
        "boost": 9.2,
        "f1": 0.44,
        "f2": 0.36,
        "f3": 0.20,
        "target_bond": "Nitrile C≡N + Persulfide Hydrodisulfide R–S–SH (415 kJ/mol)",
        "linker_name": "GGGGS ×3 Haloalkaliphilic Tether (28.0 Å Separation)",
        "sink_name": "0.67 Å MBL–Rhodanese Chameleon (A0ABD6AX71 × M0AE48) → SCN⁻ + SO₄²⁻",
        "beacon_name": "ArsR/BigR Sensor (A0A2S2KQG4) → Halophilic CrtI (A0A0W1R8L8)",
    },
    "desalination-brine-upcycling": {
        "title": "Desalination Brine & Cheese-Whey Permeate -> Soda-Lake GalE/Glf Rare Sugars (45°C, pH 9.5)",
        "temp_c": 45.0,
        "ph": 9.5,
        "smiles": "OCC1OC(O)C(O)C(O)C1O",
        "ref_smiles": "OCC1OC(O)C(O)C1O",
        "sub_label": "Salted Whey Lactose / UDP-Glucose (µM)",
        "int_label": "Transient UDP-Galactopyranose Pool (µM)",
        "prod_label": "Rare UDP-Galactofuranose & Prebiotic GOS Sink (µM)",
        "kcat1": 27.0,
        "km1": 330.0,
        "kcat2": 57.5,
        "km2": 24.0,
        "ki": 20.0,
        "boost": 9.5,
        "f1": 0.50,
        "f2": 0.30,
        "f3": 0.20,
        "target_bond": "Pyranose C4–OH & Pyranose–Furanose Ring Contraction (305 kJ/mol)",
        "linker_name": "GGGGSEAAAKGGGGS Soda-Lake Bridge (28.0 Å Separation)",
        "sink_name": "0.44 Å GalE (D3SWG7) + 0.78 Å Glf Mutase (A0A1I1DB55) → UDP-Galf",
        "beacon_name": "GalR/LacI Sensor → Halophilic CrtI Bacterioruberin Beacon",
    },
}


def compute_effective_boost(base_boost: float, anchor_gravy: float) -> float:
    return round(max(1.5, min(14.0, base_boost + float(anchor_gravy) * 2.5)), 1)


def load_or_fallback_pdb(uniprot_id: str, role: str) -> str:
    candidates = [
        os.path.join(MODELS_DIR, f"AF-{uniprot_id}-F1-model_v4.pdb"),
        os.path.join(MODELS_DIR, f"{uniprot_id}.pdb"),
        os.path.join(STRUCTURES_DIR, f"{uniprot_id}.pdb"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read()

    os.makedirs(STRUCTURES_DIR, exist_ok=True)
    cached_path = os.path.join(STRUCTURES_DIR, f"AF-{uniprot_id}.pdb")
    if os.path.exists(cached_path):
        with open(cached_path, "r") as f:
            return f.read()

    for ver in ("v6", "v4"):
        url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_{ver}.pdb"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pg_bio_swarm_web/1.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                pdb_text = resp.read().decode("utf-8", errors="ignore")
                if "ATOM  " in pdb_text:
                    with open(cached_path, "w") as f:
                        f.write(pdb_text)
                    return pdb_text
        except Exception:
            pass

    fallback_file = "hydrophobin.pdb" if role == "anchor" else "dehalogenase.pdb"
    with open(os.path.join(STRUCTURES_DIR, fallback_file), "r") as f:
        return f.read()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark">
    <title>pg_bio Layer 14 — Bioprocess Swarm &amp; RK4 Cascade Digital Twin</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
    <style>
        :root {
            --bg-light: #f8fafc;
            --bg-dark: #090d16;
            --panel-light: #ffffff;
            --panel-dark: #0f172a;
            --header-light: #f1f5f9;
            --header-dark: #020617;
            --text-light: #0f172a;
            --text-dark: #f8fafc;
            --muted-light: #475569;
            --muted-dark: #94a3b8;
            --border-light: #cbd5e1;
            --border-dark: #1e293b;
            --accent-light: #0284c7;
            --accent-dark: #38bdf8;

            --bg-color: var(--bg-dark);
            --panel-bg: var(--panel-dark);
            --header-bg: var(--header-dark);
            --text-color: var(--text-dark);
            --muted-color: var(--muted-dark);
            --border-color: var(--border-dark);
            --accent-color: var(--accent-dark);

            @media (prefers-color-scheme: light) {
                --bg-color: var(--bg-dark);
            }

            @supports (color: light-dark(white, black)) {
                --accent-color: light-dark(var(--accent-light), var(--accent-dark));
            }

            color-scheme: light dark;
            accent-color: var(--accent-color);
        }

        * { box-sizing: border-box; }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            padding: 10px 20px;
            background: var(--header-bg);
            border-bottom: 1px solid var(--border-color);
        }
        .topbar h1 { margin: 0; font-size: 1.08rem; color: #f8fafc; display: inline-block; }
        .topbar .subtitle { color: var(--muted-color); font-size: 0.82rem; margin-left: 10px; }
        .controls { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
        select, button {
            background: #1e293b;
            color: #f8fafc;
            border: 1px solid #38bdf8;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.82rem;
            cursor: pointer;
        }
        button:hover { background: #38bdf8; color: #020617; font-weight: 600; }

        .dashboard-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.08fr) minmax(0, 1.22fr);
            gap: 14px;
            padding: 14px;
            flex: 1;
            width: 100%;
            max-width: 100vw;
        }
        @media (max-width: 1180px) {
            .dashboard-grid { grid-template-columns: minmax(0, 1fr); }
        }

        .card {
            min-width: 0;
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow: hidden;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
        }
        .title-group {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            min-width: 0;
        }
        .card-title { font-weight: 700; font-size: 0.93rem; color: #38bdf8; }
        .info-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            padding: 0;
            border-radius: 999px;
            background: rgba(56, 189, 248, 0.14);
            color: #38bdf8;
            border: 1.5px solid #38bdf8;
            font-family: Georgia, "Times New Roman", serif;
            font-style: italic;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1;
            cursor: pointer;
            flex-shrink: 0;
            transition: background 0.15s, color 0.15s;
        }
        .info-btn:hover, .info-btn:focus-visible {
            background: #38bdf8;
            color: #020617;
        }
        .info-popover {
            max-width: min(500px, 92vw);
            background: #0f172a;
            color: #f8fafc;
            border: 1px solid #38bdf8;
            border-radius: 10px;
            padding: 14px 16px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.85);
            font-size: 0.82rem;
            line-height: 1.55;
        }
        [popover]:is(:popover-open, .\\:popover-open) {
            display: block;
        }
        .info-popover::backdrop {
            background: rgba(2, 6, 23, 0.55);
        }
        .info-popover h3 {
            margin: 0 0 8px 0;
            font-size: 0.94rem;
            color: #38bdf8;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 6px;
        }
        .info-popover ul {
            margin: 6px 0 0 0;
            padding-left: 18px;
        }
        .info-popover li { margin-bottom: 5px; color: #cbd5e1; }
        .info-popover li b { color: #f8fafc; }
        .info-popover .formula-note {
            margin-top: 8px;
            padding: 6px 9px;
            background: #020617;
            border: 1px dashed #334155;
            border-radius: 6px;
            color: #a5f3fc;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.75rem;
        }
        .badge {
            background: #020617;
            border: 1px solid #334155;
            color: #34d399;
            font-size: 0.74rem;
            padding: 3px 9px;
            border-radius: 999px;
            white-space: nowrap;
            flex-shrink: 0;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }

        #pareto-heatmap { width: 100%; height: 400px; }
        #rk4-chart { width: 100%; height: 300px; }

        .sliders-row {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 10px;
            background: #020617;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 12px;
        }
        @media (max-width: 900px) {
            .sliders-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        .slider-box {
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 5px;
            font-size: 0.74rem;
            color: #cbd5e1;
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid #1e293b;
            border-radius: 7px;
            padding: 7px 7px;
            transition: border-color 0.15s;
        }
        .slider-top-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 3px 4px;
            min-width: 0;
        }
        .param-label-btn {
            background: transparent;
            border: none;
            border-bottom: 1.5px dashed #64748b;
            color: #e2e8f0;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 1px 2px;
            border-radius: 3px;
            cursor: help;
            white-space: nowrap;
            flex-shrink: 0;
            transition: color 0.15s, border-color 0.15s, background 0.15s;
        }
        .param-label-btn.zone-optimal {
            color: #34d399;
            border-bottom-color: rgba(52, 211, 153, 0.7);
        }
        .param-label-btn.zone-warn {
            color: #fbbf24;
            border-bottom-color: rgba(251, 191, 36, 0.7);
        }
        .param-label-btn.zone-danger {
            color: #fb7185;
            border-bottom-color: rgba(251, 113, 133, 0.75);
        }
        .param-label-btn:hover,
        .param-label-btn:focus-visible,
        .param-label-btn:is(:interest-source, .interest-source) {
            background: rgba(56, 189, 248, 0.16);
            filter: brightness(1.15);
            box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.35);
        }
        .param-val-pill {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.69rem;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 999px;
            border: 1px solid #10b981;
            background: rgba(16, 185, 129, 0.16);
            color: #34d399;
            cursor: help;
            white-space: nowrap;
            flex-shrink: 0;
            transition: background 0.15s, color 0.15s, border-color 0.15s;
        }
        .param-val-pill.zone-optimal {
            border-color: #10b981;
            background: rgba(16, 185, 129, 0.16);
            color: #34d399;
        }
        .param-val-pill.zone-warn {
            border-color: #f59e0b;
            background: rgba(245, 158, 11, 0.18);
            color: #fbbf24;
        }
        .param-val-pill.zone-danger {
            border-color: #f43f5e;
            background: rgba(244, 63, 94, 0.18);
            color: #fb7185;
        }
        .param-val-pill:hover,
        .param-val-pill:focus-visible,
        .param-val-pill:is(:interest-source, .interest-source) {
            filter: brightness(1.2);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.35);
        }

        /* Brand-Consistent Range Slider per modern-web-guidance `slider` */
        input[type="range"] {
            --slider-track-size: 0.38rem;
            --slider-thumb-size: 0.92rem;
            --slider-track-radius: 999px;
            --slider-thumb-radius: 50%;
            --slider-track-color: #1e293b;
            --slider-fill-color: #10b981;
            --slider-thumb-color: var(--slider-fill-color);
            --slider-direction: to right;

            --attr-min: attr(min type(<number>), 0);
            --attr-max: attr(max type(<number>), 100);
            --control-value: attr(value type(<number>), 50);
            --slider-progress: calc(
                progress(var(--control-value), var(--attr-min), var(--attr-max)) * 100%
            );

            appearance: none;
            inline-size: 100%;
            block-size: 1.35rem;
            margin: 0;
            padding: 0;
            border: 0;
            border-radius: 0;
            background: transparent;
            cursor: pointer;
        }
        input[type="range"]:dir(rtl) {
            --slider-direction: to left;
        }
        @supports not (opacity: progress(1, 0, 100)) {
            input[type="range"] {
                --slider-progress: calc(
                    (var(--control-value) - var(--attr-min)) /
                    (var(--attr-max) - var(--attr-min)) * 100%
                );
            }
        }
        input[type="range"]::-webkit-slider-runnable-track {
            block-size: var(--slider-track-size);
            border: 0;
            border-radius: var(--slider-track-radius);
            background: linear-gradient(
                var(--slider-direction),
                var(--slider-fill-color) var(--slider-progress),
                var(--slider-track-color) var(--slider-progress)
            );
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            inline-size: var(--slider-thumb-size);
            block-size: var(--slider-thumb-size);
            margin-block-start: calc(
                (var(--slider-track-size) - var(--slider-thumb-size)) / 2
            );
            border: 2px solid #020617;
            border-radius: var(--slider-thumb-radius);
            background: var(--slider-thumb-color);
            box-shadow: 0 0 6px rgba(0, 0, 0, 0.7);
        }
        input[type="range"]::-moz-range-track {
            block-size: var(--slider-track-size);
            border: 0;
            border-radius: var(--slider-track-radius);
            background: var(--slider-track-color);
        }
        input[type="range"]::-moz-range-progress {
            block-size: var(--slider-track-size);
            border-radius: var(--slider-track-radius);
            background: var(--slider-fill-color);
        }
        input[type="range"]::-moz-range-thumb {
            inline-size: var(--slider-thumb-size);
            block-size: var(--slider-thumb-size);
            border: 2px solid #020617;
            border-radius: var(--slider-thumb-radius);
            background: var(--slider-thumb-color);
        }
        input[type="range"]:focus-visible {
            outline: 2px solid var(--slider-fill-color);
            outline-offset: 3px;
        }

        .range-zone-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.65rem;
            color: #94a3b8;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            padding-top: 1px;
        }
        .range-zone-bar .zone-tag {
            font-weight: 700;
            letter-spacing: 0.02em;
        }

        /* Interest-Triggered Tooltips per modern-web-guidance `interest-triggered-tooltips` */
        [interestfor] {
            --interest-delay-start: 0.12s;
            interest-delay-start: var(--interest-delay-start);
            --interest-delay-end: 0.12s;
            interest-delay-end: var(--interest-delay-end);
        }
        .hint-tooltip {
            position: fixed;
            inset: auto;
            margin: 0;
            max-width: min(355px, 90vw);
            width: max-content;
            background: #0f172a;
            color: #f8fafc;
            border: 1px solid #38bdf8;
            border-radius: 9px;
            padding: 10px 12px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.85);
            font-size: 0.77rem;
            line-height: 1.48;
            z-index: 9999;
            position-try-fallbacks: flip-block, flip-inline, flip-block flip-inline;
        }
        .hint-tooltip:is(:interest-target, .interest-target) {
            border-color: #38bdf8;
        }
        #tip-param-kcat1 { position-anchor: --anc-param-kcat1; top: calc(anchor(bottom) + 6px); left: anchor(left); }
        #tip-thresh-kcat1 { position-anchor: --anc-thresh-kcat1; top: calc(anchor(bottom) + 6px); left: anchor(left); }
        #tip-param-km1 { position-anchor: --anc-param-km1; top: calc(anchor(bottom) + 6px); left: anchor(left); }
        #tip-thresh-km1 { position-anchor: --anc-thresh-km1; top: calc(anchor(bottom) + 6px); left: anchor(left); }
        #tip-param-kcat2 { position-anchor: --anc-param-kcat2; top: calc(anchor(bottom) + 6px); left: anchor(left); }
        #tip-thresh-kcat2 { position-anchor: --anc-thresh-kcat2; top: calc(anchor(bottom) + 6px); left: anchor(left); }
        #tip-param-ki { position-anchor: --anc-param-ki; top: calc(anchor(bottom) + 6px); right: anchor(right); left: auto; }
        #tip-thresh-ki { position-anchor: --anc-thresh-ki; top: calc(anchor(bottom) + 6px); right: anchor(right); left: auto; }
        #tip-param-boost { position-anchor: --anc-param-boost; top: calc(anchor(bottom) + 6px); right: anchor(right); left: auto; }
        #tip-thresh-boost { position-anchor: --anc-thresh-boost; top: calc(anchor(bottom) + 6px); right: anchor(right); left: auto; }
        #tip-ledger-gravy { position-anchor: --anc-ledger-gravy; bottom: calc(anchor(top) + 6px); right: anchor(right); left: auto; top: auto; }
        #tip-ledger-scissor { position-anchor: --anc-ledger-scissor; bottom: calc(anchor(top) + 6px); right: anchor(right); left: auto; top: auto; }
        #tip-ledger-globular { position-anchor: --anc-ledger-globular; bottom: calc(anchor(top) + 6px); right: anchor(right); left: auto; top: auto; }

        .thresh-meter {
            display: grid;
            grid-template-columns: 1fr 1fr 1.2fr;
            height: 7px;
            border-radius: 999px;
            overflow: hidden;
            margin: 7px 0 5px 0;
            border: 1px solid #334155;
        }
        .thresh-legend {
            display: flex;
            justify-content: space-between;
            font-size: 0.69rem;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            margin-bottom: 6px;
        }

        .bottom-split {
            display: grid;
            grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
            gap: 12px;
        }
        .bottom-split > div { min-width: 0; }
        @media (max-width: 900px) {
            .bottom-split { grid-template-columns: minmax(0, 1fr); }
        }

        #mol-viewer {
            width: 100%;
            height: 255px;
            position: relative;
            background: #020617;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }

        /* 4-Phase Step-by-Step Pipeline Bar */
        .phase-stepper {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }
        .phase-step-btn {
            background: #1e293b;
            color: #e2e8f0;
            border: 1px solid #475569;
            padding: 6px 11px;
            border-radius: 7px;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }
        .phase-step-btn:hover {
            border-color: #7dd3fc;
            color: #ffffff;
            background: #334155;
        }
        .phase-step-btn.active-phase {
            background: #38bdf8;
            color: #020617;
            border-color: #bae6fd;
            font-weight: 800;
            box-shadow: 0 0 14px rgba(56, 189, 248, 0.45);
        }
        .phase-inline-banner {
            background: #0f172a;
            border: 1px solid #334155;
            border-left: 4px solid #38bdf8;
            border-radius: 8px;
            padding: 9px 12px;
            margin-top: 6px;
            font-size: 0.82rem;
            color: #f8fafc;
            line-height: 1.5;
        }
        .fs-btn {
            background: rgba(56, 189, 248, 0.22);
            color: #7dd3fc;
            border: 1px solid #38bdf8;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.76rem;
            font-weight: 700;
            cursor: pointer;
        }
        .fs-btn:hover {
            background: #38bdf8;
            color: #020617;
        }

        /* Modal Dialog per modern-web-guidance `dialog` + `light-dismiss-a-dialog` */
        dialog:modal {
            overscroll-behavior: contain;
        }
        dialog::backdrop {
            overflow: hidden;
            overscroll-behavior: contain;
            background-color: rgba(2, 6, 23, 0.86);
            backdrop-filter: blur(5px);
        }
        #fusion-fs-dialog[open] {
            width: min(1440px, 96vw);
            max-width: 96vw;
            height: min(890px, 93vh);
            max-height: 93vh;
            background: #0b1120;
            color: #f8fafc;
            border: 2px solid #38bdf8;
            border-radius: 14px;
            padding: 18px 22px;
            box-shadow: 0 25px 75px rgba(0, 0, 0, 0.95);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .fs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            border-bottom: 1px solid #334155;
            padding-bottom: 12px;
        }
        .fs-header h2 {
            margin: 0 0 4px 0;
            font-size: 1.15rem;
            color: #7dd3fc;
            font-weight: 800;
        }
        .fs-header button {
            background: #1e293b;
            color: #f8fafc;
            border: 1px solid #64748b;
            font-weight: 700;
            font-size: 0.8rem;
            padding: 6px 12px;
        }
        .fs-header button:hover {
            background: #334155;
            border-color: #7dd3fc;
        }
        .fs-body {
            display: grid;
            grid-template-columns: minmax(0, 1.5fr) minmax(0, 1.05fr);
            gap: 16px;
            flex: 1;
            min-height: 0;
        }
        @media (max-width: 1024px) {
            .fs-body { grid-template-columns: minmax(0, 1fr); overflow-y: auto; }
        }
        .fs-viewer-wrap {
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 0;
        }
        #fs-mol-viewer {
            width: 100%;
            flex: 1;
            min-height: 440px;
            position: relative;
            background: #060b19;
            border: 1.5px solid #334155;
            border-radius: 10px;
            overflow: hidden;
        }
        .fs-phase-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
            padding-right: 4px;
        }
        .fs-phase-card {
            background: #111c33;
            border: 1px solid #334155;
            border-left: 5px solid #64748b;
            border-radius: 9px;
            padding: 12px 14px;
            cursor: pointer;
            transition: all 0.15s;
            font-size: 0.83rem;
            color: #f1f5f9;
            line-height: 1.52;
        }
        .fs-phase-card:hover {
            background: #1e293b;
            border-color: #64748b;
        }
        .fs-phase-card.active-card {
            background: #172542;
            border-color: #7dd3fc;
            border-width: 1.5px;
            border-left-width: 6px;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.25);
        }

        .kpi-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
        }
        @media (max-width: 900px) {
            .kpi-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        .kpi-item {
            min-width: 0;
            background: #020617;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 7px 9px;
            font-size: 0.74rem;
        }
        .kpi-item .k-label {
            color: var(--muted-color);
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .kpi-item .k-val {
            color: #f8fafc;
            font-weight: 700;
            font-size: 0.88rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
            margin-top: 2px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }

        /* Responsive Table per modern-web-guidance `responsive-table` */
        .table-wrapper {
            overflow: auto;
            width: 100%;
            max-inline-size: 100%;
            max-block-size: min(320px, 60vh);
            container-type: inline-size;
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.79rem;
            --label-1: "Rank";
            --label-2: "Anchor × Scissor";
            --label-3: "GRAVY";
            --label-4: "Pareto";
            --label-5: "48h RK4 Yield";
        }
        caption {
            text-align: left;
            padding: 8px 12px;
            font-weight: 600;
            color: #cbd5e1;
            background: #020617;
            border-bottom: 1px solid var(--border-color);
        }
        thead {
            position: sticky;
            inset-block-start: 0;
            z-index: 2;
            background: #020617;
        }
        th, td {
            padding: 7px 10px;
            text-align: left;
            border-bottom: 1px solid #1e293b;
            white-space: nowrap;
        }
        tbody th {
            position: sticky;
            inset-inline-start: 0;
            background: #0f172a;
            color: #38bdf8;
            z-index: 1;
        }
        tbody tr { cursor: pointer; transition: background 0.12s; }
        tbody tr:hover { background: #1e293b; }
        tbody tr.selected-row { background: rgba(56, 189, 248, 0.16); }

        @container (width < 420px) {
            table, thead, tbody, tr, th, td { display: block; white-space: normal; }
            thead { display: none; }
            tr { margin-block-end: 1rem; border: 1px solid #334155; }
            tbody th {
                position: sticky;
                inset-block-start: 0;
                z-index: 2;
                background: #1e293b;
            }
            td:nth-child(2)::before { content: var(--label-2) ": "; font-weight: 600; color: #94a3b8; }
            td:nth-child(3)::before { content: var(--label-3) ": "; font-weight: 600; color: #94a3b8; }
            td:nth-child(4)::before { content: var(--label-4) ": "; font-weight: 600; color: #94a3b8; }
            td:nth-child(5)::before { content: var(--label-5) ": "; font-weight: 600; color: #94a3b8; }
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div>
            <h1>🧬 Bio-Pipelines Unified System — 8-Feedstock 4-Module (M1&rarr;M4) RK4 Digital Twin</h1>
            <span class="subtitle">Click any (Anchor × Scissor) cell to run in-database RK4 kinetics &amp; 3D rigid-body complex assembly · Unified with Swarm Discovery &amp; Telemetry</span>
        </div>
        <div class="controls">
            <label for="pipeline-select" style="font-size:0.82rem;color:#cbd5e1;">Feedstock Pipeline:</label>
            <select id="pipeline-select" onchange="loadPipelineSwarm()">
                <option value="ptfe-to-bioceramic" selected>1. PTFE / PFAS -> Fluorapatite (37°C, pH 7.4)</option>
                <option value="plastics-upcycling">2. PET Polyester -> PCA/Vanillin (68°C, pH 8.0)</option>
                <option value="sugarcane-bagasse">3. Sugarcane Bagasse -> 2,5-FDCA (55°C, pH 5.0)</option>
                <option value="corn-stover-bran">4. Corn Stover Diferulate -> Bio-Vanillin (50°C, pH 5.5)</option>
                <option value="habanero-spicy-fuel">5. Habanero Capsicum GGPPS -> Bio-Jet Fuel (32°C, pH 6.8)</option>
                <option value="biochar-water-remediation">6. Agro-Waste Biochar -> Micropollutant Remediation (30°C, pH 6.5)</option>
                <option value="cyanide-mine-tailings">7. Gold-Mine Cyanide &amp; Sulfide -> MBL-Rhodanese Chameleon (38°C, pH 9.8)</option>
                <option value="desalination-brine-upcycling">8. Desalination Brine &amp; Whey -> Soda-Lake GalE/Glf Sugars (45°C, pH 9.5)</option>
            </select>
            <button onclick="resetSlidersToPreset()">Reset Preset</button>
            <button onclick="window.location.href='/discovery'" style="border-color:#38bdf8;color:#7dd3fc;background:rgba(56,189,248,0.16);font-weight:700;">🛰️ Swarm Discovery</button>
            <button onclick="window.location.href='/cards'" style="border-color:#f59e0b;color:#fbbf24;background:rgba(245,158,11,0.14);font-weight:700;">🃏 Card Arena</button>
            <button onclick="window.location.href='/compare'" style="border-color:#10b981;color:#34d399;background:rgba(16,185,129,0.14);font-weight:700;">🔬 3D Compare</button>
            <button onclick="window.location.href='/tpp'" style="border-color:#f43f5e;color:#fb7185;background:rgba(244,63,94,0.14);font-weight:700;">🌡️ TPP Lab</button>
            <button onclick="window.location.href='/telemetry'" style="border-color:#c084fc;color:#e9d5ff;background:rgba(192,132,252,0.18);font-weight:700;">📊 Unified Telemetry</button>
        </div>
    </div>

    <div class="dashboard-grid">
        <!-- Left Column: Pareto Swarm Heatmap + Accessible Top Candidates Table -->
        <div class="card">
            <div class="card-header">
                <div class="title-group">
                    <span class="card-title">1. In-Database Pareto Swarm Matrix (<code>pareto_score_domain_pair</code>)</span>
                    <button type="button" class="info-btn" commandfor="info-pareto-matrix" command="toggle-popover" aria-label="How to read the Pareto Swarm Matrix">i</button>
                </div>
                <span class="badge" id="swarm-timing-badge">PostgreSQL 18 Live</span>
            </div>
            <div id="pareto-heatmap"></div>

            <div tabindex="0" role="region" aria-labelledby="pareto-table-caption" class="table-wrapper">
                <table>
                    <caption id="pareto-table-caption">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;width:100%;">
                            <span>Top Pareto-Optimal (M1 Anchor × M2 Scissor) Candidates — Click Row to Inspect</span>
                            <button type="button" class="info-btn" commandfor="info-leaderboard-table" command="toggle-popover" aria-label="How to read the Top Candidates Leaderboard">i</button>
                        </div>
                    </caption>
                    <thead>
                        <tr>
                            <th scope="col">Rank</th>
                            <th scope="col">Anchor × Scissor</th>
                            <th scope="col">Anchor GRAVY</th>
                            <th scope="col">Pareto Score</th>
                            <th scope="col">48h RK4 Yield</th>
                        </tr>
                    </thead>
                    <tbody id="leaderboard-body"></tbody>
                </table>
            </div>
        </div>

        <!-- Right Column: Live RK4 Cascade Digital Twin + Sliders + 3D Complex & Stoichiometry -->
        <div class="card">
            <div class="card-header">
                <div class="title-group">
                    <span class="card-title" id="rk4-title">2. 48-Hour RK4 Cascade Digital Twin (<code>simulate_cascade_kinetics</code>)</span>
                    <button type="button" class="info-btn" commandfor="info-rk4-twin" command="toggle-popover" aria-label="How to read the 48-Hour RK4 Cascade Digital Twin">i</button>
                </div>
                <div style="display:flex;align-items:center;gap:6px;">
                    <button type="button" class="info-btn" commandfor="info-sliders-kpis" command="toggle-popover" title="How to use the kinetic sliders &amp; KPI cards" aria-label="How to read the kinetic sliders and KPI strip">i</button>
                    <span class="badge" id="rk4-timing-badge">RK4 Solver</span>
                </div>
            </div>

            <div class="sliders-row">
                <div class="slider-box" id="box-kcat1">
                    <div class="slider-top-row">
                        <button type="button" class="param-label-btn zone-optimal" id="lbl-btn-kcat1" interestfor="tip-param-kcat1" style="anchor-name: --anc-param-kcat1;">Scissor kcat1</button>
                        <button type="button" class="param-val-pill zone-optimal" id="lbl-kcat1" interestfor="tip-thresh-kcat1" style="anchor-name: --anc-thresh-kcat1;">24.0/h</button>
                    </div>
                    <input type="range" id="sl-kcat1" min="5" max="60" step="0.5" value="24.0" aria-label="Scissor kcat1 turnover rate" oninput="updateRK4FromSliders()">
                    <div class="range-zone-bar">
                        <span style="color:#fb7185;">&lt;15 Slow</span>
                        <span style="color:#fbbf24;">15–22</span>
                        <span class="zone-tag" style="color:#34d399;">≥22 Opt</span>
                    </div>
                </div>
                <div class="slider-box" id="box-km1">
                    <div class="slider-top-row">
                        <button type="button" class="param-label-btn zone-optimal" id="lbl-btn-km1" interestfor="tip-param-km1" style="anchor-name: --anc-param-km1;">Solid Km1</button>
                        <button type="button" class="param-val-pill zone-optimal" id="lbl-km1" interestfor="tip-thresh-km1" style="anchor-name: --anc-thresh-km1;">380 µM</button>
                    </div>
                    <input type="range" id="sl-km1" min="50" max="800" step="10" value="380" aria-label="Solid Km1 Michaelis constant" oninput="updateRK4FromSliders()">
                    <div class="range-zone-bar">
                        <span class="zone-tag" style="color:#34d399;">≤420 Tight</span>
                        <span style="color:#fbbf24;">420–560</span>
                        <span style="color:#fb7185;">&gt;560 Weak</span>
                    </div>
                </div>
                <div class="slider-box" id="box-kcat2">
                    <div class="slider-top-row">
                        <button type="button" class="param-label-btn zone-optimal" id="lbl-btn-kcat2" interestfor="tip-param-kcat2" style="anchor-name: --anc-param-kcat2;">Sink kcat2</button>
                        <button type="button" class="param-val-pill zone-optimal" id="lbl-kcat2" interestfor="tip-thresh-kcat2" style="anchor-name: --anc-thresh-kcat2;">42.0/h</button>
                    </div>
                    <input type="range" id="sl-kcat2" min="0" max="80" step="1.0" value="42.0" aria-label="Sink kcat2 clearance rate" oninput="updateRK4FromSliders()">
                    <div class="range-zone-bar">
                        <span style="color:#fb7185;">&lt;18 Stall</span>
                        <span style="color:#fbbf24;">18–30</span>
                        <span class="zone-tag" style="color:#34d399;">≥30 Opt</span>
                    </div>
                </div>
                <div class="slider-box" id="box-ki">
                    <div class="slider-top-row">
                        <button type="button" class="param-label-btn zone-optimal" id="lbl-btn-ki" interestfor="tip-param-ki" style="anchor-name: --anc-param-ki;">Inhibition Ki</button>
                        <button type="button" class="param-val-pill zone-optimal" id="lbl-ki" interestfor="tip-thresh-ki" style="anchor-name: --anc-thresh-ki;">22.0 µM</button>
                    </div>
                    <input type="range" id="sl-ki" min="5" max="150" step="1.0" value="22.0" aria-label="Inhibition Ki constant" oninput="updateRK4FromSliders()">
                    <div class="range-zone-bar">
                        <span style="color:#fb7185;">&lt;14 Severe</span>
                        <span style="color:#fbbf24;">14–22</span>
                        <span class="zone-tag" style="color:#34d399;">≥22 Safe</span>
                    </div>
                </div>
                <div class="slider-box" id="box-boost">
                    <div class="slider-top-row">
                        <button type="button" class="param-label-btn zone-optimal" id="lbl-btn-boost" interestfor="tip-param-boost" style="anchor-name: --anc-param-boost;">Anchor Boost</button>
                        <button type="button" class="param-val-pill zone-optimal" id="lbl-boost" interestfor="tip-thresh-boost" style="anchor-name: --anc-thresh-boost;">8.5×</button>
                    </div>
                    <input type="range" id="sl-boost" min="1.0" max="15.0" step="0.1" value="8.5" aria-label="Anchor Boost multiplier" oninput="updateRK4FromSliders()">
                    <div class="range-zone-bar">
                        <span style="color:#fb7185;">&lt;4× Low</span>
                        <span style="color:#fbbf24;">4–7×</span>
                        <span class="zone-tag" style="color:#34d399;">≥7× High</span>
                    </div>
                </div>
            </div>

            <div class="kpi-strip">
                <div class="kpi-item">
                    <span class="k-label">Selected Chimera Pair</span>
                    <span class="k-val" id="kpi-pair">—</span>
                </div>
                <div class="kpi-item">
                    <span class="k-label">48h Full 4-Module Sink Yield</span>
                    <span class="k-val" id="kpi-sink-yield" style="color:#34d399;">—</span>
                </div>
                <div class="kpi-item">
                    <span class="k-label">48h No-Sink (Ki Stalled)</span>
                    <span class="k-val" id="kpi-nosink-yield" style="color:#facc15;">—</span>
                </div>
                <div class="kpi-item">
                    <span class="k-label">Consortium Ratio (w1:w2:w3)</span>
                    <span class="k-val" id="kpi-stoich" style="color:#38bdf8;">—</span>
                </div>
            </div>

            <div id="rk4-chart"></div>

            <div class="bottom-split">
                <div>
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;">
                        <div class="title-group">
                            <span style="font-size:0.82rem;font-weight:600;color:#38bdf8;">3D Rigid-Body Fusion (<code>translate_and_merge_pdb_chains</code>)</span>
                            <button type="button" class="info-btn" commandfor="info-3d-fusion" command="toggle-popover" aria-label="How to read the 3D Rigid-Body Fusion Viewer">i</button>
                        </div>
                        <div style="display:flex;align-items:center;gap:6px;">
                            <span class="badge" id="globular-badge">Rg: —</span>
                            <button type="button" class="fs-btn" command="show-modal" commandfor="fusion-fs-dialog" onclick="syncFullScreenViewer()">⛶ Full Screen &amp; Phases</button>
                        </div>
                    </div>
                    <div class="phase-stepper" id="inline-phase-stepper">
                        <button type="button" class="phase-step-btn active-phase" data-phase="0" onclick="selectPipelinePhase(0)">All Phases</button>
                        <button type="button" class="phase-step-btn" data-phase="1" onclick="selectPipelinePhase(1)">1. M1 Anchor</button>
                        <button type="button" class="phase-step-btn" data-phase="2" onclick="selectPipelinePhase(2)">2. 28 Å Linker</button>
                        <button type="button" class="phase-step-btn" data-phase="3" onclick="selectPipelinePhase(3)">3. M2 Scissor</button>
                        <button type="button" class="phase-step-btn" data-phase="4" onclick="selectPipelinePhase(4)">4. M3 Sink &amp; Beacon</button>
                    </div>
                    <div id="mol-viewer"></div>
                    <div class="phase-inline-banner" id="inline-phase-desc">
                        <b>All 4 Modules Active:</b> Click any phase tab above (or open <b>⛶ Full Screen &amp; Phases</b>) to step through M1 Surface Adsorption, the 28.0 Å Linker Bridge, M2 Bond Cleavage, and M3 Equilibrium Sink.
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;justify-content:space-between;background:#020617;border:1px solid #1e293b;border-radius:8px;padding:12px;">
                    <div>
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">
                            <span style="font-size:0.84rem;font-weight:700;color:#38bdf8;">Live PostgreSQL 18 Biophysical Ledger</span>
                            <button type="button" class="info-btn" commandfor="info-sql-ledger" command="toggle-popover" aria-label="How to read the Live PostgreSQL 18 Biophysical Ledger">i</button>
                        </div>
                        <div id="pair-details" style="font-size:0.79rem;color:#cbd5e1;line-height:1.55;"></div>
                    </div>
                    <pre id="sql-preview" style="background:#090d16;border:1px solid #1e293b;color:#a5f3fc;font-size:0.72rem;padding:8px;border-radius:6px;overflow-x:auto;margin:8px 0 0 0;"></pre>
                </div>
            </div>
        </div>
    </div>

    <!-- Full-Screen 3D Rigid-Body Fusion & 4-Phase Walkthrough Modal Dialog -->
    <dialog id="fusion-fs-dialog" closedby="any" aria-labelledby="fusion-fs-title">
        <div class="fs-header">
            <div>
                <h2 id="fusion-fs-title">🧬 3D Rigid-Body Fusion &amp; 4-Phase Pipeline Walkthrough (<code>translate_and_merge_pdb_chains</code>)</h2>
                <span id="fs-subtitle" style="font-size:0.84rem;color:#e2e8f0;font-weight:500;">Click any phase step below or use Prev/Next to inspect each structural module in 3D</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <button type="button" onclick="stepPhase(-1)">◀ Prev Phase</button>
                <button type="button" onclick="stepPhase(1)">Next Phase ▶</button>
                <button type="button" onclick="toggleSpin3D()" id="btn-spin-3d">↻ Spin 3D</button>
                <button type="button" onclick="reset3DCamera()">⌖ Reset Camera</button>
                <form method="dialog" style="margin:0;">
                    <button type="submit" autofocus style="background:rgba(244,63,94,0.18);border-color:#fb7185;color:#fecdd3;font-weight:800;">✕ Exit Full Screen (Esc)</button>
                </form>
            </div>
        </div>
        <div class="phase-stepper" id="fs-phase-stepper" style="margin-bottom:2px;">
            <button type="button" class="phase-step-btn active-phase" data-phase="0" onclick="selectPipelinePhase(0)">0. Full Chimeric Complex</button>
            <button type="button" class="phase-step-btn" data-phase="1" onclick="selectPipelinePhase(1)">Phase 1 · M1 Interfacial Anchor (Chain B)</button>
            <button type="button" class="phase-step-btn" data-phase="2" onclick="selectPipelinePhase(2)">Phase 2 · 28.0 Å Linker Bridge</button>
            <button type="button" class="phase-step-btn" data-phase="3" onclick="selectPipelinePhase(3)">Phase 3 · M2 Primary Bond Scissor (Chain A)</button>
            <button type="button" class="phase-step-btn" data-phase="4" onclick="selectPipelinePhase(4)">Phase 4 · M3 Equilibrium Sink &amp; M4 Beacon</button>
        </div>
        <div class="fs-body">
            <div class="fs-viewer-wrap">
                <!-- Interactive 4-State Bar for Moving, Fitting, Breaking & Computed Trajectory Motion -->
                <div id="fs-cut-motion-bar" style="display:flex;flex-direction:column;gap:6px;background:#111c33;border:1px solid #475569;border-radius:8px;padding:8px 12px;">
                    <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;">
                        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                            <span style="font-size:0.75rem;font-weight:800;color:#fde047;text-transform:uppercase;letter-spacing:0.04em;">✂️ 4-State 3D Structural Cleavage:</span>
                            <button type="button" id="btn-cut-play" onclick="toggleCutAnimation()" style="background:#10b981;color:#020617;border:1px solid #a7f3d0;font-weight:800;font-size:0.74rem;padding:3px 10px;border-radius:6px;cursor:pointer;">⏸ Pause Motion</button>
                            <button type="button" class="cut-sub-btn" id="cut-sub-1" onclick="setCutProgress(0.14)" style="background:#1e293b;color:#f8fafc;border:1px solid #475569;font-size:0.72rem;font-weight:700;padding:3px 8px;border-radius:6px;cursor:pointer;">State 1: 🧲 Yellow Moves &amp; Fits</button>
                            <button type="button" class="cut-sub-btn" id="cut-sub-2" onclick="setCutProgress(0.38)" style="background:#1e293b;color:#f8fafc;border:1px solid #475569;font-size:0.72rem;font-weight:700;padding:3px 8px;border-radius:6px;cursor:pointer;">State 2: ⚡ Lock Scissile Joint</button>
                            <button type="button" class="cut-sub-btn" id="cut-sub-3" onclick="setCutProgress(0.62)" style="background:#1e293b;color:#f8fafc;border:1px solid #475569;font-size:0.72rem;font-weight:700;padding:3px 8px;border-radius:6px;cursor:pointer;">State 3: ✂️ Break / Cut Piece Off</button>
                            <button type="button" class="cut-sub-btn" id="cut-sub-4" onclick="setCutProgress(0.90)" style="background:#1e293b;color:#f8fafc;border:1px solid #475569;font-size:0.72rem;font-weight:700;padding:3px 8px;border-radius:6px;cursor:pointer;">State 4: 🚀 Cα Trajectory → Sink</button>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;min-width:190px;flex:1;max-width:260px;">
                            <input type="range" id="cut-progress-slider" min="0" max="100" value="50" aria-label="Scission and handoff reaction coordinate" oninput="setCutProgress(this.value / 100)" style="flex:1;accent-color:#fde047;">
                            <span id="cut-stage-pill" style="font-family:monospace;font-size:0.73rem;font-weight:800;color:#fde047;min-width:95px;text-align:right;">50% · STATE 2</span>
                        </div>
                    </div>
                    <!-- 4-Column Live State Breakdown -->
                    <div id="fs-mech-breakdown" style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;border-top:1px solid #1e293b;padding-top:6px;font-size:0.71rem;"></div>
                </div>
                <div id="fs-mol-viewer"></div>
                <!-- Visual Legend Strip for 3D Structural & Mechanistic Elements -->
                <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:7px 12px;font-size:0.73rem;color:#f1f5f9;">
                    <span><b style="color:#fde047;">🟡 Yellow Structure (Chain B):</b> Anchor + Substrate Carrier</span>
                    <span><b style="color:#fb923c;">🟠 Amber/Coral Tip (Chain C):</b> Segment That Gets Cut Off [I]</span>
                    <span><b style="color:#67e8f9;">🔷 Cyan Structure (Chain A):</b> Catalytic Scissor Jaws</span>
                    <span><b style="color:#f0abfc;">🟣➔🟢 Computed Cα Pathway (W1–W5):</b> Exact Structural Trajectory → Sink [P]</span>
                </div>
                <div class="phase-inline-banner" id="fs-active-banner" style="font-size:0.82rem;padding:10px 14px;"></div>
            </div>
            <div class="fs-phase-list" id="fs-phase-cards"></div>
        </div>
    </dialog>

    <!-- Interest-Triggered Hover Tooltips (`popover="hint"`) for Parameter Definitions, Thresholds & Biophysical Ledger -->
    <div popover="hint" id="tip-param-kcat1" class="hint-tooltip">
        <b style="color:#38bdf8;">Scissor <i>k</i><sub>cat,1</sub> (Primary Catalytic Turnover, h<sup>−1</sup>)</b><br>
        Number of recalcitrant substrate bonds cleaved per enzyme molecule per hour by <b>Module 2 (Primary Scissor)</b>.<br>
        <div class="formula-note"><i>v</i><sub>1</sub> = <i>k</i><sub>cat,1</sub> · (<i>A</i><sub>boost</sub> · [<i>S</i>]) / (<i>K</i><sub>m,1</sub> · (1 + [<i>I</i>] / <i>K</i><sub>i</sub>) + <i>A</i><sub>boost</sub> · [<i>S</i>])</div>
    </div>
    <div popover="hint" id="tip-thresh-kcat1" class="hint-tooltip">
        <div id="thresh-body-kcat1"></div>
    </div>

    <div popover="hint" id="tip-param-km1" class="hint-tooltip">
        <b style="color:#38bdf8;">Solid <i>K</i><sub>m,1</sub> (Interfacial Michaelis Constant, µM)</b><br>
        Effective substrate concentration required to reach half-maximal cleavage velocity (0.5 · <i>V</i><sub>max</sub>) on the solid polymer or lipid interface. <b>Lower <i>K</i><sub>m,1</sub> means tighter catalytic binding.</b>
        <div class="formula-note">Apparent <i>K</i><sub>m,app</sub> = <i>K</i><sub>m,1</sub> · (1 + [<i>I</i>] / <i>K</i><sub>i</sub>) / <i>A</i><sub>boost</sub></div>
    </div>
    <div popover="hint" id="tip-thresh-km1" class="hint-tooltip">
        <div id="thresh-body-km1"></div>
    </div>

    <div popover="hint" id="tip-param-kcat2" class="hint-tooltip">
        <b style="color:#38bdf8;">Sink <i>k</i><sub>cat,2</sub> (Module 3 Equilibrium Sink Rate, h<sup>−1</sup>)</b><br>
        Rate at which <b>Module 3</b> drains the inhibitory cleavage intermediate <i>I</i>(<i>t</i>) into the final phase-separated sink product <i>P</i>(<i>t</i>) (Fluorapatite, Bio-Vanillin, 2,5-FDCA, or Bio-Jet Terpene).
        <div class="formula-note"><i>v</i><sub>2</sub> = <i>k</i><sub>cat,2</sub> · [<i>I</i>] / (<i>K</i><sub>m,2</sub> + [<i>I</i>])</div>
    </div>
    <div popover="hint" id="tip-thresh-kcat2" class="hint-tooltip">
        <div id="thresh-body-kcat2"></div>
    </div>

    <div popover="hint" id="tip-param-ki" class="hint-tooltip">
        <b style="color:#38bdf8;">Inhibition <i>K</i><sub>i</sub> (Competitive Product Inhibition Constant, µM)</b><br>
        Concentration of free intermediate <i>I</i>(<i>t</i>) that cuts Module 2 Scissor affinity in half via the penalty factor (1 + [<i>I</i>] / <i>K</i><sub>i</sub>). Without Module 3 Sink, low <i>K</i><sub>i</sub> stalls the reactor around 45–60%.
        <div class="formula-note">Inhibition Penalty = 1 + [<i>I</i>](<i>t</i>) / <i>K</i><sub>i</sub></div>
    </div>
    <div popover="hint" id="tip-thresh-ki" class="hint-tooltip">
        <div id="thresh-body-ki"></div>
    </div>

    <div popover="hint" id="tip-param-boost" class="hint-tooltip">
        <b style="color:#38bdf8;">Anchor Boost <i>A</i><sub>boost</sub> (Langmuir–Hinshelwood Surface Multiplier)</b><br>
        Effective local substrate concentration multiplier provided by <b>Module 1 Surface Anchor</b> (<code>1.0×</code> = unfused wild-type enzyme; <code>8–12×</code> = high-GRAVY hydrophobin, oleosin, or CBM).
        <div class="formula-note"><i>A</i><sub>boost</sub> = clamp(<i>B</i><sub>0</sub> + 2.5 · GRAVY<sub>M1</sub>, 1.5×, 14.0×)</div>
    </div>
    <div popover="hint" id="tip-thresh-boost" class="hint-tooltip">
        <div id="thresh-body-boost"></div>
    </div>

    <div popover="hint" id="tip-ledger-gravy" class="hint-tooltip">
        <div id="ledger-tip-gravy-body"></div>
    </div>
    <div popover="hint" id="tip-ledger-scissor" class="hint-tooltip">
        <div id="ledger-tip-scissor-body"></div>
    </div>
    <div popover="hint" id="tip-ledger-globular" class="hint-tooltip">
        <div id="ledger-tip-globular-body"></div>
    </div>
    <div popover="hint" id="tip-ledger-rangefinder" class="hint-tooltip">
        <div id="ledger-tip-rangefinder-body"></div>
    </div>

    <!-- Declarative Popover Instruction Guides for Every Widget -->
    <div id="info-pareto-matrix" class="info-popover" popover>
        <h3>
            <span>How to Read: 1. In-Database Pareto Swarm Matrix</span>
            <button type="button" commandfor="info-pareto-matrix" command="hide-popover" style="padding:2px 8px;font-size:0.75rem;">Close</button>
        </h3>
        <ul>
            <li><b>Y-Axis (Rows):</b> 12 stratified <b>Module 1 Surface Anchors</b> (Hydrophobins, CBMs, Dockerins, Oleosins) sampled across the hydropathy (<code>GRAVY</code>) spectrum in <code>bio_domain_atlas</code>.</li>
            <li><b>X-Axis (Columns):</b> 16 stratified <b>Module 2 Primary Bond Scissors</b> (Dehalogenases, Cutinases/PETases, Cellulases/LPMOs, Feruloyl Esterases, GGPPS Prenyl Synthases) sampled by isoelectric <code>pI</code> match to the reactor pH.</li>
            <li><b>Cell Color (Dark Blue → Emerald → Gold):</b> Multi-objective Pareto score computed in Rust inside PostgreSQL via <code>pareto_score_domain_pair()</code>. Gold/Emerald cells (<code>&gt; 0.90</code>) combine high interfacial binding with optimal reactor pH compatibility.</li>
            <li><b>Action:</b> Click any cell to load that <code>(Anchor × Scissor)</code> pair into the RK4 Cascade Digital Twin and 3D Structure Viewer.</li>
        </ul>
        <div class="formula-note">Pareto = 0.30 · GRAVY<sub>norm</sub> + 0.30 · H<sub>Shannon,norm</sub> + 0.25 · pH<sub>match</sub> + 0.15 · MW<sub>compact</sub></div>
    </div>

    <div id="info-leaderboard-table" class="info-popover" popover>
        <h3>
            <span>How to Read: Top Pareto-Optimal Leaderboard &amp; GRAVY Scale</span>
            <button type="button" commandfor="info-leaderboard-table" command="hide-popover" style="padding:2px 8px;font-size:0.75rem;">Close</button>
        </h3>
        <ul>
            <li><b>What is Anchor GRAVY?</b> <b>G</b>rand <b>A</b>verage of <b>Hy</b>dropathy on the Kyte–Doolittle amino acid scale (<code>−4.5</code> Arg to <code>+4.5</code> Ile), computed in PostgreSQL via <code>gravy_score(seq) = (1/N) · Σ H<sub>i</sub></code>.</li>
            <li><b>Is GRAVY +1.158 Good?</b> <b>Yes — <code>+1.158</code> is Elite!</b> Most water-soluble enzymes have negative GRAVY (<code>−0.60 to −0.10</code>). For <b>Module 1 Surface Anchors</b>, positive GRAVY drives spontaneous hydrophobic adsorption onto solid polymers or lipid droplets:
                <div style="margin-top:5px;padding:6px 8px;background:#020617;border:1px solid #1e293b;border-radius:6px;font-size:0.75rem;">
                    <div><span style="color:#fb7185;font-weight:700;">🔴 &lt; −0.20 (LOW / Hydrophilic):</span> Remains in bulk water; weak surface tethering (<code>Boost &lt; 4×</code>).</div>
                    <div><span style="color:#fbbf24;font-weight:700;">🟡 −0.20 to +0.25 (MOD / Amphipathic):</span> Moderate interfacial partitioning (<code>Boost 4–7×</code>).</div>
                    <div><span style="color:#34d399;font-weight:700;">🟢 +0.25 to +0.60 (GOOD Hydrophobic):</span> Strong solid/lipid surface binding (<code>Boost 7–9.5×</code>).</div>
                    <div><span style="color:#34d399;font-weight:700;">🌟 ≥ +0.60 (ELITE Super-Hydrophobic, e.g. +1.158):</span> Extreme interfacial affinity (<code>Boost 10–14×</code>).</div>
                </div>
            </li>
            <li><b>Pareto Score (<code>0.0000 – 1.0000</code>):</b> 🟢 <code>≥ 0.90</code> Elite | 🟡 <code>0.78 – 0.90</code> Good | 🔴 <code>&lt; 0.78</code> Sub-optimal.</li>
            <li><b>48h RK4 Yield:</b> Exact 48-hour sink product conversion (<code>%</code> and <code>µM</code>) solved inside PostgreSQL via <code>simulate_cascade_kinetics()</code>.</li>
        </ul>
    </div>

    <div id="info-rk4-twin" class="info-popover" popover>
        <h3>
            <span>How to Read: 2. 48-Hour RK4 Cascade Digital Twin</span>
            <button type="button" commandfor="info-rk4-twin" command="hide-popover" style="padding:2px 8px;font-size:0.75rem;">Close</button>
        </h3>
        <ul>
            <li><b>Solid Green Curve (With Sink):</b> Final upcycled product <i>P</i>(<i>t</i>) when all 4 modules operate together. Module 3 continuously drains the intermediate so the primary scissor never stalls.</li>
            <li><b>Orange Dashed Curve (Transient Intermediate):</b> Concentration of the soluble cleavage intermediate <i>I</i>(<i>t</i>) (cellobiose, MHET, GGPP, or free F<sup>−</sup>). Notice how Module 3 keeps it capped well below <i>K</i><sub>i</sub>.</li>
            <li><b>Dotted Slate Curve (Remaining Substrate):</b> Unconverted solid polymer/biomass bond equivalents <i>S</i>(<i>t</i>) starting from <code>1,000 µM</code>.</li>
            <li><b>Blue Dash-Dot Curve (Cleaved w/o Sink):</b> Control where Sink <i>k</i><sub>cat,2</sub> = 0. Intermediate accumulates above <i>K</i><sub>i</sub> and competitively stalls the scissor around 45–60%.</li>
            <li><b>Gray Curve (Wild-Type Alone):</b> Unfused enzyme without surface anchor (<code>Boost = 1.0×</code>) or sink (<code>20–27%</code> conversion).</li>
        </ul>
        <div class="formula-note">d[S]/dt = −v<sub>1</sub> &nbsp;|&nbsp; d[I]/dt = +v<sub>1</sub> − v<sub>2</sub> &nbsp;|&nbsp; d[P]/dt = +v<sub>2</sub> &nbsp;(4th-Order Runge–Kutta)</div>
    </div>

    <div id="info-sliders-kpis" class="info-popover" popover>
        <h3>
            <span>How to Read: Kinetic Sliders &amp; KPI Strip</span>
            <button type="button" commandfor="info-sliders-kpis" command="hide-popover" style="padding:2px 8px;font-size:0.75rem;">Close</button>
        </h3>
        <ul>
            <li><b>Hover Any Parameter Name:</b> Hovering <code>Scissor kcat1</code>, <code>Solid Km1</code>, etc. opens an instant biophysical formula tooltip.</li>
            <li><b>Hover Any Colored Number Pill:</b> Hovering <code>26.0 /h · OPT</code> shows the 3-zone operating threshold bar (🔴 Stalled/Bottleneck, 🟡 Transitional, 🟢 Optimal Regime) and live status.</li>
            <li><b>Consortium Ratio (<i>w</i><sub>1</sub> : <i>w</i><sub>2</sub> : <i>w</i><sub>3</sub>):</b> Optimal enzyme mass fractions (<i>w</i><sub>1</sub> + <i>w</i><sub>2</sub> + <i>w</i><sub>3</sub> = 1.00) solved by <code>optimize_consortium_stoichiometry()</code> for 3-component feedstocks.</li>
        </ul>
    </div>

    <div id="info-3d-fusion" class="info-popover" popover>
        <h3>
            <span>How to Read: 3D Rigid-Body Fusion Viewer</span>
            <button type="button" commandfor="info-3d-fusion" command="hide-popover" style="padding:2px 8px;font-size:0.75rem;">Close</button>
        </h3>
        <ul>
            <li><b>Cyan Ribbon (Chain A):</b> Primary Catalytic Scissor domain (Module 2).</li>
            <li><b>Gold Ribbon + Sticks (Chain B):</b> Interfacial Surface Anchor domain (Module 1), translated along the principal axis by <code>translate_and_merge_pdb_chains()</code> to guarantee a clash-free <b>28.0 Å inter-domain clearance</b>.</li>
            <li><b>Step-by-Step Phase Tabs &amp; Full Screen:</b> Click <code>1. M1 Anchor</code> → <code>2. 28 Å Linker</code> → <code>3. M2 Scissor</code> → <code>4. M3 Sink</code> or open <b>⛶ Full Screen &amp; Phases</b> to zoom and highlight each functional module in 3D.</li>
        </ul>
    </div>

    <div id="info-sql-ledger" class="info-popover" popover>
        <h3>
            <span>How to Read: Live PostgreSQL 18 Biophysical Ledger &amp; Ranges</span>
            <button type="button" commandfor="info-sql-ledger" command="hide-popover" style="padding:2px 8px;font-size:0.75rem;">Close</button>
        </h3>
        <ul>
            <li><b>M1 Surface Anchor GRAVY (<code>gravy_score(seq)</code>):</b> Kyte–Doolittle hydropathy average (<code>(1/N) · Σ H<sub>i</sub></code>).
                <br>• <span style="color:#34d399;font-weight:700;">🟢 Good / Elite (<code>&gt; +0.25</code>; <code>≥ +0.60</code> is Elite, e.g. <code>+1.158</code>):</span> Strong hydrophobic surface coating (<code>8–12×+</code> substrate boost).
                <br>• <span style="color:#fbbf24;font-weight:700;">🟡 Moderate (<code>−0.20 to +0.25</code>):</span> Amphipathic binding (<code>4–7×</code> boost).
                <br>• <span style="color:#fb7185;font-weight:700;">🔴 Weak (<code>&lt; −0.20</code>):</span> Water-soluble; poor solid/lipid adhesion.
            </li>
            <li><b>M2 Scissor MW &amp; Isoelectric Point (<code>pI</code>):</b>
                <br>• <b>MW:</b> <span style="color:#34d399;">🟢 <code>18–55 kDa</code> (Compact &amp; Fast Diffusion)</span> | <span style="color:#fbbf24;">🟡 <code>55–75 kDa</code></span> | <span style="color:#fb7185;">🔴 <code>&gt; 75 kDa</code> (Bulky)</span>.
                <br>• <b>pI vs. Reactor pH:</b> <span style="color:#34d399;">🟢 <code>|pI − pH| ≤ 1.8</code> (Tuned to Reactor pH)</span>.
            </li>
            <li><b>Flory Compactness Ratio (<i>R</i><sub>g</sub> / (2.25 · <i>N</i><sup>0.38</sup>)):</b> Ratio of actual 3D Radius of Gyration (<i>R</i><sub>g</sub>) to ideal single-domain globular scaling 2.25 · <i>N</i><sup>0.38</sup>.
                <br>• <span style="color:#34d399;">🟢 <code>1.00–1.65</code> (Compact Globule)</span> | <span style="color:#38bdf8;">🔵 <code>1.65–2.35</code> (Expected 2-Domain Dumbbell with 28 Å Linker)</span> | <span style="color:#fb7185;">🔴 <code>&gt; 2.50</code> (Unfolded)</span>.
            </li>
            <li><b>SQL Query Preview:</b> Shows the exact PostgreSQL 18 SQL statement executed against <code>$libdir/pg_bio</code> whenever you drag a slider or click a candidate.</li>
        </ul>
        <div class="formula-note">GRAVY = (1 / N) · Σ KyteDoolittle(AA<sub>i</sub>) &nbsp;|&nbsp; Flory Ratio = R<sub>g</sub> / (2.25 · N<sup>0.38</sup>)</div>
    </div>

    <script type="module">
        if (!('commandForElement' in HTMLButtonElement.prototype)) {
            import('https://esm.run/invokers-polyfill');
        }
        if (!('popover' in HTMLElement.prototype)) {
            import('https://unpkg.com/@oddbird/popover-polyfill@latest/dist/popover.min.js');
        }
        if (!HTMLButtonElement.prototype.hasOwnProperty('interestForElement')) {
            await import('https://unpkg.com/interestfor@latest');
        }
        if (!('anchorName' in document.documentElement.style)) {
            await import('https://unpkg.com/@oddbird/css-anchor-positioning');
        }
    </script>

    <script>
        // Fallback for browsers without <dialog closedby="any"> support per modern-web-guidance `light-dismiss-a-dialog`
        const fsDialog = document.getElementById('fusion-fs-dialog');
        if (!('closedBy' in HTMLDialogElement.prototype)) {
            fsDialog.addEventListener('click', (event) => {
                if (event.target !== fsDialog) return;
                const rect = fsDialog.getBoundingClientRect();
                const isDialogContent = (
                    rect.top <= event.clientY &&
                    event.clientY <= rect.top + rect.height &&
                    rect.left <= event.clientX &&
                    event.clientX <= rect.left + rect.width
                );
                if (isDialogContent) return;
                fsDialog.close();
            });
        }

        var heatmapChart = echarts.init(document.getElementById('pareto-heatmap'));
        var rk4Chart = echarts.init(document.getElementById('rk4-chart'));
        var molViewer = null;
        var fsMolViewer = null;
        var currentSwarmData = null;
        var currentComplex3D = null;
        var activeAnchor = null;
        var activeScissor = null;
        var currentPhaseIdx = 0;
        var isSpinning3D = false;

        const SLIDER_SPECS = {
            kcat1: {
                id: 'sl-kcat1', lbl: 'lbl-kcat1', labelBtn: 'lbl-btn-kcat1', box: 'box-kcat1', body: 'thresh-body-kcat1',
                name: 'Scissor kcat1 (Catalytic Turnover)', unit: '/h', decimals: 1, inverse: false,
                low: 15.0, high: 22.0,
                lowLabel: '< 15 /h (Rate-Limited)', midLabel: '15–22 /h (Moderate)', highLabel: '≥ 22 /h (Optimal)',
                advice: {
                    optimal: 'High primary bond cleavage velocity; paired with Module 3 Sink, drives >90% 48-hour conversion.',
                    warn: 'Moderate turnover; requires strong Module 1 Anchor Boost (>8×) to reach >85% conversion in 48 hours.',
                    danger: 'Catalytic bottleneck: primary scissor cleaves too slowly to clear the solid feedstock within 48 hours.'
                }
            },
            km1: {
                id: 'sl-km1', lbl: 'lbl-km1', labelBtn: 'lbl-btn-km1', box: 'box-km1', body: 'thresh-body-km1',
                name: 'Solid Km1 (Interfacial Michaelis Constant)', unit: ' µM', decimals: 0, inverse: true,
                low: 420.0, high: 560.0,
                lowLabel: '≤ 420 µM (Tight Binding)', midLabel: '420–560 µM (Moderate)', highLabel: '> 560 µM (Weak Affinity)',
                advice: {
                    optimal: 'Tight interfacial affinity (low Km1); enzyme saturates rapidly on the solid/lipid surface.',
                    warn: 'Moderate Km1; benefits from higher Module 1 GRAVY hydropathy to concentrate local substrate.',
                    danger: 'Weak substrate affinity (high Km1); catalytic pocket struggles to engage recalcitrant polymer chains.'
                }
            },
            kcat2: {
                id: 'sl-kcat2', lbl: 'lbl-kcat2', labelBtn: 'lbl-btn-kcat2', box: 'box-kcat2', body: 'thresh-body-kcat2',
                name: 'Sink kcat2 (Module 3 Equilibrium Sink Rate)', unit: '/h', decimals: 1, inverse: false,
                low: 18.0, high: 30.0,
                lowLabel: '< 18 /h (Ki Stalled)', midLabel: '18–30 /h (Partial Drain)', highLabel: '≥ 30 /h (Optimal Sink)',
                advice: {
                    optimal: 'Fast metabolic/mineral sink keeps transient intermediate [I] well below Ki so Scissor never stalls.',
                    warn: 'Sink barely keeps pace with Scissor; transient intermediate rises near Ki threshold.',
                    danger: 'Sink bottleneck! Intermediate accumulates above Ki and competitively stalls the primary scissor.'
                }
            },
            ki: {
                id: 'sl-ki', lbl: 'lbl-ki', labelBtn: 'lbl-btn-ki', box: 'box-ki', body: 'thresh-body-ki',
                name: 'Inhibition Ki (Competitive Product Inhibition)', unit: ' µM', decimals: 1, inverse: false,
                low: 14.0, high: 22.0,
                lowLabel: '< 14 µM (Severe Inhibition)', midLabel: '14–22 µM (Sensitive)', highLabel: '≥ 22 µM (Tolerant)',
                advice: {
                    optimal: 'High tolerance to free intermediate; combined with Module 3 Sink, competitive inhibition is negligible.',
                    warn: 'Moderate product inhibition sensitivity; Module 3 Sink (kcat2 ≥ 30 /h) is essential to prevent stalling.',
                    danger: 'Severe competitive feedback inhibition (low Ki)! Without a fast Module 3 Sink, reaction stalls early.'
                }
            },
            boost: {
                id: 'sl-boost', lbl: 'lbl-boost', labelBtn: 'lbl-btn-boost', box: 'box-boost', body: 'thresh-body-boost',
                name: 'Anchor Boost (Module 1 Surface Adsorption)', unit: '×', decimals: 1, inverse: false,
                low: 4.0, high: 7.0,
                lowLabel: '< 4.0× (Weak Anchor)', midLabel: '4.0–7.0× (Moderate)', highLabel: '≥ 7.0× (High-GRAVY Anchor)',
                advice: {
                    optimal: 'Strong Langmuir-Hinshelwood surface adsorption concentrates enzyme 7–14× at the feedstock interface.',
                    warn: 'Moderate interfacial enrichment; selecting a higher-GRAVY Module 1 anchor increases effective boost.',
                    danger: 'Near wild-type diffusion limit (1–4×); enzyme remains mostly in bulk solution away from solid substrate.'
                }
            }
        };

        // Deterministic viewport-clamped (x, y) placement for all [interestfor] hover tooltips
        let lastHoveredTrigger = null;
        function positionHintTooltip(triggerEl, tooltipEl) {
            if (!triggerEl || !tooltipEl) return;
            const rect = triggerEl.getBoundingClientRect();
            const vw = window.innerWidth;
            const vh = window.innerHeight;
            const pad = 12;

            // Measure tooltip dimensions (fallback to 330x145 if not yet rendered)
            const tipW = tooltipEl.offsetWidth || 330;
            const tipH = tooltipEl.offsetHeight || 145;

            let left = rect.left;
            if (left + tipW + pad > vw) {
                left = rect.right - tipW;
            }
            left = Math.max(pad, Math.min(left, vw - tipW - pad));

            let top = rect.bottom + 7;
            if (top + tipH + pad > vh && rect.top - tipH - 7 >= pad) {
                top = rect.top - tipH - 7;
            } else {
                top = Math.max(pad, Math.min(top, vh - tipH - pad));
            }

            tooltipEl.style.inset = 'auto';
            tooltipEl.style.right = 'auto';
            tooltipEl.style.bottom = 'auto';
            tooltipEl.style.left = `${Math.round(left)}px`;
            tooltipEl.style.top = `${Math.round(top)}px`;
        }

        function bindHintTooltipPositioning() {
            document.addEventListener('pointerover', (e) => {
                const trigger = e.target.closest('[interestfor]');
                if (!trigger) return;
                lastHoveredTrigger = trigger;
                const tipId = trigger.getAttribute('interestfor');
                const tipEl = document.getElementById(tipId);
                if (tipEl) {
                    positionHintTooltip(trigger, tipEl);
                    requestAnimationFrame(() => positionHintTooltip(trigger, tipEl));
                }
            }, { passive: true });

            document.addEventListener('focusin', (e) => {
                const trigger = e.target.closest('[interestfor]');
                if (!trigger) return;
                lastHoveredTrigger = trigger;
                const tipId = trigger.getAttribute('interestfor');
                const tipEl = document.getElementById(tipId);
                if (tipEl) {
                    positionHintTooltip(trigger, tipEl);
                    requestAnimationFrame(() => positionHintTooltip(trigger, tipEl));
                }
            });

            document.querySelectorAll('.hint-tooltip').forEach(tipEl => {
                tipEl.addEventListener('beforetoggle', () => {
                    const trigger = (lastHoveredTrigger && lastHoveredTrigger.getAttribute('interestfor') === tipEl.id)
                        ? lastHoveredTrigger
                        : document.querySelector(`[interestfor="${tipEl.id}"]`);
                    if (trigger) positionHintTooltip(trigger, tipEl);
                });
                tipEl.addEventListener('toggle', (ev) => {
                    if (ev.newState === 'open') {
                        const trigger = (lastHoveredTrigger && lastHoveredTrigger.getAttribute('interestfor') === tipEl.id)
                            ? lastHoveredTrigger
                            : document.querySelector(`[interestfor="${tipEl.id}"]`);
                        if (trigger) positionHintTooltip(trigger, tipEl);
                    }
                });
            });
        }
        bindHintTooltipPositioning();

        window.addEventListener('resize', function() {
            heatmapChart.resize();
            rk4Chart.resize();
            if (molViewer) molViewer.resize();
            if (fsMolViewer) fsMolViewer.resize();
        });

        function evaluateSliderZone(spec, val) {
            if (!spec.inverse) {
                if (val >= spec.high) return { cls: 'zone-optimal', tag: 'OPT', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.42)', title: '🟢 OPTIMAL REGIME', msg: spec.advice.optimal };
                if (val >= spec.low) return { cls: 'zone-warn', tag: 'MOD', color: '#f59e0b', borderColor: 'rgba(245, 158, 11, 0.48)', title: '🟡 TRANSITIONAL REGIME', msg: spec.advice.warn };
                return { cls: 'zone-danger', tag: 'LOW', color: '#f43f5e', borderColor: 'rgba(244, 63, 94, 0.55)', title: '🔴 RATE-LIMITED / STALLED', msg: spec.advice.danger };
            } else {
                if (val <= spec.low) return { cls: 'zone-optimal', tag: 'OPT', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.42)', title: '🟢 OPTIMAL TIGHT AFFINITY', msg: spec.advice.optimal };
                if (val <= spec.high) return { cls: 'zone-warn', tag: 'MOD', color: '#f59e0b', borderColor: 'rgba(245, 158, 11, 0.48)', title: '🟡 MODERATE AFFINITY', msg: spec.advice.warn };
                return { cls: 'zone-danger', tag: 'WEAK', color: '#f43f5e', borderColor: 'rgba(244, 63, 94, 0.55)', title: '🔴 WEAK SUBSTRATE AFFINITY', msg: spec.advice.danger };
            }
        }

        function syncSliderLabels() {
            Object.keys(SLIDER_SPECS).forEach(key => {
                const spec = SLIDER_SPECS[key];
                const input = document.getElementById(spec.id);
                const pill = document.getElementById(spec.lbl);
                const labelBtn = document.getElementById(spec.labelBtn);
                const boxEl = document.getElementById(spec.box);
                const val = Number(input.value);
                const min = Number(input.min || 0);
                const max = Number(input.max || 100);
                const pct = Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100));

                const zone = evaluateSliderZone(spec, val);
                const formatted = val.toFixed(spec.decimals) + spec.unit;

                // Sync CSS custom properties per modern-web-guidance `slider`
                input.style.setProperty('--attr-min', min);
                input.style.setProperty('--attr-max', max);
                input.style.setProperty('--control-value', val);
                input.style.setProperty('--slider-fill-color', zone.color);
                input.setAttribute('aria-valuetext', `${formatted} (${zone.title})`);

                // Update both the main parameter label and the value badge to match the active rule color
                if (labelBtn) {
                    labelBtn.className = `param-label-btn ${zone.cls}`;
                }
                if (boxEl) {
                    boxEl.style.borderColor = zone.borderColor;
                }
                pill.className = `param-val-pill ${zone.cls}`;
                pill.textContent = `${formatted}`;

                const leftColor = spec.inverse ? '#10b981' : '#f43f5e';
                const rightColor = spec.inverse ? '#f43f5e' : '#10b981';
                const bodyEl = document.getElementById(spec.body);
                if (bodyEl) {
                    bodyEl.innerHTML = `
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;">
                            <b style="color:#f8fafc;">${spec.name}</b>
                            <span style="color:${zone.color};font-weight:800;font-family:monospace;">${formatted} · ${zone.tag}</span>
                        </div>
                        <div style="font-size:0.72rem;font-weight:700;color:${zone.color};margin-bottom:4px;">${zone.title}</div>
                        <div style="position:relative;padding-bottom:10px;">
                            <div class="thresh-meter">
                                <div style="background:${leftColor};"></div>
                                <div style="background:#f59e0b;"></div>
                                <div style="background:${rightColor};"></div>
                            </div>
                            <div style="position:absolute;left:calc(${pct.toFixed(1)}% - 5px);top:10px;color:#fff;font-size:0.68rem;line-height:1;">▲</div>
                        </div>
                        <div class="thresh-legend">
                            <span style="color:${leftColor};">${spec.lowLabel}</span>
                            <span style="color:#fbbf24;">${spec.midLabel}</span>
                            <span style="color:${rightColor};">${spec.highLabel}</span>
                        </div>
                        <div style="color:#cbd5e1;font-size:0.74rem;border-top:1px solid #1e293b;padding-top:5px;">${zone.msg}</div>
                    `;
                }
            });

            // Also sync M3 Sink main label color in the Biophysical Ledger if present
            const ledgerSinkLbl = document.getElementById('ledger-lbl-sink');
            const ledgerSinkVal = document.getElementById('ledger-val-sink');
            if (ledgerSinkLbl && ledgerSinkVal) {
                const kcat2Val = Number(document.getElementById('sl-kcat2').value);
                const kiVal = Number(document.getElementById('sl-ki').value);
                const sinkZone = evaluateSliderZone(SLIDER_SPECS.kcat2, kcat2Val);
                ledgerSinkLbl.className = `param-label-btn ${sinkZone.cls}`;
                ledgerSinkVal.innerHTML = `Drains intermediate below <i>K</i><sub>i</sub> (<b>${kiVal} µM</b>) at <i>k</i><sub>cat,2</sub> = <span class="param-val-pill ${sinkZone.cls}">${kcat2Val.toFixed(1)}/h · ${sinkZone.tag}</span>`;
            }
        }

        function loadPipelineSwarm() {
            let pid = document.getElementById('pipeline-select').value;
            heatmapChart.showLoading({ text: 'Querying pg_bio Domain Atlas...', color: '#38bdf8', textColor: '#fff', maskColor: 'rgba(9,13,22,0.8)' });

            fetch('/api/swarm?pipeline=' + encodeURIComponent(pid))
                .then(r => r.json())
                .then(data => {
                    heatmapChart.hideLoading();
                    currentSwarmData = data;
                    document.getElementById('swarm-timing-badge').textContent = `pg_bio: ${data.elapsed_ms} ms (${data.anchors.length}×${data.scissors.length})`;
                    document.getElementById('kpi-stoich').textContent = `${data.stoichiometry.w1} : ${data.stoichiometry.w2} : ${data.stoichiometry.w3}`;

                    let p = data.preset;
                    document.getElementById('sl-kcat1').value = p.kcat1;
                    document.getElementById('sl-km1').value = p.km1;
                    document.getElementById('sl-kcat2').value = p.kcat2;
                    document.getElementById('sl-ki').value = p.ki;
                    document.getElementById('sl-boost').value = p.boost;
                    syncSliderLabels();

                    renderHeatmap(data);
                    renderLeaderboard(data.top_pairs);

                    if (data.top_pairs.length > 0) {
                        selectPair(data.top_pairs[0].anchor_id, data.top_pairs[0].scissor_id);
                    }
                });
        }

        function resetSlidersToPreset() {
            if (!currentSwarmData) return;
            let p = currentSwarmData.preset;
            document.getElementById('sl-kcat1').value = p.kcat1;
            document.getElementById('sl-km1').value = p.km1;
            document.getElementById('sl-kcat2').value = p.kcat2;
            document.getElementById('sl-ki').value = p.ki;
            let adjBoost = activeAnchor ? Math.max(1.5, Math.min(14.0, p.boost + Number(activeAnchor.gravy) * 2.5)) : p.boost;
            document.getElementById('sl-boost').value = adjBoost.toFixed(1);
            syncSliderLabels();
            runRK4Simulation();
            renderPhaseWalkthrough();
        }

        function renderHeatmap(data) {
            let xLabels = data.scissors.map(s => s.id);
            let yLabels = data.anchors.map(a => a.id);

            let option = {
                tooltip: {
                    position: 'top',
                    backgroundColor: 'rgba(2,6,23,0.95)',
                    borderColor: '#38bdf8',
                    textStyle: { color: '#fff', fontSize: 12 },
                    formatter: function(params) {
                        let s = data.scissors[params.value[0]];
                        let a = data.anchors[params.value[1]];
                        return `<b>Anchor (M1):</b> ${a.id} (${a.org}) | GRAVY: ${a.gravy}<br>` +
                               `<b>Scissor (M2):</b> ${s.id} (${s.org}) | MW: ${s.mw} kDa, pI: ${s.pi}<br>` +
                               `<span style="color:#34d399">Pareto Score: <b>${params.value[2].toFixed(4)}</b></span>`;
                    }
                },
                grid: { top: '5%', bottom: '19%', left: '16%', right: '12%' },
                xAxis: {
                    type: 'category',
                    data: xLabels,
                    axisLabel: { rotate: 45, fontSize: 10, color: '#94a3b8' }
                },
                yAxis: {
                    type: 'category',
                    data: yLabels,
                    axisLabel: { fontSize: 10, color: '#38bdf8' }
                },
                visualMap: {
                    min: data.min_score,
                    max: data.max_score,
                    calculable: true,
                    orient: 'vertical',
                    right: '1%',
                    top: 'center',
                    precision: 3,
                    textStyle: { color: '#cbd5e1', fontSize: 10 },
                    inRange: { color: ['#0f172a', '#1d4ed8', '#0284c7', '#10b981', '#facc15'] }
                },
                series: [{
                    name: 'Pareto Score',
                    type: 'heatmap',
                    data: data.matrix_cells,
                    itemStyle: { borderColor: '#090d16', borderWidth: 1 },
                    emphasis: { itemStyle: { borderColor: '#fff', borderWidth: 2 } }
                }]
            };
            heatmapChart.setOption(option);
            heatmapChart.off('click');
            heatmapChart.on('click', function(params) {
                if (!params.value) return;
                let s = data.scissors[params.value[0]];
                let a = data.anchors[params.value[1]];
                selectPair(a.id, s.id);
            });
        }

        function evaluateGravyRange(g) {
            const val = Number(g);
            const signStr = (val >= 0 ? '+' : '') + val.toFixed(3);
            if (val >= 0.60) {
                return {
                    cls: 'zone-optimal', tag: 'ELITE', color: '#10b981', signStr,
                    title: '🌟 ELITE SUPER-HYDROPHOBIC ANCHOR (≥ +0.60)',
                    verdict: `Yes — GRAVY ${signStr} is exceptionally high! Most soluble proteins score −0.60 to −0.10. A score of ${signStr} means dense apolar side chains (Ile, Val, Leu, Phe, Ala) coat the surface, driving spontaneous Langmuir–Hinshelwood adsorption onto solid polymers or lipid droplets (10–12×+ substrate boost).`
                };
            }
            if (val >= 0.25) {
                return {
                    cls: 'zone-optimal', tag: 'GOOD', color: '#10b981', signStr,
                    title: '🟢 GOOD HYDROPHOBIC ANCHOR (+0.25 to +0.60)',
                    verdict: `GRAVY ${signStr} is well above average for globular proteins, providing strong hydrophobic surface tethering (7–9.5× local substrate boost) without aggregation.`
                };
            }
            if (val >= -0.20) {
                return {
                    cls: 'zone-warn', tag: 'MOD', color: '#f59e0b', signStr,
                    title: '🟡 AMPHIPATHIC / MODERATE ANCHOR (−0.20 to +0.25)',
                    verdict: `GRAVY ${signStr} is balanced between polar and apolar residues, giving moderate surface partitioning (4–7× boost) best suited for polysaccharide/lignocellulose CBM binding.`
                };
            }
            return {
                cls: 'zone-danger', tag: 'LOW', color: '#f43f5e', signStr,
                title: '🔴 HYDROPHILIC / WEAK SURFACE BINDING (< −0.20)',
                verdict: `GRAVY ${signStr} is water-loving (hydrophilic). Without a specialized carbohydrate-binding cleft, this domain prefers bulk water over hydrophobic solid surfaces.`
            };
        }

        function renderLeaderboard(topPairs) {
            let tbody = document.getElementById('leaderboard-body');
            tbody.innerHTML = '';
            topPairs.forEach((row, idx) => {
                let tr = document.createElement('tr');
                tr.dataset.pair = `${row.anchor_id}_${row.scissor_id}`;
                tr.onclick = () => selectPair(row.anchor_id, row.scissor_id);
                let gInfo = evaluateGravyRange(row.anchor_gravy);
                tr.innerHTML = `
                    <th scope="row">#${idx + 1}</th>
                    <td><b>${row.anchor_id}</b> × <b>${row.scissor_id}</b> <span style="color:#94a3b8;font-size:0.73rem;">(${row.scissor_org})</span></td>
                    <td><span class="param-val-pill ${gInfo.cls}" style="font-size:0.69rem;padding:1px 6px;">${gInfo.signStr} · ${gInfo.tag}</span></td>
                    <td style="color:#38bdf8;font-weight:700;">${row.pareto_score.toFixed(4)}</td>
                    <td style="color:#34d399;font-weight:700;">${row.yield_pct.toFixed(1)}% (${row.yield_um} µM)</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function selectPair(anchorId, scissorId) {
            activeAnchor = currentSwarmData.anchors.find(a => a.id === anchorId) || { id: anchorId, gravy: 0.3, org: 'Unknown' };
            activeScissor = currentSwarmData.scissors.find(s => s.id === scissorId) || { id: scissorId, mw: 30.0, pi: 6.5, org: 'Unknown' };

            document.querySelectorAll('#leaderboard-body tr').forEach(tr => {
                tr.classList.toggle('selected-row', tr.dataset.pair === `${anchorId}_${scissorId}`);
            });

            document.getElementById('kpi-pair').textContent = `${anchorId} × ${scissorId}`;

            let p = currentSwarmData.preset;
            document.getElementById('sl-kcat1').value = p.kcat1;
            document.getElementById('sl-km1').value = p.km1;
            document.getElementById('sl-kcat2').value = p.kcat2;
            document.getElementById('sl-ki').value = p.ki;
            let adjBoost = Math.max(1.5, Math.min(14.0, p.boost + Number(activeAnchor.gravy) * 2.5));
            document.getElementById('sl-boost').value = adjBoost.toFixed(1);
            syncSliderLabels();

            runRK4Simulation();
            load3DComplex(anchorId, scissorId);
        }

        function updateRK4FromSliders() {
            syncSliderLabels();
            runRK4Simulation();
            renderPhaseWalkthrough();
        }

        function runRK4Simulation() {
            if (!currentSwarmData) return;
            let pid = document.getElementById('pipeline-select').value;
            let kcat1 = document.getElementById('sl-kcat1').value;
            let km1 = document.getElementById('sl-km1').value;
            let kcat2 = document.getElementById('sl-kcat2').value;
            let ki = document.getElementById('sl-ki').value;
            let boost = document.getElementById('sl-boost').value;

            let qs = new URLSearchParams({
                pipeline: pid, kcat1: kcat1, km1: km1, kcat2: kcat2, ki: ki, boost: boost
            });

            fetch('/api/rk4?' + qs.toString())
                .then(r => r.json())
                .then(res => {
                    document.getElementById('rk4-timing-badge').textContent = `RK4 SQL: ${res.elapsed_ms} ms`;
                    document.getElementById('kpi-sink-yield').textContent = `${res.sink_48h_pct.toFixed(1)}% (${res.sink_48h_um} µM)`;
                    document.getElementById('kpi-nosink-yield').textContent = `${res.nosink_48h_pct.toFixed(1)}%`;

                    let p = currentSwarmData.preset;
                    let option = {
                        tooltip: {
                            trigger: 'axis',
                            backgroundColor: 'rgba(2,6,23,0.95)',
                            borderColor: '#38bdf8',
                            textStyle: { color: '#fff', fontSize: 12 }
                        },
                        legend: {
                            top: 0,
                            textStyle: { color: '#cbd5e1', fontSize: 10.5 }
                        },
                        grid: { top: '16%', bottom: '12%', left: '7%', right: '7%' },
                        xAxis: {
                            type: 'category',
                            data: res.time_hr,
                            name: 'Hours',
                            nameLocation: 'end',
                            axisLabel: { color: '#94a3b8' }
                        },
                        yAxis: {
                            type: 'value',
                            min: 0,
                            max: 1020,
                            name: 'µM eq',
                            axisLabel: { color: '#94a3b8' },
                            splitLine: { lineStyle: { color: '#1e293b' } }
                        },
                        series: [
                            {
                                name: p.prod_label + ' (With Sink)',
                                type: 'line',
                                data: res.with_sink_prod,
                                smooth: true,
                                lineStyle: { width: 3, color: '#34d399' },
                                areaStyle: { color: 'rgba(52, 211, 153, 0.14)' }
                            },
                            {
                                name: 'Transient ' + p.int_label,
                                type: 'line',
                                data: res.with_sink_int,
                                smooth: true,
                                lineStyle: { width: 2, type: 'dashed', color: '#f59e0b' }
                            },
                            {
                                name: 'Remaining ' + p.sub_label,
                                type: 'line',
                                data: res.with_sink_sub,
                                smooth: true,
                                lineStyle: { width: 1.8, type: 'dotted', color: '#64748b' }
                            },
                            {
                                name: 'Cleaved w/o Sink (Ki Stalled)',
                                type: 'line',
                                data: res.nosink_cleaved,
                                smooth: true,
                                lineStyle: { width: 2, type: 'dashdot', color: '#38bdf8' }
                            },
                            {
                                name: 'Wild-Type Scissor Alone',
                                type: 'line',
                                data: res.wt_cleaved,
                                smooth: true,
                                lineStyle: { width: 1.5, color: '#94a3b8' }
                            }
                        ]
                    };
                    rk4Chart.setOption(option);

                    document.getElementById('sql-preview').textContent =
`SELECT time_hr, substrate_u_m, intermediate_u_m, sink_product_u_m, fractional_conversion
FROM simulate_cascade_kinetics(${kcat1}, ${km1}, ${kcat2}, ${p.km2}, ${ki}, ${boost}, 1000.0, 48.0, 48);`;
                });
        }

        function getPhaseDefinitions() {
            if (!currentSwarmData || !activeAnchor || !activeScissor) return [];
            const p = currentSwarmData.preset;
            const boost = document.getElementById('sl-boost').value;
            const kcat1 = document.getElementById('sl-kcat1').value;
            const km1 = document.getElementById('sl-km1').value;
            const kcat2 = document.getElementById('sl-kcat2').value;
            const ki = document.getElementById('sl-ki').value;
            const rg = currentComplex3D ? currentComplex3D.globular.radius_of_gyration.toFixed(1) : '—';
            const ca = currentComplex3D ? currentComplex3D.globular.ca_count : '—';

            return [
                {
                    idx: 0,
                    color: '#7dd3fc',
                    shortTitle: 'All 4 Modules Active (Full Chimera)',
                    title: 'Phase 0 · Complete 4-Module Chimeric Machine',
                    summary: `<b style="color:#ffffff;">${activeAnchor.id} × ${activeScissor.id}</b> (${ca} Cα atoms, Rg ${rg} Å): Chain B (<b style="color:#fde047;">Gold Anchor</b>) adsorbs onto the ${p.sub_label} interface (<b style="color:#ffffff;">${boost}× boost</b>), separated by a <b style="color:#f0abfc;">28.0 Å clash-free bridge</b> from Chain A (<b style="color:#67e8f9;">Cyan Scissor</b>, ${kcat1} /h) and the C-terminal Equilibrium Sink (${kcat2} /h).`,
                    sqlFn: 'translate_and_merge_pdb_chains(scissor_pdb, anchor_pdb, 28.0)'
                },
                {
                    idx: 1,
                    color: '#fde047',
                    shortTitle: 'Phase 1 · M1 Interfacial Surface Anchor (Chain B)',
                    title: `Phase 1 · Module 1 Surface Anchor (${activeAnchor.id})`,
                    summary: `<b style="color:#ffffff;">Interfacial Adsorption (${activeAnchor.org}, GRAVY ${activeAnchor.gravy}):</b> Hydrophobic surface patch binds directly onto the solid/lipid phase, boosting effective local substrate concentration by <b style="color:#fde047;">${boost}×</b> via Langmuir-Hinshelwood partitioning.`,
                    sqlFn: `pareto_score_domain_pair(gravy => ${activeAnchor.gravy}, ph => ${p.ph})`
                },
                {
                    idx: 2,
                    color: '#f0abfc',
                    shortTitle: 'Phase 2 · 28.0 Å Rigid-Body Linker Bridge',
                    title: `Phase 2 · ${p.linker_name || '28.0 Å Clash-Free Linker Bridge'}`,
                    summary: `<b style="color:#ffffff;">Steric Isolation &amp; Orientation:</b> <code style="color:#67e8f9;">translate_and_merge_pdb_chains()</code> translates Chain B along the principal X-axis to enforce an exact <b style="color:#f0abfc;">28.0 Å minimum inter-chain clearance</b>, preventing domain misfolding while tethering Chain A directly above the substrate.`,
                    sqlFn: 'translate_and_merge_pdb_chains(..., clearance_angstroms => 28.0)'
                },
                {
                    idx: 3,
                    color: '#fda4af',
                    shortTitle: 'Phase 3 · M2 Primary Bond Scissor (Chain A)',
                    title: `Phase 3 · Module 2 Primary Scissor (${activeScissor.id})`,
                    summary: `<b style="color:#ffffff;">Catalytic Bond Scission (${activeScissor.org}, MW ${activeScissor.mw} kDa, pI ${activeScissor.pi}):</b> Cleaves <b style="color:#fda4af;">${p.target_bond || p.sub_label}</b> at <b style="color:#ffffff;">k<sub>cat,1</sub> = ${kcat1} /h</b> (K<sub>m,1</sub> = ${km1} µM) to release soluble ${p.int_label}.`,
                    sqlFn: `simulate_cascade_kinetics(kcat1 => ${kcat1}, km1 => ${km1}, ...)`
                },
                {
                    idx: 4,
                    color: '#6ee7b7',
                    shortTitle: 'Phase 4 · M3 Equilibrium Sink & M4 Optical Beacon',
                    title: `Phase 4 · ${p.sink_name || 'Equilibrium Sink & Optical Beacon'}`,
                    summary: `<b style="color:#ffffff;">Le Chatelier Equilibrium Pull (k<sub>cat,2</sub> = ${kcat2} /h, K<sub>i</sub> = ${ki} µM):</b> Immediately drains ${p.int_label} into <b style="color:#6ee7b7;">${p.prod_label}</b> so [I] stays well below K<sub>i</sub> (${ki} µM), while triggering <b style="color:#ffffff;">${p.beacon_name || 'the M4 Optical Beacon'}</b>.`,
                    sqlFn: `simulate_cascade_kinetics(..., kcat2 => ${kcat2}, ki => ${ki})`
                }
            ];
        }

        let cutProgress = 0.50;
        let isCutAnimating = true;
        let cutAnimTimer = null;

        function updateCutControlsUI() {
            const slider = document.getElementById('cut-progress-slider');
            const pill = document.getElementById('cut-stage-pill');
            const b1 = document.getElementById('cut-sub-1');
            const b2 = document.getElementById('cut-sub-2');
            const b3 = document.getElementById('cut-sub-3');
            const b4 = document.getElementById('cut-sub-4');
            if (slider) slider.value = Math.round(cutProgress * 100);
            let stageText = 'STATE 1 · FIT';
            let activeBtn = 1;
            if (cutProgress >= 0.28 && cutProgress < 0.52) {
                stageText = '⚡ STATE 2 · LOCK';
                activeBtn = 2;
            } else if (cutProgress >= 0.52 && cutProgress < 0.76) {
                stageText = '✂️ STATE 3 · BREAK';
                activeBtn = 3;
            } else if (cutProgress >= 0.76) {
                stageText = '🚀 STATE 4 · SINK';
                activeBtn = 4;
            }
            if (pill) pill.textContent = `${Math.round(cutProgress * 100)}% · ${stageText}`;
            [b1, b2, b3, b4].forEach((btn, idx) => {
                if (!btn) return;
                const isSel = (idx + 1) === activeBtn;
                btn.style.background = isSel ? '#fde047' : '#1e293b';
                btn.style.color = isSel ? '#020617' : '#f8fafc';
                btn.style.borderColor = isSel ? '#ffffff' : '#475569';
            });

            const breakdownEl = document.getElementById('fs-mech-breakdown');
            if (breakdownEl) {
                const p = currentSwarmData ? currentSwarmData.preset : {};
                const subShort = (p.sub_label || 'Feedstock [S]').split('(')[0].trim();
                const bondShort = (p.bond_name || 'Scissile Bond').split('(')[0].trim();
                const intShort = (p.int_label || 'Cleaved Intermediate [I]').split('(')[0].trim();
                const prodShort = (p.prod_label || 'Mineralized Sink [P]').split('(')[0].trim();
                const s1 = activeBtn === 1 ? 'background:#1e293b;border:2px solid #fde047;' : 'background:#0f172a;border:1px solid #334155;opacity:0.85;';
                const s2 = activeBtn === 2 ? 'background:#3b1d06;border:2px solid #fb923c;' : 'background:#0f172a;border:1px solid #334155;opacity:0.85;';
                const s3 = activeBtn === 3 ? 'background:#3b071e;border:2px solid #fb7185;' : 'background:#0f172a;border:1px solid #334155;opacity:0.85;';
                const s4 = activeBtn === 4 ? 'background:#064e3b;border:2px solid #34d399;' : 'background:#0f172a;border:1px solid #334155;opacity:0.85;';
                breakdownEl.innerHTML = `
                    <div onclick="setCutProgress(0.14)" style="${s1}border-radius:6px;padding:5px 7px;cursor:pointer;">
                        <div style="font-weight:800;color:#fde047;">State 1 · 🧲 Move &amp; Fit:</div>
                        <div style="color:#f1f5f9;">Yellow structure carries <b>${subShort}</b> across 28 Å into Cyan Scissor</div>
                    </div>
                    <div onclick="setCutProgress(0.38)" style="${s2}border-radius:6px;padding:5px 7px;cursor:pointer;">
                        <div style="font-weight:800;color:#fb923c;">State 2 · ⚡ Lock Joint:</div>
                        <div style="color:#f1f5f9;">Amber tip fits inside Gold Triad; targets <b>${bondShort}</b></div>
                    </div>
                    <div onclick="setCutProgress(0.62)" style="${s3}border-radius:6px;padding:5px 7px;cursor:pointer;">
                        <div style="font-weight:800;color:#fda4af;">State 3 · ✂️ Break Piece Off:</div>
                        <div style="color:#f1f5f9;">3D chain breaks! Coral piece (<b>${intShort}</b>) detaches; Yellow recoils</div>
                    </div>
                    <div onclick="setCutProgress(0.90)" style="${s4}border-radius:6px;padding:5px 7px;cursor:pointer;">
                        <div style="font-weight:800;color:#6ee7b7;">State 4 · 🚀 Cα Trajectory:</div>
                        <div style="color:#f1f5f9;">Broken piece follows <b>W1→W5 Cα channel</b> into <b>${prodShort}</b></div>
                    </div>
                `;
            }
        }

        function setCutProgress(val) {
            cutProgress = Math.max(0.0, Math.min(1.0, Number(val)));
            updateCutControlsUI();
            if (currentComplex3D) {
                applyPhaseStyleToViewer(molViewer, currentComplex3D.merged_pdb, currentPhaseIdx);
                if (fsDialog.open && fsMolViewer) {
                    applyPhaseStyleToViewer(fsMolViewer, currentComplex3D.merged_pdb, currentPhaseIdx);
                }
            }
        }

        function toggleCutAnimation() {
            isCutAnimating = !isCutAnimating;
            const btn = document.getElementById('btn-cut-play');
            if (btn) {
                btn.textContent = isCutAnimating ? '⏸ Pause Motion' : '▶ Play Motion';
                btn.style.background = isCutAnimating ? '#10b981' : '#38bdf8';
            }
        }

        function startCutAnimationLoop() {
            if (cutAnimTimer) clearInterval(cutAnimTimer);
            cutAnimTimer = setInterval(() => {
                if (!isCutAnimating) return;
                if (currentPhaseIdx !== 2 && currentPhaseIdx !== 3 && currentPhaseIdx !== 4 && !fsDialog.open) return;
                cutProgress += 0.022;
                if (cutProgress > 1.0) cutProgress = 0.03;
                updateCutControlsUI();
                if (currentComplex3D) {
                    if (fsDialog.open && fsMolViewer) {
                        applyPhaseStyleToViewer(fsMolViewer, currentComplex3D.merged_pdb, currentPhaseIdx, true);
                    } else if (molViewer && (currentPhaseIdx === 2 || currentPhaseIdx === 3 || currentPhaseIdx === 4)) {
                        applyPhaseStyleToViewer(molViewer, currentComplex3D.merged_pdb, currentPhaseIdx, true);
                    }
                }
            }, 140);
        }

        // Smoothstep helper for physical rigid-body docking, recoil, and C-alpha pathway interpolation
        function smoothStep01(t) {
            let c = Math.max(0.0, Math.min(1.0, t));
            return c * c * (3.0 - 2.0 * c);
        }

        // Format a 3D coordinate into standard fixed-width PDB columns 31..54
        function replacePdbCoords(line, x, y, z) {
            const xs = x.toFixed(3).padStart(8, ' ');
            const ys = y.toFixed(3).padStart(8, ' ');
            const zs = z.toFixed(3).padStart(8, ' ');
            return line.substring(0, 30) + xs + ys + zs + line.substring(54);
        }

        // Build the 4-State Dynamic PDB (using the actual 3D representation of Chain B + Cleavable Segment Chain C)
        // and compute the exact C-alpha structural trajectory waypoints (W1 -> W2 -> W3 -> W4 -> W5) across Chain A!
        function buildDynamicStatePdbAndPath(rawPdb, prog) {
            const lines = rawPdb.split('\\n');
            let caA = [], caB = [];
            let minResB = 999999, maxResB = -999999;

            for (let i = 0; i < lines.length; i++) {
                const l = lines[i];
                if (!l.startsWith('ATOM  ')) continue;
                const ch = l[21];
                const atomName = l.substring(12, 16).trim();
                const resi = parseInt(l.substring(22, 26), 10);
                const x = parseFloat(l.substring(30, 38));
                const y = parseFloat(l.substring(38, 46));
                const z = parseFloat(l.substring(46, 54));
                if (ch === 'A' && atomName === 'CA') {
                    caA.push({ resi, x, y, z });
                } else if (ch === 'B') {
                    if (resi < minResB) minResB = resi;
                    if (resi > maxResB) maxResB = resi;
                    if (atomName === 'CA') caB.push({ resi, x, y, z });
                }
            }

            // Determine the Cleavable Segment on Chain B: the 24 residues closest to Chain A (N-terminal face of Chain B)
            const totalResB = Math.max(1, maxResB - minResB + 1);
            const cutSpan = Math.min(26, Math.max(14, Math.floor(totalResB * 0.24)));
            const cutResThreshold = minResB + cutSpan;

            // Compute resting centroids of Chain A, Chain B (Main Yellow Body), and Chain C (Cleavable Segment of Yellow Part)
            let centroidA = { x: 0, y: 0, z: 0 };
            if (caA.length > 0) {
                caA.forEach(a => { centroidA.x += a.x; centroidA.y += a.y; centroidA.z += a.z; });
                centroidA.x /= caA.length; centroidA.y /= caA.length; centroidA.z /= caA.length;
            }

            let tipCa = caB.filter(b => b.resi <= cutResThreshold);
            let bodyCa = caB.filter(b => b.resi > cutResThreshold);
            if (tipCa.length === 0) tipCa = caB.slice(0, Math.min(15, caB.length));
            if (bodyCa.length === 0) bodyCa = caB;

            let tipOrigin = { x: 0, y: 0, z: 0 };
            tipCa.forEach(a => { tipOrigin.x += a.x; tipOrigin.y += a.y; tipOrigin.z += a.z; });
            if (tipCa.length > 0) { tipOrigin.x /= tipCa.length; tipOrigin.y /= tipCa.length; tipOrigin.z /= tipCa.length; }

            let bodyOrigin = { x: 0, y: 0, z: 0 };
            bodyCa.forEach(a => { bodyOrigin.x += a.x; bodyOrigin.y += a.y; bodyOrigin.z += a.z; });
            if (bodyCa.length > 0) { bodyOrigin.x /= bodyCa.length; bodyOrigin.y /= bodyCa.length; bodyOrigin.z /= bodyCa.length; }

            // Compute bridge landmarks in resting frame
            let bridgeA = caA.length > 0 ? caA[caA.length - 1] : centroidA;
            let bridgeB0 = caB.length > 0 ? caB[0] : bodyOrigin;
            let maxAx = -1e9, minBx = 1e9;
            caA.forEach(a => { if (a.x > maxAx) { maxAx = a.x; bridgeA = a; } });
            caB.forEach(b => { if (b.x < minBx) { minBx = b.x; bridgeB0 = b; } });

            // Compute 5 Real C-Alpha Structural Waypoints (W1..W5) along Chain A's backbone from Catalytic Triad (45%) -> C-terminal Sink (100%)
            // We average local 5-residue windows along Chain A and offset slightly toward the front surface (+z) so the path is 100% visible!
            const centerIdx = Math.floor(caA.length * 0.45);
            const waypointFracs = [0.45, 0.58, 0.72, 0.86, 0.98];
            let waypoints = waypointFracs.map((f, wIdx) => {
                if (caA.length === 0) return { x: 0, y: 0, z: 0, label: `W${wIdx + 1}` };
                let idx = Math.min(caA.length - 1, Math.max(0, Math.floor(caA.length * f)));
                let wStart = Math.max(0, idx - 2), wEnd = Math.min(caA.length - 1, idx + 2);
                let wx = 0, wy = 0, wz = 0, cnt = 0;
                for (let k = wStart; k <= wEnd; k++) {
                    wx += caA[k].x; wy += caA[k].y; wz += caA[k].z; cnt++;
                }
                wx /= cnt; wy /= cnt; wz /= cnt;
                // Offset 4.5 A toward the front (+z) and slightly outward from centroidA so the pathway sits clearly in the surface cleft
                return {
                    x: wx,
                    y: wy + (wIdx === 0 ? 1.5 : -1.5 * wIdx),
                    z: wz + 5.0,
                    resi: caA[idx].resi,
                    label: wIdx === 0 ? 'W1 (Triad Cut Site)' : (wIdx === 4 ? 'W5 (Phase 4 Sink)' : `W${wIdx + 1}`)
                };
            });

            const triadTarget = waypoints[0]; // W1: Exact Catalytic Triad Cleft
            const sinkTarget = waypoints[waypoints.length - 1]; // W5: Phase 4 Equilibrium Sink

            // Docking vector V_dock that brings Chain B's Cleavable Tip (tipOrigin) directly into W1 (triadTarget)
            const vDock = {
                x: triadTarget.x - tipOrigin.x,
                y: triadTarget.y - tipOrigin.y,
                z: triadTarget.z - tipOrigin.z
            };

            // Compute 4-State Displacement Shifts for Main Yellow Body (Chain B) and Cleavable Segment (Chain C):
            // - State 1 (0.00..0.28): Both Chain B & Chain C move together from 28 A station into Chain A's catalytic cleft
            // - State 2 (0.28..0.52): Fitted in catalytic jaws; scissile joint is locked & strained
            // - State 3 (0.52..0.76): BREAK! Chain C detaches at W1->W2; Chain B recoils back to its 28 A anchor station
            // - State 4 (0.76..1.00): Chain B rests at 28 A anchor station; Broken-off Chain C travels W2 -> W3 -> W4 -> W5 (Phase 4 Sink)
            let bodyShift = { x: 0, y: 0, z: 0 };
            let tipShift = { x: 0, y: 0, z: 0 };
            let isCut = prog >= 0.52;

            if (prog < 0.28) {
                let s = smoothStep01(prog / 0.28);
                bodyShift = { x: vDock.x * s, y: vDock.y * s, z: vDock.z * s };
                tipShift = { x: vDock.x * s, y: vDock.y * s, z: vDock.z * s };
            } else if (prog < 0.52) {
                let strain = smoothStep01((prog - 0.28) / 0.24) * 2.2;
                bodyShift = { x: vDock.x + strain, y: vDock.y, z: vDock.z };
                tipShift = { x: vDock.x - strain * 0.4, y: vDock.y, z: vDock.z };
            } else {
                // Chain B (Main Yellow Body) recoils back to its 28.0 A station during State 3 (0.52..0.76)
                let recoilFrac = 1.0 - smoothStep01(Math.min(1.0, (prog - 0.52) / 0.24));
                bodyShift = { x: vDock.x * recoilFrac, y: vDock.y * recoilFrac, z: vDock.z * recoilFrac };

                // Chain C (Broken-Off 3D Piece) travels along the 5 C-alpha waypoints W1 -> W2 -> W3 -> W4 -> W5
                let pathProgress = Math.min(1.0, Math.max(0.0, (prog - 0.52) / 0.48));
                let totalSegs = waypoints.length - 1;
                let segFloat = pathProgress * totalSegs;
                let segIdx = Math.min(totalSegs - 1, Math.floor(segFloat));
                let segFrac = smoothStep01(segFloat - segIdx);
                let wpA = waypoints[segIdx];
                let wpB = waypoints[segIdx + 1];
                let targetPos = {
                    x: wpA.x + (wpB.x - wpA.x) * segFrac,
                    y: wpA.y + (wpB.y - wpA.y) * segFrac,
                    z: wpA.z + (wpB.z - wpA.z) * segFrac
                };
                tipShift = {
                    x: targetPos.x - tipOrigin.x,
                    y: targetPos.y - tipOrigin.y,
                    z: targetPos.z - tipOrigin.z
                };
            }

            // Rewrite PDB lines so Chain C (the Cleavable 3D Segment) has chain ID 'C' and independent 3D coordinates!
            let outLines = [];
            let insertedTerForCut = false;
            for (let i = 0; i < lines.length; i++) {
                let l = lines[i];
                if (!l.startsWith('ATOM  ')) {
                    outLines.push(l);
                    continue;
                }
                const ch = l[21];
                if (ch !== 'B') {
                    outLines.push(l);
                    continue;
                }
                const resi = parseInt(l.substring(22, 26), 10);
                const x = parseFloat(l.substring(30, 38));
                const y = parseFloat(l.substring(38, 46));
                const z = parseFloat(l.substring(46, 54));

                if (resi <= cutResThreshold) {
                    // Cleavable 3D Segment -> assign to chain 'C' so we can style & break it independently!
                    let modLine = l.substring(0, 21) + 'C' + l.substring(22);
                    outLines.push(replacePdbCoords(modLine, x + tipShift.x, y + tipShift.y, z + tipShift.z));
                } else {
                    if (isCut && !insertedTerForCut) {
                        outLines.push('TER');
                        insertedTerForCut = true;
                    }
                    outLines.push(replacePdbCoords(l, x + bodyShift.x, y + bodyShift.y, z + bodyShift.z));
                }
            }

            return {
                pdb: outLines.join('\\n'),
                centerIdx,
                centroidA,
                bodyOrigin,
                tipOrigin,
                bodyCurrent: { x: bodyOrigin.x + bodyShift.x, y: bodyOrigin.y + bodyShift.y, z: bodyOrigin.z + bodyShift.z },
                tipCurrent: { x: tipOrigin.x + tipShift.x, y: tipOrigin.y + tipShift.y, z: tipOrigin.z + tipShift.z },
                bridgeA,
                bridgeB0,
                bridgeBCurrent: { x: bridgeB0.x + bodyShift.x, y: bridgeB0.y + bodyShift.y, z: bridgeB0.z + bodyShift.z },
                waypoints,
                triadTarget,
                sinkTarget,
                isCut
            };
        }

        function applyPhaseStyleToViewer(viewer, pdbText, phaseIdx, preserveCamera) {
            if (!viewer || !pdbText) return;
            let camState = preserveCamera ? viewer.getView() : null;
            viewer.clear();

            // In Phase 0, 2, 3, and 4, drive the 4-State Dynamic PDB using `cutProgress` (in Phase 1 keep resting 28A frame so Anchor GRAVY is inspected cleanly)
            let effectiveProg = (phaseIdx === 1) ? 0.0 : cutProgress;
            const dyn = buildDynamicStatePdbAndPath(pdbText, effectiveProg);
            let model = viewer.addModel(dyn.pdb, 'pdb');
            let atomsA = model.selectedAtoms({ chain: 'A', atom: 'CA' });
            const p = currentSwarmData ? currentSwarmData.preset : {};

            // Helper to render the Computed C-Alpha Trajectory (Approach Path + W1..W5 C-Alpha Channel) and State Callouts
            function renderComputedTrajectoryAndStates(showDetailedLabels) {
                // 1. Draw the Resting 28.0 A Reference Station of Chain B (so even as Yellow moves in, you see its 28A origin!)
                viewer.addSphere({
                    center: dyn.tipOrigin,
                    radius: 1.4,
                    color: '#fde047',
                    opacity: 0.45
                });
                // Dashed Approach Vector from Chain B's 28A Origin (tipOrigin) -> W1 Catalytic Triad (triadTarget)
                viewer.addCylinder({
                    start: dyn.tipOrigin,
                    end: dyn.triadTarget,
                    radius: 0.28,
                    color: '#fde047',
                    dashed: true,
                    fromCap: 1,
                    toCap: 1
                });

                // 2. Draw the Computed 5-Waypoint C-Alpha Structural Pathway (W1 -> W2 -> W3 -> W4 -> W5) across Chain A
                for (let w = 0; w < dyn.waypoints.length; w++) {
                    const wp = dyn.waypoints[w];
                    const isTriad = (w === 0);
                    const isSink = (w === dyn.waypoints.length - 1);
                    viewer.addSphere({
                        center: wp,
                        radius: isTriad ? 1.55 : (isSink ? 2.1 : 1.05),
                        color: isTriad ? '#fde047' : (isSink ? '#10b981' : '#f0abfc'),
                        opacity: isSink ? 0.65 : 0.90
                    });
                    if (w < dyn.waypoints.length - 1) {
                        const nextWp = dyn.waypoints[w + 1];
                        viewer.addCylinder({
                            start: wp,
                            end: nextWp,
                            radius: 0.38,
                            color: w < 2 ? '#f0abfc' : '#34d399',
                            dashed: false,
                            fromCap: 1,
                            toCap: 1
                        });
                    }
                }

                // 3. Draw the Scissile Joint / Break Flash between Chain B (Yellow Body) and Chain C (Cleavable 3D Segment)
                if (!dyn.isCut) {
                    // Intact Scissile Joint Collar connecting the Cleavable Segment (Chain C) to the Main Yellow Body (Chain B)
                    viewer.addCylinder({
                        start: dyn.tipCurrent,
                        end: dyn.bodyCurrent,
                        radius: 0.55,
                        color: '#fde047',
                        dashed: true
                    });
                    if (effectiveProg >= 0.26) {
                        // Glowing target ring at the exact Catalytic Triad cleavage point
                        viewer.addSphere({
                            center: dyn.tipCurrent,
                            radius: 2.2,
                            color: '#fb923c',
                            opacity: 0.55
                        });
                    }
                } else {
                    // Scission Flash at W1 + Recoil Vector showing Chain B returning to its 28A station
                    viewer.addSphere({
                        center: dyn.triadTarget,
                        radius: effectiveProg < 0.68 ? 1.85 : 1.0,
                        color: '#ff4d6d',
                        opacity: 0.85
                    });
                }

                // 4. Outer-Perimeter Non-Overlapping Callout Tags with Leader Lines
                if (showDetailedLabels) {
                    // Top-Right Callout: Yellow Structure (Chain B) Moving / Recoiling
                    let bLblPos = { x: dyn.bodyCurrent.x - 12.0, y: dyn.bodyCurrent.y + 14.5, z: dyn.bodyCurrent.z };
                    viewer.addCylinder({ start: dyn.bodyCurrent, end: bLblPos, radius: 0.18, color: '#fde047', dashed: true });
                    let bStateTxt = effectiveProg < 0.28
                        ? `🟡 STATE 1: Yellow Moves In & Fits`
                        : (effectiveProg < 0.52
                            ? `🟡 STATE 2: Fitted in Scissor Jaws`
                            : `🟡 STATE 3–4: Yellow Recoils (28 Å)`);
                    viewer.addLabel(bStateTxt, {
                        position: bLblPos,
                        backgroundColor: '#fde047', fontColor: '#020617', fontSize: 11, borderRadius: 6, padding: 4
                    });

                    // Top-Left Callout: The Cleavable 3D Segment (Chain C) That Breaks Off & Follows W1..W5
                    let cLblPos = { x: dyn.tipCurrent.x - 14.0, y: dyn.tipCurrent.y + 15.0, z: dyn.tipCurrent.z };
                    let cColor = effectiveProg > 0.88 ? '#4ade80' : (dyn.isCut ? '#fb7185' : '#fb923c');
                    viewer.addCylinder({ start: dyn.tipCurrent, end: cLblPos, radius: 0.20, color: cColor, dashed: true });
                    let cStateTxt = !dyn.isCut
                        ? `🟠 CLEAVABLE 3D TIP [S] (Fits in Triad)`
                        : (effectiveProg < 0.76
                            ? `✂️ BROKEN-OFF 3D PIECE [I] (Cut from Yellow!)`
                            : (effectiveProg <= 0.90
                                ? `🚀 SLIDING ALONG Cα PATH (W1→W5)`
                                : `✅ CAPTURED IN PHASE 4 SINK [P]`));
                    viewer.addLabel(cStateTxt, {
                        position: cLblPos,
                        backgroundColor: cColor, fontColor: '#020617', fontSize: 11, borderRadius: 6, padding: 4
                    });

                    // Bottom-Right Callout: Computed C-Alpha Trajectory Waypoints (W1 -> W5 Sink)
                    let sinkLblPos = { x: dyn.sinkTarget.x + 18.0, y: dyn.sinkTarget.y - 14.0, z: dyn.sinkTarget.z };
                    viewer.addCylinder({ start: dyn.sinkTarget, end: sinkLblPos, radius: 0.18, color: '#34d399', dashed: true });
                    viewer.addLabel(`🟣➔🟢 COMPUTED Cα PATH (W1→W5 Sink)`, {
                        position: sinkLblPos,
                        backgroundColor: '#065f46', fontColor: '#a7f3d0', fontSize: 11, borderRadius: 6, padding: 4
                    });
                }
            }

            // Style Chain C (the 24-residue Cleavable 3D Segment of the Yellow Structure) across all phases:
            // - Before cut (prog < 0.52): Bright Amber-Orange (#fb923c) with sticks so you see the exact part of the Yellow structure that will be broken!
            // - After cut (0.52..0.88): Bright Coral-Red (#ff4d6d) broken-off 3D piece sliding along W1..W5!
            // - At Sink (> 0.88): Bright Emerald Green (#4ade80) mineralized product!
            const cutPieceColor = effectiveProg > 0.88 ? '#4ade80' : (dyn.isCut ? '#ff4d6d' : '#fb923c');

            if (phaseIdx === 0) {
                viewer.setStyle({ chain: 'A' }, { cartoon: { color: '#67e8f9', opacity: 0.88, thickness: 0.42 } });
                viewer.setStyle({ chain: 'B' }, { cartoon: { color: '#fde047', opacity: 0.95, thickness: 0.44 }, stick: { radius: 0.20, color: '#facc15' } });
                viewer.setStyle({ chain: 'C' }, {
                    cartoon: { color: cutPieceColor, opacity: 1.0, thickness: 0.52 },
                    stick: { radius: 0.34, color: cutPieceColor }
                });
                renderComputedTrajectoryAndStates(true);
                if (!preserveCamera) {
                    viewer.zoomTo();
                    viewer.zoom(1.48);
                }
            } else if (phaseIdx === 1) {
                // Phase 1: Highlight Module 1 Anchor (Chain B + Cleavable Tip Chain C); keep Chain A bright and clearly visible!
                viewer.setStyle({ chain: 'A' }, {
                    cartoon: { color: '#bae6fd', opacity: 0.85, thickness: 0.40 },
                    stick: { radius: 0.14, color: '#38bdf8', opacity: 0.45 }
                });
                viewer.setStyle({ chain: 'B' }, {
                    cartoon: { color: '#fde047', opacity: 0.98, thickness: 0.48 },
                    stick: { radius: 0.28, color: '#f59e0b' }
                });
                viewer.setStyle({ chain: 'C' }, {
                    cartoon: { color: '#fb923c', opacity: 1.0, thickness: 0.52 },
                    stick: { radius: 0.34, color: '#fde047' }
                });
                viewer.addLabel(`🔷 REFERENCE: Chain A Scissor (${activeScissor ? activeScissor.id : 'M2'})`, {
                    position: { x: dyn.centroidA.x - 10.0, y: dyn.centroidA.y - 15.0, z: dyn.centroidA.z },
                    backgroundColor: '#0284c7', fontColor: '#f8fafc', fontSize: 11, borderRadius: 6, padding: 5
                });
                viewer.addLabel(`🎯 FOCUS · M1 Anchor + Cleavable Tip (${activeAnchor ? activeAnchor.id : 'Chain B'})`, {
                    position: { x: dyn.bodyOrigin.x + 2.0, y: dyn.bodyOrigin.y + 15.0, z: dyn.bodyOrigin.z },
                    backgroundColor: '#fde047', fontColor: '#020617', fontSize: 12, borderRadius: 6, padding: 5
                });
                if (!preserveCamera) {
                    viewer.zoomTo();
                    viewer.zoom(1.48);
                }
            } else if (phaseIdx === 2) {
                // Phase 2: Keep BOTH Chain A (Bright Cyan) and Chain B (Bright Yellow) 100% visible so motion across the 28.0 A bridge is easy to reference!
                viewer.setStyle({ chain: 'A' }, {
                    cartoon: { color: '#67e8f9', opacity: 0.92, thickness: 0.45 },
                    stick: { radius: 0.18, color: '#22d3ee', opacity: 0.55 }
                });
                viewer.setStyle({ chain: 'B' }, {
                    cartoon: { color: '#fde047', opacity: 0.96, thickness: 0.46 },
                    stick: { radius: 0.24, color: '#facc15', opacity: 0.75 }
                });
                viewer.setStyle({ chain: 'C' }, {
                    cartoon: { color: cutPieceColor, opacity: 1.0, thickness: 0.52 },
                    stick: { radius: 0.36, color: cutPieceColor }
                });
                // Highlight the 28.0 A Linker Bridge & Dynamic Span between Chain A and Chain B
                viewer.addSphere({ center: dyn.bridgeA, radius: 2.2, color: '#f0abfc' });
                viewer.addSphere({ center: dyn.bridgeBCurrent, radius: 2.2, color: '#f0abfc' });
                viewer.addCylinder({
                    start: dyn.bridgeA,
                    end: dyn.bridgeBCurrent,
                    radius: 0.72, color: '#f0abfc', dashed: false, fromCap: 1, toCap: 1
                });
                renderComputedTrajectoryAndStates(true);
                viewer.addLabel('🎯 FOCUS · 28.0 Å Linker Bridge & Hinged Delivery Motion', {
                    position: {
                        x: (dyn.bridgeA.x + dyn.bridgeB0.x) / 2.0,
                        y: (dyn.bridgeA.y + dyn.bridgeB0.y) / 2.0 - 15.0,
                        z: (dyn.bridgeA.z + dyn.bridgeB0.z) / 2.0
                    },
                    backgroundColor: '#f0abfc', fontColor: '#020617', fontSize: 11, borderRadius: 6, padding: 5
                });
                if (!preserveCamera) {
                    viewer.zoomTo();
                    viewer.zoom(1.48);
                }
            } else if (phaseIdx === 3) {
                // Phase 3: Both Chain A (Cyan Scissor) and Chain B (Yellow Carrier) are bright & visible;
                // Watch Chain B bring Chain C into Chain A's Gold Catalytic Triad, break off Chain C, and send it along W1->W5!
                viewer.setStyle({ chain: 'B' }, {
                    cartoon: { color: '#fde047', opacity: 0.92, thickness: 0.45 },
                    stick: { radius: 0.20, color: '#facc15', opacity: 0.65 }
                });
                viewer.setStyle({ chain: 'C' }, {
                    cartoon: { color: cutPieceColor, opacity: 1.0, thickness: 0.55 },
                    stick: { radius: 0.42, color: cutPieceColor },
                    sphere: { radius: 0.58, color: cutPieceColor, opacity: 0.85 }
                });

                // Outer Scaffold of Chain A: Bright Ice-Cyan (#67e8f9 at 0.78 opacity) so enzyme fold is vivid while keeping W1..W5 visible
                viewer.setStyle({ chain: 'A' }, { cartoon: { color: '#67e8f9', opacity: 0.78, thickness: 0.40 } });

                // Catalytic Pocket Lining + 3 Sharp Catalytic Triad Residues in Bright Gold (#fde047)
                if (atomsA.length > 10) {
                    let pocketResi = atomsA.slice(Math.max(0, dyn.centerIdx - 5), Math.min(atomsA.length, dyn.centerIdx + 6)).map(a => a.resi);
                    let triadResi = [
                        atomsA[Math.max(0, dyn.centerIdx - 2)].resi,
                        atomsA[dyn.centerIdx].resi,
                        atomsA[Math.min(atomsA.length - 1, dyn.centerIdx + 2)].resi
                    ];
                    viewer.setStyle({ chain: 'A', resi: pocketResi }, {
                        cartoon: { color: '#00f2fe', opacity: 0.98, thickness: 0.48 }
                    });
                    viewer.setStyle({ chain: 'A', resi: triadResi }, {
                        cartoon: { color: '#fde047', opacity: 1.0, thickness: 0.52 },
                        stick: { radius: 0.48, color: '#fde047' },
                        sphere: { radius: 0.75, color: '#f59e0b' }
                    });
                }

                // Highlight Phase 4 Sink destination at C-terminus (W5) in Emerald
                if (atomsA.length > 8) {
                    let sinkResi = atomsA.slice(Math.max(0, atomsA.length - 12)).map(a => a.resi);
                    viewer.setStyle({ chain: 'A', resi: sinkResi }, {
                        cartoon: { color: '#4ade80', opacity: 0.96, thickness: 0.48 }
                    });
                }

                renderComputedTrajectoryAndStates(true);

                // Bottom-Left Callout: Active Catalytic Triad Focus Label
                let focusLblPos = { x: dyn.centroidA.x - 24.0, y: dyn.centroidA.y - 14.5, z: dyn.centroidA.z };
                viewer.addCylinder({
                    start: dyn.triadTarget, end: focusLblPos,
                    radius: 0.18, color: '#fde047', dashed: true
                });
                viewer.addLabel(`🎯 FOCUS: Scissor Jaws (${activeScissor ? activeScissor.id : 'Chain A'})`, {
                    position: focusLblPos,
                    backgroundColor: '#fde047', fontColor: '#020617', fontSize: 11, borderRadius: 6, padding: 5
                });

                if (!preserveCamera) {
                    viewer.zoomTo();
                    viewer.zoom(1.48);
                }
            } else if (phaseIdx === 4) {
                // Phase 4: Highlight Module 3 Equilibrium Sink (W5) receiving the Broken-Off 3D Piece (Chain C) along the W1->W5 trajectory
                viewer.setStyle({ chain: 'B' }, {
                    cartoon: { color: '#fde047', opacity: 0.90, thickness: 0.44 },
                    stick: { radius: 0.18, color: '#facc15', opacity: 0.60 }
                });
                viewer.setStyle({ chain: 'C' }, {
                    cartoon: { color: cutPieceColor, opacity: 1.0, thickness: 0.55 },
                    stick: { radius: 0.42, color: cutPieceColor },
                    sphere: { radius: 0.62, color: cutPieceColor }
                });
                viewer.setStyle({ chain: 'A' }, { cartoon: { color: '#67e8f9', opacity: 0.75, thickness: 0.40 } });
                if (atomsA.length > 8) {
                    let sinkResi = atomsA.slice(Math.max(0, atomsA.length - 18)).map(a => a.resi);
                    viewer.setStyle({ chain: 'A', resi: sinkResi }, {
                        cartoon: { color: '#4ade80', opacity: 1.0, thickness: 0.50 },
                        stick: { radius: 0.38, color: '#22c55e' },
                        sphere: { radius: 0.80, color: '#86efac' }
                    });
                }
                renderComputedTrajectoryAndStates(true);
                viewer.addLabel('🎯 FOCUS: M3 Sink (W5) + M4 Beacon', {
                    position: { x: dyn.centroidA.x - 24.0, y: dyn.centroidA.y - 14.5, z: dyn.centroidA.z },
                    backgroundColor: '#4ade80', fontColor: '#020617', fontSize: 11, borderRadius: 6, padding: 5
                });
                if (!preserveCamera) {
                    viewer.zoomTo();
                    viewer.zoom(1.48);
                }
            }
            if (camState) {
                viewer.setView(camState);
            }
            viewer.render();
        }

        function renderPhaseWalkthrough() {
            const phases = getPhaseDefinitions();
            if (phases.length === 0) return;
            const active = phases[currentPhaseIdx] || phases[0];

            document.querySelectorAll('#inline-phase-stepper .phase-step-btn, #fs-phase-stepper .phase-step-btn').forEach(btn => {
                btn.classList.toggle('active-phase', Number(btn.dataset.phase) === currentPhaseIdx);
            });

            const inlineBanner = document.getElementById('inline-phase-desc');
            if (inlineBanner) {
                inlineBanner.style.borderLeftColor = active.color;
                inlineBanner.innerHTML = `<b style="color:${active.color};">${active.title}:</b> ${active.summary}`;
            }

            const fsBanner = document.getElementById('fs-active-banner');
            if (fsBanner) {
                fsBanner.style.borderLeftColor = active.color;
                fsBanner.innerHTML = `<b style="color:${active.color};font-size:0.86rem;">${active.title}</b> — <span style="color:#f8fafc;">${active.summary}</span>`;
            }

            const cardsContainer = document.getElementById('fs-phase-cards');
            if (cardsContainer) {
                cardsContainer.innerHTML = phases.map(p => {
                    const isActive = p.idx === currentPhaseIdx;
                    const badgeStyle = isActive
                        ? `background:${p.color};color:#020617;border:1px solid #ffffff;font-weight:800;font-size:0.72rem;padding:2px 9px;border-radius:999px;`
                        : `background:#1e293b;color:#e2e8f0;border:1px solid #64748b;font-weight:600;font-size:0.71rem;padding:2px 8px;border-radius:999px;`;
                    return `
                    <div class="fs-phase-card ${isActive ? 'active-card' : ''}"
                         style="border-left-color:${p.color};"
                         onclick="selectPipelinePhase(${p.idx})">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px;">
                            <span style="font-weight:800;font-size:0.86rem;color:${p.color};">${p.shortTitle}</span>
                            <span style="${badgeStyle}">${isActive ? '● ACTIVE IN 3D' : 'Click to Focus'}</span>
                        </div>
                        <div style="color:#f1f5f9;font-size:0.8rem;line-height:1.5;">${p.summary}</div>
                        <div style="margin-top:7px;padding:5px 9px;background:#020617;border:1px solid #334155;border-radius:5px;color:#67e8f9;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:0.74rem;font-weight:600;">
                            SQL: ${p.sqlFn}
                        </div>
                    </div>
                `}).join('');
            }
        }

        function selectPipelinePhase(phaseIdx) {
            currentPhaseIdx = phaseIdx;
            if (phaseIdx === 4 && cutProgress < 0.72) {
                cutProgress = 0.88;
            }
            updateCutControlsUI();
            renderPhaseWalkthrough();
            if (currentComplex3D) {
                applyPhaseStyleToViewer(molViewer, currentComplex3D.merged_pdb, currentPhaseIdx);
                if (fsDialog.open && fsMolViewer) {
                    applyPhaseStyleToViewer(fsMolViewer, currentComplex3D.merged_pdb, currentPhaseIdx);
                }
            }
        }

        function stepPhase(delta) {
            let nextIdx = (currentPhaseIdx + delta + 5) % 5;
            selectPipelinePhase(nextIdx);
        }

        function syncFullScreenViewer() {
            setTimeout(() => {
                let fsEl = document.getElementById('fs-mol-viewer');
                if (!fsMolViewer) {
                    fsMolViewer = $3Dmol.createViewer(fsEl, { backgroundColor: '#020617' });
                }
                fsMolViewer.resize();
                updateCutControlsUI();
                if (currentComplex3D) {
                    document.getElementById('fs-subtitle').textContent =
                        `Active Chimera: ${currentComplex3D.anchor_id} × ${currentComplex3D.scissor_id} | Cα: ${currentComplex3D.globular.ca_count} | pLDDT: ${currentComplex3D.globular.mean_plddt.toFixed(1)} | Rg: ${currentComplex3D.globular.radius_of_gyration.toFixed(1)} Å`;
                    applyPhaseStyleToViewer(fsMolViewer, currentComplex3D.merged_pdb, currentPhaseIdx);
                }
                renderPhaseWalkthrough();
            }, 60);
        }

        function toggleSpin3D() {
            isSpinning3D = !isSpinning3D;
            document.getElementById('btn-spin-3d').textContent = isSpinning3D ? '⏸ Pause Spin' : '↻ Spin 3D';
            if (molViewer) molViewer.spin(isSpinning3D ? 'y' : false);
            if (fsMolViewer) fsMolViewer.spin(isSpinning3D ? 'y' : false);
        }

        function reset3DCamera() {
            selectPipelinePhase(currentPhaseIdx);
        }

        function load3DComplex(anchorId, scissorId) {
            let pid = document.getElementById('pipeline-select').value;
            fetch(`/api/complex3d?anchor=${encodeURIComponent(anchorId)}&scissor=${encodeURIComponent(scissorId)}&pipeline=${encodeURIComponent(pid)}`)
                .then(r => r.json())
                .then(data => {
                    currentComplex3D = data;
                    document.getElementById('globular-badge').textContent =
                        `Cα: ${data.globular.ca_count} | pLDDT: ${data.globular.mean_plddt.toFixed(1)} | Rg: ${data.globular.radius_of_gyration.toFixed(1)} Å`;

                    const gInfo = evaluateGravyRange(activeAnchor.gravy);
                    const gPct = Math.max(0, Math.min(100, ((Number(activeAnchor.gravy) - (-1.0)) / (1.5 - (-1.0))) * 100));
                    const mw = Number(activeScissor.mw);
                    const pi = Number(activeScissor.pi);
                    const reactorPh = currentSwarmData ? Number(currentSwarmData.preset.ph) : 7.0;
                    const mwCls = mw <= 55 ? 'zone-optimal' : (mw <= 72 ? 'zone-warn' : 'zone-danger');
                    const mwTag = mw <= 55 ? 'COMPACT' : (mw <= 72 ? 'MODERATE' : 'BULKY');
                    const piDiff = Math.abs(pi - reactorPh);
                    const piCls = piDiff <= 1.8 ? 'zone-optimal' : 'zone-warn';
                    const compRatio = Number(data.globular.compactness_ratio);
                    const elon = Number(data.globular.elongation);
                    const compCls = compRatio <= 2.35 ? 'zone-optimal' : 'zone-warn';
                    const compTag = compRatio <= 1.65 ? 'COMPACT GLOBULE' : (compRatio <= 2.35 ? '2-DOMAIN CHIMERA' : 'EXTENDED');
                    const scissorMainCls = (mwCls === 'zone-optimal' && piCls === 'zone-optimal') ? 'zone-optimal' : (mwCls === 'zone-danger' ? 'zone-danger' : 'zone-warn');
                    const kcat2Val = Number(document.getElementById('sl-kcat2').value);
                    const kiVal = Number(document.getElementById('sl-ki').value);
                    const sinkZone = evaluateSliderZone(SLIDER_SPECS.kcat2, kcat2Val);
                    const rf = data.rangefinder || { mw_box: '[140, 355]', logp_box: '[0.8, 4.6]', tpsa_box: '[28, 92]', arom_prob: 0.86, props_matched: 7, ref_mw: 180.0, ref_logp: 1.8 };
                    const rfCls = rf.props_matched >= 7 ? 'zone-optimal' : (rf.props_matched >= 5 ? 'zone-warn' : 'zone-danger');

                    document.getElementById('pair-details').innerHTML =
                        `<div style="margin-bottom:5px;">` +
                            `<button type="button" class="param-label-btn ${gInfo.cls}" interestfor="tip-ledger-gravy" style="anchor-name: --anc-ledger-gravy;">M1 Surface Anchor &amp; GRAVY:</button> ` +
                            `<b style="color:#f59e0b">${anchorId}</b> <span style="color:#94a3b8;">(${activeAnchor.org})</span> ` +
                            `<button type="button" class="param-val-pill ${gInfo.cls}" interestfor="tip-ledger-gravy">${gInfo.signStr} · ${gInfo.tag}</button>` +
                            `<div style="font-size:0.69rem;color:#94a3b8;margin-top:2px;">` +
                                `GRAVY Scale: <span style="color:#fb7185;">&lt;−0.20 Weak</span> · <span style="color:#fbbf24;">−0.20..+0.25 Mod</span> · <span style="color:#34d399;">+0.25..+0.60 Good</span> · <span style="color:#34d399;font-weight:700;">≥+0.60 Elite</span>` +
                            `</div>` +
                        `</div>` +
                        `<div style="margin-bottom:5px;">` +
                            `<button type="button" class="param-label-btn ${scissorMainCls}" interestfor="tip-ledger-scissor" style="anchor-name: --anc-ledger-scissor;">M2 Primary Scissor:</button> ` +
                            `<b style="color:#38bdf8">${scissorId}</b> <span style="color:#94a3b8;">(${activeScissor.org})</span> ` +
                            `<button type="button" class="param-val-pill ${mwCls}" interestfor="tip-ledger-scissor">MW ${mw} kDa · ${mwTag}</button> ` +
                            `<button type="button" class="param-val-pill ${piCls}" interestfor="tip-ledger-scissor">pI ${pi} (pH ${reactorPh})</button>` +
                        `</div>` +
                        `<div style="margin-bottom:5px;">` +
                            `<button type="button" class="param-label-btn ${sinkZone.cls}" id="ledger-lbl-sink" interestfor="tip-thresh-kcat2">M3 Equilibrium Sink:</button> ` +
                            `<span id="ledger-val-sink">Drains intermediate below <i>K</i><sub>i</sub> (<b>${kiVal} µM</b>) at <i>k</i><sub>cat,2</sub> = <span class="param-val-pill ${sinkZone.cls}">${kcat2Val.toFixed(1)}/h · ${sinkZone.tag}</span></span>` +
                        `</div>` +
                        `<div style="margin-bottom:5px;">` +
                            `<button type="button" class="param-label-btn ${compCls}" interestfor="tip-ledger-globular" style="anchor-name: --anc-ledger-globular;">3D Globular Audit:</button> ` +
                            `<button type="button" class="param-val-pill ${compCls}" interestfor="tip-ledger-globular">Flory Ratio ${compRatio.toFixed(3)} · ${compTag}</button> ` +
                            `<span style="font-size:0.74rem;color:#cbd5e1;">Elongation <b>${elon.toFixed(2)}</b> (${data.elapsed_ms} ms)</span>` +
                        `</div>` +
                        `<div>` +
                            `<button type="button" class="param-label-btn ${rfCls}" interestfor="tip-ledger-rangefinder">RangeFinder 10 Å Pocket:</button> ` +
                            `<button type="button" class="param-val-pill ${rfCls}" interestfor="tip-ledger-rangefinder">MW ${rf.mw_box} Da · LogP ${rf.logp_box} · ${rf.props_matched}/8 GiST</button>` +
                        `</div>`;

                    const gravyTipEl = document.getElementById('ledger-tip-gravy-body');
                    if (gravyTipEl) {
                        gravyTipEl.innerHTML = `
                            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;">
                                <b style="color:#f8fafc;">What is M1 Surface Anchor GRAVY?</b>
                                <span style="color:${gInfo.color};font-weight:800;font-family:monospace;">${gInfo.signStr} (${gInfo.tag})</span>
                            </div>
                            <div style="font-size:0.72rem;font-weight:700;color:${gInfo.color};margin-bottom:4px;">${gInfo.title}</div>
                            <div style="color:#cbd5e1;font-size:0.73rem;margin-bottom:6px;">
                                <b>GRAVY</b> (<b>G</b>rand <b>A</b>verage of <b>Hy</b>dropathy) averages Kyte–Doolittle amino acid hydropathy values from <code>−4.5</code> (charged Arg) to <code>+4.5</code> (hydrophobic Ile) via PostgreSQL <code>gravy_score(seq)</code>.
                            </div>
                            <div style="position:relative;padding-bottom:10px;">
                                <div class="thresh-meter">
                                    <div style="background:#f43f5e;"></div>
                                    <div style="background:#f59e0b;"></div>
                                    <div style="background:#10b981;"></div>
                                </div>
                                <div style="position:absolute;left:calc(${gPct.toFixed(1)}% - 5px);top:10px;color:#fff;font-size:0.68rem;line-height:1;">▲</div>
                            </div>
                            <div class="thresh-legend">
                                <span style="color:#f43f5e;">&lt; −0.20 Weak</span>
                                <span style="color:#fbbf24;">−0.20..+0.25 Mod</span>
                                <span style="color:#10b981;">&gt; +0.25 Good / ≥ +0.60 Elite</span>
                            </div>
                            <div style="color:#e2e8f0;font-size:0.73rem;border-top:1px solid #1e293b;padding-top:5px;">${gInfo.verdict}</div>
                            <div class="formula-note">GRAVY = (1 / N) · Σ KyteDoolittle(AA<sub>i</sub>) &nbsp;→&nbsp; A<sub>boost</sub> = ${document.getElementById('sl-boost').value}×</div>
                        `;
                    }

                    const scissorTipEl = document.getElementById('ledger-tip-scissor-body');
                    if (scissorTipEl) {
                        scissorTipEl.innerHTML = `
                            <b style="color:#38bdf8;">M2 Primary Scissor Biophysical Thresholds (${scissorId})</b><br>
                            • <b>Molecular Weight (${mw} kDa):</b> <span style="color:#34d399;">🟢 18–55 kDa (Compact &amp; Fast Expression)</span> | <span style="color:#fbbf24;">🟡 55–75 kDa</span> | <span style="color:#fb7185;">🔴 &gt;75 kDa (Bulky)</span>.<br>
                            • <b>Isoelectric Point (pI ${pi} vs. Reactor pH ${reactorPh}):</b> ΔpH = <b>${piDiff.toFixed(2)}</b>. Matching enzyme pI near the operating pH regime maximizes Pareto catalytic stability.
                            <div class="formula-note">pH<sub>match</sub> = 1.0 − min(|pI − pH| / 4.5, 1.0)</div>
                        `;
                    }

                    const globTipEl = document.getElementById('ledger-tip-globular-body');
                    if (globTipEl) {
                        globTipEl.innerHTML = `
                            <b style="color:#38bdf8;">3D Flory Globular Compactness &amp; Elongation Audit</b><br>
                            Computed in Rust via <code>evaluate_globular_compactness(merged_pdb)</code>:<br>
                            • <b>Radius of Gyration (<i>R</i><sub>g</sub>):</b> <b>${data.globular.radius_of_gyration.toFixed(1)} Å</b> across <b>${data.globular.ca_count} Cα</b> atoms.<br>
                            • <b>Flory Compactness Ratio (${compRatio.toFixed(3)}):</b> Actual <i>R</i><sub>g</sub> divided by ideal single-domain sphere 2.25 · <i>N</i><sup>0.38</sup>.<br>
                            &nbsp;&nbsp;<span style="color:#34d399;">🟢 1.00–1.65 (Single Globule)</span> | <span style="color:#38bdf8;">🔵 1.65–2.35 (Expected 2-Domain Chimera with 28 Å Linker)</span> | <span style="color:#fb7185;">🔴 &gt;2.50 (Unfolded)</span>.
                            <div class="formula-note">Flory Ratio = R<sub>g</sub> / (2.25 · N<sub>Cα</sub><sup>0.38</sup>) = ${compRatio.toFixed(3)}</div>
                        `;
                    }

                    const rfTipEl = document.getElementById('ledger-tip-rangefinder-body');
                    if (rfTipEl) {
                        rfTipEl.innerHTML = `
                            <b style="color:#38bdf8;">RangeFinder 9-Property Pocket-Interval GiST Audit (${scissorId})</b><br>
                            Predicted in PostgreSQL 18 via <code>predict_pocket_ranges()</code> &amp; <code>pocket_numranges()</code> (<i>arXiv:2611.03379v1</i>):<br>
                            • <b>Predicted Ligand MW Interval:</b> <code>${rf.mw_box} Da</code> (Ref intermediate: <b>${rf.ref_mw} Da</b>).<br>
                            • <b>Predicted Ligand LogP Interval:</b> <code>${rf.logp_box}</code> (Ref LogP: <b>${rf.ref_logp}</b>) | <b>TPSA Box:</b> <code>${rf.tpsa_box} Å²</code>.<br>
                            • <b>Aromatic Ring Probability <i>P</i>(arom):</b> <b>${rf.arom_prob}</b> | <b>8-Column <code>numrange</code> GiST Containment:</b> <span style="color:#34d399;font-weight:700;">${rf.props_matched}/8 Intervals Matched</span>.
                            <div class="formula-note">I<sub>p</sub> = [μ<sub>p</sub> − 2|σ<sub>p</sub>|, μ<sub>p</sub> + 2|σ<sub>p</sub>|] &nbsp;→&nbsp; pocket_numranges(p) @&gt; compute_ligand_properties(smiles)</div>
                        `;
                    }

                    let el = document.getElementById('mol-viewer');
                    if (!molViewer) {
                        molViewer = $3Dmol.createViewer(el, { backgroundColor: '#020617' });
                    }
                    applyPhaseStyleToViewer(molViewer, data.merged_pdb, currentPhaseIdx);
                    if (fsDialog.open && fsMolViewer) {
                        applyPhaseStyleToViewer(fsMolViewer, data.merged_pdb, currentPhaseIdx);
                    }
                    renderPhaseWalkthrough();
                });
        }

        (function() {
            const urlParams = new URLSearchParams(window.location.search);
            const qPipe = urlParams.get('pipeline');
            const sel = document.getElementById('pipeline-select');
            if (qPipe && sel && Array.from(sel.options).some(o => o.value === qPipe)) {
                sel.value = qPipe;
            }
            updateCutControlsUI();
            startCutAnimationLoop();
            loadPipelineSwarm();
        })();
    </script>
</body>
</html>
"""


@app.route("/")
@app.route("/pipelines")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/swarm")
def api_swarm():
    pid = request.args.get("pipeline", "ptfe-to-bioceramic")
    if pid not in PIPELINE_PRESETS:
        pid = "ptfe-to-bioceramic"
    preset = PIPELINE_PRESETS[pid]

    t0 = time.perf_counter()
    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            # Sample 12 diverse anchors spanning the full hydropathy range so heatmap shows rich Pareto contrast
            cur.execute(
                """
                WITH ranked_a AS (
                    SELECT uniprot_id, organism_name,
                           ROUND(gravy_hydropathy::numeric, 3) AS gravy,
                           ROUND(shannon_entropy::numeric, 3) AS entropy,
                           NTILE(12) OVER (ORDER BY gravy_hydropathy DESC, shannon_entropy DESC) AS bucket
                    FROM bio_domain_atlas
                    WHERE pipeline_family = %s AND module_role = 'M1_Anchor'
                )
                SELECT DISTINCT ON (bucket) uniprot_id, organism_name, gravy, entropy
                FROM ranked_a
                ORDER BY bucket ASC, gravy DESC;
                """,
                (pid,),
            )
            anchors = [
                {"id": r[0], "org": r[1], "gravy": float(r[2]), "entropy": float(r[3])}
                for r in cur.fetchall()
            ]

            # Sample 16 diverse scissors spanning pI and MW
            cur.execute(
                """
                WITH ranked_s AS (
                    SELECT uniprot_id, organism_name,
                           ROUND(mw_kda::numeric, 1) AS mw,
                           ROUND(isoelectric_pi::numeric, 2) AS pi,
                           ROUND(shannon_entropy::numeric, 3) AS entropy,
                           NTILE(16) OVER (ORDER BY (uniprot_id = 'P80042') DESC, ABS(isoelectric_pi - %s) ASC, shannon_entropy DESC) AS bucket
                    FROM bio_domain_atlas
                    WHERE pipeline_family = %s AND module_role = 'M2_Scissor'
                      AND mw_kda BETWEEN 16.0 AND 75.0
                )
                SELECT DISTINCT ON (bucket) uniprot_id, organism_name, mw, pi, entropy
                FROM ranked_s
                ORDER BY bucket ASC, (uniprot_id = 'P80042') DESC, entropy DESC;
                """,
                (preset["ph"], pid),
            )
            scissors = [
                {"id": r[0], "org": r[1], "mw": float(r[2]), "pi": float(r[3]), "entropy": float(r[4])}
                for r in cur.fetchall()
            ]

            matrix_cells = []
            all_pairs = []
            scores = []
            for y_idx, a in enumerate(anchors):
                for x_idx, s in enumerate(scissors):
                    cur.execute(
                        "SELECT pareto_score_domain_pair(%s, %s, %s, %s, %s, %s);",
                        (a["gravy"], a["entropy"], s["mw"], s["pi"], s["entropy"], preset["ph"]),
                    )
                    score = round(float(cur.fetchone()[0]), 4)
                    scores.append(score)
                    matrix_cells.append([x_idx, y_idx, score])
                    all_pairs.append(
                        {
                            "anchor_id": a["id"],
                            "anchor_org": a["org"],
                            "anchor_gravy": a["gravy"],
                            "scissor_id": s["id"],
                            "scissor_org": s["org"],
                            "pareto_score": score,
                        }
                    )

            all_pairs.sort(key=lambda x: x["pareto_score"], reverse=True)
            top_pairs = all_pairs[:10]

            # Compute exact RK4 48h yield in PostgreSQL for each top-10 pair so table & KPI match 100%!
            for row in top_pairs:
                eff_boost = compute_effective_boost(preset["boost"], row["anchor_gravy"])
                cur.execute(
                    """
                    SELECT sink_product_u_m, fractional_conversion
                    FROM simulate_cascade_kinetics(%s, %s, %s, %s, %s, %s, 1000.0, 48.0, 48)
                    ORDER BY time_hr DESC
                    LIMIT 1;
                    """,
                    (
                        preset["kcat1"],
                        preset["km1"],
                        preset["kcat2"],
                        preset["km2"],
                        preset["ki"],
                        eff_boost,
                    ),
                )
                sink_um, frac_conv = cur.fetchone()
                row["yield_pct"] = round(float(frac_conv) * 100.0, 1)
                row["yield_um"] = int(round(float(sink_um)))
                row["effective_boost"] = eff_boost

            cur.execute(
                "SELECT * FROM optimize_consortium_stoichiometry(%s, %s, %s, 14.0, 18.0, 10.5, 48.0);",
                (preset["f1"], preset["f2"], preset["f3"]),
            )
            w1, w2, w3, conv, bal = cur.fetchone()

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    min_score = round(min(scores) if scores else 0.5, 3)
    max_score = round(max(scores) if scores else 1.0, 3)

    return jsonify(
        {
            "pipeline": pid,
            "preset": preset,
            "anchors": anchors,
            "scissors": scissors,
            "matrix_cells": matrix_cells,
            "min_score": min_score,
            "max_score": max_score,
            "top_pairs": top_pairs,
            "stoichiometry": {
                "w1": f"{w1:.2f}",
                "w2": f"{w2:.2f}",
                "w3": f"{w3:.2f}",
                "conv_pct": round(conv * 100.0, 1),
                "balance": round(bal, 4),
            },
            "elapsed_ms": elapsed_ms,
        }
    )


@app.route("/api/rk4")
def api_rk4():
    pid = request.args.get("pipeline", "ptfe-to-bioceramic")
    preset = PIPELINE_PRESETS.get(pid, PIPELINE_PRESETS["ptfe-to-bioceramic"])

    kcat1 = float(request.args.get("kcat1", preset["kcat1"]))
    km1 = float(request.args.get("km1", preset["km1"]))
    kcat2 = float(request.args.get("kcat2", preset["kcat2"]))
    ki = float(request.args.get("ki", preset["ki"]))
    boost = float(request.args.get("boost", preset["boost"]))
    km2 = preset["km2"]

    t0 = time.perf_counter()
    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT time_hr, substrate_u_m, intermediate_u_m, sink_product_u_m, fractional_conversion
                FROM simulate_cascade_kinetics(%s, %s, %s, %s, %s, %s, 1000.0, 48.0, 48)
                ORDER BY time_hr ASC;
                """,
                (kcat1, km1, kcat2, km2, ki, boost),
            )
            ws = cur.fetchall()

            cur.execute(
                """
                SELECT time_hr, substrate_u_m
                FROM simulate_cascade_kinetics(%s, %s, 0.0, %s, %s, %s, 1000.0, 48.0, 48)
                ORDER BY time_hr ASC;
                """,
                (kcat1, km1, km2, ki, boost),
            )
            ns = cur.fetchall()

            cur.execute(
                """
                SELECT time_hr, substrate_u_m
                FROM simulate_cascade_kinetics(%s, %s, 0.0, %s, %s, 1.0, 1000.0, 48.0, 48)
                ORDER BY time_hr ASC;
                """,
                (kcat1, km1, km2, ki),
            )
            wt = cur.fetchall()

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return jsonify(
        {
            "time_hr": [int(r[0]) for r in ws],
            "with_sink_sub": [round(r[1], 1) for r in ws],
            "with_sink_int": [round(r[2], 1) for r in ws],
            "with_sink_prod": [round(r[3], 1) for r in ws],
            "nosink_cleaved": [round(1000.0 - r[1], 1) for r in ns],
            "wt_cleaved": [round(1000.0 - r[1], 1) for r in wt],
            "sink_48h_pct": round(ws[-1][4] * 100.0, 1),
            "sink_48h_um": int(round(ws[-1][3])),
            "nosink_48h_pct": round((1000.0 - ns[-1][1]) / 10.0, 1),
            "elapsed_ms": elapsed_ms,
        }
    )


@app.route("/api/complex3d")
def api_complex3d():
    anchor_id = request.args.get("anchor", "P79073")
    scissor_id = request.args.get("scissor", "Q1JU72")
    pid = request.args.get("pipeline", "ptfe-to-bioceramic")
    preset = PIPELINE_PRESETS.get(pid, PIPELINE_PRESETS["ptfe-to-bioceramic"])
    ref_smiles = preset.get("ref_smiles", "OC(=O)c1ccc(C(=O)O)cc1")

    pdb_scissor = load_or_fallback_pdb(scissor_id, "scissor")
    pdb_anchor = load_or_fallback_pdb(anchor_id, "anchor")

    ca_pts = []
    for ln in pdb_scissor.splitlines():
        if ln.startswith("ATOM  ") and ln[12:16].strip() == "CA":
            try:
                ca_pts.append((float(ln[30:38]), float(ln[38:46]), float(ln[46:54])))
            except ValueError:
                pass
    if ca_pts:
        cx = round(sum(p[0] for p in ca_pts) / len(ca_pts), 3)
        cy = round(sum(p[1] for p in ca_pts) / len(ca_pts), 3)
        cz = round(sum(p[2] for p in ca_pts) / len(ca_pts), 3)
    else:
        cx, cy, cz = 0.0, 0.0, 0.0

    t0 = time.perf_counter()
    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH merged AS (
                    SELECT translate_and_merge_pdb_chains(%s, %s, 28.0) AS pdb_str
                ),
                pk AS (
                    SELECT predict_pocket_ranges(%s::text, %s::text, %s::float8, %s::float8, %s::float8, 10.0::float8) AS p
                ),
                lig AS (
                    SELECT r.* FROM compute_ligand_properties_row(%s::text) r
                )
                SELECT m.pdb_str,
                       evaluate_globular_compactness(m.pdb_str)::text,
                       ROUND(ib.mw_min::numeric, 0), ROUND(ib.mw_max::numeric, 0),
                       ROUND(ib.logp_min::numeric, 2), ROUND(ib.logp_max::numeric, 2),
                       ROUND(ib.tpsa_min::numeric, 1), ROUND(ib.tpsa_max::numeric, 1),
                       ROUND(ib.aromatic_probability::numeric, 3),
                       (
                           (CASE WHEN nr.mw_range @> lig.mw::numeric THEN 1 ELSE 0 END) +
                           (CASE WHEN nr.logp_range @> lig.logp::numeric THEN 1 ELSE 0 END) +
                           (CASE WHEN nr.hbd_range @> lig.hbd::numeric THEN 1 ELSE 0 END) +
                           (CASE WHEN nr.hba_range @> lig.hba::numeric THEN 1 ELSE 0 END) +
                           (CASE WHEN nr.tpsa_range @> lig.tpsa::numeric THEN 1 ELSE 0 END) +
                           (CASE WHEN nr.rot_range @> lig.rotatable_bonds::numeric THEN 1 ELSE 0 END) +
                           (CASE WHEN nr.arom_range @> lig.aromatic_rings::numeric THEN 1 ELSE 0 END) +
                           (CASE WHEN nr.fsp3_range @> lig.fsp3::numeric THEN 1 ELSE 0 END)
                       ) AS props_matched,
                       ROUND(lig.mw::numeric, 1), ROUND(lig.logp::numeric, 2)
                FROM merged m, pk, lig,
                     LATERAL pocket_interval_bounds(pk.p) ib,
                     LATERAL pocket_numranges(pk.p) nr;
                """,
                (pdb_scissor, pdb_anchor, scissor_id, pdb_scissor, cx, cy, cz, ref_smiles),
            )
            row = cur.fetchone()
            merged_pdb = row[0]
            glob_json = row[1]
            rf_summary = {
                "mw_box": f"[{int(row[2])}, {int(row[3])}]",
                "logp_box": f"[{row[4]}, {row[5]}]",
                "tpsa_box": f"[{row[6]}, {row[7]}]",
                "arom_prob": float(row[8]),
                "props_matched": int(row[9]),
                "ref_mw": float(row[10]),
                "ref_logp": float(row[11]),
            }

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return jsonify(
        {
            "anchor_id": anchor_id,
            "scissor_id": scissor_id,
            "merged_pdb": merged_pdb,
            "globular": json.loads(glob_json),
            "rangefinder": rf_summary,
            "elapsed_ms": elapsed_ms,
        }
    )


HYPOTHESIS_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>pg_bio × bio-pipelines — Autonomous Agent Hypotheses &amp; DUF Annotation Ledger</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; }
        body {
            margin: 0;
            background: #060a14;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.5;
        }
        .topbar {
            position: sticky;
            top: 0;
            z-index: 20;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            padding: 12px 24px;
            background: rgba(2, 6, 23, 0.96);
            border-bottom: 1px solid #1e293b;
        }
        .topbar h1 { margin: 0; font-size: 1.12rem; color: #c084fc; }
        .topbar .sub { font-size: 0.78rem; color: #94a3b8; }
        .nav-btns { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .btn {
            background: #0f172a;
            color: #38bdf8;
            border: 1px solid #38bdf8;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
        }
        .btn:hover { background: #38bdf8; color: #020617; }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px 24px 60px 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(200px, 1fr));
            gap: 14px;
        }
        @media (max-width: 1000px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
        .kpi-card {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 14px 16px;
        }
        .kpi-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; font-weight: 700; }
        .kpi-val { font-size: 1.5rem; font-weight: 800; font-family: ui-monospace, monospace; margin-top: 4px; color: #f8fafc; }
        .kpi-sub { font-size: 0.74rem; color: #34d399; margin-top: 2px; }
        .panel {
            background: #0b1324;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 16px 18px;
            overflow-x: auto;
        }
        .panel h2 { margin: 0 0 12px 0; font-size: 1.02rem; color: #38bdf8; }
        table { width: 100%; border-collapse: collapse; font-size: 0.81rem; }
        th, td { padding: 10px 12px; border-bottom: 1px solid #1e293b; text-align: left; vertical-align: top; }
        thead th { background: #020617; color: #94a3b8; font-size: 0.73rem; text-transform: uppercase; letter-spacing: 0.04em; }
        tbody tr:hover { background: rgba(56, 189, 248, 0.06); }
        .pill {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.71rem;
            font-weight: 700;
        }
        .pill-green { background: rgba(16, 185, 129, 0.16); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .pill-purple { background: rgba(192, 132, 252, 0.16); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.4); }
        .pill-amber { background: rgba(245, 158, 11, 0.16); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        a.kpi-card {
            display: block;
            text-decoration: none;
            color: inherit;
            transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
        }
        a.kpi-card:hover {
            transform: translateY(-2px);
            border-color: #38bdf8;
            box-shadow: 0 8px 24px rgba(56, 189, 248, 0.14);
        }
        a.metric-link {
            color: inherit;
            text-decoration: none;
            border-bottom: 1px dashed rgba(148, 163, 184, 0.45);
            transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
            border-radius: 3px;
            padding: 0 2px;
        }
        a.metric-link:hover {
            color: #38bdf8 !important;
            border-bottom-color: #38bdf8;
            background: rgba(56, 189, 248, 0.12);
        }
    </style>
</head>
<body>
    <header class="topbar">
        <div>
            <h1>🤖 pg_bio × bio-pipelines — Autonomous Agent Hypotheses &amp; Evolving DUF Annotation Ledger</h1>
            <div class="sub">Closed-loop validation between the 70.2M-edge <code>pg_bio</code> discovery graph and the 8-feedstock <code>bio-pipelines</code> RK4 digital twin · <b>Click any metric to inspect live items</b></div>
        </div>
        <div class="nav-btns">
            <a class="btn" href="/">← Back to 8-Feedstock RK4 Explorer</a>
            <a class="btn" style="border-color:#0ea5e9;color:#38bdf8;" href="/telemetry">📊 Unified Swarm &amp; Pipeline Telemetry</a>
            <a class="btn" style="border-color:#38bdf8;color:#7dd3fc;" href="/discovery">🛰️ Swarm Discovery Heatmap</a>
            <a class="btn" style="border-color:#10b981;color:#34d399;" href="/cards">🃏 1-to-N Card Arena</a>
            <a class="btn" style="border-color:#f59e0b;color:#fbbf24;" href="/compare">🔬 3D Compare Lab</a>
            <a class="btn" href="/hypotheses?format=json" target="_blank">{ } Raw JSON</a>
        </div>
    </header>
    <main class="container">
        <section class="kpi-grid">
            <a class="kpi-card" href="/telemetry" title="Click to open Unified Swarm & Pipeline Telemetry">
                <div class="kpi-label">Swarm Edges Scanned ↗</div>
                <div class="kpi-val" id="kpi-edges">--</div>
                <div class="kpi-sub" id="kpi-last-run">--</div>
            </a>
            <a class="kpi-card" href="#duf-panel" title="Click to jump to Evolving DUF / Orphan Annotations">
                <div class="kpi-label">Evolving DUF / Orphan Annotations ↓</div>
                <div class="kpi-val" id="kpi-anns" style="color:#38bdf8;">--</div>
                <div class="kpi-sub">Fold &amp; Length-Ratio Gated (TM &ge; 0.50)</div>
            </a>
            <a class="kpi-card" href="#hyp-panel" title="Click to jump to Validated Bio-Pipeline Hypotheses">
                <div class="kpi-label">Validated Bio-Pipeline Hypotheses ↓</div>
                <div class="kpi-val" id="kpi-hyps" style="color:#c084fc;">--</div>
                <div class="kpi-sub">Promoted to <code>bio_domain_atlas</code> &amp; New Scenarios</div>
            </a>
            <a class="kpi-card" href="/hypotheses?format=json" target="_blank" title="Click to inspect raw checkpoint & ledger JSON">
                <div class="kpi-label">Scheduled Agent Cadence ↗</div>
                <div class="kpi-val" style="color:#34d399;">Every 25 Waves + 30m</div>
                <div class="kpi-sub" id="kpi-cycles">In-Process Swarm Hook + Cron Active</div>
            </a>
        </section>

        <section class="panel" id="hyp-panel">
            <h2>1. Validated Bioprocess Hypotheses &amp; Promoted New Scenarios (<code>bio_hypothesis_ledger</code>)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Code &amp; Status</th>
                        <th>Target Pipeline &amp; Module</th>
                        <th>Discovery Pair (Candidate &times; Ref)</th>
                        <th>Hypothesis &amp; Biological Rationale</th>
                        <th>3D Fold Gate &amp; Pocket IoU</th>
                        <th>48h RK4 Yield (&Delta;)</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="hyp-tbody"></tbody>
            </table>
        </section>

        <section class="panel" id="duf-panel">
            <h2>2. Evolving Dark-Proteome (<code>DUF</code> / Uncharacterized) Functional Annotations (<code>bio_annotation_evolution</code>)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Orphan ID (Version)</th>
                        <th>Extremophile Organism</th>
                        <th>Original Annotation</th>
                        <th>Evolved Functional Annotation</th>
                        <th>Best Homolog Partner</th>
                        <th>Evidence (Edges / Genera)</th>
                        <th>3D TM / RMSD &amp; Pocket IoU</th>
                        <th>Gated Synergy</th>
                        <th>Inspect 3D</th>
                    </tr>
                </thead>
                <tbody id="ann-tbody"></tbody>
            </table>
        </section>
    </main>
    <script>
        fetch('/hypotheses?format=json')
            .then(r => r.json())
            .then(d => {
                const c = d.checkpoint || {};
                document.getElementById('kpi-edges').textContent = Number(c.last_scanned_edge_id || 0).toLocaleString();
                document.getElementById('kpi-last-run').textContent = `Last cycle: ${(c.last_run_at || '').slice(0, 19)}`;
                document.getElementById('kpi-anns').textContent = `${c.total_annotations_evolved || 0} Orphans`;
                document.getElementById('kpi-hyps').textContent = `${c.total_hypotheses_promoted || 0} Active`;
                document.getElementById('kpi-cycles').textContent = `${c.total_cycles_run || 1} Cycles Completed · Cron */30 * * * *`;

                document.getElementById('hyp-tbody').innerHTML = (d.hypotheses || []).map(h => {
                    const pillCls = h.is_new_scenario ? 'pill-amber' : 'pill-green';
                    const pipeLink = h.pipeline !== 'all-pipelines' ? `/?pipeline=${encodeURIComponent(h.pipeline)}` : '/';
                    const cmpLink = `/compare?node1=${encodeURIComponent(h.reference_homolog)}&node2=${encodeURIComponent(h.candidate_uniprot)}&preset=rangefinder`;
                    const structLink = `/compare?node1=${encodeURIComponent(h.reference_homolog)}&node2=${encodeURIComponent(h.candidate_uniprot)}&preset=structure`;
                    const cardLink = `/cards?hub=${encodeURIComponent(h.reference_homolog)}&challenger=${encodeURIComponent(h.candidate_uniprot)}`;
                    return `
                        <tr>
                            <td>
                                <a class="metric-link" href="${pipeLink}" title="Open ${h.code} in RK4 Explorer"><b style="color:#f8fafc;">${h.code}</b></a><br>
                                <span class="pill ${pillCls}">${h.status}</span>
                            </td>
                            <td>
                                <a class="metric-link" href="${pipeLink}" title="Launch ${h.pipeline} in 8-Feedstock RK4 Explorer"><b style="color:#38bdf8;">${h.pipeline}</b></a><br>
                                <span style="color:#94a3b8;font-size:0.74rem;">${h.module_role} · ${h.subtype}</span>
                            </td>
                            <td>
                                <a class="metric-link" href="${cmpLink}" title="Compare ${h.candidate_uniprot} × ${h.reference_homolog} in 3D Compare Lab"><b style="color:#34d399;">${h.candidate_uniprot}</b></a> (${h.candidate_organism})<br>
                                <a class="metric-link" href="${cardLink}" title="Inspect in 1-to-N Card Arena"><span style="color:#94a3b8;">&times; ${h.reference_homolog}</span></a>
                            </td>
                            <td style="max-width:460px;"><b style="color:#e2e8f0;">${h.title}</b><div style="color:#94a3b8;font-size:0.75rem;margin-top:3px;">${h.rationale}</div></td>
                            <td>
                                <a class="metric-link" href="${structLink}" title="Inspect 3D TM-Score & Kabsch RMSD"><b style="color:#38bdf8;">TM ${Number(h.tm_score).toFixed(3)} (${Number(h.core_rmsd_a).toFixed(2)} Å)</b></a><br>
                                <a class="metric-link" href="${cmpLink}" title="Inspect 10Å RangeFinder Pocket IoU"><span style="color:#34d399;">IoU ${(Number(h.rf_pocket_iou)*100).toFixed(1)}% (${h.gist_props_matched}/8 GiST)</span></a>
                            </td>
                            <td>
                                <a class="metric-link" href="${pipeLink}" title="Simulate 48h RK4 cascade in Bio-Pipelines">
                                    <b style="color:#34d399;font-size:0.92rem;">${Number(h.predicted_48h_yield_pct).toFixed(1)}%</b><br>
                                    <span style="color:#fbbf24;font-weight:700;">+${Number(h.yield_delta_pct).toFixed(1)}% vs base (${Number(h.baseline_48h_yield_pct).toFixed(1)}%)</span>
                                </a>
                            </td>
                            <td>
                                <div style="display:flex;gap:6px;flex-direction:column;">
                                    <a class="btn" style="padding:3px 8px;font-size:0.72rem;text-align:center;" href="${pipeLink}">⚡ Open in RK4 Twin</a>
                                    <a class="btn" style="padding:3px 8px;font-size:0.72rem;border-color:#10b981;color:#34d399;text-align:center;" href="${cmpLink}">🔬 3D Compare</a>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');

                document.getElementById('ann-tbody').innerHTML = (d.evolving_annotations || []).map(a => {
                    const pillCls = a.status === 'Promoted_To_Atlas' ? 'pill-green' : (a.status === '3D_Verified' ? 'pill-purple' : 'pill-amber');
                    const tmTxt = a.tm_score != null ? `TM ${Number(a.tm_score).toFixed(3)} (${Number(a.core_rmsd || 0).toFixed(2)} Å)` : 'Pending 3D';
                    const iouTxt = a.rf_range_iou != null ? `IoU ${(Number(a.rf_range_iou)*100).toFixed(1)}%` : '—';
                    const cmpLink = `/compare?node1=${encodeURIComponent(a.best_partner)}&node2=${encodeURIComponent(a.uniprot_id)}`;
                    const cardLink = `/cards?hub=${encodeURIComponent(a.best_partner)}&challenger=${encodeURIComponent(a.uniprot_id)}`;
                    return `
                        <tr>
                            <td>
                                <a class="metric-link" href="${cmpLink}" title="Inspect ${a.uniprot_id} in 3D Compare Lab"><b style="color:#38bdf8;">${a.uniprot_id}</b></a>
                                <span style="color:#94a3b8;">(v${a.version})</span><br>
                                <span class="pill ${pillCls}">${a.status}</span>
                            </td>
                            <td><a class="metric-link" href="/galaxy" title="Explore ${a.organism} in 3D Galaxy"><b>${a.organism}</b></a></td>
                            <td style="color:#94a3b8;">${a.original_annotation}</td>
                            <td>
                                <a class="metric-link" href="${cardLink}" title="Inspect evolved functional annotation in 1-to-N Card Arena"><b style="color:#34d399;">${a.evolved_annotation}</b></a><br>
                                <span style="color:#cbd5e1;font-size:0.73rem;">${a.family}</span>
                            </td>
                            <td>
                                <a class="metric-link" href="${cardLink}" title="Open ${a.best_partner} in 1-to-N Card Arena"><b style="color:#fbbf24;">${a.best_partner}</b></a><br>
                                <span style="color:#94a3b8;font-size:0.73rem;">${a.best_partner_org}</span>
                            </td>
                            <td>
                                <a class="metric-link" href="/discovery?limit=twilight-40" title="Inspect cross-genus twilight evidence"><b>${a.evidence_edges} edges</b> across <b>${a.distinct_genera} genera</b></a><br>
                                <a class="metric-link" href="${cmpLink}&preset=twilight" style="color:#94a3b8;font-size:0.73rem;">SW ${a.seq_identity_pct}% · Tw ${Number(a.twilight_score).toFixed(3)}</a>
                            </td>
                            <td>
                                <a class="metric-link" href="${cmpLink}&preset=structure" title="Inspect Kabsch 3D superposition"><b style="color:#38bdf8;">${tmTxt}</b></a><br>
                                <a class="metric-link" href="${cmpLink}&preset=rangefinder" title="Inspect 10Å RangeFinder pocket overlap"><span style="color:#34d399;">${iouTxt}</span></a>
                            </td>
                            <td><a class="metric-link" href="${cardLink}" title="Inspect Fold-Gated Synergy in 1-to-N Card Arena"><b style="color:#c084fc;font-size:0.9rem;">${(Number(a.gated_synergy_score)*100).toFixed(1)}%</b></a></td>
                            <td><a class="btn" style="padding:3px 8px;font-size:0.72rem;" href="${cmpLink}">🔬 3D Lab</a></td>
                        </tr>
                    `;
                }).join('');
            });
    </script>
</body>
</html>
"""


@app.route("/hypotheses")
@app.route("/api/hypotheses")
def api_hypotheses():
    wants_json = (
        request.args.get("format") == "json"
        or "application/json" in (request.headers.get("Accept") or "")
    )
    if not wants_json and request.path in ("/hypotheses", "/api/hypotheses"):
        return render_template_string(HYPOTHESIS_DASHBOARD_HTML)

    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT last_scanned_edge_id, total_cycles_run, total_annotations_evolved, total_hypotheses_promoted, last_run_at::text FROM bio_agent_checkpoint WHERE id = 1;")
            chk = cur.fetchone()
            cur.execute(
                """
                SELECT hypothesis_code, target_pipeline, is_new_scenario, module_role, subtype,
                       candidate_uniprot, candidate_organism, reference_homolog,
                       hypothesis_title, biological_rationale,
                       fold_gate_tm, core_rmsd_a, rf_pocket_iou, gist_props_matched,
                       gated_synergy_score, pareto_score,
                       baseline_48h_yield_pct, predicted_48h_yield_pct, yield_delta_pct, status
                FROM bio_hypothesis_ledger
                ORDER BY hypothesis_code ASC;
                """
            )
            hyps = [
                {
                    "code": r[0],
                    "pipeline": r[1],
                    "is_new_scenario": bool(r[2]),
                    "module_role": r[3],
                    "subtype": r[4],
                    "candidate_uniprot": r[5],
                    "candidate_organism": r[6],
                    "reference_homolog": r[7],
                    "title": r[8],
                    "rationale": r[9],
                    "tm_score": r[10],
                    "core_rmsd_a": r[11],
                    "rf_pocket_iou": r[12],
                    "gist_props_matched": r[13],
                    "gated_synergy_score": r[14],
                    "pareto_score": r[15],
                    "baseline_48h_yield_pct": r[16],
                    "predicted_48h_yield_pct": r[17],
                    "yield_delta_pct": r[18],
                    "status": r[19],
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT uniprot_id, organism_name, original_annotation, evolved_annotation,
                       inferred_ec_or_family, best_partner_uniprot, best_partner_organism,
                       evidence_edges_count, distinct_genera_count,
                       vector_distance, seq_identity_pct, twilight_score,
                       tm_score, core_rmsd, rf_range_iou, rf_score,
                       gated_synergy_score, evolution_version, status
                FROM bio_annotation_evolution
                ORDER BY (status = 'Promoted_To_Atlas') DESC, (rf_range_iou IS NOT NULL) DESC, gated_synergy_score DESC
                LIMIT 30;
                """
            )
            anns = [
                {
                    "uniprot_id": r[0],
                    "organism": r[1],
                    "original_annotation": r[2],
                    "evolved_annotation": r[3],
                    "family": r[4],
                    "best_partner": r[5],
                    "best_partner_org": r[6],
                    "evidence_edges": r[7],
                    "distinct_genera": r[8],
                    "vector_distance": r[9],
                    "seq_identity_pct": r[10],
                    "twilight_score": r[11],
                    "tm_score": r[12],
                    "core_rmsd": r[13],
                    "rf_range_iou": r[14],
                    "rf_score": r[15],
                    "gated_synergy_score": r[16],
                    "version": r[17],
                    "status": r[18],
                }
                for r in cur.fetchall()
            ]
    return jsonify(
        {
            "checkpoint": {
                "last_scanned_edge_id": chk[0] if chk else 0,
                "total_cycles_run": chk[1] if chk else 0,
                "total_annotations_evolved": chk[2] if chk else 0,
                "total_hypotheses_promoted": chk[3] if chk else 0,
                "last_run_at": chk[4] if chk else None,
            },
            "hypotheses": hyps,
            "evolving_annotations": anns,
        }
    )


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("SWARM_WEB_PORT", "8090"))
    app.run(host="127.0.0.1", port=port, debug=False)
