#!/usr/bin/env python3
"""
csv_to_haml.py - Convert One Lambda Fusion SAB CSV export to HAML XML.

Converts a standard One Lambda HLA Fusion single antigen bead (SAB) CSV
export into a valid HAML XML document. Validates the output against the
HAML XSD schema.

Input CSV columns (One Lambda HLA Fusion export):
    Sample ID, Bead ID, Specificity, Raw Value, BCM, Ranking, Bead Count

Output: HAML XML file conforming to the HAML 0.6.1 draft schema.

Usage:
    python csv_to_haml.py data/sample_sab_class1.csv -o output/demo.haml.xml
    python csv_to_haml.py data/sample_sab_class1.csv --validate

Part of the HAML 1.0 specification demo scripts.
"""

import argparse
import csv
import os
import sys
from datetime import date
from pathlib import Path

from lxml import etree

# HAML namespace and version
HAML_NS = "urn:HAML.Namespace"
HAML_VERSION = "0.5.3"  # XSD declares this; will become 1.0 on publication
NSMAP = {None: HAML_NS}

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "haml__version_0_6_1.xsd"


def sub(parent, tag, text=None):
    """Create a child element with optional text content."""
    el = etree.SubElement(parent, f"{{{HAML_NS}}}{tag}")
    if text is not None:
        el.text = str(text)
    return el


