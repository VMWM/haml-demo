#!/usr/bin/env python3
"""
benchmark_pipeline.py - Parse and analyze a multi-case HAML benchmark file.

Demonstrates how to use HAML as the input format for a cohort of HLA antibody
cases. This script reads benchmark_all55.haml.xml (available for download from
HLAbAssist.app after login) and shows:

  1. How to iterate over a multi-patient HAML file
  2. How to identify platform (One Lambda vs Werfen) and timepoint
     (current vs historic) from patient metadata
  3. How to apply a per-assay NC-adaptive MFI threshold
  4. How to aggregate results across a cohort (antibody prevalence by locus)

The benchmark contains 55 cases (61 HAML patient entries, because historic
timepoints and platform variants are encoded as separate patient elements).

Usage:
    python scripts/benchmark_pipeline.py haml/benchmark_all55.haml.xml
    python scripts/benchmark_pipeline.py haml/benchmark_all55.haml.xml --threshold 1000
    python scripts/benchmark_pipeline.py haml/benchmark_all55.haml.xml --case-detail

Requirements:
    lxml, pandas (pip install lxml pandas)
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from lxml import etree
import pandas as pd

HAML_NS = "urn:HAML.Namespace"
NS = {"h": HAML_NS}

DEFAULT_THRESHOLD = 1000  # MFI; standard clinical cutoff for most loci


# ---------------------------------------------------------------------------
# HAML parsing
# ---------------------------------------------------------------------------

def t(name: str) -> str:
    return f"{{{HAML_NS}}}{name}"


def parse_benchmark_haml(haml_path: Path) -> list[dict]:
    """Parse all patients from a benchmark HAML file.

    Returns a list of patient dicts, each with keys:
        patient_id, platform, timepoint, assay_date,
        nc_mfi, pc_mfi, beads (list of dicts)

    Each bead dict: bead_id, bead_type, specificity, raw_mfi, bead_count
    """
    tree = etree.parse(str(haml_path))
    root = tree.getroot()

    version = root.get("version", "unknown")
    patients_el = root.findall(t("patient"))

    records = []
    for patient_el in patients_el:
        patient_id = patient_el.findtext(t("patient-id"), "").strip()
        platform = _detect_platform(patient_id, patient_el)
        timepoint = "historic" if "_historic" in patient_id else "current"

        # Collect all assays (Class I + Class II are separate assays under one
        # working-sample; each assay has its own NC/PC beads)
        assay_date = None
        nc_mfi = None
        pc_mfi = None
        beads = []

        for assay_el in patient_el.iter(t("assay")):
            if assay_date is None:
                assay_date = assay_el.findtext(t("assay-date"), "")

            for obs in assay_el.findall(t("target-bead-observation")):
                info = obs.find(t("bead-info"))
                raw_el = obs.find(t("bead-raw-data"))
                if info is None or raw_el is None:
                    continue

                bead_type = info.findtext(t("bead-type"), "target")
                specificity = info.findtext(t("HLA-target-type"), "")
                bead_id_str = info.findtext(t("bead-id"), "")
                raw_mfi_str = raw_el.findtext(t("raw-MFI"), "")
                bead_count_str = raw_el.findtext(t("bead-count"), "")

                raw_mfi = float(raw_mfi_str) if raw_mfi_str else 0.0
                bead_count = int(float(bead_count_str)) if bead_count_str else None

                if bead_type == "negative-control":
                    if nc_mfi is None or raw_mfi > nc_mfi:
                        nc_mfi = raw_mfi
                elif bead_type == "positive-control":
                    if pc_mfi is None:
                        pc_mfi = raw_mfi
                else:
                    beads.append({
                        "bead_id": bead_id_str,
                        "bead_type": bead_type,
                        "specificity": specificity,
                        "raw_mfi": raw_mfi,
                        "bead_count": bead_count,
                        "locus": _extract_locus(specificity),
                    })

        records.append({
            "patient_id": patient_id,
            "platform": platform,
            "timepoint": timepoint,
            "assay_date": assay_date or "",
            "nc_mfi": nc_mfi or 0.0,
            "pc_mfi": pc_mfi or 0.0,
            "beads": beads,
        })

    return records, version


def _detect_platform(patient_id: str, patient_el) -> str:
    """Identify platform from patient-id suffix or assay-kit manufacturer."""
    if "_im" in patient_id or "_werfen" in patient_id:
        return "Werfen"
    if "_ol" in patient_id or "_onelambda" in patient_id:
        return "One Lambda"
    # Fall back to manufacturer field in first assay-kit
    for kit in patient_el.iter(t("assay-kit")):
        mfr = kit.findtext(t("kit-manufacturer"), "")
        if "Werfen" in mfr or "Immucor" in mfr:
            return "Werfen"
        if "One Lambda" in mfr or "Lambda" in mfr:
            return "One Lambda"
    return "Unknown"


def _extract_locus(specificity: str) -> str:
    """Extract HLA locus group from a specificity string."""
    if not specificity:
        return ""
    if specificity.startswith("DQA") or specificity.startswith("DQB"):
        return "DQ"
    if specificity.startswith("DPA") or specificity.startswith("DPB"):
        return "DP"
    m = re.match(r"([A-Z]+\d*)\*", specificity)
    return m.group(1) if m else specificity.split("*")[0]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def classify_beads(patient: dict, threshold: float) -> dict:
    """Apply MFI threshold with NC-adaptive floor.

    The effective threshold is max(threshold, nc_mfi * 10). This matches the
    clinical convention that a bead must clear both the fixed threshold and
    10x the assay's negative control to be considered positive.

    Returns a dict with keys:
        positive, borderline, negative (lists of bead dicts)
        effective_threshold (float)
        nc_snr (float): PC/NC signal-to-noise ratio
    """
    nc = patient["nc_mfi"]
    pc = patient["pc_mfi"]

    # NC-adaptive floor: bead must exceed both the fixed threshold and 10x NC
    effective = max(threshold, nc * 10) if nc > 0 else threshold

    positive, borderline, negative = [], [], []
    for bead in patient["beads"]:
        mfi = bead["raw_mfi"]
        if mfi >= effective:
            positive.append(bead)
        elif mfi >= effective * 0.5:
            borderline.append(bead)
        else:
            negative.append(bead)

    nc_snr = pc / nc if nc > 0 else None

    return {
        "positive": positive,
        "borderline": borderline,
        "negative": negative,
        "effective_threshold": effective,
        "nc_snr": nc_snr,
    }


def cohort_summary(all_patients: list[dict], threshold: float) -> pd.DataFrame:
    """Compute per-locus antibody prevalence across the cohort.

    A case is 'antibody positive' at a locus if it has at least one bead
    above the effective threshold for that locus. Prevalence = positive cases
    / total cases tested at that locus.

    Only 'current' timepoint entries are counted; historic entries are excluded
    to avoid double-counting multi-timepoint cases.
    """
    current = [p for p in all_patients if p["timepoint"] == "current"]

    locus_pos = defaultdict(int)
    locus_total = defaultdict(int)

    for patient in current:
        result = classify_beads(patient, threshold)
        loci_tested = set(b["locus"] for b in patient["beads"] if b["locus"])
        loci_positive = set(b["locus"] for b in result["positive"] if b["locus"])
        for locus in loci_tested:
            locus_total[locus] += 1
        for locus in loci_positive:
            locus_pos[locus] += 1

    all_loci = sorted(locus_total.keys())
    rows = []
    for locus in all_loci:
        total = locus_total[locus]
        pos = locus_pos.get(locus, 0)
        rows.append({
            "Locus": locus,
            "Cases tested": total,
            "Cases positive": pos,
            "Prevalence": f"{100 * pos / total:.0f}%" if total > 0 else "—",
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_cohort_overview(all_patients: list[dict], version: str) -> None:
    current = [p for p in all_patients if p["timepoint"] == "current"]
    historic = [p for p in all_patients if p["timepoint"] == "historic"]
    ol = sum(1 for p in current if p["platform"] == "One Lambda")
    werfen = sum(1 for p in current if p["platform"] == "Werfen")
    multi_platform = len(current) - ol - werfen

    total_beads = sum(len(p["beads"]) for p in current)

    print(f"HAML version:      {version}")
    print(f"Total entries:     {len(all_patients)} "
          f"({len(current)} current + {len(historic)} historic timepoint entries)")
    print(f"Platform split:    {ol} One Lambda, {werfen} Werfen, {multi_platform} other")
    print(f"Total target beads (current): {total_beads:,}")
    print()


def print_case_detail(patient: dict, result: dict) -> None:
    pid = patient["patient_id"]
    nc = patient["nc_mfi"]
    pc = patient["pc_mfi"]
    snr = result["nc_snr"]
    eff = result["effective_threshold"]
    n_pos = len(result["positive"])
    n_bord = len(result["borderline"])
    n_neg = len(result["negative"])

    snr_str = f"{snr:.1f}" if snr else "n/a"
    print(f"\n{'─'*60}")
    print(f"Case:      {pid}")
    print(f"Platform:  {patient['platform']}  |  Timepoint: {patient['timepoint']}")
    print(f"NC={nc:.0f}  PC={pc:.0f}  PC/NC={snr_str}  "
          f"Effective threshold={eff:.0f}")
    print(f"Beads:     {n_pos} positive, {n_bord} borderline, {n_neg} negative")

    if result["positive"]:
        specs = sorted({b["specificity"] for b in result["positive"]})
        print(f"Positive:  {', '.join(specs)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse and analyze a multi-case HAML benchmark file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Download benchmark_all55.haml.xml from HLAbAssist.app (login required).\n"
            "This script demonstrates HAML as a cohort-level data format — not a\n"
            "production antibody interpretation pipeline."
        ),
    )
    parser.add_argument("haml_file", help="Path to benchmark_all55.haml.xml")
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help=f"Fixed MFI threshold (default: {DEFAULT_THRESHOLD}). "
             "Effective threshold = max(this, NC × 10).",
    )
    parser.add_argument(
        "--case-detail", action="store_true",
        help="Print per-case breakdown (positive bead list per patient)",
    )
    parser.add_argument(
        "--current-only", action="store_true",
        help="Skip historic timepoint entries in per-case output",
    )
    args = parser.parse_args()

    haml_path = Path(args.haml_file)
    if not haml_path.exists():
        print(f"Error: {haml_path} not found.", file=sys.stderr)
        print("Download benchmark_all55.haml.xml from HLAbAssist.app.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing {haml_path.name} ...")
    all_patients, version = parse_benchmark_haml(haml_path)
    print_cohort_overview(all_patients, version)

    # Per-case output
    if args.case_detail:
        for patient in all_patients:
            if args.current_only and patient["timepoint"] == "historic":
                continue
            result = classify_beads(patient, args.threshold)
            print_case_detail(patient, result)
        print()

    # Cohort summary
    print("=" * 60)
    print(f"COHORT SUMMARY — antibody prevalence by locus")
    print(f"(current timepoint entries only; threshold = {args.threshold:.0f} MFI, NC-adaptive)")
    print("=" * 60)
    summary = cohort_summary(all_patients, args.threshold)
    print(summary.to_string(index=False))
    print()
    print("Note: A case is 'positive' at a locus if any bead for that locus")
    print("exceeds max(threshold, NC × 10). Multi-platform cases (One Lambda +")
    print("Werfen) count once per current-timepoint patient entry.")


if __name__ == "__main__":
    main()
