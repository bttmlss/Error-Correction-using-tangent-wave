# Verifier-Driven Correction Learning — Exp 21 (shared reference)

**Status:** UNBLOCKED by Exp 20 (2026-10-05 — bar passed both halves, all 4
folds). This is the conceptual escalation Adrian locked in: Exps 18–20
hand-built or hill-climbed every correction law; Exp 21 asks whether a
verifier/reward mechanism can *discover the history advantage itself*.

**Pilot note (2026-10-05, 40-epoch single-fold diagnostic, before the full
run):** the PG machinery learns (held-out 28.5 → 8.5 steps; α 0.1 → 0.35,
matching the reference's α≈0.33) — but β moved *positive* (+0.20), not
negative, with γ = +0.19. A head-to-head on fresh noise showed why: under the
minimal improvement reward the positive-β (reactive/lead) law scores +23.73 vs
+23.27 for Exp-20's negative-β (smoothing) law — nearly indifferent (2% gap) —
while the hand-shaped composite (with its explicit overshoot penalty) separates
them sharply (68.7 vs 30.8). So the minimal verifier does not strongly select
Exp-20's smoothing law; the overshoot penalty in the hand-designed metric was
load-bearing for discovering *that particular* law. The bar below was refined
accordingly (transparently, before the full run): the primary question is
whether reward-driven learning discovers *history-dependence* (β,γ ≠ 0) that
beats the memoryless learner — the *sign* of β is a measurement of the
verifier's inductive bias, not a pass/fail on whether learning worked.

## Why this experiment (plain language)

Exp 20 proved that watching the error's history lets a machine steer faster
through semantic space — and that the learned trick is a damping term
(negative β). But so far every law was handed to the machine: we fixed the PID
form and hill-climbed its knobs against a hand-designed score. Exp 21 removes
the hand. The learner gets the same residual measurements, no teacher showing
it the right move, and a verifier that only says "that correction helped" or
"that didn't." If reward-driven learning rediscovers the damping law on its
own — negative β, appropriate α, faster settling on unseen chains — then the
program crosses from dynamical analogy into a learning architecture. The
Exp-20 history operator stays frozen as the reference; the *only* thing that
changes is how the policy is learned.

## The three players (pinned)

1. **Frozen reference/expert:** Exp 20's tuned history-aware PID, per fold,
   loaded verbatim from `tangent_experiment/exp20_results.json`. Deterministic
   (mean action, no exploration noise). The bar to approach — not to beat.
2. **PG-history learner:** stochastic linear PID. Mean action
   μ_t = α·ε̂_t + β·Δε̂_t + γ·Δ²ε̂_t; executed action a_t ~ N(μ_t, σ_π²I_d).
   Learned by REINFORCE + Adam on the verifier's reward. Init
   (α,β,γ) = (0.1, 0, 0) — it starts with no damping and must discover it.
3. **PG-memoryless learner:** identical setup, μ_t = α·ε̂_t only (β=γ=0 frozen
   at zero). Tests whether a reward-driven learner *without* history access
   plateaus below — i.e., whether the temporal structure is what gets
   discovered, not just "a bigger step."

## The verifier (pinned — minimal by design)

- Per-step reward r_t = ||ε̂_{t-1}|| − ||ε̂_t|| for t ≥ 1 (r_0 = 0): the
  reduction in the *noisy* residual the verifier reports. Positive means "that
  correction helped." No composite score, no overshoot penalty, no efficiency
  term — the verifier only judges improvement.
- Discount γ = 0.99 on the return-to-go G_t. Episode ends at settle
  (instrument-aware: ||ε̂|| < 2σ√d for 3 consecutive steps, min-step guard 5)
  or timeout 200.
- Exp 12's telescoping caution is handled by construction: Σr_t telescopes to
  ||ε̂_0|| − ||ε̂_T||, so dawdling earns discounted near-zero while real
  improvement earns positive return, and doing nothing earns ~0. There is no
  do-nothing absorbing optimum with positive value.
- σ is the Exp-19/20 pinned verifier noise (0.05 × median|ε_0|); the reward is
  computed from the same noisy ε̂ the policy sees. The learner must discover
  damping *through* the noise — which is exactly what β<0 is for.

## Load-bearing constraint (from Exp 11)

The learner NEVER sees a correct ΔX — only (ε̂_t, Δε̂_t, Δ²ε̂_t) at step time
and scalar rewards. No per-step labels, no demonstrations, no teacher.

## What is frozen vs what changes

Frozen from Exp 20: the substrate (Qwen2.5-0.5B L23, 4D PCA, same 24 trials,
same 4 leave-one-chain-out folds, same pinned noise banks), the
representation, the correction inputs, and the linear PID policy form. The
reference controller is Exp 20's champion, untouched. The ONLY change is the
learning rule: black-box hill-climbing on a hand-designed composite →
online REINFORCE on the verifier's minimal improvement signal. (A full neural
verifier that *predicts* which dynamics are productive is a possible 21b —
not now.)

