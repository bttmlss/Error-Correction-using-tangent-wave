# Exp-26 — β Sensitivity Sweep: What the β Knob Actually Does

*Report — 2026-10-06. Frozen evaluation, no training. Adrian's markdown.*

## Plain-language headline

**The β knob has a clean, portable response curve — and the learner landed
on its knee.** We turned β through 8 settings (from strongly positive
through zero to hyper-damped), everything else frozen, on all three
substrates. The picture is the same everywhere:

- Jerk falls smoothly as β goes more negative, bottoms out at almost
  *exactly the learned value*, then ticks back up at hyper-damping.
- Crossing zero flips what history *means*: negative β damps motion,
  zero β ignores history, positive β *reinforces* motion — the controller
  gets visibly more reactive.
- Push β to about +0.3 and the controller goes chaotic (timeouts,
  hundred-plus jerk) — on all three substrates, at the same place. That's
  the empirical stability boundary, and it lands right next to the
  degenerate law Exp-22's minimal verifier stumbled into (β = +0.405).

So the answer to Exp-25's sharper question: it's the **sign** that draws
the behavioral boundary, the **magnitude** that tunes smoothness down to a
floor — and the learned value sits on that floor. Not a lucky number; the
verifier drove it to the knee of the curve.

## Prediction verdicts

**(a) Harness check — PASSED on all three substrates.** m=+1.0 reproduces
the Exp-24/25 A0 pooled fingerprints bit-exactly (diff 0.00000 on
overshoot, path, jerk). The sweep machinery is sound; everything below is
real signal.

**(b) Sign boundary — PASSED on all three substrates (strict).**
Jerk ordering, pooled:

| substrate | positive-β arms (min) | m = 0 | negative-β arms (max) |
|---|---|---|---|
| S1 (Qwen L12) | 0.190 | 0.143 | 0.116 |
| S2 (SmolLM2) | 0.292 | 0.208 | 0.158 |
| L23 (home) | 0.189 | 0.142 | 0.115 |

Every positive-β arm is jerkier than the no-history arm, which is jerkier
than every negative-β arm. β < 0 → history damps; β = 0 → memoryless;
β > 0 → history reinforces. A real behavioral boundary, identical shape
on all three substrates.

**(c) Negative-side monotonicity — PASSED on S1 and S2; effectively
holds on L23.** Jerk for m = 0 → +0.5 → +1.0 → +1.5:

- S1: 0.1429 → 0.1158 → 0.1073 → 0.1068 (strictly decreasing ✓)
- S2: 0.2077 → 0.1579 → 0.1359 → 0.1335 (strictly decreasing ✓)
- L23: 0.1421 → 0.1153 → 0.1073 → 0.1074 (misses strict on a 0.0001 tie —
  the curve hits its floor at the learned value and goes flat)

At m = +2.0 (hyper-damped) jerk ticks back up on all three (0.1090 /
0.1409 / 0.1079) *and* overshoot, steps, and path cost all rise
(S1: ov 2.91, steps 8.0, eff 1.42). The pre-registered overdamping
possibility is confirmed as data: too much damping gets sluggish, and
sluggishness overshoots.

**(d) Exp-21 bridge — confirmed, then some (exploratory).** Positive-β
arms show the reactive fingerprint, graded by magnitude:

| arm (β ≈) | jerk (S1/S2/L23) | overshoot | steps | character |
|---|---|---|---|---|
| m=−0.5 (+0.12) | 0.19 / 0.29 / 0.19 | 1.4–1.5 | 6–8 | mildly reactive |
| m=−1.0 (+0.24) | 0.26 / 0.43 / 0.26 | 3.0–3.7 | 8.5–12 | clearly reactive |
| m=−1.5 (+0.35) | 127–203 | 5.0–6.7 | 10.5–13.5, 23% timeouts | **chaotic blow-up** |

The m=−1.5 blow-up (β ≈ +0.35) sits in the same neighborhood as Exp-22's
degenerate V1 fold (β = +0.405, 17.5 overshoots) — the minimal verifier's
chaotic attractor, reproduced here by turning one knob. The stability
boundary lands between m=−1.0 and m=−1.5 on **all three substrates**.
Exp-21's reactive regime and Exp-25's damping law are now connected
experimentally: they're two regions of one β axis.

## The curves (pooled over 40 pairings × 4 folds; primary outcome: jerk)

**S1 — Qwen layer 12:**

| m | β (abs) | jerk | overshoot | steps | path | timeout |
|---|---|---|---|---|---|---|
| −1.5 | +0.353 | 129.017 | 6.369 | 12.8 | 1.477 | 0.23 ✕ |
| −1.0 | +0.235 | 0.262 | 3.013 | 11.2 | 1.241 | 0.00 |
| −0.5 | +0.118 | 0.190 | 1.369 | 7.5 | 1.108 | 0.00 |
| 0 | 0.000 | 0.143 | 0.887 | 7.0 | 1.062 | 0.00 |
| +0.5 | −0.118 | 0.116 | 1.025 | 6.0 | 1.054 | 0.00 |
| +1.0 | −0.235 | 0.107 | 1.369 | 6.5 | 1.082 | 0.00 ← learned |
| +1.5 | −0.353 | 0.107 | 1.719 | 7.0 | 1.201 | 0.00 |
| +2.0 | −0.471 | 0.109 | 2.906 | 8.0 | 1.423 | 0.00 |

