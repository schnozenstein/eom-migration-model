# Geographic uncertainty in EOM

## Purpose
Add an explicit geographical-uncertainty layer to the existing macro EOM ranking without silently treating unknown data as low risk or high risk.

## Components
Each input component is scored 1–5 (1 = low exposure; 5 = very high exposure). Leave blank when evidence is insufficient.

- **Regional conflict exposure (30%)**: exposure to nearby interstate conflict, militarized flashpoints, and regional escalation.
- **Strategic isolation (20%)**: vulnerability from limited strategic depth, constrained alternatives, or dependence on a small number of external partners. This is not a proxy for military strength alone.
- **Critical route dependency (15%)**: dependence on vulnerable maritime chokepoints, air corridors, land corridors, or imported critical goods.
- **Natural hazard exposure (20%)**: exposure to relevant natural hazards, ideally using comparable official hazard data.
- **Cross-border spillover (15%)**: exposure to regional disruptions, refugee flows, conflict spillovers, or transboundary shocks.

## Formula and interpretation
The script combines standardized baseline macro energy, standardized environmental/economic partial risk, and standardized geographic uncertainty. The initial 0.25 / 0.25 adjustment weights are scenario assumptions only; they are not fitted estimates. Lower adjusted energy is better. The model emits no adjusted rank unless every geographic component and the environmental/economic risk input are present.

## Scientific safeguards
1. Use dated, source-linked inputs and preserve source vintage.
2. Score comparable evidence, not broad impressions or media salience.
3. Keep country-specific exposure distinct from the probability of war or a particular event.
4. Do not double-count the same exposure in political stability, conflict risk and geographic uncertainty without documenting the overlap.
5. Publish baseline rank, adjusted rank, rank change, missingness and sensitivity to alternative weights.
6. A risk-adjusted destination ranking is not a personal migration probability, visa eligibility assessment or forecast.

## Current status
The implementation creates a blank input template and a gated output. It intentionally does not fabricate geographic scores. Populate `data/geographical_uncertainty_inputs.csv` with evidence-backed assessments, then run `python src/eom_empirical/geographical_uncertainty.py`.
