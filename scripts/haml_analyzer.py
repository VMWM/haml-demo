#!/usr/bin/env python3
"""
haml_analyzer.py - Read HAML XML and classify beads by MFI threshold.

Parses a HAML XML file, extracts bead MFI values, applies a configurable
threshold (default 2000), and produces a summary table of positive,
borderline, and negative beads by HLA locus.

Usage:
    python haml_analyzer.py output/demo.haml.xml
    python haml_analyzer.py output/demo.haml.xml --threshold 1500

Part of the HAML 1.0 specification demo scripts.
"""

import argparse
import re
import sys
from pathlib import Path

from lxml import etree
import pandas as pd

HAML_NS = "urn:HAML.Namespace"
NS = {"h": HAML_NS}


def parse_haml_beads(haml_path):
    """Parse target bead observations from a HAML XML file.

    Returns a list of dicts with keys:
        bead_id, bead_type, hla_specificity, raw_mfi, bead_count
    Control beads (positive-control, negative-control) are included
    but flagged by bead_type.
    """
    tree = etree.parse(str(haml_path))
    beads = []

    for obs in tree.iter(f"{{{HAML_NS}}}target-bead-observation"):
        info = obs.find(f"{{{HAML_NS}}}bead-info")
        raw = obs.find(f"{{{HAML_NS}}}bead-raw-data")

        if info is None or raw is None:
            continue

        bead_id = info.findtext(f"{{{HAML_NS}}}bead-id", "")
        bead_type = info.findtext(f"{{{HAML_NS}}}bead-type", "")
        hla_spec = info.findtext(f"{{{HAML_NS}}}HLA-target-type", "")
        raw_mfi_text = raw.findtext(f"{{{HAML_NS}}}raw-MFI", "")
        bead_count_text = raw.findtext(f"{{{HAML_NS}}}bead-count", "")

        beads.append({
            "bead_id": bead_id,
            "bead_type": bead_type,
            "hla_specificity": hla_spec,
            "raw_mfi": float(raw_mfi_text) if raw_mfi_text else 0.0,
            "bead_count": int(float(bead_count_text)) if bead_count_text else None,
        })

    return beads


def extract_locus(specificity):
    """Extract HLA locus from a specificity string.

    Examples:
        'A*02:01' -> 'A'
        'DRB1*04:01' -> 'DRB1'
        'DQA1*05:01~DQB1*02:01' -> 'DQ'  (heterodimer -> DQ)
        'DPA1*01:03~DPB1*04:01' -> 'DP'  (heterodimer -> DP)
    """
    if not specificity:
        return ""
    # DQ/DP heterodimers
    if specificity.startswith("DQA") or specificity.startswith("DQB"):
        return "DQ"
    if specificity.startswith("DPA") or specificity.startswith("DPB"):
        return "DP"
    # Standard loci: match up to the asterisk
    m = re.match(r"([A-Z]+\d*)\*", specificity)
    return m.group(1) if m else specificity.split("*")[0]


def classify_bead(raw_mfi, threshold=2000.0):
    """Classify a bead based on MFI threshold.

    Returns 'Positive', 'Borderline', or 'Negative'.
    Borderline zone: 50-100% of threshold.
    """
    if raw_mfi >= threshold:
        return "Positive"
    elif raw_mfi >= threshold * 0.5:
        return "Borderline"
    else:
        return "Negative"


def analyze(haml_path, threshold=2000.0):
    """Analyze a HAML file: classify beads and produce summary.

    Returns (DataFrame of all target beads, summary DataFrame by locus).
    """
    all_beads = parse_haml_beads(haml_path)

    # Filter to target beads only (skip NC/PC controls)
    target_beads = [b for b in all_beads if b["bead_type"] == "target"]

    # Extract controls for reference
    nc = next((b for b in all_beads if b["bead_type"] == "negative-control"), None)
    pc = next((b for b in all_beads if b["bead_type"] == "positive-control"), None)

    if nc:
        print(f"Negative Control (NC): MFI = {nc['raw_mfi']:.0f}")
    if pc:
        print(f"Positive Control (PC): MFI = {pc['raw_mfi']:.0f}")
    if nc and pc and nc["raw_mfi"] > 0:
        print(f"PC/NC Ratio: {pc['raw_mfi'] / nc['raw_mfi']:.1f}")
    print(f"Target beads: {len(target_beads)}")
    print(f"MFI threshold: {threshold:.0f}\n")

    # Classify each bead
    rows = []
    for b in target_beads:
        locus = extract_locus(b["hla_specificity"])
        classification = classify_bead(b["raw_mfi"], threshold)
        rows.append({
            "bead_id": b["bead_id"],
            "specificity": b["hla_specificity"],
            "locus": locus,
            "raw_mfi": b["raw_mfi"],
            "classification": classification,
        })

    df = pd.DataFrame(rows)

    # Summary by locus
    summary = (
        df.groupby("locus")["classification"]
        .value_counts()
        .unstack(fill_value=0)
        .reindex(columns=["Positive", "Borderline", "Negative"], fill_value=0)
    )
    summary["Total"] = summary.sum(axis=1)

    return df, summary


def main():
    parser = argparse.ArgumentParser(
        description="Analyze HAML XML: classify beads by MFI threshold")
    parser.add_argument("input", help="Input HAML XML file path")
    parser.add_argument("--threshold", type=float, default=2000.0,
                        help="MFI threshold for positive classification (default: 2000)")
    parser.add_argument("--show-all", action="store_true",
                        help="Show all beads, not just positives")
    args = parser.parse_args()

    df, summary = analyze(args.input, threshold=args.threshold)

    # Print positive beads
    positives = df[df["classification"] == "Positive"].sort_values("raw_mfi", ascending=False)
    borderline = df[df["classification"] == "Borderline"].sort_values("raw_mfi", ascending=False)

    if not positives.empty:
        print(f"=== POSITIVE BEADS ({len(positives)}) ===")
        print(positives[["specificity", "locus", "raw_mfi"]].to_string(index=False))
        print()

    if not borderline.empty:
        print(f"=== BORDERLINE BEADS ({len(borderline)}) ===")
        print(borderline[["specificity", "locus", "raw_mfi"]].to_string(index=False))
        print()

    if args.show_all:
        print("=== ALL BEADS ===")
        print(df.to_string(index=False))
        print()

    print("=== SUMMARY BY LOCUS ===")
    print(summary.to_string())

    total_pos = (df["classification"] == "Positive").sum()
    total_bord = (df["classification"] == "Borderline").sum()
    total_neg = (df["classification"] == "Negative").sum()
    print(f"\nTotal: {total_pos} positive, {total_bord} borderline, "
          f"{total_neg} negative ({len(df)} beads)")


if __name__ == "__main__":
    main()
