# SAB CSV to HAML Column Mapping

This document explains how single antigen bead (SAB) assay data maps into
HAML 0.5.3 XML structure, including kit metadata, control beads, adjusted MFI
values, and HLA typing.

The mapping covers two common vendor export formats: **One Lambda HLA Fusion**
and **Werfen (Immucor) MATCH IT**. Both produce bead-level MFI tables with
vendor-specific column names; HAML normalizes them into a common structure.

---

## HAML document hierarchy (quick reference)

```
haml
└── patient
    ├── patient-id           ← Sample identifier
    └── sample
        └── working-sample
            ├── treatment    ← Dilution / heat inactivation / EDTA treatment
            └── assay
                ├── assay-kit            ← Kit metadata (lot, catalog, manufacturer)
                ├── control-serum [×2]   ← NC and PC serum identifiers
                └── target-bead-observation [×N]
                    ├── bead-info        ← Bead ID, type, HLA specificity
                    ├── bead-raw-data    ← Raw or adjusted MFI, bead count
                    └── bead-adjusted-data [optional]  ← BCM / normalized MFI
```

HLA typing (recipient or donor) lives in an optional `diagnostic-report`
element attached to the `patient`:

```
patient
├── patient-id
├── sample ...
└── diagnostic-report
    └── tissue-type    ← Recipient HLA typing as PLString
```

---

## One Lambda HLA Fusion CSV

One Lambda exports two files per run — Class I and Class II — with this column
structure:

| CSV column | HAML element | Notes |
|---|---|---|
| `Sample ID` | `patient > patient-id` | Also used for `sample-id` |
| `Bead ID` | `bead-info > bead-id` | Integer; 1 = NC bead, 2 = PC bead in Fusion |
| `Specificity` | `bead-info > HLA-target-type` | Allele-level (`A*02:01`) or serologic (`A2`) |
| `Raw Value` | `bead-raw-data > raw-MFI` | Truly raw Luminex count |
| `BCM` | `bead-adjusted-data > adjusted-mfi` | Background-corrected MFI (see note below) |
| `Bead Count` | `bead-raw-data > bead-count` | Events counted per bead |
| `Ranking` | `bead-adjusted-data > adjusted-data-id` | Optional; Fusion-specific ranking |
| Lot number (CSV header) | `assay-kit > lot-number` | In header rows, not data rows |
| Catalog number (CSV header) | `assay-kit > catalog-number` | In header rows, not data rows |

**Control beads** are bead-type rows, not separate files. Map them as:

| Fusion bead | `bead-type` value |
|---|---|
| Bead ID 1 (blank bead) | `negative-control` |
| Bead ID 2 (PC bead) | `positive-control` |
| All others | `target` |

---

## Werfen (Immucor) MATCH IT CSV

Werfen exports a single file per run with Class I and Class II beads combined.
Column names differ from One Lambda:

| CSV column | HAML element | Notes |
|---|---|---|
| `px_id` / patient column | `patient > patient-id` | |
| `Specificity` | `bead-info > HLA-target-type` | Same format as One Lambda |
| `RawData` | `bead-raw-data > raw-MFI` | Truly raw Luminex count |
| `NormalValue` | `bead-adjusted-data > adjusted-mfi` | Background-corrected (equivalent to BCM) |
| `NegativeControl` | NC bead `bead-raw-data > raw-MFI` | Per-row value; use first valid row per panel |
| `PositiveControl` | PC bead `bead-raw-data > raw-MFI` | Per-row value; use first valid row per panel |
| `Description` | `assay-kit > kit-description` | Encodes lot and catalog in one string |
| `BeadID` | `bead-info > bead-id` | 1 = NC, 2 = PC in Werfen convention |

---

## The raw-MFI vs adjusted-mfi distinction

This is the most common source of confusion when consuming HAML files.

**Strictly correct mapping** (schema intent):
- `bead-raw-data > raw-MFI` = raw Luminex photon count, before any background subtraction
- `bead-adjusted-data > adjusted-mfi` = BCM / NormalValue after background subtraction

**Common practice** (IHIW converters and haml-converter.js):
- `bead-raw-data > raw-MFI` = the background-corrected value (BCM / NormalValue)
- The truly raw count is either omitted or stored in `extended-bead-data`

The HLAbAssist benchmark file (`benchmark_all55.haml.xml`) follows the common
practice: `raw-MFI` holds NormalValue (background-adjusted), and where present,
`extended-bead-data` carries the unprocessed `RawData` as an attribute.

