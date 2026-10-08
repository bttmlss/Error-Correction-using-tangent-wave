# REVISION-LOOP ATLAS — CLOSEOUT (2026-10-07)

## Bar 0 execution & retirement

> "The state hypothesis is retired for local Gemma 2B × GSM8K-style numeric math
> tasks × the neutral revision prompt × the frozen exact-match/embedding
> measurement pipeline × the 9-round horizon.
>
> Under this scope, multi-round LLM revision trajectories are adequately described
> without recurring dynamical states. The model exhibits simple single-regime
> behavior with monotonic completion: it either remains stuck on its initial
> response, transitions deterministically to a correct answer via a single solve
> onset, or declines to re-answer via repetitive self-praise commentary."

Adjudicated by Adrian 2026-10-07 ~19:37. Holding the 18<20 tripwire binding would
have been a mechanical misapplication of a power rule designed for edge cases, not
to override a statistically decisive result.

## The decisive numbers (Stage 1.1, carry-forward corrected)

- 30 trajectories × 9 rounds, 270 real Gemma-2B calls (temp 0), zero errors.
- Frozen 4-detector battery: Track A 6 / B1 0 / B2 0 / B3 0
  (calibrated null expectations 0.0 / 1.11 / 0.93 / 0.0).
- All 6 non-clean trajectories are solve onsets (wrong→right) — the intended
  behavior of a revision loop, not exotic states.
- **0/18 exotic firings** (stall/oscillation/divergence) across the 18 informative
  trajectories. At 20% true prevalence, P(0/18) = 0.8^18 ≈ 0.018 → 98.2% confidence
  exotic non-single-regime states are negligible in this scope.
- Bar 0: 24/30 = 80% zero-firing ≥ 75% → FIRES.

## Power caveat (documented, not hidden)

- Informative trajectories: 18/30 < the frozen 20-tripwire. The tripwire was
  overruled by adjudication (see above), not silently dropped.
- 12 of the 24 clean trajectories are non-informative (vacuous zeros); among
  informative trajectories the clean fraction is 12/18 = 67%.
- Retirement is therefore strong against *exotic* regimes (98.2% as computed) and
  weaker against the claim "no nontrivial dynamics whatsoever" — which was never
  the hypothesis under test.

## The methodological ledger (the real discovery of the pilot)

Four distinct failure modes that corrupt dynamical-state research in LLMs,
each caught before a false inference:

1. **Discontinuity bias** (Stage 0.0): free-intercept change-point models chase
   vertical step functions; sharp solves detected, smooth transitions missed.
2. **SNR wall** (Stage 0.1): continuous models drown smooth transitions in
   measurement noise at n=9 (σ≥0.05 → recovery ≤0.26; near-oracle-efficient).
3. **Curvature confound** (Stage 0.2): residual kink fitting reads exponential
   curvature as sharp kinks (B4: 28.6% FPR; dropped, gate not weakened).
4. **Commentary confound** (Stage 1.0→1.1): the volunteer declines to re-answer
   via self-praise 27% of the time; scoring that as e≈0.9 manufactures
   oscillation/divergence/solve spikes. Fixed by the carry-forward rule
   (no-answer round → e(t)=e(t−1), flagged non-revision) — chosen over the prompt
   fix, which would have steered the volunteer and broken anti-circularity.

## What was spent

- Stages 0–0.2: zero LLM calls (three instrument failures caught synthetically).
- Stage 1.0: 270 calls, ~3 h — revealed the commentary confound.
- Stage 1.1: zero new calls — reprocessing only.
- Total: 270 LLM calls, one local 2B model, no API spend.

## Files

- `revision-loop-atlas-SPEC.md` — full spec with dated entries
- `revision_loop/revision_loop_raw.jsonl` — 30×9 recorded rounds, full texts
- `revision_loop/revision_loop_results.json` — frozen-pipeline measurements
- `revision_loop/revision_loop_results_11.json` — carry-forward corrected
- `revision_loop/REVISION-STAGE1-REPORT.md` — the confounded run (evidence)
- `revision_loop/REVISION-STAGE11-REPORT.md` — corrected analysis
- `revision_loop/REVISION-ATLAS-CLOSEOUT.md` — this file
- `ATLAS-ONE-PAGER.md` — dense brief of the whole arc
- `revision_stage0*.py`, `revision_stage01*`, `revision_stage02*` — the
  three failed instruments (preserved as the autopsy record)

## Standing principle (unchanged)

Don't ask the atlas to discover states until a state model is demonstrated
necessary. The synthetic atlas retired the two-state grammar; the revision-loop
atlas retires the state hypothesis for this scope. Neither retirement generalizes
beyond its scope — that is what scope-bounding is for.
