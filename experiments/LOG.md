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
