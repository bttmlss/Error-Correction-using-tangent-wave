# Revision-Loop Atlas — STAGE 0.1 REPORT (instrument fix + re-validation)

**Date:** 2026-10-07 · **Status:** strict checkpoint — **VERDICT: FAIL**. Zero LLM calls made.
**Authority:** `revision-loop-atlas-SPEC.md` ("Stage 0.1" section, authorized ~10:45).
The frozen error-signal math (`revision_measure.py`) was untouched throughout.
**Determinism:** seed 1907 throughout.

## The short version

The adjudicated fix was implemented exactly as specified — continuous piecewise-linear
change-point model (one intercept, two slopes, change point; 4 parameters, continuity
forced at τ) plus dual-track Bar 0 (deterministic exact-match solve flags off the
change-point job). The instrument improved, but **not enough**: smooth-transition kink
recovery is 0.11–0.38 per class against the pre-registered 0.90 bar. Null protection
held (95.8%), the metric layer stayed 9/9, solve flags are perfect (1.00).

The precise failure mode is now localized: it is **not** model misspecification — the
CPL detector is near-oracle-efficient. It is a **signal-to-noise boundary**: at n=9,
the synthetic kink magnitudes sit below the change-point detection limit once
round-to-round jitter reaches σ≥0.05. At σ=0.02, three of four smooth classes clear
0.90. The 0.90 bar is unachievable on the current synthetic suite as specified — the
suite's kinks are too subtle for its noise, and no change-point formulation fixes that
at n=9.

Per the checkpoint rule: **no LLM calls happen.** The instrument needs another round,
or the gate needs re-scoping. Both options are laid out below; the call is Adrian's.

## Checkpoint scorecard (both contract sides)

| Contract side | Requirement | Measured | Verdict |
|---|---|---|---|
| (1) Null protection | ≥95% one-regime at n=9 | **0.958** | **PASS** |
| (2) Smooth-transition power, each class | ≥0.90 kink recovery | rate_change **0.26**, stall_improve **0.35**, give_up **0.11**, reversal **0.38** | **FAIL** |
| Metric layer (re-run) | 9/9 | 9/9 | PASS |
| Track A solve flags | ≥0.90 deterministic | 1.00 (all taus, both solve kinds) | PASS |

**Overall: FAIL.** Side (1) held — the original 95.5% was not sacrificed to buy power.
Side (2) failed on all four classes.

## What was built

**CPL fitter** (`revision_stage0_cpl.py`, verified by smoke test before the run):
e(t) = a + m1·t for t ≤ τ; e(t) = a + m1·τ + m2·(t−τ) for t > τ, implemented as
a + b1·t + b2·max(0, t−τ) (equivalent; m1=b1, m2=b1+b2). Grid search τ∈{1..n−2},
least squares for (a, b1, b2) given τ. BIC with k=4 (a, b1, b2, τ) vs k=2 null.

**Dual-track Bar 0:** Track A detects solve onsets deterministically from exact-zero
structure (first t>0 with e[t]==0 exactly and e[t−1]>0 — mirrors the exact-match flags).
Track B runs the CPL change-point on e(t) for continuous dynamics.

**Recalibration from scratch:** n-conditional ΔBIC null thresholds recomputed for the
CPL model (2000 nulls per n; the old table belonged to the retired 5-parameter version):

| n | 5 | 6 | 7 | 8 | **9** | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|------|----|----|----|----|----|----|
| p97 | 18.0 | 12.8 | 11.8 | 12.6 | **13.9** | 17.3 | 21.0 | 25.1 | 35.2 | 39.2 | 44.5 |

