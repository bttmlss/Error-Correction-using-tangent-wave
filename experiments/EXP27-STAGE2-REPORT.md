# Exp-27 Stage 2 — 20-seed verdicts (V1/V2/V3/V4)

*2026-10-07. GREEN-LIT by Adrian ~00:44, V3 added. 320 trainings
(V1/V2/V3/V4 × 4 folds × 20 seeds) on the L23 real substrate, 629 s
wall. Rep 0 reproduces Exp-22 bit-exactly for all four verifiers
(max drift 0.0). Same hyperparams and seed schedule as the pilot —
reps 0–4 reproduce the pilot for V1/V2/V4. Per-fold checkpointing;
no runs dropped (degenerate runs kept and reported).*

---

## Plain-language summary

**V4 holds — the sign is real.** 76 of 80 runs learned negative β (95%),
and all four folds' 95% intervals sit cleanly below zero. The claim that
survives is the *sign*: "the smoothness verifier reliably induces
negative β." Magnitudes bounce with the seed (−0.38 to +0.07), so the
old "tightest cluster" language stays retired.

**V2 fails — "damping 4/4" does not survive.** Not a single fold's 95%
interval sits below zero (0/4), and the pooled 80-run interval is
[−0.026, +0.033] — tightly bracketing zero. This is the verdict the
power caveat demanded: judged on the pooled 20-seed interval, V2's β is
indistinguishable from zero across seeds. The original all-negative draw
was seed luck.

**V3 is new and mostly noise.** First seed distribution: 53/80 negative
(66%), only one fold's interval below zero, pooled interval
[−0.043, −0.003] — a weak negative lean that barely excludes zero, with
the pooled median |β| sitting exactly on the old 0.05 line. Neutral
reading: V3 does not reliably induce signed β.

**V1 scatters, as underdetermination predicts.** 25 reactive / 37
damping / 8 neither / 10 degenerate across 80 runs — a 12.5% chaos rate.
One nuance the pilot missed at n=5: degenerate runs are no longer all
positive-β. Three are sluggish-but-settled with *negative* β (eff
3.9–7.7), and one near-zero-β run wanders (eff 3.5). V1's chaos has (at
least) two flavors: blow-up (positive β, timeouts) and sluggish drift
(any sign, eff ≫ 3).

**The confound is resolved — decisively.** Fold explains essentially
*none* of the β variance at n=20: seed-within-fold fractions are 1.00
(V1), 1.00 (V2), 0.996 (V3), 1.000 (V4). The pilot's hint of fold
structure in V4 (frac_fold 0.156 at n=5) vanished with more seeds — it
was small-sample noise. Single-seed thetas were seed luck for
magnitudes, everywhere; the robust invariants are the *signs* (V4) and
the *scatter* (V1).

---

## Verdicts vs pre-registered expectations

| check | expectation | result |
|---|---|---|
| V4 sign | β < 0 in ≥ 90% of runs | **PASSED** — 76/80 (95.0%) |
| V2 damping | 95% CI below 0 in ≥3/4 folds AND pooled median\|β\| > 0.05 | **FAILED** — 0/4 folds below zero (magnitude condition met at 0.073, but the fold condition fails outright) |
| V1 scatter | mixed outcomes (underdetermination predicts scatter) | **CONFIRMED** — 25 / 37 / 8 / 10 reactive/damping/neither/degenerate |
| V3 | none (first distribution; neutral) | weak negative lean, mostly noise — 53/80 negative, one fold CI below zero |

## Per-verifier detail (β, n=20/fold, t₉₅ df=19)

**V2 — the verdict.** Per-fold 95% CIs:
size [−0.084, +0.054], temperature [−0.031, +0.074],
brightness [−0.065, +0.042], speed [−0.039, +0.080].
Means: −0.015 / +0.022 / −0.012 / +0.020 — all near zero, sds 0.11–0.15.
Pooled (n=80): mean +0.004, 95% CI [−0.026, +0.033]; median|β| = 0.073
(the 0.073 is spread, not signal — the CI is centered on zero).
**"Damping 4/4" is refuted; replace with "β indistinguishable from zero
across seeds" (pooled 80-run interval).**

