#!/usr/bin/env python3
"""
simple_vxm.py - Simple virtual crossmatch using HAML antibody data.

Given a HAML XML file and a donor HLA typing file, identifies
donor-specific antibodies (DSA) above the MFI threshold and predicts
virtual crossmatch compatibility.

This is a pedagogical demo, not a clinical tool. It uses simple exact
matching (bead specificity == donor allele) without cross-reactive group
analysis, epitope matching, or multi-tier fallback.

Usage:
    python simple_vxm.py output/demo.haml.xml data/sample_donor_typing.txt
    python simple_vxm.py output/demo.haml.xml data/sample_donor_typing.txt --threshold 1500

Part of the HAML 1.0 specification demo scripts.
"""

import argparse
import sys
from pathlib import Path

from haml_analyzer import parse_haml_beads, extract_locus, classify_bead


def read_donor_typing(filepath):
    """Read donor HLA typing from a text file.

    Format: one allele per line, lines starting with # are comments.
    Returns a set of allele strings.
    """
    alleles = set()
    with open(filepath) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            alleles.add(line)
    return alleles


def identify_dsa(beads, donor_alleles, threshold=2000.0):
    """Identify donor-specific antibodies using exact matching.

    For each positive bead (MFI >= threshold), check if its HLA
    specificity matches any donor allele.

    Returns a list of DSA dicts with: specificity, locus, raw_mfi, donor_allele.
    """
    dsa_list = []

    for bead in beads:
        if bead["bead_type"] != "target":
            continue
        if bead["raw_mfi"] < threshold:
            continue

        spec = bead["hla_specificity"]
        if not spec:
            continue

        # Exact match against donor alleles
        if spec in donor_alleles:
            dsa_list.append({
                "specificity": spec,
                "locus": extract_locus(spec),
                "raw_mfi": bead["raw_mfi"],
                "donor_allele": spec,
                "match_type": "exact",
            })
            continue

        # For heterodimers (DQ/DP), check if either chain matches
        if "~" in spec:
            chains = spec.split("~")
            for chain in chains:
                if chain in donor_alleles:
                    dsa_list.append({
                        "specificity": spec,
                        "locus": extract_locus(spec),
                        "raw_mfi": bead["raw_mfi"],
                        "donor_allele": chain,
                        "match_type": "heterodimer-chain",
                    })
                    break

    return dsa_list


def predict_vxm(dsa_list):
    """Predict virtual crossmatch result from DSA list.

    Simple logic: any DSA above threshold = Incompatible.
    No DSA = Compatible.
    """
    if dsa_list:
        return "Positive (Incompatible)"
    return "Negative (Compatible)"


def main():
    parser = argparse.ArgumentParser(
        description="Simple virtual crossmatch using HAML antibody data")
    parser.add_argument("haml", help="Input HAML XML file path")
    parser.add_argument("donor", help="Donor HLA typing file path")
    parser.add_argument("--threshold", type=float, default=2000.0,
                        help="MFI threshold for positive (default: 2000)")
    args = parser.parse_args()

    # Parse HAML beads
    beads = parse_haml_beads(args.haml)
    target_beads = [b for b in beads if b["bead_type"] == "target"]
    print(f"Loaded {len(target_beads)} target beads from HAML\n")

    # Read donor typing
    donor_alleles = read_donor_typing(args.donor)
    print(f"Donor HLA typing ({len(donor_alleles)} alleles):")
    for allele in sorted(donor_alleles):
        print(f"  {allele}")
    print()

    # Identify DSA
    dsa_list = identify_dsa(beads, donor_alleles, threshold=args.threshold)

    # Predict VXM
    prediction = predict_vxm(dsa_list)

    # Report
    print(f"MFI threshold: {args.threshold:.0f}")
    print(f"{'=' * 50}")

    if dsa_list:
        print(f"\nDonor-Specific Antibodies ({len(dsa_list)} found):")
        print(f"{'Specificity':<35} {'Locus':<8} {'MFI':>8} {'Match'}")
        print(f"{'-'*35} {'-'*8} {'-'*8} {'-'*20}")
        for dsa in sorted(dsa_list, key=lambda d: d["raw_mfi"], reverse=True):
            print(f"{dsa['specificity']:<35} {dsa['locus']:<8} "
                  f"{dsa['raw_mfi']:>8.0f} {dsa['match_type']}")
    else:
        print("\nNo donor-specific antibodies detected.")

    print(f"\n{'=' * 50}")
    print(f"Virtual Crossmatch Prediction: {prediction}")
    print(f"{'=' * 50}")

    if dsa_list:
        # Clinical note
        loci = sorted({d["locus"] for d in dsa_list})
        max_mfi = max(d["raw_mfi"] for d in dsa_list)
        print(f"\nNote: {len(dsa_list)} DSA detected across {', '.join(loci)} loci.")
        print(f"Strongest DSA: MFI {max_mfi:.0f}")


if __name__ == "__main__":
    main()
