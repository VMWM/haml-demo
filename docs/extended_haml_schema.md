# Extended HAML Schema Reference

HLAbAssist extends HAML 0.5.3 to carry information that the base schema does not
accommodate: recipient and donor HLA typing, multi-vendor bead data with
instrument-native ratio values, and algorithm interpretation results. This document
describes every extension, its rationale, and the design decisions behind it.

## Standards context

The HAML specification positions HLA antibody data exchange on the antibody side of
immunogenetics, occupying the same role that HML occupies on the genotype side.
HML is the transport format for HLA genotyping results (NGS allele data, GL strings,
allele ambiguity); HAML is the transport format for antibody assay observations and
their interpretation. The two standards are complementary and intentionally separate.

The extensions described here are additions to the antibody side of that division,
not to the genotype side. `<recipient-profile>` and `<donor-profile>` carry the
minimal HLA typing context needed for antibody interpretation: self-antigen exclusion
and donor-specific antibody identification. This is interpretation input, not a
genotyping report. It belongs in HAML, not HML.

HAML 1.0 introduces a structured report header for patient, sample, and laboratory
metadata required by accreditation frameworks (EFI, ASHI). That header is
administrative provenance. Our typing extensions serve a different purpose: they
provide the algorithmic context required to produce a clinically meaningful antibody
interpretation from raw bead data. The two are distinct layers.

`<donor-profile>` in particular addresses a gap the HAML 1.0 manuscript identifies
explicitly: flow crossmatch and virtual crossmatch support are an active extension
pathway in the current specification. The donor typing required to evaluate a virtual
crossmatch against a specific potential donor is not yet formally defined in the
schema. HLAbAssist is a production use case demonstrating what that extension needs
to contain.

This is a real-world production schema. HLAbAssist uses it in two contexts:

1. **Single-patient web UI** — the browser assembles Extended HAML from a user-uploaded
   SAB CSV file and HLA typing, then POSTs it to the server. No raw CSV ever reaches
   the server; HAML is the only transport format.

2. **Benchmark distribution** — the ASHI Consensus Benchmark (55 cases: 40 antibody
   identification + 15 virtual crossmatch) is distributed as a single multi-patient
   Extended HAML file (`hlabassist_benchmark.haml.xml`, ~6.7 MB). External evaluators
   can run any algorithm against the same standardized input.

---

## Document conventions

Elements are written as `<element>`, attributes as `attr="value"`.
Elements marked **[HAML 0.5.3]** are standard; elements marked **[Extension]** are
HLAbAssist additions. The namespace `xmlns="urn:HAML.Namespace"` applies to all HAML
0.5.3 elements; extension elements carry no namespace.

---

## Root structure

```xml
<extended-haml version="1.0" created="2026-05-12T08:22:15Z">

  <haml xmlns="urn:HAML.Namespace" version="0.5.3">
    <!-- standard HAML content: one <patient> per entry -->
  </haml>

  <recipient-profile format="molecular">          <!-- [Extension] -->
    <alleles>A*01:01, A*24:02, B*07:02, B*44:02, DRB1*04:01, DRB1*15:01</alleles>
  </recipient-profile>

  <donor-profile format="molecular">              <!-- [Extension, optional] -->
    <alleles>A*02:01, A*24:02, B*44:02, B*57:01, DRB1*04:01, DRB1*07:01</alleles>
  </donor-profile>

  <interpretation-results>                        <!-- [Extension, optional] -->
    ...
  </interpretation-results>

</extended-haml>
```

The `<extended-haml>` root is intentionally **not namespaced**. Standard HAML
parsers that expect a `<haml>` root will not recognize this file, but the inner
`<haml>` element is 100% schema-valid HAML 0.5.3. A plain HAML 0.5.3 file (no
wrapper) is also accepted by `ExtendedHAMLParser` for backward compatibility.

---

## `<extended-haml>` [Extension]

Root wrapper. Attributes:

| Attribute | Type | Required | Description |
|---|---|---|---|
| `version` | string | Yes | Extended HAML schema version. Currently `"1.0"`. |
| `created` | ISO 8601 datetime | No | File creation timestamp (UTC). |