**V4 — sign robust, magnitude seed-noisy.** Per-fold CIs all below zero:
size [−0.227, −0.163], temperature [−0.219, −0.119],
brightness [−0.200, −0.101], speed [−0.194, −0.116].
Pooled mean −0.167, CI [−0.189, −0.146]; range −0.375 to +0.067.
The 4 positive runs are all small (+0.030 to +0.066) and settle cleanly
(6–8 steps, eff ≤ 1.57): small positive β is harmless; magnitude kills.
Paper language: "V4 reliably induces negative β (76/80); magnitudes
vary with seed."

**V3 — first distribution.** 53/80 negative. Only temperature's CI below
zero ([−0.080, −0.015]); pooled mean −0.023, CI [−0.043, −0.003];
median|β| = 0.051. Verdict: no reliable signed-β induction; weak
negative lean, report neutrally.

**V1 — quantified underdetermination.** Per-fold CIs all straddle zero
(sds 0.23–0.35); range −0.577 to +0.729. Chaos rate 10/80 = 12.5%
(pilot: 15%): 1 blow-up (timeout, β=+0.201, eff 18.7), 9 sluggish
(settled, eff 3.5–7.7, β spanning −0.553 to +0.729). Median steps 8.25
vs 6.0 for the other verifiers.

## Variance decomposition (folds = groups, seeds = replicates)

| verifier | frac fold | frac seed-within-fold |
|---|---|---|
| V1 | 0.000 | 1.000 |
| V2 | 0.000 | 1.000 |
| V3 | 0.004 | 0.996 |
| V4 | 0.000 | 1.000 |

Seed explains essentially all β variance. (V4's pilot frac_fold of 0.156
did not replicate — small-sample noise.)

---

## Technical appendix

- **Code:** `tangent_experiment/exp27_stage2.py` (extends
  `exp27_multiseed.py`; Exp-22 loop imported verbatim; per-fold
  checkpointing added after the first launch died silently at 118/320
  with no checkpoint — the 118 partial runs were lost and redone from
  scratch; final run clean, `complete: true`).
- **Analysis:** `exp27_stage2_analyze.py` → `exp27_stage2_analysis.json`.
- **Results:** `exp27_stage2_results.json` (raw thetas per run; rep-0
  drift vs Exp-22 = 0.0 for all four verifiers).
- **Figure:** `figures/exp27_stage2_seed_betas.png` (per-seed β strips,
  fold means ± 95% CI, Exp-22 gold stars).
- **Seed schedule (pinned):** pg = SEED+8000+DIM·100+fold·10+vi+rep·100000;
  tune = SEED+1000+DIM·100+fold+rep·100000;
  eval = SEED+2000+DIM·100+fold (fixed across reps per verifier/fold).
  Same scheme as the pilot; reps 0–4 reproduce it bit-exactly.
- **V1 classification:** degenerate if timeout_rate > 0 or eff_med > 3
  (checked first); else reactive (β > +0.05), damping (β < −0.05),
  neither.
- Env: `~/workspace/venvs/llm/bin/python`. L23 cached embeddings only;
  no model loading.

## Paper implications

1. V2 "damping 4/4" → **"β indistinguishable from zero across seeds
   (pooled 80-run 95% CI [−0.026, +0.033])"** — the verdict is now
   closed, per the power caveat.
2. V4 "tightest cluster (range 0.06)" → **"consistent negative sign
   (76/80); magnitudes seed-variable (−0.38 to +0.07)"**.
3. V1 underdetermination quantified: **12.5% chaos rate**, two
   degenerate flavors (blow-up / sluggish drift), scatter spanning
   β ∈ [−0.58, +0.73].
4. V3: report the weak negative lean neutrally; no signed-β claim.
5. The fold×seed confound is resolved: **all β variance is
   seed-within-fold** — single-seed thetas were seed luck for
   magnitudes, in every verifier.
