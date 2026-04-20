# HAML Demo Scripts

Demo scripts for the [HAML 1.0 specification](https://github.com/immunomath/haml): converting, validating, and processing HLA Antibody Markup Language (HAML) files.

These scripts accompany the HAML 1.0 specification manuscript and demonstrate how to work with HLA antibody data in a standardized, interoperable format.

## What is HAML?

HAML (HLA Antibody Markup Language) is an XML-based standard for representing HLA single antigen bead (SAB) assay results. It enables interoperability between HLA laboratories, analysis software, and clinical decision support tools. Developed by the [IHIW](https://www.ihiw.org/) Clinical Histocompatibility Laboratory Informatics Working Group.

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/csv_to_haml.py` | Convert One Lambda Fusion SAB CSV export to HAML XML |
| `scripts/haml_analyzer.py` | Read HAML XML, apply MFI threshold, classify beads |
| `scripts/simple_vxm.py` | Simple virtual crossmatch: HAML + donor typing to DSA identification |

## Quick Start

```bash
pip install -r requirements.txt

# Convert CSV to HAML
python scripts/csv_to_haml.py data/sample_sab_class1.csv -o output/demo.haml.xml

# Analyze the HAML file
python scripts/haml_analyzer.py output/demo.haml.xml --threshold 2000

# Run a simple virtual crossmatch
python scripts/simple_vxm.py output/demo.haml.xml data/sample_donor_typing.txt
```

## Interactive Demo

See `notebooks/haml_demo.ipynb` for a guided walkthrough of all three scripts with narrative and visualizations.

## Schema

This demo targets the HAML 0.6.1 draft schema (`schema/haml__version_0_6_1.xsd`), which will become HAML 1.0 upon publication.

## Sample Data

All data in `data/` is synthetic and does not represent real patients. See `data/README.md` for details.

## Authors

Vanessa W. Menard, Loren Gragert, Eric Spierings, Ben Matern

## License

MIT