---

## Standard HAML 0.5.3 content (`<haml>`)

HLAbAssist follows the HAML 0.5.3 hierarchy:

```
<haml>
  <patient>
    <patient-id>PT-2026-001</patient-id>
    <sample>
      <working-sample>
        <assay>
          <assay-kit>...</assay-kit>
          <target-bead-observation>...</target-bead-observation>  <!-- NC bead -->
          <target-bead-observation>...</target-bead-observation>  <!-- target beads -->
          ...
        </assay>
      </working-sample>
    </sample>
  </patient>
</haml>
```

### `<patient-id>` [HAML 0.5.3]

In the web UI path this is a user-supplied pseudo-ID (e.g., `PT-2026-001`). In the
benchmark file it is a case identifier with optional vendor suffixes:

| Suffix | Platform |
|---|---|
| `_ol` or `_onelambda` | One Lambda (LABScreen) |
| `_im` or `_werfen` | Werfen (LIFECODES) |
| `_historic` | Historic timepoint from the same patient |

Example: `AC-540_ol` = One Lambda data for antibody case AC-540.

The suffixes allow multi-vendor cases to be split into separate `<patient>` entries
while preserving their shared case identity. The benchmark pipeline groups them back
by stripping the suffix before algorithm execution.

### Multi-vendor assay splitting

One `<assay>` element is created per **(vendor × NC-group)** combination, not per
locus class or per panel. This preserves per-panel NC values through the HAML
round-trip.

**Why this matters:** Class I and Class II panels have different negative control
beads. If both classes were merged into one `<assay>` with a single NC bead, the
algorithm could not apply per-class adaptive thresholds. Keeping them as separate
assays within the same `<working-sample>` makes the NC grouping explicit.

```xml
<working-sample>
  <assay>   <!-- One Lambda Class I -->
    <assay-kit><kit-manufacturer>One Lambda</kit-manufacturer>...</assay-kit>
    <target-bead-observation><!-- NC bead --></target-bead-observation>
    <target-bead-observation><!-- Class I target beads --></target-bead-observation>
    ...
  </assay>
  <assay>   <!-- One Lambda Class II -->
    <assay-kit><kit-manufacturer>One Lambda</kit-manufacturer>...</assay-kit>
    <target-bead-observation><!-- NC bead --></target-bead-observation>
    <target-bead-observation><!-- Class II target beads --></target-bead-observation>
    ...
  </assay>
</working-sample>
```

### Control beads as `<target-bead-observation>` [HAML 0.5.3]

Negative and positive control beads are stored as standard `<target-bead-observation>`
elements, distinguished by `<bead-type>`:

```xml
<!-- Negative control -->
<target-bead-observation>
  <bead-info>
    <bead-id>0</bead-id>
    <bead-type>negative-control</bead-type>
  </bead-info>
  <bead-raw-data><raw-MFI>31</raw-MFI></bead-raw-data>
</target-bead-observation>

<!-- Positive control -->
<target-bead-observation>
  <bead-info>
    <bead-id>1</bead-id>
    <bead-type>positive-control</bead-type>
  </bead-info>
  <bead-raw-data><raw-MFI>18420</raw-MFI></bead-raw-data>
</target-bead-observation>
```

The positive control value is stored for provenance but is not used in the adaptive
threshold calculation; only the negative control drives the per-panel NC floor.

### MFI field convention

`<raw-MFI>` in the HAML schema carries the **background-corrected (normalized) MFI**,
not the Luminex instrument raw count. This follows the IHIW HAML converter convention.
The field name was chosen to avoid confusion with MFI values that have had additional
processing (normalization to a lot standard, ratio-based correction).

The truly raw instrument value is stored in `<extended-bead-data raw-MFI-unprocessed="..."/>`.

---

## `<extended-bead-data>` [Extension]

Child element of `<target-bead-observation>`. Carries non-schema bead fields as
attributes so they survive the HAML round-trip without polluting the standard
`<bead-raw-data>` element.

