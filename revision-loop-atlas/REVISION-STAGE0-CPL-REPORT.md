# Stage 0 re-validation: continuous piecewise-linear detector — FAIL

**Run:** 2026-10-07 ~10:27 ET · **Instrument:** CPL (continuous piecewise-linear) change-point + deterministic solve-flag split · **Seed:** 1907 · **Code:** `revision_stage0_cpl.py` · **Results:** `revision_stage0_cpl_results.json`

## Plain-language verdict

I built the recommended fix exactly as specified — a continuous two-regime
model (no jump parameter) plus solve-events detected from the exact-match
flags instead of the change-point detector — and re-ran Stage 0 on the same
synthetic trajectories as the failed run. **It still fails.** The smooth
changes (stalls, give-ups, gradual slope shifts) that the old detector missed
are missed by the new one too. The problem is not the extra jump parameter;
it is the noise itself. At the trajectory lengths the pilot uses (n=9), a
two-regime fit on a smooth slope change simply does not separate from what a
two-regime fit can hallucinate in pure noise.

## The scorecard

| Bar | Target | CPL result |
|---|---|---|
| (a) Metric layer exact | 9/9 | carried over PASS (frozen measurement untouched) |
| (b) Fresh-null one-regime | ≥0.95 | **PASS** (0.958 at n=9) |
| (c) Smooth-kink recovery | ≥0.90 pooled | **FAIL — 0.219 pooled** |
| (d) Solve flags | ≥0.90 | **PASS** (1.000 everywhere) |

Per-kind recovery at n=9, τ=4 (200 reps each):

| Kind | Old model (k=5) | CPL (k=4) |
|---|---|---|
| breakthrough | 0.44 | ~0.02 |
| give_up | 0.09 | ~0.08 |
| rate_change | 0.27 | ~0.30 |
| stall_improve | 0.31 | ~0.35 |
| reversal | 0.35 | ~0.36 |

The pooled number barely moved (0.29 → 0.219). Two things are worth seeing in
this table. First, the CPL constraint bought almost nothing: the null
threshold fell only from 15.35 to 13.89. Second, it *lost* breakthrough —
the one kind the old model could catch — because the jump parameter that
overfit noise was also the parameter that represented level jumps. The cure
ate the one thing that was working.

## Where the power actually lives: noise

Stratifying recovery by noise level (τ=4, 200 reps):

| Kind | noise 0.02 | noise 0.05 | noise 0.10 |
|---|---|---|---|
| give_up | 0.375 | 0.01 | 0.00 |
| rate_change | **0.935** | 0.145 | 0.015 |
| stall_improve | **0.96** | 0.18 | 0.035 |
| reversal | **0.975** | 0.35 | 0.06 |
| breakthrough | 0.00 | 0.00 | 0.00 |

At the lowest pilot-plausible noise the detector is fine; at 0.05 and above
it collapses. The binding constraint is the noise level of the real e(t)
curves — which is not a property of the instrument and cannot be known until
real trajectories exist. (And the noise in the synthetics stands in for
trajectory-to-trajectory irregularity, not measurement error: the frozen
measurement is deterministic, so real "noise" is model behavior, not sensor
error.)

## A deeper finding, independent of the model

The null threshold is U-shaped in n and grows superlinearly afterward:

- n=7: p97 = 11.83 (minimum) · n=9: 13.89 · n=12: 25.08 · n=15: 44.52

This held for the old model too (and was the 1a close-out's n-dependence
finding). So "run longer trajectories" is not a rescue, for either model.
More rounds = more room for the knot search to overfit noise.

## What this earns

1. The quick fix — constrain to CPL — is falsified as implemented. Do not
   amend the spec with it.
2. Bar 0 as designed (BIC change-point at n=9, p97 calibration) is powered
   only for sharp discontinuities and deterministic solves. Smooth slope
   changes live below the noise floor at any noise ≥ 0.05.
3. The honest branching point is now: (a) accept the instrument as
   discontinuity-powered and scope smooth changes out of Bar 0; (b) detect
   stalls from the frozen Δe/magnitude signals instead of e(t) kinks;
   (c) a different statistic entirely. None of these is a spec amendment
   until Adrian picks one.

Zero LLM calls spent. The checkpoint keeps doing its job.
