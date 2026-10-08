# Revision-Loop Atlas — STAGE 0 SYNTHETIC VALIDATION REPORT

**Date:** 2026-10-07 · **Status:** strict checkpoint — **VERDICT: FAIL**. Zero LLM calls made.
No Ollama installed, no models pulled, no API calls.
**Authority:** `revision-loop-atlas-SPEC.md` (DESIGN GREEN-LIT; all freezes applied).
**Determinism:** seed 1907 throughout.

## The short version

The measurement pipeline is exact and the false-positive control holds — but the
Bar-0 change-point detector **cannot reliably recover structural kinks at n=9**.
Pooled kink recovery is **0.29** against the pre-registered **0.90** bar. This is not a
bug; it is a statistical power limit: at n=9, the BIC change-point test with a
5-parameter two-regime model requires an RSS improvement factor of ~11×, which only
sharp discontinuities provide. Per the pre-registered rule, **no LLM calls happen** —
the instrument needs fixing first. The precise failure mode and the fix directions are
below. Nothing here was tuned after seeing the numbers; the bars were frozen before
the run.

## Checkpoint scorecard

| Bar | Requirement | Measured | Verdict |
|-----|-------------|----------|---------|
| (a) Metric layer exact | 9/9 synthetic pairs | 9/9 | **PASS** |
| (b) Single-regime null | ≥95% one-regime on fresh nulls | 0.955 at n=9 (all n ≥ 0.95) | **PASS** |
| (c) Kink recovery | ≥90% on structural kinks | **0.29 pooled** | **FAIL** |

**Overall: FAIL.** The detector does not meet the reliability bar for the pilot's
Bar 0 as specified.

## What was built and validated

**Measurement pipeline** (`revision_measure.py`) — the spec's frozen error-signal math,
implemented exactly, 9/9 metric checks passing:
- Pinned checkpoint `sentence-transformers/all-MiniLM-L6-v2`, exact revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (verified via Hub API; model files
  downloaded verbatim at that revision).
- Exact-match parser: `####`-number else last-numeric-token; normalized exact compare.
  Verified: `#### 72` → e=0.0; different-reasoning-same-number → e=0.0 (exact dominates);
  no-`####` fallback → e=0.0; "48.0" vs "48" → no match (documented edge).
- Near-paraphrase (wrong number): d=0.088 (small). Unrelated: d=1.0 (clipped, large).
  Ordering holds. Truncation at 4000 chars verified.
- Revision magnitude: identical texts → 0.0; paraphrase (0.254) < unrelated (1.0).
- Instrument note: embeddings vary by ~1e-7 across calls (batch numerics; characterized,
  5+ orders of magnitude below signal scales). Deterministic to 1e-6.

**Bar-0 machinery** (`revision_stage0.py`): change-point on e(t), one-regime linear
(k=2) vs two-regime DISCONTINUOUS piecewise linear with free intercepts (k=5:
a1,b1,a2,b2,τ — jumps representable because exact match forces e=0 exactly).
τ searched over {1..n−2}. Degenerate trajectories → one regime by definition.

**n-conditional calibration** (2000 nulls per n; null = linear/exponential/flat +
Gaussian noise, clipped [0,1]); operational threshold = p97 per n:

| n | 5 | 6 | 7 | 8 | **9** | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|------|----|----|----|----|----|----|
| p97 | 37.3 | 22.8 | 16.6 | 15.6 | **15.35** | 18.4 | 20.8 | 25.3 | 35.0 | 40.1 | 45.4 |

U-shaped in n (confirms and extends the 1a close-out): the 5-param model overfits few
points at small n and finds spurious breaks in noise at large n. n-conditional
calibration is mandatory, not optional.

## The failure mode, precisely

Kink recovery at n=9, threshold 15.35, noise σ∈{0.02,0.05,0.10} (200 reps per
kink × position):

| kink | τ=2 | τ=4 | τ=6 | mean |
|------|-----|-----|-----|------|
| breakthrough (0.35 drop) | 0.43 | 0.38 | 0.52 | 0.44 |
| give_up (decay→flat) | 0.07 | 0.13 | 0.07 | 0.09 |
| rate_change (−0.03→−0.12) | 0.23 | 0.35 | 0.23 | 0.27 |
| stall_improve (flat→decay) | 0.26 | 0.42 | 0.24 | 0.31 |
| reversal (decay→worsen) | 0.36 | 0.42 | 0.26 | 0.35 |
| **pooled (bar c)** | | | | **0.29** |
| solve (jump to exact 0) | 0.97 | 0.71 | 0.47 | 0.72 |
| solve_leave | 0.10 | 0.31 | 0.50 | 0.30 |
| weak_kink (probe only) | 0.04 | 0.12 | 0.04 | 0.07 |

**Why it fails (mechanism, not just numbers):** at n=9 with a 5-parameter two-regime
model, the BIC penalty is 3·log(9)≈6.6, but the null ΔBIC distribution is wide
(p97=15.35) because the flexible model overfits noise. A kink needs ΔBIC>15.35, i.e.
an RSS improvement factor of ~11×. Only sharp discontinuities clear that bar. Smooth
slope changes — however real — do not.

**It gets worse with n, not better:** null p97 grows superlinearly (15@9 → 45@15),
while kink signals grow only linearly. Power at n=15/20 is *lower* than at n=9
(verified: solve recovery 0.72@9 → 0.40@15 → 0.30@20). Lengthening trajectories is
NOT a fix for this detector.

## What the detector CAN do (honest capabilities)

- **False-positive control:** 95.5% correct one-regime calls on fresh nulls at n=9.
  It does not hallucinate regimes on smooth data.
- **Large interior discontinuities:** solve-like jumps detected at 97% (τ=2) / 71%
  (τ=4); degrades near edges (47% at τ=6).
- **Deterministic solve detection exists independently:** the exact_match flags
  identify solve events with certainty — the most important real-world regime change
  does not need the change-point detector at all.

## Fix directions (for whoever redesigns the instrument)

1. **Reduce model flexibility.** The 5-param free-intercept model overfits at n=9.
   A constrained two-regime family (or a test targeted at level shifts specifically)
   would lower the null threshold and raise power for jumps.
2. **Split the job.** Solve events via exact_match flags (deterministic, perfect);
   change-point only for non-solve regime changes. Don't ask one test to do both.
3. **Accept the detection limit.** If Bar 0 is re-scoped to "large discontinuities
   only," the current detector passes — but the retirement rule must then be
   reworded, because subtle kinks would be systematically missed (bias toward
   one-regime calls, i.e., toward retirement).
4. **Do not lengthen trajectories** expecting more power from this BIC formulation —
   verified to backfire.

## Files

- `revision_measure.py` — frozen measurement pipeline (metric layer: PASS)
- `revision_stage0.py` — Bar-0 machinery, synthetic generators, metric pairs
- `run_stage0.py` — validation driver (deterministic, seed 1907)
- `revision_stage0_results.json` — every number (calibration, rates, recovery grid)
- `REVISION-STAGE0-REPORT.md` — this file
- `.stage0-venv/` — isolated venv (torch CPU + sentence-transformers)
- `~/.hf-cache/manual/` — model files verbatim at pinned revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`

## Standing notes

- Environment: 2 CPU cores, no GPU. Embeddings on CPU are fast enough for the
  pilot's scale (ms per text).
- No LLM calls were made at any point in Stage 0. The checkpoint did its job:
  it caught an underpowered instrument before any trajectories were spent.
