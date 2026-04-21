# HAML Demo: Working with HLA Antibody Data

Demo scripts for the [HAML 1.0 specification](https://github.com/immunomath/haml) showing how to convert, analyze, and use HLA antibody data in a standardized format.

## Background

Every transplant center in the US uses single antigen bead (SAB) assays to test transplant patients for HLA antibodies. The results, mean fluorescence intensity (MFI) values for ~100 beads per panel, determine whether a patient can safely receive a given donor organ. But the raw data comes out in vendor-specific CSV formats that differ between manufacturers (One Lambda/Thermo Fisher, Werfen/Immucor) and laboratory information systems. There is no standard way to share, compare, or reuse this data across institutions or software tools.

**HAML** (HLA Antibody Markup Language) solves this by providing a single, vendor-neutral XML format for SAB assay results. A laboratory converts its data once (CSV to HAML), and any downstream tool can consume it: analysis algorithms, clinical decision support, multi-center research databases, or quality assurance platforms.

HAML was developed by the [IHIW](https://www.ihiw.org/) Clinical Histocompatibility Laboratory Informatics Working Group and is maintained at [github.com/immunomath/haml](https://github.com/immunomath/haml).

## What's in This Repo

This repository contains three standalone Python scripts and an interactive notebook that demonstrate the core HAML workflow:

| | Script | What It Does |
|---|--------|-------------|
| 1 | `scripts/csv_to_haml.py` | **Convert** a One Lambda Fusion SAB CSV export to validated HAML XML |
| 2 | `scripts/haml_analyzer.py` | **Analyze** a HAML file: apply an MFI threshold, classify beads as positive/borderline/negative, summarize by HLA locus |
| 3 | `scripts/simple_vxm.py` | **Virtual Crossmatch**: given a HAML file and donor HLA typing, identify donor-specific antibodies (DSA) and predict crossmatch compatibility |

These scripts are intentionally simple. They demonstrate the HAML format, not production-grade clinical analysis. Real-world antibody interpretation involves cross-reactive group analysis, artifact detection, historical patterns, platform concordance, and eplet-level matching.

## Quick Start

**Requirements:** Python 3.10+, lxml, pandas, matplotlib

```bash
git clone https://github.com/VMWM/haml-demo.git
cd haml-demo
pip install -r requirements.txt
```

### 1. Convert CSV to HAML

```bash
python scripts/csv_to_haml.py data/sample_sab_class1.csv -o output/demo.haml.xml --validate
```

This reads a One Lambda Fusion CSV export, builds a HAML XML document, and validates it against the HAML XSD schema. Output:

```
Read 89 beads from data/sample_sab_class1.csv
Wrote HAML XML to output/demo.haml.xml
Validation: PASSED
```

### 2. Analyze the HAML File

```bash
python scripts/haml_analyzer.py output/demo.haml.xml --threshold 2000
```

Applies a 2,000 MFI threshold to classify each bead. Output includes positive beads, borderline beads, and a summary by HLA locus.

### 3. Run a Simple Virtual Crossmatch

```bash
cd scripts
python simple_vxm.py ../output/demo.haml.xml ../data/sample_donor_typing.txt
```

Compares the patient's positive antibodies against a donor's HLA typing to identify DSA and predict VXM compatibility. Supports exact matching and heterodimer chain matching for DQ/DP beads.

## Interactive Notebook

For a guided walkthrough with narrative, visualizations, and both Class I + Class II data:

```bash
jupyter notebook notebooks/haml_demo.ipynb
```

A Quarto version is also available in `quarto/index.qmd` for manuscript-quality rendering:

```bash
cd quarto
quarto render index.qmd
open _output/index.html
```

## Schema

This demo targets the **HAML 0.6.1 draft schema** (`schema/haml__version_0_6_1.xsd`), which will become HAML 1.0 upon publication. Key features of this version:

- Bead-based solid phase assay support (SAB, screening panels)
- Cell-based assay support (flow crossmatch, CDC) -- new in 0.6.1
- Multiple adjusted MFI calculations and interpretations per bead
- Assay kit metadata (manufacturer, lot, catalog, software)
- XSD validation for structural correctness

## Sample Data

All data in `data/` is **synthetic** and does not represent real patients. The sample includes:

- **Class I panel** (97 target beads + NC + PC = 99 rows): HLA-A, B, C with 9 positive, 3 borderline, 85 negative beads
- **Class II panel** (94 target beads + NC + PC = 96 rows): HLA-DR, DQ, DP with 7 positive (5 DR4 + 2 DQ)
- **Donor typing** (14 alleles): Creates 5 DSA matches across both classes

## Repository Structure

```
haml-demo/
├── scripts/
│   ├── csv_to_haml.py          # CSV → HAML converter with XSD validation
│   ├── haml_analyzer.py        # HAML parser + MFI threshold classifier
│   └── simple_vxm.py           # DSA identification + VXM prediction
├── notebooks/
│   └── haml_demo.ipynb         # Interactive Jupyter walkthrough
├── quarto/
│   ├── index.qmd               # Quarto manuscript document
│   └── _quarto.yml             # Quarto project config
├── schema/
│   └── haml__version_0_6_1.xsd # HAML XML Schema Definition
├── data/
│   ├── sample_sab_class1.csv   # Synthetic Class I SAB data
│   ├── sample_sab_class2.csv   # Synthetic Class II SAB data
│   └── sample_donor_typing.txt # Donor HLA typing for VXM demo
├── output/                     # Generated HAML XML (gitignored)
├── requirements.txt
└── README.md
```

## Authors

- **Vanessa W. Menard** -- Tulane University School of Medicine
- **Loren Gragert, PhD** -- Tulane University School of Medicine
- **Eric Spierings, PhD** -- University Medical Center Utrecht
- **Ben Matern, PhD** -- National Marrow Donor Program

## Related Projects

- [HAML Specification](https://github.com/immunomath/haml) -- XML schema and documentation
- [IHIW Converters](https://github.com/IHIW/Converters) -- Production-grade HAML converters for the IHIW database
- [PLString](https://plstring.org/) -- HLA Phenotype List String notation used in HAML

## License

MIT
