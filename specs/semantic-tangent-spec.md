# Semantic Tangent Spec — Exp 19 (shared reference, DRAFT)

**Status:** COMPLETED 2026-10-05 — qualified yes, pre-registered bar NOT passed
(speed won 4/4 held-out folds, efficiency lost 4/4; |Δ²ε|→0 settling signature
falsified; 16D robustness degenerate — settle tol not sized from verifier
noise). Advanced to Exp 20 as a *qualified advancement* (see
semantic-tangent-exp20-spec.md), which carries the failure modes forward and
folds the 16D noise-scaling fix into its robustness condition.

## Why this experiment (plain language)

Exp 18 proved the world has geometry: contextual hidden states, reduced with PCA instead of a random squash, preserve real semantic distances — and word order in that space carries predictive information. Exp 19 asks the next question: can a machine actually *move* through that world? Not "is the map accurate" but "can you walk it."

The machine gets a current position and a target, plus a verifier that reports the residual (how far off it is) at each step. Three walkers compete: one that steps straight at the target every time, one that also watches *how its error is changing* — is the miss shrinking? accelerating? oscillating? — and one that stumbles randomly as a control. The critical rule: nobody is ever shown the correct step. The learner sees its position, its miss, and the verifier's measurements — never the answer. (That is the Exp-11 teacher problem, and we are not repeating it.)

If the walker that watches its own correction dynamics learns something the straight-line walker cannot — settles faster, overshoots less, walks a cleaner path, and does it on semantic territory it never trained on — then correction dynamics are doing real work. That is the bridge rung this experiment is.

## The substrate (pinned)

