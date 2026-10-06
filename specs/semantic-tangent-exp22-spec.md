# Verifier Selection — Exp 22 (shared reference)

**Status:** DIRECTIVE from Adrian (2026-10-05), building now. Exp 21's honest
conclusion — "there was no uniquely correct correction law specified by the
verifier, and the learner discovered one of the behaviors that the verifier
rewarded" — becomes Exp 22's controlled experiment: freeze the learner and
substrate, vary ONLY the verifier, and map verifier shape → learned correction
dynamics. This is the empirical version of the pointer-vs-arrow principle.

## Why this experiment (plain language)

Exp 20 (hand-shaped verifier with overshoot/cleanliness penalties) produced
the smoothing law: negative β, damping, clean paths. Exp 21 (bare "did it
help" verifier) produced the reactive law: positive β, aggressive α, messy
paths — and a memoryless learner that sometimes discovered a reckless
α≈0.86 exploit. Same substrate, same correction architecture, same learning
machinery, different verifier. Exp 22 turns that observation into the actual
experiment: run the identical learner against four verifier shapes and watch
where (α, β) — and the whole behavioral fingerprint — lands. If the verifier
reliably moves the discovered dynamics, we have demonstrated verifier shape →
incentive landscape → correction dynamics. And we preserve the subtle point:
the positive-β law is not "wrong" — under its objective it may be the correct
solution. The machine understood the verifier; the question is what the
verifier asked for.

## The controlled comparison (pinned)

Everything is frozen from Exp 21 — substrate (Qwen2.5-0.5B L23, 4D PCA, same
24 trials, same 4 leave-one-chain-out folds, same pinned noise), learner
(REINFORCE + Adam, linear PID, init (0.1,0,0), 200 epochs × 18 trials, same
exploration, same discount γ=0.99), policy inputs, settle criterion. The ONLY
independent variable is the per-step reward function:

- **V₁ = improvement only** (Exp-21's verifier, the known endpoint):
  r_t = |ê_{t-1}| − |ê_t| (noisy residual, t≥1; r_0 = 0).
- **V₂ = improvement − overshoot penalty**:
  r_t = (|ê_{t-1}| − |ê_t|) − 5.0·ov_t,
  ov_t = 1{|e_true,t| > |e_true,t−1| and |e_true,t−1| < |ε_0|} (Exp-20's
  overshoot rule, t≥1).
- **V₃ = improvement − path-cost penalty**:
  r_t = (|ê_{t-1}| − |ê_t|) − 20.0·(|ΔX_t| / med|ε_0|),
  med|ε_0| = median initial error across trials (pinned per dim).
- **V₄ = improvement + stability (action-smoothing) term**:
  r_t = (|ê_{t-1}| − |ê_t|) − 10.0·(|ΔX_t − ΔX_{t−1}| / med|ε_0|) (t≥2; 0 at
  t=1). Rewards persistent, smooth correction direction.

Penalty scales are pinned a priori to be comparable to a typical per-step
improvement (~|ε_0|/8): λ_ov=5.0 and μ=20.0 follow Exp-20's composite
precedent; λ_st=10.0 is ~10–15% of typical improvement per step. The
improvement term always uses the verifier's *noisy* measurement; the penalty
terms use the true trajectory (the designer's preference about what "good
correction" means) — same split as Exp-20's tuner metric. The experiment tests
whether these move the regime, not optimal tuning.

Both learners run under every verifier: the history learner (α,β,γ) and the
memoryless learner (α only) — the latter shows whether the verifier also moves
the memoryless operating point (Exp-21's bimodal α≈0.86 exploit is the thing
to watch). The frozen Exp-20 reference is evaluated as an anchor (not trained).

## The question (pinned)

Does changing only the verifier reliably move the discovered (α, β) toward
different dynamical regimes? Two endpoints are already known (minimal →
positive β; overshoot-aware → negative β). Exp 22 fills in the map.

## Measurements (pinned) — the full behavioral fingerprint

Per (verifier × learner × fold), held-out:
1. Learned (α, β, γ).
2. Convergence time: median + IQR steps-to-settle.
3. Path cost: median path_length/|ε_0|.
4. Overshoot: mean count (Exp-20 true-eps rule).
5. Failure rate: timeout rate.
6. Sign consistency of β across folds per verifier.

The point is the *joint* fingerprint, not β alone: verifier shape →
incentive landscape → correction dynamics.

## Pre-registered bar (4D, held-out, history learner)

(a) β(V₂) < β(V₁) in all 4 folds — the overshoot penalty moves β negative
relative to minimal (directional prediction);
(b) β(V₂) < 0 in ≥3/4 folds — the overshoot penalty recovers damping;
(c) β(V₁) > 0 in all 4 folds — replication of Exp 21's verifier bias.
Report all numbers either way. V₃ and V₄ are exploratory mapping (no
directional pre-registration — their regimes are genuinely unknown).

## Honest limits

- Penalty scales are pinned a priori, not tuned; a null for V₃/V₄ could mean
  "wrong scale" rather than "no effect" — the fingerprint table is the
  diagnostic.
- Linear PID policy class frozen; the map is over (α,β,γ)-space, not over
  architectures.
- 4D only (the effects live in the top PCs per Exp 20).
- One pinned seed per fold; the memoryless learner's bimodality (Exp 21) is
  itself a seed/trajectory-dependent phenomenon worth watching across
  verifiers.
- If the map is clean, the claim is: "Varying only the verifier's reward
  shape reliably moved the learned correction dynamics across distinguishable
  regimes (smoothing ↔ reactive ↔ aggressive)." The verifier selects the law;
  the learner discovers it. Not "we built intelligence."
