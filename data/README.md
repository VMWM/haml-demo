# Sample Data

All files in this directory contain **synthetic data** created for demonstration purposes. No real patient data is used.

## Files

| File | Description |
|------|-------------|
| `sample_sab_class1.csv` | Synthetic One Lambda LABScreen Single Antigen Class I bead data (97 beads) |
| `sample_sab_class2.csv` | Synthetic One Lambda LABScreen Single Antigen Class II bead data (95 beads) |
| `sample_donor_typing.txt` | Donor HLA typing for virtual crossmatch demo |

## Format

CSV files follow the One Lambda HLA Fusion export format with columns:
`Sample ID, Bead ID, Specificity, Raw Value, BCM, Ranking, Bead Count`

The donor typing file contains one HLA allele per line (molecular 2-field notation).
