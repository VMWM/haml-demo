# HLAbAssist HAML Workflow: End-to-End

This document explains how HAML moves through HLAbAssist from raw SAB data to
algorithm results — covering both the single-patient web UI path and the
benchmark batch path. It is the reference for understanding what the algorithm
receives, what it returns, and how the public haml-demo scripts relate to the
production system.

---

## Overview

HAML is the data format at the center of every HLAbAssist analysis. There are
two paths into the algorithm:

```
Path 1 (web UI):
  User uploads SAB CSV → browser builds HAML → POST to API → algorithm → annotated HAML returned

Path 2 (benchmark batch):
  Assembled benchmark CSVs → convert_benchmark_to_haml.py → benchmark_all55.haml.xml → algorithm
```

Both paths produce the same Extended HAML format as input; the algorithm is
input-format agnostic once HAML is parsed.

---

## Path 1: Single-patient web UI (Convert Wizard)

### Step 1 — Upload CSV

The user uploads one or two SAB CSV files (Class I + Class II) in One Lambda
HLA Fusion or Werfen MATCH IT! format. The browser reads the file; nothing is
sent to the server yet.

### Step 2 — PHI scrubbing (browser-side)

`haml-converter.js` (browser JavaScript) inspects every column name against a
PHI blacklist. Columns matching patterns like `patient_name`, `dob`, `mrn`,
`ssn`, `accession`, `ws_caseno` are dropped. Vendor-specific non-PHI columns
(Werfen ratio values, panel identifiers) are preserved as `<extended-bead-data>`
attributes.

This converts the privacy claim from attestation ("I de-identified it") to an
architectural property: the server physically cannot receive PHI through this
path.

### Step 3 — Pseudo ID and typing entry

The Convert Wizard (4-step modal in the React UI) prompts the user for:

- **Pseudo ID** — a non-PHI identifier for the patient (e.g., `PT-2026-001`).
  This becomes the `patient-id` in the HAML file.
- **Recipient HLA typing** — the patient's own HLA alleles, used by the
  algorithm to exclude self-antigens. Accepted as free text
  (`A*02:01, B*07:02, DRB1*04:01`), a HistoTrac haplotype-row CSV, or a
  PLString. Optional; omitting it disables self-antigen exclusion.
- **Donor HLA typing** — the donor's alleles, used for DSA identification and
  virtual crossmatch prediction. Accepted in the same formats. Optional; omitting
  it disables DSA and VXM stages.

### Step 4 — HAML assembly (browser-side)

`haml-converter.js` assembles an Extended HAML file in memory:

```xml
<extended-haml version="1.0">
  <haml xmlns="urn:HAML.Namespace" version="0.5.3">
    <patient>
      <patient-id>PT-2026-001</patient-id>
      <sample>
        <working-sample>
          <assay>
            <assay-kit>
              <kit-manufacturer>One Lambda</kit-manufacturer>
              <lot-number>013</lot-number>
              ...
            </assay-kit>
            <!-- NC bead -->
            <target-bead-observation>
              <bead-info><bead-id>0</bead-id><bead-type>negative-control</bead-type></bead-info>
              <bead-raw-data><raw-MFI>31</raw-MFI></bead-raw-data>
            </target-bead-observation>
            <!-- Target beads -->
            <target-bead-observation>
              <bead-info>
                <bead-id>3</bead-id>
                <bead-type>target</bead-type>
                <HLA-target-type>A*02:01</HLA-target-type>
              </bead-info>
              <bead-raw-data><raw-MFI>5420</raw-MFI><bead-count>100</bead-count></bead-raw-data>
              <extended-bead-data ratio-adj="0.82" result-id="RUN_001"/>
            </target-bead-observation>
            ...
          </assay>
        </working-sample>
      </sample>
    </patient>
  </haml>
  <recipient-profile format="molecular">
    <alleles>A*01:01, A*24:02, B*07:02, B*44:02, DRB1*04:01, DRB1*15:01</alleles>
  </recipient-profile>
  <donor-profile format="molecular">
    <alleles>A*02:01, A*24:02, B*44:02, B*57:01, DRB1*04:01, DRB1*07:01</alleles>
  </donor-profile>
</extended-haml>
```

### Step 5 — POST to API

The assembled HAML is submitted to the HLAbAssist API:

```
POST /api/haml/analyze
Content-Type: multipart/form-data
  haml_file: [Extended HAML XML file]
```

No CSV ever reaches the server through this path — only the de-identified HAML.

### Step 6 — Server-side parsing and algorithm execution

`ExtendedHAMLParser` (Python, `utilities/extended_haml.py`) reads the HAML and
reconstructs the data structures the algorithm expects:

```python
parser = ExtendedHAMLParser()
parsed = parser.parse("patient.haml.xml")

sab_df        = parsed["sab_df"]         # DataFrame: Specificity, NormalValue, NC, PC, vendor, ...
recipient_hla = parsed["recipient_hla"]  # ["A*01:01", "A*24:02", ...]
donor_hla     = parsed["donor_hla"]      # ["A*02:01", "A*24:02", ...]
```

The three-stage algorithm then runs:

1. **`interpret_sab(sab_df, px_id, recipient_hla_list)`** — antibody detection,
   self-antigen exclusion, CREG and artifact analysis, temporal classification
   (current vs historic antibodies)
2. **`identify_dsa(antibodies, donor_hla)`** — donor-specific antibody
   identification using OPTN equivalency groups and HATS cross-reactivity tables
3. **`predict_vxm(antibodies, donor_hla)`** — virtual crossmatch prediction
   (T-cell and B-cell flow cytometry crossmatch)

### Step 7 — Annotated HAML output

