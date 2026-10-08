# Revision-Loop Atlas — STAGE 0.2 REPORT: Targeted Pattern Battery

**Date:** 2026-10-07 · **Pre-registered** (Adrian's call ~11:20) · **Zero LLM calls**
**Files:** `revision_stage02.py` (frozen detectors) · `run_stage02.py` (driver) ·
`revision_stage02_results.json` (every number)

## The short version

**Verdict: FAIL as specified — because B4 cannot be validated.** But this is a
precise, informative failure, and the primary battery validates cleanly:

| Detector | Null FPR (valid) | Pattern recovery | Bar |
|---|---|---|---|
| Track A — Solve (deterministic flags) | 0.0% | 100% | PASS |
| B1 — Stall (high-error + flat slope) | 3.7% | 99.0% | PASS |
| B2 — Oscillation (reversals > noise) | 3.1% | 98.9% | PASS |
| B3 — Divergence (sustained +Δe) | 0.0% | 96.6% | PASS |
| B4 — Residual kink (CPL change-point) | **28.6%** | 40.6% | **FAIL** |

Four-detector family-wise FPR (Track A + B1–B3): **6.7%** — well under the 15% bar.
With B4 included: 35.1%.

The strict gate fails on B4. The recommendation below is to drop B4 (documented),
not to weaken the gate.

## What B4's failure means (the mechanism, precisely)

B4 is the Stage 0.1 CPL change-point detector plus a |Δslope| ≥ 3σ̂ gate. It fails
because **a piecewise-linear change-point model cannot distinguish exponential
curvature from kinks at n=9**:

- B4's false-positive rate tracks null curvature strength: 2.9% on slow decays →
  8.3% on gentle exponentials (ρ∈[0.80,0.95]) → **28.6% on the full null family**.
- The |Δslope| ≥ 3σ̂ gate does not filter curvature — curvature produces large
  |Δslope| relative to CPL residuals, so the gate never binds on nulls.
- No threshold rescues it (ROC on the null family): thr 13.89 → 4.0% FPR / 63%
  recovery; thr 20 → 0.7% / 33%. The ROC curve never reaches the (≤5%, ≥90%)
  corner. This is structural, not a calibration problem.
- B4's recovery on large kinks is only 41% — and sharp non-solve breakthroughs
  (0.35 drops without exact match) fall between the tracks entirely.

This is the third strike against generic change-point detection in this program,
each one more precise than the last:
- Stage 0.0: discontinuity bias (great on jumps, blind to smooth changes).
- Stage 0.1: SNR wall (even an oracle with true τ recovers only 8–38%).
- Stage 0.2: curvature confound (cannot separate exponential curvature from kinks).

The through-line: **change-point models answer "did the slope change?", but the
science needs "did the behavior change?"** — and at n=9 those are different
questions. The pattern battery (B1–B3 + Track A) asks the second question directly,
with low-degree-of-freedom operational definitions, and it works.

## What validated cleanly

**Frozen thresholds** (set on calibration-half nulls only, never on patterns):
- B1: |slope| < 0.055 over rounds 3–8, with mean(e) > 0.4 → FPR 3.7%
- B2: ≥3 reversals with both |Δe| > 0.10 → FPR 3.1%
- B3: ≥5 positive Δe AND e₈−e₀ > 0.03 → FPR 0.0%
- Track A: exact-match flag transition → FPR 0.0%, recovery 100%

**Recovery** (independent gross-pattern synthetics, pooled over σ∈{0.02,0.05,0.10}):
stall 99.0%, oscillation 98.9%, divergence 96.6% (86.8% at σ=0.10 for the weaker
slope variant — the only sub-90 cell, documented), solve 100%.

**Null discipline held:** thresholds came from empirical nulls, never from theory.
The "decay forbids positive drift" premise was never used — B3's threshold was
calibrated on noisy nulls that do produce local positive differences.

**Gray zone, documented:** on very slow decays (the stress subset, not part of the
gate), B1's FPR is 60% — it cannot distinguish slow steady improvement from a
stall. This is an acknowledged limitation for Stage 1 interpretation, not a hidden
one. B2/B3 are unaffected (6.2% / 0.2% on stress).

## Recommendation

**Drop B4 from the validated battery; do not weaken the gate.** The validated
instrument is Track A + B1 + B2 + B3:
- Per-detector FPR ≤ 3.7% everywhere (bar: ≤5%).
- Family-wise FPR 6.7% (bar: ≤15%).
- Recovery ≥ 96.6% per pattern class (bar: ≥90%).

B4's niche — sharp non-solve breakthroughs — remains uncovered. That is a
documented limitation, not a silent gap. If breakthrough detection becomes
scientifically necessary, it needs a detector designed for discontinuities, not a
retrofit of the change-point machinery that just failed three validations.

## Preserved failure sequence (methodological result)

- Stage 0.0: generic two-regime detector had discontinuity bias.
- Stage 0.1: removing the bias exposed the SNR wall.
- Stage 0.2: operational pattern detectors validate; residual change-point does
  not (curvature confound).

No LLM calls have been spent. The instrument-characterization program keeps
paying: we now know exactly what each detector can and cannot see, before any
model trajectory exists.

## Methods (second)

Detectors operate on e(t), t=0..8 (n=9), plus exact-match flags for Track A.
All randomness from numpy Generator(seed=1907) with spawned streams.
Null family: single-regime exponential (a∈{0.6,0.9}, ρ∈{0.85,0.92}) and linear
(a∈{0.6,0.9}, b∈{0.05,0.10}) decay, σ∈{0.02,0.05,0.10}, clipped [0,1]; 36,000
trajectories split calibration/validation halves. "Ordinary steady improvement";
very slow decays form a documented stress subset. Pattern synthetics (independent
seeds): flat stalls at 0.55/0.70, decay-then-flat stalls, rising-error divergence
(slopes 0.07/0.10), alternating oscillation (amplitudes 0.12/0.18), solve-flag
sequences, large kinks for B4. CPL math verified bit-identical to Stage 0.1
(max |ΔBIC| diff 0.0 over 300 random trajectories). exact_match re-verified 6/6
on synthetic text pairs (Stage 0's 9/9 stands).
