# Integrating MHSCI into EOM as an optional energy adjustment

## Decision

Use MHSCI as a **separate social-climate penalty scenario**, not as a replacement for the macro EOM score. EOM's sign convention is preserved: **lower energy is better**. Higher MHSCI scores mean greater coded hostility/social-climate risk and therefore increase energy; lower scores reduce energy.

## Formula

For destinations with a full provisional MHSCI composite:

\[
E_i^{social}=E_i^{macro}+\lambda z(H_i)
\]

- \(E_i^{macro}\): existing EOM equal-weight macro energy.
- \(H_i\): MHSCI score on 0–100, higher means more hostility/risk.
- \(z(H_i)\): standardized MHSCI score among destinations with comparable scored composites.
- \(\lambda\): sensitivity parameter; default 0.5 energy units per one standard deviation.

This is a transparent scenario parameter, not a fitted causal coefficient. Compare at multiple weights (e.g. 0.25, 0.5, 1.0) before interpreting rank changes.

## Missing-data and evidence rules

- A destination is adjusted only when it has a scored composite with at least 3 of 4 MHSCI dimensions.
- Blank or insufficient evidence stays unscored; it is never treated as zero hostility.
- Adjusted ranks compare only destinations with comparable MHSCI composites. Do not imply the unscored destinations are safer or worse.
- MHSCI v0.1 includes manual ordinal coding and some general immigration-attitude proxies. It is not yet a validated measure of anti-Indian hostility and must not be described as such.
- The baseline macro energy/rank columns are retained and not overwritten. The optional scenario does not change the primary EOM ranking until evidence coverage, validity and sensitivity are reviewed.

## Run

```bash
python scripts/build_mhsci.py
python scripts/build_mhsci_eom_scenario.py --weight 0.5
```

Outputs:
- `outputs/mhsci_adjusted_eom_scenario.csv`
- `reports/mhsci_eom_scenario.md`

The script reads the existing macro ranking and MHSCI output, and is intentionally deterministic/offline.