```xml
<target-bead-observation>
  <bead-info>
    <bead-id>3</bead-id>
    <bead-type>target</bead-type>
    <HLA-target-type>A*02:01</HLA-target-type>
  </bead-info>
  <bead-raw-data>
    <raw-MFI>5420</raw-MFI>
    <bead-count>100</bead-count>
  </bead-raw-data>
  <extended-bead-data
    raw-MFI-unprocessed="6104"
    ratio-adj="0.82"
    ratio-cut="3.0"
    mfi-cut="1500"
    assay-name="LSA1v07"
    result-id="RUN_2026_001"/>
</target-bead-observation>
```

Standard attributes written by HLAbAssist:

| Attribute | Source platform | Description |
|---|---|---|
| `raw-MFI-unprocessed` | Both | Luminex instrument raw count before background correction |
| `ratio-adj` | Werfen | BEAD_MFI_RATIO_ADJ — instrument-computed MFI/LRA normalization ratio |
| `ratio-cut` | Werfen | BEAD_MFI_RATIO_CUT — lot-specific cutoff ratio from recording sheet |
| `mfi-cut` | Werfen | BEAD_MFI_VALUE_CUT — per-bead threshold as configured in MATCH IT! |
| `assay-name` | Werfen | WS_ASSAY — panel name (e.g., `LSA1v07`) |
| `result-id` | Werfen | RESULT_ID — HistoTrac run/panel identifier |

Any non-PHI column not recognized as a standard field is also preserved as an
attribute with a lowercase-hyphenated name. This makes the format extensible
without schema changes.

**PHI stripping:** The browser-side converter (`haml-converter.js`) inspects every
CSV column name against a PHI pattern list before writing `<extended-bead-data>`.
Columns matching `patient_name`, `dob`, `mrn`, `ssn`, `accession`, `ws_caseno`,
and related patterns are dropped entirely. This is an architectural property of the
conversion, not a post-hoc scrubbing step: by the time HAML is assembled the PHI
columns no longer exist.

---

## `<recipient-profile>` [Extension]

HLA typing for the patient whose antibody profile is being analyzed. Sibling of `<haml>`.

```xml
<recipient-profile format="molecular">
  <alleles>A*01:01, A*24:02, B*07:02, B*44:02, DRB1*04:01, DRB1*15:01</alleles>
</recipient-profile>
```

| Attribute | Values | Description |
|---|---|---|
| `format` | `molecular` \| `serologic` | Typing resolution. Molecular: allele-level (e.g., `A*02:01`). Serologic: antigen-level (e.g., `A2`). |

The algorithm uses recipient typing to exclude self-antigens from the antibody list.
When `format="serologic"`, typing is expanded to allele groups via OPTN equivalency
before self-antigen evaluation. Omitting this element disables self-antigen exclusion.

---

## `<donor-profile>` [Extension, optional]

HLA typing for the potential donor. Same structure as `<recipient-profile>`.

```xml
<donor-profile format="molecular">
  <alleles>A*02:01, A*24:02, B*44:02, B*57:01, DRB1*04:01, DRB1*07:01</alleles>
</donor-profile>
```

Omitting this element disables DSA identification and virtual crossmatch prediction.
When present, the algorithm identifies donor-specific antibodies and predicts T-cell
and B-cell flow cytometry crossmatch results.

In the benchmark file, donor typing is present only for VXM cases (the 15 virtual
crossmatch cases). The 40 antibody identification cases have no donor typing.

---

## `<interpretation-results>` [Extension, optional]

Algorithm output attached to the HAML file after analysis. Omitted in benchmark
distribution files (they carry inputs only) and added by the server when it returns
an annotated HAML to the web UI.

