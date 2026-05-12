# HAML Demo: Working with HLA Antibody Data

Demo scripts for the [HAML specification](https://github.com/immunomath/haml) showing how to convert, analyze, and use HLA antibody data in a standardized format.

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
| 4 | `scripts/benchmark_pipeline.py` | **Benchmark cohort**: parse a multi-patient benchmark HAML file, apply NC-adaptive thresholds per assay, and compute antibody prevalence across the cohort |

Scripts 1–3 work on the synthetic single-patient data in `data/`. Script 4 requires `benchmark_all55.haml.xml`, a 55-case benchmark file available for download from [HLAbAssist.app](https://hlabassist.app) after login.

These scripts are intentionally simple. They demonstrate the HAML format, not production-grade clinical analysis. Real-world antibody interpretation involves cross-reactive group analysis, artifact detection, historical patterns, platform concordance, and eplet-level matching.

## Documentation

| Document | What It Covers |
|---|---|
| [`docs/extended_haml_schema.md`](docs/extended_haml_schema.md) | Extended HAML schema reference: every extension element (`<recipient-profile>`, `<donor-profile>`, `<interpretation-results>`, `<extended-bead-data>`), design rationale, multi-vendor assay splitting, and benchmark file structure |
| [`docs/column_mapping.md`](docs/column_mapping.md) | SAB CSV → HAML field mapping for One Lambda HLA Fusion and Werfen MATCH IT formats; raw-MFI vs adjusted-mfi distinction; NC/PC encoding; kit metadata; HLA typing |
| [`docs/hlabassist_workflow.md`](docs/hlabassist_workflow.md) | End-to-end workflow: how HLAbAssist moves from raw SAB CSV through HAML to algorithm results, covering both the single-patient web UI path and the benchmark batch path |

## Quick Start

**Requirements:** Python 3.10+, lxml, pandas, matplotlib, ipykernel (for notebooks)

```bash
git clone https://github.com/VMWM/haml-demo.git
cd haml-demo
python3 -m venv .venv
source .venv/bin/activate
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

### 4. Analyze the Benchmark Cohort (requires login at HLAbAssist.app)

Download `benchmark_all55.haml.xml` from [HLAbAssist.app](https://hlabassist.app), then:

```bash
python scripts/benchmark_pipeline.py haml/benchmark_all55.haml.xml
python scripts/benchmark_pipeline.py haml/benchmark_all55.haml.xml --case-detail --current-only
```

The file contains 55 benchmark cases (61 HAML patient entries: 56 current + 5 historic timepoint entries) drawn from ASHI proficiency testing materials. The pipeline applies an NC-adaptive MFI threshold to each assay and computes antibody prevalence by HLA locus across the cohort.

## Interactive Notebooks

| Notebook | What It Demonstrates |
|---|---|
| [`notebooks/haml_demo.ipynb`](notebooks/haml_demo.ipynb) | Core HAML workflow: convert a CSV, analyze MFI values, run a simple VXM |
| [`notebooks/benchmark_conversion.ipynb`](notebooks/benchmark_conversion.ipynb) | How the ASHI Consensus Benchmark (55 cases) was converted to a multi-patient Extended HAML file: vendor suffixes, multi-assay splitting, historic timepoints |
| [`notebooks/user_upload_conversion.ipynb`](notebooks/user_upload_conversion.ipynb) | How HLAbAssist converts a user-uploaded SAB CSV to Extended HAML in the browser: PHI detection, pseudo-ID assignment, recipient/donor typing, HAML assembly |

```bash
jupyter notebook notebooks/haml_demo.ipynb
jupyter notebook notebooks/benchmark_conversion.ipynb
jupyter notebook notebooks/user_upload_conversion.ipynb
```


## Schema

This demo targets **HAML 0.5.3** (`schema/haml__version_0_5_3.xsd`), the current version of the specification maintained at [github.com/immunomath/haml](https://github.com/immunomath/haml). Key features:

- Bead-based solid phase assay support (SAB, screening panels)
- Multiple adjusted MFI calculations and interpretations per bead
- Assay kit metadata (manufacturer, lot, catalog, software)
- XSD validation for structural correctness

HLAbAssist extends HAML 0.5.3 with a non-namespaced `<extended-haml>` wrapper that adds
four sibling elements to the standard `<haml>` root: `<recipient-profile>` (patient HLA
typing for self-antigen exclusion), `<donor-profile>` (donor HLA typing for DSA and VXM),
`<interpretation-results>` (algorithm output), and `<extended-bead-data>` at the bead
level (vendor-specific ratio values and raw instrument counts). Plain HAML 0.5.3 files are
also accepted. See [`docs/extended_haml_schema.md`](docs/extended_haml_schema.md) for the
full schema reference.

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
│   ├── simple_vxm.py           # DSA identification + VXM prediction
│   └── benchmark_pipeline.py   # Multi-patient cohort analysis (requires benchmark download)
├── notebooks/
│   ├── haml_demo.ipynb                 # Core HAML walkthrough
│   ├── benchmark_conversion.ipynb      # Benchmark → multi-patient Extended HAML
│   └── user_upload_conversion.ipynb    # User CSV → Extended HAML (PHI scrubbing)
├── schema/
│   └── haml__version_0_5_3.xsd # HAML XML Schema Definition
├── data/
│   ├── sample_sab_class1.csv   # Synthetic Class I SAB data
│   ├── sample_sab_class2.csv   # Synthetic Class II SAB data
│   └── sample_donor_typing.txt # Donor HLA typing for VXM demo
├── docs/
│   ├── extended_haml_schema.md     # Extended HAML schema reference
│   ├── column_mapping.md           # SAB CSV → HAML field mapping (One Lambda + Werfen)
│   └── hlabassist_workflow.md      # End-to-end workflow: CSV → HAML → algorithm → results
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
