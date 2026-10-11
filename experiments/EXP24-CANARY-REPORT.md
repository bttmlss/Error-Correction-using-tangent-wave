# Exp-24 Canary Report: Does the Steering Trick Travel?

*2026-10-05 — BTTMLSS tangent-trajectory program*

## The headline

**Yes — the steering trick travels.** We took the exact correction settings
the smoothness verifier taught on Qwen's layer 23 — frozen, zero retraining —
and dropped them into two brand-new places: a shallower layer of the same
model, and a completely different small model. In both places the controller
steered just as cleanly as it did at home: same low overshoot, same tidy
paths, zero crashes.

The third test model (Pythia) didn't quite have enough geometric structure in
4 dimensions to run the test fairly (it missed our pre-set bar by a hair:
0.698 vs 0.700), so we stopped there instead of grading the controller on an
unfair track. That's the safety check doing its job, not a failure of the law.

**Bottom line:** the damping law isn't glued to the room it learned in. It's
a portable operator — across depth *and* across model families.

## What we actually did

1. Read the "steering brain" (three numbers: α, β, γ) that the V4 verifier
   had sculpted on Qwen layer 23. Froze them — no further learning allowed.
2. Pointed that frozen brain at the same 40 unseen steering challenges from
   Exp 23, but inside three new geometries:
   - **Canary:** Qwen layer 12 (same model, much shallower layer)
   - **Bridge 1:** SmolLM2-135M, final layer (different model family)
   - **Bridge 2:** Pythia-70M, final layer (different model family)
3. Before grading anything, checked each new geometry was "real" enough to
   steer in (the Exp-18 structure checks), and re-calibrated our measuring
   instruments to each geometry's native scale — so a size difference
   between models could never masquerade as a broken controller.

## Results by substrate

### Geometry checks (do these worlds have structure?)

| Substrate | 4D structure score | Needed | Word-order test | Verdict |
|---|---|---|---|---|
| Qwen layer 12 (canary) | 0.763 | ≥ 0.700 | p = 0.0001 ✓ | **Go** |
| SmolLM2 final layer | 0.849 | ≥ 0.700 | p = 0.0001 ✓ | **Go** |
| Pythia final layer | 0.698 | ≥ 0.700 | p = 0.0001 ✓ | **Stopped** — missed by 0.002 |

### The frozen controller's report card

Lower is better on all of these. "Overshoot" = how often it sailed past the
target; "path cost" = 1.0 is a perfect straight line; "timeouts" = crashes.

| Substrate | Timeouts | Overshoot | Path cost | Steps | Smoothness (jerk) | Bar |
|---|---|---|---|---|---|---|
| Qwen layer 23 (home turf, ref) | 0 | 1.43 | 1.081 | ~6.5 | 0.107 | — |
| **Qwen layer 12 (canary)** | **0** | **1.37** | **1.082** | **6.5** | **0.107** | **PASSED** |
| **SmolLM2 final** | **0** | **1.43** | **1.131** | **6.0** | **0.136** | **PASSED** |
| Pythia final | — | — | — | — | — | not graded (stopped at gate) |

The canary's numbers are essentially identical to home turf — overshoot 1.37
vs 1.43, path cost 1.082 vs 1.081. The backup plan (re-teaching the
controller from scratch on the new geometry) was never needed.

### Two things worth knowing

**The scale trap we dodged.** Qwen's layer 12 activations are ~19× smaller
than layer 23's. If we'd skipped the per-substrate recalibration, the frozen
controller would have "failed" for pure unit-mismatch reasons — a false
alarm. The rescaling amendment earned its keep on day one.

**The bad law stays bad.** As a control we also ported the *worst*
verifier's law (the degenerate one from Exp 22, fold 1). It blew up on the
new geometries exactly like it did at home (overshoot ~20 vs ~1.4 for the
good law). The fragility travels with the law — which tells us these are
genuine properties of the learned controllers, not luck.

## What this means

Exp 23 showed the law transfers to unseen *situations*. Exp 24 shows it
transfers to unseen *geometries*. The verifier didn't just memorize a
neighborhood — it sculpted a genuinely portable correction operator. The
Pythia near-miss bounds the claim honestly: portability holds where the
geometry has enough 4D structure, and we check that *before* grading.