## Training (pinned)

- Budget matched to Exp 20: 200 epochs × 18 training trials = 3600 episodes
  per learner per fold (same trial-run count as Exp 20's tuning budget).
- One epoch = one sweep over the 18 training trials (order shuffled per epoch,
  pinned rng). Batch policy gradient: accumulate
  Σ_episodes Σ_t (G_t − b_ep)·∇log π(a_t|s_t) over the epoch, then one Adam
  step (lr = 0.03, betas (0.9, 0.999)). b_ep = per-episode mean return-to-go.
- Gaussian log-prob gradients: ∇_α log π = (a_t−μ_t)·ε̂_t/σ_π² (and analogously
  for β, γ with Δε̂_t, Δ²ε̂_t).
- Exploration σ_π = 0.10 × median|ε_0|/√d (pinned). One pinned seed per fold
  for each learner (shared across the two learners within a fold).
- Held-out evaluation uses the deterministic mean policy on fresh pinned noise
  shared across all three players (fair comparison).

## Measurements (pinned)

1. Held-out median steps-to-settle per player per fold (PRIMARY).
2. Learned (α, β, γ) per fold for the PG-history learner — the fingerprint is
   *history-dependence*: |β| (and |γ|) moved substantially away from the zero
   init. Sign reported per fold and interpreted: negative β = low-pass /
   smoothing law (Exp-20's solution: (α+β)·ê_t − β·ê_{t−1} averages consecutive
   noisy measurements); positive β = reactive / lead law (emphasizes the
   current measurement, backs off when already shrinking). The sign reveals the
   verifier's inductive bias.
3. Learning curves: held-out median steps vs epoch for both learners (does the
   history learner pull away from the memoryless one, and when?).
4. Path cost per player per fold (secondary, Pareto).
5. Sanity: PG-memoryless final α vs Exp-20's hill-climbed memoryless α (do the
   two learning rules agree where they should?).

## Pre-registered bar (4D, held-out)

(a) PG-history median steps < PG-memoryless median steps, same direction in
all 4 folds;
(b) learned |β| > 0.05 in all 4 folds (history-dependence discovered from the
zero init; sign reported per fold with the interpretation above);
(c) PG-history median steps within 1.5× of the frozen reference in all 4
folds (approach the expert; PG-from-scratch need not match hill-climbing
exactly).
Report all numbers either way.

## Honest limits

- The linear PID policy class is frozen — a null kills "reward rediscovers
  THIS law," not reward-driven correction learning in general.
- REINFORCE hyperparameters (lr, exploration scale, discount, init) are pinned
  a priori; a null could be an optimization failure rather than a conceptual
  one — the learning curves are the diagnostic that separates the two.
- 4D only: the effect to be rediscovered lives in the top PCs (Exp 20's 16D
  attenuation); 16D policy-gradient is out of scope.
- One pinned seed per fold per learner; seed sensitivity is noted, not tested.
- If the bar passes, the claim is exactly this: "A verifier-driven learner
  recovered a temporally structured correction policy (negative-β damping)
  from semantic-state residuals without teacher demonstrations." Not "we built
  intelligence."

## Queued (not built now)

- **Exp 22 — Unseen situations:** generalization of the resulting operator to
  semantic situations outside the chain family entirely.
- **Possible 21b:** a learned verifier *model* proper — predicting which
  correction dynamics are productive rather than judging improvement
  post-hoc.
