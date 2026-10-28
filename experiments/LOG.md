# Experiment log — Zindi Bias Bounty Mapping Equity Challenge

Validation protocol. The organisers provide **no labels**. Any local "validation" against our
own reconstruction of the target would need the removed reference layers (TIGER, Microsoft,
HIFLD, CBP), which the rules prohibit. The only legitimate validator is therefore the official
public leaderboard (≈30 % of tracts, RMSE). Each experiment is one whole-file submission: a
written hypothesis, a control (best previous public score), one change, and a decision.
The pipeline is deterministic (no random seeds involved); reruns give byte-identical CSVs (SHA-256 logged).
Negative results are logged like positive ones.

## E000 — discard the September baseline (decision, not a submission)
- Hypothesis: n/a. The 2026-09-23 baseline reconstructs the target from TIGER/Microsoft/CBP/HIFLD layers.
- Decision (JEV, provenance=jev, confidence 1.0): **discarded fully**. Not submitted, not used as labels, features or calibration.

## Prespecified official tests,28October (prepared, not scored)
E003: building base gap .05 rather than .02; hypothesis baseline underestimates footprint omission. E004: road tertiary leakage .30 rather than .15; hypothesis class-boundary mismatch hides more named-road length. E005: building base gap0 rather than .02; competing hypothesis conflation already covers almost all footprints. Each is isolated against unchanged E001; compare only accepted official RMSE and retain every score. No local accuracy estimate is possible without organiser labels. All changes fixed before obtaining official feedback.
The E002 absence diagnostic affects zero tracts (no Overture buildings with positive ACS housing); its CSV was identical to control and will not be submitted. ACS is not a substitute building denominator.
Generator src/prepare_interventions.py,9379unique IDs perfile, finite[0,1], same E001 SHA2569c34cbb7c56ab60ae174747ebc34a96275de2e9aa3c4bf2f920706189ac6591f. Three distinct candidate CSVs and input hashes committed. Official quota confirmed via page:10/day,300total. Login/Join pending; no official experiment score/receipt yet.
