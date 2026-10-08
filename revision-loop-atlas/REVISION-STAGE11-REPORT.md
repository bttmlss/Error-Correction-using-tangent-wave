# REVISION-STAGE11-REPORT — carry-forward reprocessing (no new LLM calls)

## Plain-language summary

Adrian's adjudication: the commentary confound is a measurement-layer gap, fixed by
the carry-forward rule — a round with no numeric answer (per the *frozen* parser)
is a non-revision: e(t) = e(t−1), exact(t) = exact(t−1), flagged. The model's active
hypothesis did not change, so measured error must not jump. Option 2 (prompt fix)
was rejected: forcing a restated answer would steer the volunteer's revision policy
and break the anti-circularity rule.

Applied to the recorded 270 rounds: 74 carry-forward rounds (exactly the 74
commentary rounds — the frozen parser agrees with the audit). The frozen 4-detector
battery was re-run on the corrected trajectories.

## Stage 1.1 numbers

| Detector | Firings / 30 (corrected) | Was (Stage 1.0) | Calibrated null expectation |
|---|---|---|---|
| Track A (solve onset) | 6 | 9 | 0.0 |
| B1 (stall) | 0 | 3 | 1.11 |
| B2 (oscillation) | 0 | 3 | 0.93 |
| B3 (divergence) | 0 | 4 | 0.0 |
| Informative trajectories | 18 | 22–23 | (≥20 = adequate power) |

The 3 killed Track-A firings (trajs 3, 14, 23) were pure commentary↔answer flicker
around already-correct answers. The 6 survivors (trajs 1, 11, 18, 22, 24, 29) are
all genuine wrong→right onsets — verified against the answer texts.

**After commentary removal, the only gross pattern in 30 trajectories is solving.
No stall, no oscillation, no divergence.** B1/B2/B3 fire at or below their
calibrated null rates.

## Bar 0 vs. the power tripwire — a genuine conflict

- **Bar 0** (Adrian's Stage-1.1 rule): 24/30 = **80%** of corrected trajectories
  show zero detector firings ≥ 75% → **FIRES → retire the state hypothesis** for
  (Gemma 2B × GSM8K × neutral revision prompt × frozen measurement × 9-round horizon).
- **Expansion ground (a)** (frozen rule): 18 informative < 20 → the tripwire trips →
  "power inadequate, expand toward 100."

Both rules are Adrian's; they point in opposite directions. The honest context:

- The 12 non-informative trajectories contribute vacuous zeros to the 80%. Among
  *informative* trajectories, the clean fraction is 12/18 = 67% — below the Bar-0 bar.
- But power against the *exotic* patterns was adequate: with 18 moving trajectories,
  a 20% true stall/oscillation/divergence rate would have shown at least one firing
  with probability 98%. We saw zero.
- All 6 non-clean trajectories are solve onsets — the desired behavior of a revision
  loop, not evidence of exotic dynamical states.

**Recommendation:** retire per Bar 0 (the preregistered rule, met at 80%), with the
power caveat documented — or, if the 18 < 20 tripwire is held binding, expand to
~100 trajectories, which at current rates would cost ~9 more hours and is unlikely
to overturn an 80/20 split. Adrian adjudicates.

## Scope-bound retirement wording (if accepted)

"The state hypothesis is retired for Gemma 2B × GSM8K-style numeric tasks × the
neutral revision prompt × the frozen exact-match/embedding measurement × the
9-round horizon. Revision trajectories in this scope are adequately described
without recurring dynamical states; the only detected gross pattern is
wrong→right solve onsets."

## Files

- `revision_loop_results_11.json` — corrected e(t), exact flags, non-revision
  markers, detector classifications, Bar-0 evaluation
- `stage11_carryforward.py` — the reprocessing script (deterministic)
- `REVISION-STAGE1-REPORT.md` — the confounded run (superseded for inference,
  preserved as evidence of the commentary confound)