def read_fusion_csv(filepath):
    """Read a One Lambda HLA Fusion SAB CSV export.

    Returns a list of dicts with keys:
        sample_id, bead_id, specificity, raw_mfi, bead_count, ranking
    Beads 1 and 2 (NC/PC controls) have no specificity.
    """
    beads = []
    with open(filepath, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw_val = row.get("Raw Value", "").strip()
            if not raw_val:
                continue
            beads.append({
                "sample_id": row.get("Sample ID", "").strip(),
                "bead_id": row.get("Bead ID", "").strip(),
                "specificity": row.get("Specificity", "").strip(),
                "raw_mfi": float(raw_val),
                "bead_count": row.get("Bead Count", "").strip() or None,
                "ranking": row.get("Ranking", "").strip() or None,
            })
    return beads


def classify_bead_type(bead_id, specificity):
    """Determine bead type from bead ID and specificity.

    Bead 1 = negative control, Bead 2 = positive control,
    all others with a specificity = target beads.
    """
    if bead_id == "1":
        return "negative-control"
    elif bead_id == "2":
        return "positive-control"
    elif specificity:
        return "target"
    return None


def build_haml(beads, reporting_center="Demo Laboratory", hla_class="I",
               catalog="LS1A04", lot="DEMO-001"):
    """Build a HAML XML document from parsed bead data.

    Args:
        beads: List of bead dicts from read_fusion_csv().
        reporting_center: Name of the reporting laboratory.
        hla_class: "I" or "II" (used for assay-type description).
        catalog: Kit catalog number.
        lot: Kit lot number.

    Returns:
        lxml.etree.Element (root <haml> element).
    """
    # Determine sample ID from data (all beads should share the same one)
    sample_ids = {b["sample_id"] for b in beads}
    if len(sample_ids) != 1:
        raise ValueError(f"Expected 1 sample ID, found {len(sample_ids)}: {sample_ids}")
    sample_id = sample_ids.pop()

    # Root
    root = etree.Element(f"{{{HAML_NS}}}haml", nsmap=NSMAP)
    root.set("version", HAML_VERSION)

    # Document ID
    haml_id = sub(root, "haml-id")
    sub(haml_id, "root", "0.0.0.0")
    sub(haml_id, "extension", f"haml-demo-{sample_id}")

    # Reporting center
    sub(root, "reporting-center", reporting_center)

    # Patient
    patient = sub(root, "patient")
    sub(patient, "patient-id", sample_id)

    # Sample
    sample = sub(patient, "sample")
    sub(sample, "sample-id", f"{sample_id}-serum")
    sub(sample, "sample-date", str(date.today()))
    sub(sample, "sample-type", "Serum")

    # Working sample (neat = untreated)
    ws = sub(sample, "working-sample")
    sub(ws, "working-sample-id", f"{sample_id}-NEAT")

    # Treatment: neat (no dilution)
    treatment = sub(ws, "treatment")
    sub(treatment, "method", "NEAT")

    # Assay
    assay = sub(ws, "assay")
    sub(assay, "assay-id", f"{sample_id}-SAB-C{hla_class}")
    sub(assay, "run-id", f"RUN-{sample_id}")
    sub(assay, "assay-date", str(date.today()))

    # Assay kit
    kit = sub(assay, "assay-kit")
    sub(kit, "assay-type", "Solid Phase Assay")
    sub(kit, "catalog-number", catalog)
    sub(kit, "lot-number", lot)
    sub(kit, "kit-manufacturer", "One Lambda (Thermo Fisher)")
    sub(kit, "interpretation-software", "HLA Fusion")

    # Bead observations
    for bead in beads:
        bead_type = classify_bead_type(bead["bead_id"], bead["specificity"])
        if bead_type is None:
            continue

        obs = sub(assay, "target-bead-observation")

        # bead-info (required)
        info = sub(obs, "bead-info")
        sub(info, "bead-id", bead["bead_id"])
        sub(info, "bead-type", bead_type)
        if bead["specificity"]:
            sub(info, "HLA-target-type", bead["specificity"])

        # bead-raw-data (required)
        raw_data = sub(obs, "bead-raw-data")
        sub(raw_data, "raw-MFI", str(bead["raw_mfi"]))
        if bead["bead_count"]:
            sub(raw_data, "bead-count", bead["bead_count"])

    return root


def validate_haml(root):
    """Validate HAML XML against the XSD schema.

    Returns (is_valid, error_log).
    """
    if not SCHEMA_PATH.exists():
        return None, "Schema file not found: " + str(SCHEMA_PATH)

    schema_doc = etree.parse(str(SCHEMA_PATH))
    schema = etree.XMLSchema(schema_doc)
    is_valid = schema.validate(root)
    return is_valid, str(schema.error_log) if not is_valid else ""


def main():
    parser = argparse.ArgumentParser(
        description="Convert One Lambda Fusion SAB CSV to HAML XML")
    parser.add_argument("input", help="Input CSV file path")
    parser.add_argument("-o", "--output", help="Output HAML XML file path")
    parser.add_argument("--validate", action="store_true",
                        help="Validate output against HAML XSD schema")
    parser.add_argument("--center", default="Demo Laboratory",
                        help="Reporting center name")
    parser.add_argument("--class", dest="hla_class", default="I",
                        choices=["I", "II"], help="HLA class (I or II)")
    parser.add_argument("--catalog", default="LS1A04",
                        help="Kit catalog number")
    parser.add_argument("--lot", default="DEMO-001",
                        help="Kit lot number")
    args = parser.parse_args()

    # Read CSV
    beads = read_fusion_csv(args.input)
    print(f"Read {len(beads)} beads from {args.input}")

    # Build HAML
    root = build_haml(
        beads,
        reporting_center=args.center,
        hla_class=args.hla_class,
        catalog=args.catalog,
        lot=args.lot,
    )

    # Serialize
    xml_bytes = etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
    xml_str = xml_bytes.decode("utf-8")

    # Output
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(xml_str)
        print(f"Wrote HAML XML to {args.output}")
    else:
        print(xml_str)

    # Validate
    if args.validate:
        is_valid, errors = validate_haml(root)
        if is_valid is None:
            print(f"Validation skipped: {errors}")
        elif is_valid:
            print("Validation: PASSED")
        else:
            print(f"Validation: FAILED\n{errors}")
            sys.exit(1)


if __name__ == "__main__":
    main()
