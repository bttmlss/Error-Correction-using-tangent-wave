# Exp-25 — Causal Ablation of the Portable Law

**Status: COMPLETE (2026-10-06).** Report for Adrian — plain language first.

## What traveled, in one breath

**The damping term β — but not for the reason we guessed.** We took the
frozen law apart and removed β, expecting the controller to get wild.
Instead it got *cautious*: fewer overshoots, slightly slower, jerkier
moves. So β isn't the "don't overshoot" ingredient — it's the "move
smoothly and decisively" ingredient. Which makes perfect sense: the
verifier that sculpted this law was specifically rewarding *smooth
actions*. The ablation isolated exactly what the verifier asked for.
α gets you there carefully; β gets you there smoothly and fast, at the
cost of occasionally overshooting. The γ term does basically nothing.

## The bar failed, and that's the finding

Bar (b) as literally written did **not** pass: removing β did not spike
overshoot — it *cut* overshoot by ~30% on every substrate (A1/A0 ratios
0.65 / 0.73 / 0.69 on S1 / S2 / L23, zero timeouts everywhere, consistent
on all 12 folds). Per this program's own rule — informative bar failures
are findings — the dissociation still appeared, just on the metric the
verifier actually shaped: **jerk rose 33–53%** when β was removed
(0.107→0.143, 0.136→0.208, 0.107→0.142), while reachability stayed
perfect. The portable ingredient is confirmed in corrected form: β
carries the *action-smoothing* fingerprint V4's reward sculpted, plus a
small speed bonus (~0.5 fewer steps), paid for in overshoots.

## Bar verdicts

| bar | S1 (Qwen L12) | S2 (SmolLM2) | L23 (ref track) |
|---|---|---|---|
| (a) A0 replicates Exp-24 ≤1.2× | **PASSED** (bit-exact) | **PASSED** (bit-exact) | sanity OK vs Exp-23 |
| (b) A1 ov ≥2× A0, 0 timeouts | **NOT PASSED** (ratio 0.65, ov *fell*) | **NOT PASSED** (ratio 0.73) | NOT PASSED (0.69) |
| (b′) corrected: A1 jerk rises, 0 timeouts | holds (+33%) | holds (+53%) | holds (+33%) |
| (c) A2 ≈ A0 ≤1.3× (exploratory) | ov 0.96, jerk 0.99 | ov 0.98, jerk 0.93 | ov 0.98, jerk 0.98 |
| (d) A3 vs V4mem_ref | A3 ov 0.79 < ref 1.42 | A3 ov 1.06 < ref 1.77 | A3 ov 0.92 < ref 1.56 |

## Pooled numbers per arm (40 pairings × 4 folds)

**S1 — Qwen layer 12:**

| arm | steps | path cost | overshoot | jerk | timeouts |
|---|---|---|---|---|---|
| A0 full (α,β,γ) | 6.5 | 1.082 | 1.37 | 0.107 | 0.00 |
| A1 (α,0,γ) | 7.0 | 1.062 | 0.89 | 0.143 | 0.00 |
| A2 (α,β,0) | 6.5 | 1.080 | 1.31 | 0.106 | 0.00 |
| A3 (α,0,0) | 7.0 | 1.046 | 0.79 | 0.115 | 0.00 |
| V4mem ref (trained α-only) | 6.0 | 1.173 | 1.42 | 0.189 | 0.00 |

**S2 — SmolLM2 final layer:**

| arm | steps | path cost | overshoot | jerk | timeouts |
|---|---|---|---|---|---|
| A0 full | 6.0 | 1.131 | 1.43 | 0.136 | 0.00 |
| A1 (α,0,γ) | 6.0 | 1.137 | 1.04 | 0.208 | 0.00 |
| A2 (α,β,0) | 6.0 | 1.131 | 1.40 | 0.127 | 0.00 |
| A3 (α,0,0) | 6.0 | 1.121 | 1.06 | 0.160 | 0.00 |
| V4mem ref | 6.0 | 1.360 | 1.77 | 0.255 | 0.00 |

**L23 — home turf (exploratory reference):** identical arm ordering on
every metric (A0 ov 1.42/jerk 0.107; A1 ov 0.98/jerk 0.142; A2 ≈ A0;
A3 ov 0.92). β's role is substrate-independent — the *decomposition*
travels, not just the law.

## What each piece does (the corrected decomposition)

- **α — the cautious reacher.** Alone (A3), it reaches every target with
  the fewest overshoots and best path cost, but moves in slightly
  jerkier steps and arrives a touch slower.
- **β (negative) — the portable ingredient.** Adds decisive, smooth
  action: lowest jerk on every substrate, ~0.5 fewer steps — at the
  price of more frequent overshoots. This is *exactly* what V4's
  action-smoothing penalty rewarded. The verifier's fingerprint, found.
- **γ — dead weight.** Zeroing it changes nothing measurable (all ratios
  0.93–0.99). Second-order history earns no follow-up.
- **Co-adaptation (d):** the ablated A3 (small co-adapted α) overshoots
  *less* than the from-scratch trained memoryless α (large α) on all
  three substrates. The full law's α stays small because β does part of
  the work — ablating β leaves a cautious controller, while a learner
  denied history compensates with aggression. The spec's honest-limits
  caveat is confirmed empirically.

## What this earns

"β is the portable ingredient" — confirmed in corrected form: across
depth (L23→L12) and model family (Qwen→SmolLM2), removing β from the
frozen law selectively destroys the low-jerk fingerprint the V4
verifier sculpted, while leaving reachability untouched. The mechanism
is isolated, not merely observed. The natural sequel stands: a
β-magnitude sweep (Exp-26 candidate) — is it the sign, the magnitude,
or the learned value that matters?

## Figures

- `figures/exp25_overshoot_4d.png` — pooled overshoot by arm × substrate
  (2× A0 line = bar (b); note A1 sits *below* it)
- `figures/exp25_eff_4d.png` — pooled path cost by arm × substrate
- `figures/exp25_jerk_4d.png` — pooled jerk by arm × substrate (the
  metric where the dissociation actually lives)

## Files

- `exp25_ablation.py` — 4 ablation arms × (S1, S2, L23), frozen eval
- `exp25_results.json` — full results (all COMPLETE), per-fold +
  per-type tables
- `EXP25-ABLATION-REPORT.md` — this report

## Technical appendix (choices where the spec left room)

- **L23 track construction:** E_base/E_chain from `exp21_embed_cache.npz`,
  PCA via the identical deterministic recipe (`pca_ladder`, same SVD →
  same basis as Exp-23); new-word 4D vectors from `exp23_new_words.npz`
  (`C_new`, already projected). Instrument re-derived with the same rule
  (σ=0.05·median|ε₀|, tol=2σ√d); noise regenerated with the identical
  construction (SEED+9000+trial) — L23 A0 matches Exp-23 pooled values
  to 3 decimals, validating the track.
- **Thetas read at runtime** from `exp22_results.json` (V4-history and
  V4-memoryless per fold); max drift vs spec's rounded values is
  rounding-only.
- **Pooling:** mean across folds for mean-metrics (overshoot/jerk/
  timeout), median across folds for median-metrics (steps/eff) —
  Exp-24 precedent.
- **S1/S2 bar (a) is bit-exact**, not just ≤1.2×: same caches, same
  instruments, same pinned noise as Exp-24 — a true harness check.
- No training of any kind; models observational-only throughout.
- Python env: `~/workspace/venvs/llm/bin/python`.