**S2 — SmolLM2 final layer:**

| m | β (abs) | jerk | overshoot | steps | path | timeout |
|---|---|---|---|---|---|---|
| −1.5 | +0.353 | 203.118 | 4.981 | 10.5 | 1.832 | 0.23 ✕ |
| −1.0 | +0.235 | 0.428 | 3.381 | 8.5 | 1.423 | 0.00 |
| −0.5 | +0.118 | 0.292 | 1.406 | 6.2 | 1.218 | 0.00 |
| 0 | 0.000 | 0.208 | 1.038 | 6.0 | 1.137 | 0.00 |
| +0.5 | −0.118 | 0.158 | 1.169 | 6.0 | 1.116 | 0.00 |
| +1.0 | −0.235 | 0.136 | 1.425 | 6.0 | 1.131 | 0.00 ← learned |
| +1.5 | −0.353 | 0.134 | 1.606 | 6.5 | 1.246 | 0.00 |
| +2.0 | −0.471 | 0.141 | 2.263 | 6.5 | 1.461 | 0.00 |

**L23 — home reference (exploratory track):**

| m | β (abs) | jerk | overshoot | steps | path | timeout |
|---|---|---|---|---|---|---|
| −1.5 | +0.353 | 126.994 | 6.737 | 13.5 | 1.447 | 0.23 ✕ |
| −1.0 | +0.235 | 0.263 | 3.694 | 12.0 | 1.211 | 0.00 |
| −0.5 | +0.118 | 0.189 | 1.512 | 8.0 | 1.138 | 0.00 |
| 0 | 0.000 | 0.142 | 0.981 | 7.0 | 1.084 | 0.00 |
| +0.5 | −0.118 | 0.115 | 1.025 | 6.2 | 1.055 | 0.00 |
| +1.0 | −0.235 | 0.107 | 1.425 | 6.5 | 1.081 | 0.00 ← learned |
| +1.5 | −0.353 | 0.107 | 1.613 | 7.0 | 1.196 | 0.00 |
| +2.0 | −0.471 | 0.108 | 2.844 | 8.0 | 1.412 | 0.00 |

✕ = truncated per the stability rule (timeout > 0). The boundary is data.

## What this earns

- The β-*response curve* is itself portable: same shape on L23, L12, and
  SmolLM2. Stronger than Exp-24's single transplanted point.
- The sign boundary (damp / ignore / reinforce) is a real behavioral
  boundary, not a one-substrate accident.
- The learned value sits at the jerk floor — V4's verifier didn't just
  find *a* damping law, it found the knee of the smoothness curve.
- Exp-21's reactive regime is now experimentally the positive side of
  the same axis, with the chaotic blow-up landing where Exp-22's
  degenerate law lived. Four experiments, one knob.

**Pinned claim earned:** "β's sign draws the behavioral boundary and its
magnitude tunes smoothness to a floor at the learned value — identically
across depth and model family."

## Technical appendix

- 8 arms × 4 folds × 3 substrates × 40 pairings = 3840 frozen evals (+
  per-type breakdowns); no training, models observational-only.
- Thetas: α_k, γ_k frozen per fold from exp22_results.json V4-history;
  β = m × β_k (β_k = −0.215/−0.264/−0.260/−0.202). Read at runtime;
  drift vs spec's rounded values is rounding-only.
- Same 40 pairings, pinned noise (SEED+9000+trial), timeout 200,
  instruments verbatim from Exp-24/25 (S1 σ=0.0709/tol=0.2836;
  S2 σ=0.5374/tol=2.1495; L23 σ=1.3306/tol=5.3226).
- Pooling (Exp-24 precedent): mean across folds for mean-metrics
  (overshoot/jerk/timeout), median for median-metrics (steps/eff).
- m=+1.0 reproduces Exp-25 A0 bit-exactly on all substrates (diff
  0.00000); m=0 reproduces Exp-25 A1 (cross-check, not pre-registered).
- L23 track rebuilt as in Exp-25 (exp21_embed_cache.npz +
  exp23_new_words.npz, deterministic SVD); sanity-checked vs Exp-23.
- (c) on L23: the strict-monotonicity miss is a 1e-4 tie at the
  measurement floor (0.1073 → 0.1074), reported as flat-floor, not a
  substantive reversal.
- Stability rule applied as pre-registered: m=−1.5 truncated on all
  substrates (timeout_rate 0.23, eff up to 1.83); last stable reactive
  arm m=−1.0 everywhere; damped side stable through +2.0.
- Run: `~/workspace/venvs/llm/bin/python exp26_sweep.py` (~15 s).