- Base: the Exp-18 contextual substrate — Qwen2.5-0.5B-Instruct, layer 23, 3 carrier sentences per word (reuse Exp 18's carriers verbatim), same venv, `torch.no_grad()`, seeds pinned.
- PCA: refit on the original 72 contextual vectors with the identical procedure (PCA via SVD is deterministic — refitting reproduces the basis). **Verification gate:** the refit must reproduce the Exp-18 ladder (r ≈ 0.59 / 0.83 / 0.98 / 1.00 at dims {1,4,16,64}) before anything else runs. If it doesn't, stop — the procedure drifted.
- Primary space: **4D** PCA (the smallest dim that passed Exp 18's r ≥ 0.70 gate). Robustness condition: **16D** PCA, whole experiment repeated.
- New chain words (12, embedded with the identical procedure, projected into the fitted PCA — the basis does not change):
  - size: small → medium → large
  - temperature: cold → warm → hot
  - brightness: dark → dim → bright
  - speed: slow → steady → fast
- A trial = one directed pair within a chain (6 per chain: small→medium, small→large, medium→large, and reverses). Start X_0 = start-word vector; target T = target-word vector. Static T per trial.

## The three operators (pinned)

Per step t, the verifier reports ε̂_t = (T − X_t) + noise. History gives Δε̂_t = ε̂_t − ε̂_{t-1} and Δ²ε̂_t = Δε̂_t − Δε̂_{t-1}.

1. **Direct:** ΔX = α·ε̂_t. One parameter α, tuned.
2. **Tangent:** ΔX = α·ε̂_t + β·Δε̂_t + γ·Δ²ε̂_t. (This is f(ε, Δε, Δ²ε) in linear PID form: proportional + damping/anticipation + curvature. A nonlinear f is a possible 19b if the linear form shows nothing — not now.)
3. **Random control:** ΔX = s·u_t, u_t uniform random unit vector, s matched to the typical |αε̂| step magnitude of the direct operator (matching rule pinned in code). Same starts and targets.

## The learning rule (no teacher, no reward model yet)

- The operators' parameters are found by **black-box hill-climbing** (zero-order search, in the spirit of Exp 9's honest optimizer), scored by a **fixed, hand-defined verifier metric** per trial:
  score = steps-to-settle + λ·overshoot_penalty + μ·(path_length / |ε_0|), λ and μ pinned in code.
- Both the direct and tangent operators get the **same tuning budget**. The comparison is best-P vs best-PID, not tuned vs untuned.
- The learner NEVER sees a correct ΔX — only (X_t, ε̂_t, Δε̂_t, Δ²ε̂_t) at step time and the per-trial verifier score. No per-step labels (Exp 11's teacher problem), no policy gradients on shaped rewards (Exp 13 showed shaping can't steer a non-gradient update — here only 3 parameters are searched, the update form is fixed).
- Learning the verifier/reward itself is **Exp 21's job**, not this one's. Here the verifier metric is fixed and the verifier "stands alone."

## Verifier noise (why the problem is non-trivial)

- With a static target and a noiseless residual, proportional correction is already near-optimal and no history term can help — the experiment would be rigged to null.
- So the verifier reports ε̂_t = ε_t + η_t, η_t ~ N(0, σ²I), σ = 0.05 × median|ε_0| across trials (pinned). Justification: the verifier is a measurement device with uncertainty — the Exp-15 principle that margin is sized from verifier noise. The D-term (β·Δε) then has real work to do: filtering noise, damping overshoot.
- This is a load-bearing design choice by Muse, recorded here so it can be challenged.

## Training / generalization (the held-out constraint)

- **Leave-one-chain-out:** 4 folds. Each fold: tune operators on 3 chains (18 directed pairs), test the tuned operators on the held-out chain (6 pairs, words never seen in training).
- This is Adrian's small→medium→large → cold→warm→hot constraint, operationalized: the operator must learn *correction geometry*, not word locations. The operator's parameters are global (shared across all chains) — there is nowhere to memorize a word.
- Report train and held-out numbers separately, mean ± spread across folds.

## Settle/timeout (pinned)

- Settled: |ε̂_t| < tol for k=3 consecutive steps, tol = 0.10 × |ε_0| (relative — coordinates are large in this space).
- Timeout: 200 steps. Timeouts reported, not dropped.

## Measurements (Adrian's list, pinned)

1. **Speed:** steps to settle (median + IQR per operator per fold).
2. **Overshoot:** count of steps where |ε̂| grows after shrinking, plus max excursion beyond T along the initial ε_0 direction.
3. **Direction stability:** mean cosine(ΔX_t, ΔX_{t-1}) over the trajectory.
4. **Settling signature:** slope of |Δ²ε̂| over trajectory halves — does it decay as the system settles?
5. **Efficiency:** path_length / |ε_0|, and its trend across hill-climbing generations (does the trajectory get cleaner *over training*?).
6. **Generalization:** all of the above on the held-out chain vs the direct operator. Pre-registered bar: tangent beats direct on held-out steps-to-settle AND efficiency, with the gap in the same direction across all 4 folds (a weak bar on purpose — n=4 folds; report the numbers either way).

## Honest limits

- One 0.5B model, one layer, 4 hand-picked gradation chains — the chains are Adrian's example types made concrete; chain choice is a confound until varied.
- The PID form is linear; a null here kills the linear tangent, not the tangent idea.
- Verifier noise level is a chosen constant; sensitivity to σ is a 19b question.
- 16D is a robustness condition, not a second experiment — if 4D and 16D disagree, that's a finding, not a failure.

## Queued (gated on Exp 19's success — not built now)

- **Exp 20 — Residual-Only Correction:** remove raw target coordinates from the learner. Input is only (ε_t, Δε_t, Δ²ε_t); it must determine the next correction. Tests whether the remainder of correction can itself be the information for the next correction.
- **Exp 21 — Learned verifier:** can a reward/verifier model learn *which correction dynamics are productive*, replacing the fixed hand-defined metric?
- **Exp 22 — Unseen situations:** generalization of the resulting operator to semantic situations outside the chain family entirely.

## The progression (Adrian's framing, kept verbatim)

- 18: Does the substrate contain usable semantic geometry? ✅
- 19: Can a correction operator move through that geometry?
- 20: Can correction dynamics themselves provide the information needed for subsequent correction?
- 21: Can a reward/verifier learn which correction dynamics are actually productive?
- 22: Can the resulting operator generalize to unseen semantic situations?

The big transition: Exp 18 gave us a world with geometry. Exp 19 asks whether our machine can actually move through that world.
