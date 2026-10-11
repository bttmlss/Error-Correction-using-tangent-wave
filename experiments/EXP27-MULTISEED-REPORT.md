# Exp 27D — Multi-Seed Pilot Report

*2026-10-07. 60 trainings: V1/V4/V2 history-learner cells × 4 folds × 5 seeds.
Stage 1 of the staged multi-seed plan (Stage 2, 20-seed, NOT run).*

## Plain-language headline

**Seeds matter more than folds — and the paper's weakest claim just broke.**
We re-ran the verifier-selection training 5 times per fold to separate
"the fold made it do that" from "the seed made it do that." Three
verdicts: **V4 holds** — 19 of 20 runs learned negative β, so "the
smoothness verifier induces damping" survives as a sign claim (though the
exact number bounces around with the seed). **V2 breaks** — its β is seed
noise hovering around zero, so "damping 4/4" was seed luck and has to go.
**V1 scatters exactly as predicted** — reactive, damping, flat, and
degenerate outcomes across seeds, including 3 chaotic blow-ups, which is
what "underdetermined" looks like when you roll the dice 20 times. The
variance math is blunt: 84–100% of the β variance is seed-within-fold,
not fold. The single-seed thetas were mostly seed luck — for magnitudes.
The signs are the robust part.

## Verdicts vs pre-registered expectations

| check | expectation | result |
|---|---|---|
| V4 sign | β < 0 in ≥ 90% of runs | **PASSED** — 19/20 (95%) |
| V2 damping | 95% CI below 0 in ≥3/4 folds AND pooled median\|β\| > 0.05 | **FAILED** — 0/4 folds below zero; pooled median\|β\| = 0.061 |
| V1 scatter | mixed outcomes (underdetermination predicts scatter) | **CONFIRMED** — 5 reactive / 9 damping / 3 neither / 3 degenerate |

## V4: sign robust, magnitude seed-noisy

β across 20 runs ranges −0.281 to +0.041 (fold means −0.22/−0.16/−0.10/
−0.13). The single-seed "tightest cluster (range 0.06)" does **not**
survive contact with seeds — the robust invariant is the *sign*, not the
value. The one positive run (brightness, β=+0.041) still settled cleanly
(6 steps, eff 1.57): small positive β is harmless; it's magnitude that
kills (cf. Exp-26's boundary at β≈+0.35). Paper language to fix: "V4
induces the tightest β cluster" → "V4 reliably induces negative β
(19/20); magnitudes vary with seed."

## V2: "damping 4/4" is refuted

Fold means: −0.022/+0.034/+0.007/+0.026 — every 95% interval straddles
zero. The original all-negative draw (−0.22/−0.03/−0.06/−0.05) was a
~4% luck event, not a finding. V2's history term is seed noise around
zero; the overshoot penalty does not reliably buy damping. The honest
paper line: "V2 showed negative β in the single-seed run, but across
seeds its β is indistinguishable from zero — the penalty's effect, if
any, is below the seed-noise floor."

## V1: underdetermination, quantified

Outcome rates across 20 runs: reactive (β>0.05) 5, damping (β<−0.05) 9,
neither 3, degenerate (timeout or eff>3) 3 — a 15% chaos rate. All three
degenerate runs had β>+0.23 with eff 4.1–5.7, landing in the same
neighborhood as Exp-26's positive-β blow-up boundary. Scatter *is* the
prediction here, and it confirmed.

## Variance decomposition (the confound, resolved)

One-way random effects per verifier (folds = groups, seeds = replicates;
seed-within-fold is the residual — no further replication exists):

| verifier | frac fold | frac seed-within-fold |
|---|---|---|
| V1 | 0.087 | **0.913** |
| V2 | 0.000 | **1.000** |
| V4 | 0.156 | **0.844** |

Seed dominates everywhere. For V1 and V2 this means the original thetas
were seed luck, full stop. For V4 it means the *magnitudes* were seed
luck while the *sign* is verifier-induced — which is precisely why the
paper's claims should be stated in signs, not values.

## Timing (for the Stage-2 decision)

Mean 2.3 s per training; 60 trainings in 137 s wall. Stage 2 (20 seeds ×
4 folds × 3 verifiers = 240 trainings) would take **~9–10 minutes, not
overnight** — the spec's cost framing was wrong because the cached
substrate removed model loading. Cheap enough to run any time; the green
light is still required per the staged plan.

## Technical appendix

- **Harness check:** rep 0 reproduces Exp-22 thetas bit-exactly
  (max drift 0.0 across all 12 cells) — the training loop is verbatim.
- **Seed schedule (pinned):** pg = 17911254+8000+400+fold·10+vi+rep·100000;
  tune-noise = 17911254+1000+400+fold+rep·100000; eval noise fixed per
  fold across reps (17911254+2000+400+fold), so thetas are compared on
  identical held-out conditions and the variance is pure learning noise.
- **Bug caught by the harness check:** the first run generated each
  trial's tune noise from a fresh same-seed rng (identical noise on all
  18 trials); rep-0 drift came back 0.67 instead of 0.0. Fixed to
  sequential draws per Exp-22 and re-ran; those results were discarded.
- **Classification rule (V1):** degenerate if timeout_rate>0 or
  eff_med>3, else reactive β>0.05 / damping β<−0.05 / neither.
- **95% intervals:** t-interval, df=4.
- No LLM training anywhere; models observational-only throughout.

## Files

- `exp27_multiseed.py` — pilot harness (imports Exp-22 loop verbatim)
- `exp27_multiseed_results.json` — 60 thetas + fingerprints + timing
- `exp27_multiseed_analysis.json` — criteria verdicts, intervals, decomposition
- `figures/exp27_seed_betas.png` — per-seed β strips per verifier (rep 0 = Exp-22 ★)
- `exp27_multiseed_run.log` — full training log