**Practical recommendation:** when reading HAML files, check whether the NC bead
`raw-MFI` is in the 20–100 range (background-corrected convention) or the
200–2000 range (truly raw). Confirm with the file's producer which convention
they used.

---

## NC and PC encoding

Control beads are emitted as separate `target-bead-observation` elements with
`bead-type` = `negative-control` or `positive-control`. Their `raw-MFI` holds
the control MFI value used for adaptive threshold calculation.

Per-assay NC value (used as the adaptive threshold floor):
```
effective_threshold = max(fixed_threshold, NC_MFI × 10)
```

If a vendor stores NC/PC values as per-row columns (Werfen `NegativeControl`,
`PositiveControl`) rather than dedicated bead rows (One Lambda), take the first
valid value from any bead row in that panel — all rows share the same NC/PC for
a given run.

---

## Kit metadata

The `assay-kit` element captures provenance fields that are essential for
reproducibility:

| `assay-kit` child | Content | Where to find it |
|---|---|---|
| `assay-type` | `"Single Antigen Bead"` | Fixed string |
| `catalog-number` | Kit catalog number | One Lambda CSV header; Werfen `Description` field |
| `lot-number` | Kit lot number | One Lambda CSV header; Werfen `Description` field |
| `kit-manufacturer` | `"One Lambda"` or `"Werfen / Immucor"` | Detected from file format |
| `interpretation-software` | `"HLA Fusion"` or `"MATCH IT"` | Fixed per vendor |
| `interpretation-software-version` | Software version | CSV header when present |
| `raw-MFI-divider` | Instrument calibration constant | Optional; relevant for multi-machine labs |

One Lambda embeds lot and catalog in header rows above the data (typically
rows 1–8 in a Fusion export). Werfen encodes them together in the `Description`
column (e.g., `"LABScreen™ Single Antigen HLA Class I - Combi, Lot 013"`).

---

## HLA typing (recipient and donor)

The 0.5.3 schema encodes HLA typing as a **PLString** (HLA Phenotype List
String; see [plstring.org](https://plstring.org/)). PLString is a compact
notation that encodes multi-locus HLA typing in a single string.

**Recipient (patient) typing** attaches to `patient > diagnostic-report >
tissue-type`:

```xml
<diagnostic-report>
  <report-id>DR-001</report-id>
  <tissue-type>HLA-A*02:01+HLA-A*24:02^HLA-B*07:02+HLA-B*44:02^HLA-DRB1*04:01+HLA-DRB1*07:01</tissue-type>
</diagnostic-report>
```

**Donor typing** is not a first-class field in HAML 0.5.3. In practice, donor
typing is supplied to the analysis algorithm separately (as a companion file or
API parameter). The bead panel itself encodes the antigen specificity of each
bead in `HLA-target-type` — so the algorithm performs donor-specific antibody
identification by comparing positive beads against a supplied donor HLA list,
not from data embedded in the HAML file itself.

The `diagnostic-report > patient-antibody-profile` element is available for
storing the interpretation output (identified specificities, DSA list,
crossmatch prediction) after algorithm analysis — making HAML a complete
round-trip format from raw beads to clinical interpretation.

---

## Multi-platform cases

When both One Lambda and Werfen data are available for the same patient, the
HAML convention used in the HLAbAssist benchmark is to create **separate patient
entries** per platform, with a platform suffix in the patient-id:

```
patient-id: ac_566_ol   → One Lambda assay
patient-id: ac_566_im   → Werfen / Immucor assay
```

An alternative is to encode both platforms as separate `assay` elements within
the same `working-sample`. Both conventions are valid; the separate-patient
approach simplifies single-platform parsing while the nested approach keeps all
data for one patient under one `patient` element.

---

## Multi-timepoint cases

Historic and current sera are encoded as separate `patient` entries with a
timepoint suffix:

```
patient-id: case_04_historic   → serum drawn before sensitizing event
patient-id: case_04            → current serum (at evaluation)
```

Code consuming multi-timepoint HAML should group entries by stripping `_historic`
(and platform suffixes like `_ol`, `_im`) to reconstruct the case-level view.
See `scripts/benchmark_pipeline.py` for a worked example.

---

## References

- [HAML specification](https://github.com/immunomath/haml) — schema source
- [IHIW Converters](https://github.com/IHIW/Converters) — production-grade One Lambda and Werfen converters
- [PLString](https://plstring.org/) — HLA Phenotype List String notation
- [HLAbAssist.app](https://hlabassist.app) — benchmark download (login required)