```xml
<interpretation-results>
  <algorithm name="HLAbAssist" version="1.0" run-timestamp="2026-05-12T08:22:15Z"/>
  <reference-data>
    <imgt-hla version="3.64.0" count="47977" fetched-at="2025-10-01T00:00:00Z"/>
    <hats-groups imgt-version="3.64.0" n-alleles="24173"/>
    <optn-splits n-broad-groups="21" fetched-at="2025-10-01T00:00:00Z"/>
    <eplet-registry version="2026-01" n-eplets="521" extracted-date="2026-01-15"/>
  </reference-data>
  <summary>
    <antibodies-detected>3</antibodies-detected>
    <current-dsa>1</current-dsa>
    <historic-dsa>0</historic-dsa>
  </summary>
  <vxm-prediction>
    <t-cell-fcxm>negative</t-cell-fcxm>
    <b-cell-fcxm>positive</b-cell-fcxm>
    <confidence>moderate</confidence>
  </vxm-prediction>
  <unique-antibodies>
    <antibody
      specificity="A*02:01"
      mfi="5420"
      confidence="high"
      is-dsa="true"
      temporal-category="current">
      <evidence-score>0.85</evidence-score>
      <rules-applied>
        <rule>RULE_MFI_THRESHOLD_001</rule>
        <rule>RULE_DSA_TIER2_001</rule>
      </rules-applied>
    </antibody>
  </unique-antibodies>
  <dsa-list>
    <dsa specificity="A*02:01" mfi="5420" confidence="high"
         temporal-category="current" rule="RULE_DSA_TIER2_001"/>
  </dsa-list>
  <assay-qc>
    <panel-coverage loci="A,B,C,DR,DQ" class1-beads="97" class2-beads="84"/>
    <nc-floor class1="45" class2="38"/>
  </assay-qc>
</interpretation-results>
```

This element makes the annotated HAML a self-contained archival record: it carries
raw bead data, typing context, reference data versions, and algorithm reasoning in
one file.

---

## Multi-patient benchmark file

The benchmark file contains 55 cases as multiple `<patient>` elements within a single
`<haml>`. Each case contributes 1–2 patient entries depending on timepoints and vendors.

```xml
<extended-haml version="1.0" created="2026-05-12T08:22:15Z">
  <haml xmlns="urn:HAML.Namespace" version="0.5.3">

    <!-- Antibody ID case, One Lambda -->
    <patient>
      <patient-id>AC-540_ol</patient-id>
      ...
    </patient>

    <!-- Same case, Werfen platform -->
    <patient>
      <patient-id>AC-540_im</patient-id>
      ...
    </patient>

    <!-- VXM case with current + historic timepoints -->
    <patient>
      <patient-id>VXM-001</patient-id>    <!-- current PRETX -->
      ...
    </patient>
    <patient>
      <patient-id>VXM-001_historic</patient-id>
      ...
    </patient>

    ...

  </haml>

  <!-- No <recipient-profile> or <donor-profile> in the benchmark file.
       HLA typing is embedded per-patient as assay-kit metadata or supplied
       by the benchmark harness at runtime from the assembled JSON case files. -->

</extended-haml>
```

The benchmark file does not include `<recipient-profile>` or `<donor-profile>` at
the file level because typing is case-specific. The benchmark harness injects it
at runtime from `Aim1_Benchmark/data/assembled/`.

---

## Parser backward compatibility

`ExtendedHAMLParser` accepts:

1. **Extended HAML** — `<extended-haml>` root with inner `<haml>` and extension siblings
2. **Plain HAML 0.5.3** — `<haml xmlns="urn:HAML.Namespace">` root, no wrapper

In case 2, `recipient_hla` and `donor_hla` return as empty lists. The algorithm runs
without self-antigen exclusion or DSA identification.

---

## Related resources

- [`docs/hlabassist_workflow.md`](hlabassist_workflow.md) — end-to-end data flow from SAB CSV to algorithm results
- [`docs/column_mapping.md`](column_mapping.md) — SAB CSV column → HAML field mapping
- [HAML specification](https://github.com/immunomath/haml) — HAML 0.5.3 schema source
- [HLAbAssist.app](https://hlabassist.app) — live tool + benchmark download (login required for benchmark)
- Python implementation: `Research/Aim2_Algorithm/prototype/code/utilities/extended_haml.py`
- Browser implementation: `Research/Aim2_Algorithm/prototype/code/frontend/src/utils/haml-converter.js`