`write_results_to_haml()` attaches the algorithm results as an
`<interpretation-results>` element to the original HAML:

```xml
<interpretation-results>
  <algorithm name="HLAbAssist" version="..." run-timestamp="2026-05-09T12:00:00Z"/>
  <reference-data>
    <imgt-hla version="3.64.0"/>
    <optn-splits n-broad-groups="21"/>
  </reference-data>
  <summary>
    <antibodies-detected>3</antibodies-detected>
    <current-dsa>1</current-dsa>
  </summary>
  <vxm-prediction>
    <t-cell-fcxm>negative</t-cell-fcxm>
    <b-cell-fcxm>positive</b-cell-fcxm>
  </vxm-prediction>
  <unique-antibodies>
    <antibody specificity="A*02:01" mfi="5420" confidence="high"
              is-dsa="true" temporal-category="current">
      <evidence-score>0.85</evidence-score>
      <rules-applied>
        <rule>RULE_MFI_THRESHOLD_001</rule>
        <rule>RULE_DSA_TIER2_001</rule>
      </rules-applied>
    </antibody>
  </unique-antibodies>
</interpretation-results>
```

This annotated HAML is the archival record: it carries the raw bead data, the
typing context, and the algorithm's full reasoning in one file.

---

## Path 2: Benchmark batch conversion

The benchmark conversion is a one-time script that transforms the assembled
benchmark CSV files (One Lambda + Werfen per case, multi-timepoint) into a
single multi-patient HAML file for download and external evaluation.

### Source data

The benchmark CSVs live in `Research/Aim1_Benchmark/benchmark_distribution/`:

```
ac_survey_benchmark/sab/     → 40 AC survey sera (per-serum CSV files)
vxm_benchmark/sab/           → 15 VXM cases (per-case CSV files, current + historic)
```

Each CSV uses the normalized column schema: `Specificity`, `NormalValue` (BCM),
`RawMFI`, `NegativeControl`, `PositiveControl`, `vendor`, `Description`.

### Conversion script

`Research/Aim1_Benchmark/code/build/convert_benchmark_to_haml.py` reads all
per-case CSV files and builds `benchmark_all55.haml.xml`:

```
55 benchmark cases → 61 HAML patient entries
  - 5 VXM cases with historic timepoints → 2 patient entries each (_historic suffix)
  - 2 VXM cases with One Lambda + Werfen → 2 patient entries each (_ol / _im suffix)
  - Remaining cases → 1 patient entry each
```

Key design decisions in the converter:

1. **Historic timepoints as sibling patients** — each timepoint is a separate
   `<patient>` element, not a nested `<working-sample>`. This makes single-timepoint
   parsing simpler at the cost of requiring grouping logic for multi-timepoint cases.

2. **NormalValue → raw-MFI** — following the IHIW haml-converter.js convention,
   the background-corrected MFI (NormalValue/BCM) goes into `<raw-MFI>`. The
   truly raw Luminex count (`RawMFI`) is stored as `raw-MFI-unprocessed` in
   `<extended-bead-data>`.

3. **Multi-platform per assay** — One Lambda Class I and Class II beads are
   combined into a single `<assay>` element (two passes of beads, one NC/PC pair
   per pass). Werfen beads for the same case get their own `<patient>` entry.

### Output

`benchmark_all55.haml.xml` (~6.7 MB) is distributed through HLAbAssist.app
(login required). It is the input to `scripts/benchmark_pipeline.py` in this
repository.

---

## How haml-demo scripts relate to production

| haml-demo script | Production equivalent |
|---|---|
| `csv_to_haml.py` | `haml-converter.js` (browser-side, single patient) |
| `haml_analyzer.py` | First stage of `ExtendedHAMLParser` + `interpret_sab()` |
| `simple_vxm.py` | `identify_dsa()` + `predict_vxm()` (simplified) |
| `benchmark_pipeline.py` | Batch read of `benchmark_all55.haml.xml` via `ExtendedHAMLParser` |

The haml-demo scripts are intentionally simplified: they demonstrate the HAML
format and data flow without the clinical knowledge base (OPTN equivalency
tables, HATS serotype groups, eplet registry, CREG rules) that the production
algorithm requires.

---

## API reference (HLAbAssist server)

| Endpoint | Input | Output |
|---|---|---|
| `POST /api/haml/analyze` | Extended HAML file | Interpretation JSON + annotated HAML |
| `POST /api/haml/parse` | Extended HAML file | Structured JSON (no algorithm run) |
| `POST /api/haml/interpret` | Extended HAML file | Interpretation JSON |
| `POST /api/patient/interpret` | CSV or HAML + form fields (px_id, typing) | Antibody profile JSON |
| `POST /api/patient/identify-dsa` | CSV or HAML + form fields | Antibody + DSA JSON |
| `POST /api/patient/predict-vxm` | CSV or HAML + form fields | Full VXM prediction JSON |

The `/api/patient/*` endpoints accept both CSV and HAML via `_load_sab()`
auto-detection: if the uploaded file parses as XML with a `<haml>` or
`<extended-haml>` root, it routes through `ExtendedHAMLParser`; otherwise it
routes through `_read_csv_upload()`.

---

## Related resources

- [`docs/column_mapping.md`](column_mapping.md) — SAB CSV column → HAML field mapping
- [Research_Manual Ch. 21](https://github.com/VMWM/Anti-HLA_Research) — full I/O contract, PHI scrubber architecture, Werfen round-trip fidelity
- [HAML specification](https://github.com/immunomath/haml) — schema source (immunomath/haml)
- [IHIW Converters](https://github.com/IHIW/Converters) — production-grade One Lambda and Werfen converters
- [HLAbAssist.app](https://hlabassist.app) — live tool + benchmark download