Still U-shaped in n (the close-out's finding holds for the new model); threshold at
n=9 dropped 15.35 → 13.89, as expected from removing one parameter.

## The failure mode, precisely

**It is not misspecification.** An oracle with the true τ known clears the calibrated
threshold only 8–38% of the time (rate_change 0.35, stall_improve 0.36, give_up 0.12,
reversal 0.38) — barely above the detector's own 0.11–0.38. The detector is
near-oracle-efficient; the tau search costs almost nothing. The problem is that the
signal itself is too small.

**It is signal-to-noise.** Recovery by noise level (n=9, τ=4, threshold 13.89):

| kink | σ=0.02 | σ=0.05 | σ=0.10 |
|---|---|---|---|
| rate_change | **0.92** | 0.15 | 0.02 |
| stall_improve | **0.98** | 0.25 | 0.08 |
| give_up | 0.29 | 0.02 | 0.01 |
| reversal | **0.99** | 0.26 | 0.02 |

At σ=0.02, three of four smooth classes clear the 0.90 bar — the instrument works
where SNR permits. At σ≥0.05 the kinks drown. Give-up (decay→flat, the subtlest slope
change) is hardest at every noise level.

**Why the CPL fix helped but couldn't close the gap:** it correctly removed the
over-parameterization (threshold 15.35→13.89; no more discontinuity bias — see below),
but no 4-parameter change-point test at n=9 can detect a −0.05→0 slope change buried
in σ=0.10 jitter. Lengthening trajectories does not help either (null threshold grows
superlinearly with n for both model versions — verified in Stage 0 and again here).

## Preserved finding: Stage 0's discontinuity bias

Stage 0's failed instrument is characterized, not discarded. The 5-parameter
free-intercept model had a **discontinuity bias**: solve-like jumps detected at 0.97
while smooth slope changes recovered at 0.09–0.44. The CPL instrument removes this
bias by construction (jumps are not representable; they belong to Track A), and the
characterization stands: Track B on solve-event curves fires at ~0.00 — the two tracks
do not interfere. Breakthrough-type sharp non-solve drops (0.35 level jump, no exact
match) fall *between* the tracks: Track A doesn't fire (no exact zeros), Track B
can't represent the jump (recovery ≈0.01). This is a characterized blind spot of the
dual-track design, reported here rather than hidden.

## What this means — three honest paths (Adrian's call)

**The gate, as pre-registered, is unachievable on the current synthetic suite.**
The suite's kink magnitudes sit below the change-point detection limit at its noise
levels, for any change-point formulation at n=9. That is a fact about the suite and
the statistics, not about LLM revision behavior (which remains unmeasured).

1. **Scoped acceptance.** Characterize Bar 0's power as a measured function of SNR
   (done above) and proceed to Stage 1 with Bar 0 explicitly scoped: it reliably
   detects kinks large relative to round-to-round jitter, and is blind below that
   boundary. Real trajectories reveal their actual jitter first; interpret Bar 0
   accordingly. *Risk, stated plainly:* low sensitivity biases the ≥75% retirement
   rule toward false retirement — a retirement under this instrument would need the
   caveat that subtle kinks are outside the detection limit.
2. **Different detection approach.** Targeted pattern tests (stall = flat second half;
   oscillation = autocorrelation structure) instead of generic change-point. More
   powerful for specific hypotheses, less general; a bigger redesign than 0.1.
3. **Re-examine the synthetic suite.** If real revision kinks are larger than these
   synthetics, the instrument may be adequate — but "the test was too hard" after a
   FAIL is goalpost-moving unless grounded in measured real-trajectory scales. Stage 1
   would have to measure first, which inverts the validation order the program
   committed to.

My read: the checkpoint did its job twice now. Whatever Adrian picks, the n-conditional
calibration table, the SNR power curve, and the discontinuity-bias characterization
carry forward — they are instrument knowledge, independent of the verdict.

## Files

- `revision_stage0_cpl.py` — CPL machinery + solve-flag path (the fix; spec-authorized)
- `run_stage01.py` — Stage 0.1 validation driver (deterministic, seed 1907)
- `revision_stage01_results.json` — every number (calibration, recovery grid, SNR
  diagnostic, oracle comparison, solve-flag and Track-B characterization, gate summary)
- `REVISION-STAGE01-REPORT.md` — this file
- `revision_measure.py` — frozen measurement pipeline, untouched (metric layer 9/9)

## Standing notes

- Zero LLM calls made in Stage 0.1. No Ollama, no models pulled, no API calls.
- Environment: 2 CPU cores; the full validation (calibration + suite + metric layer)
  runs in minutes.
- Nothing was tuned after seeing the numbers; the gate was frozen before the run.