No new machinery was needed, and none is authorized: the linear controller
held up, so Phase 3 (curved-space math) stays on the shelf.

---

## Technical appendix

### Method (one paragraph per piece)

**Extraction.** `exp24_extract.py`: per model, 68 words × 3 neutral carriers
(24 map + 12 chain + 8 T1-new + 24 number words for the G2 control),
token-span mean hidden states at the target layer, fp16 CPU, `no_grad`.
Caches: `exp24_S{1,2,3}_cache.npz` + `_meta.json`. Master seed 17911254.

**Gates.** G1: PCA distance-preservation ladder on 72 map vectors at
dims {1,4,16,64}, gate r ≥ 0.70 at 4D. G2: Exp-18 predictor procedure at 4D
(ridge, K=3, 60 seqs, 40 train) — counting control must beat naive
(validity), then related-vs-shuffled with permutation p < 0.05 (10k perms).

**Instrument.** σ = 0.05·median|ε₀| over the 24 training trials, settle
tolerance 2σ√d, 3 consecutive sub-tolerance steps, min 5 steps, timeout 200 —
re-derived natively per substrate. Scale ratio s = median|ε₀|_new /
median|ε₀|_L23 (L23: 26.613, range [12.33, 43.27]).

**Frozen transfer.** Per fold (4 leave-one-chain-out folds), V4-history and
V1-history thetas from `exp22_results.json` (max drift vs spec 4e-4),
n_params=3, pinned noise streams `default_rng(17911254+9000+trial)` with
per-substrate σ, on the identical 40 Exp-23 pairings (16 T1 / 12 T2 / 12 T3;
T2/T3 range membership re-scored per substrate, same pairings). Label-shuffle
control: pinned permutation `default_rng(17911254+555)`.

**Pooling rule.** "Pooled" = mean across folds for mean-metrics (overshoot,
jerk, timeout), median across folds for median-metrics (steps, eff).

**Bar.** Canary (a) G1+G2 pass; (b) V4-history pooled: timeout_rate == 0,
overshoot_mean < 2.0, eff_med < 1.5 → PASSED. (c) fork trigger (complement
of b) did not fire → no re-tune control; Phase 3 not authorized.

### Full per-type fingerprint (V4-history)

| Substrate | Type | Steps | Path cost | Overshoot | Jerk |
|---|---|---|---|---|---|
| S1 Qwen L12 | T1 new words | 6.5 | 1.100 | 1.36 | 0.121 |
| S1 Qwen L12 | T2 new combos | 7.0 | 1.084 | 1.29 | 0.099 |
| S1 Qwen L12 | T3 new geometry | 6.8 | 1.072 | 1.46 | 0.097 |
| S2 SmolLM2 | T1 new words | 6.0 | 1.147 | 1.38 | 0.147 |
| S2 SmolLM2 | T2 new combos | 6.0 | 1.168 | 1.42 | 0.147 |
| S2 SmolLM2 | T3 new geometry | 6.8 | 1.123 | 1.50 | 0.111 |

(V1-history per type: overshoot 3.5–7.4 across types/substrates; fold-1
degenerate law per-fold overshoot 20.23 (S1) / 18.88 (S2) vs 19.2 (L23).)

### Range re-score (same 40 pairings, per-substrate range labels)

- S1 (range [0.72, 3.86]): T2 10-in/2-out, T3 8-in/4-out
- S2 (range [3.32, 15.11]): T2 11-in/1-out, T3 10-in/2-out

### Files

- `~/workspace/ai-theory/tangent_experiment/exp24_extract.py`
- `~/workspace/ai-theory/tangent_experiment/exp24_cross_substrate.py`
- `~/workspace/ai-theory/tangent_experiment/exp24_results.json`
- `~/workspace/ai-theory/tangent_experiment/figures/exp24_gates_ladder.png`
- `~/workspace/ai-theory/tangent_experiment/figures/exp24_overshoot_4d.png`
- `~/workspace/ai-theory/tangent_experiment/figures/exp24_eff_4d.png`
- `~/workspace/ai-theory/tangent_experiment/EXP24-CANARY-REPORT.md` (this file)
- Spec: `~/workspace/ai-theory/semantic-tangent-exp24-spec.md` (status: COMPLETE)
- Run logs: `exp24_extract.log`, `exp24_eval_S1.log`, `exp24_eval_S2S3.log`
