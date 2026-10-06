# Residual-Only Correction Spec — Exp 20 (shared reference)

**Status:** QUALIFIED ADVANCEMENT from Exp 19 (2026-10-05). Exp 19 returned a
qualified yes — pre-registered bar NOT passed (speed won 4/4 held-out folds,
efficiency lost 4/4). This "qualified advancement" label replaces "Exp 19
passed" as the gate for Exps 20–22. Failure modes carried forward explicitly:
(1) speed ≠ efficiency — objectives reported separately, Pareto framing;
(2) the |Δ²ε|→0 settling signature is retired (falsified: near-target the
verifier shows its noise floor); (3) the 16D condition was degenerate because
the settle tolerance was not sized from verifier noise — fixed here by the
instrument-aware criterion (this doubles as the 19b fix).

## Why this experiment (plain language)

Exp 18 gave us a world with geometry. Exp 19 showed a machine can move through
it, and that watching how its error changes helps it settle faster. Exp 20 asks
the harder question: can the *history of correction itself* become sufficient
information for choosing the next correction? The learner gets the residual and
its history — nothing else about the target beyond what the residual already
says. If the history-aware controller beats both a memoryless controller AND a
controller fed scrambled history, then temporal correction dynamics are doing
real, transferable work — and the "remainder of correction becomes the next
correction signal" idea has its first testable mechanism.

## The three arms (pinned)

Per step t the verifier reports ε̂_t = (T − X_t) + η_t, η_t ~ N(0, σ²I).
History gives Δε̂_t, Δ²ε̂_t as in Exp 19.

1. **Memoryless:** u_t = f(ε̂_t) = α·ε̂_t. Identical to Exp 19's direct operator.
2. **Real history:** u_t = f(ε̂_t, Δε̂_t, Δ²ε̂_t) = α·ε̂_t + β·Δε̂_t + γ·Δ²ε̂_t
   (linear PID). Identical to Exp 19's tangent operator.
3. **Permuted history (the new control):** u_t = α·ε̂_t + β·Δε̂_{π(t)}^ref +
   γ·Δ²ε̂_{π(t)}^ref. The history features come from a *reference trajectory* —
   the tuned memoryless arm run on the same trial with the same noise, to the
   full horizon — with time indices passed through a fixed per-trial permutation
   π (seeded, pinned). Marginal distributions of the history features are
   preserved; their temporal alignment with the controller's current state is
   destroyed. Same tuning budget, same parameter ranges as arm 2.

Reading the three-way comparison: real > memoryless replicates Exp 19's speed
finding under the new criterion (history helps). Real > permuted shows the
benefit is *temporal structure*, not merely extra features/degrees of freedom.
Real ≈ permuted would mean the tuner is exploiting feature count, not dynamics —
a very different lesson, and worth knowing.

The random control from Exp 19 is deliberately dropped; the permuted control is
the sharper instrument for this question.

## Substrate (inherits Exp 19 verbatim)

- Qwen2.5-0.5B-Instruct, layer 23, Exp 18's 3 carriers verbatim, same venv,
  `torch.no_grad()`, seeds pinned (master SEED = 17911254).
- PCA refit on the original 72 contextual vectors; **verification gate:** refit
  must reproduce the Exp-18 ladder (r ≈ 0.59 / 0.83 / 0.98 / 1.00 at dims
  {1,4,16,64}, tolerance ±0.02) or stop.
- 4 gradation chains (size, temperature, brightness, speed) × 6 directed pairs
  = 24 trials. Chain words projected into the fitted basis (basis unchanged).
- **Leave-one-chain-out:** 4 folds, tune on 3 chains (18 pairs), test on the
  held-out chain (6 pairs). Operator parameters global — nowhere to memorize
  a word.
- 4D primary; 16D robustness condition (now with the corrected tolerance).

## What changed vs Exp 19 (pinned)

- **Instrument-aware settling (replaces the relative tol):**
  settled ⇔ ||ε̂_t|| < k·σ_verifier(d) for m consecutive steps,
  with k = 2, m = 3, σ_verifier(d) = σ·√d, σ = 0.05 × median|ε_0| (the Exp-19
  pinned noise level). Rationale: "settled" now means the residual is
  statistically indistinguishable from the verifier's noise floor — we no
  longer ask the noisy instrument to prove something it cannot resolve.
  MIN_STEPS = 5 guard (a trial may not settle before step 5; protects against
  trials whose |ε_0| starts inside the tolerance — these are counted and
  reported). The old relative tol (0.10×|ε_0|) is reported as a secondary
  column for continuity with Exp 19.
- **Tuner objective unchanged** (steps + λ·overshoot + μ·efficiency, λ = 5,
  μ = 20, budget 200 evals, 6 restarts, same ranges) — tuning stays scalar and
  comparable to Exp 19; *evaluation* is Pareto. Deliberate separation.
- The reference trajectory for arm 3 uses the fold's tuned memoryless params.
  The permutation cannot be "un-learned": π differs per trial while (α,β,γ)
  are global across 18 training trials.

## Measurements (pinned)

1. **Time-to-settle** (median + IQR per arm per fold, held-out) — PRIMARY axis.
2. **Path cost** (median path_length/|ε_0| per arm per fold, held-out) —
   SECONDARY axis, reported independently. We look for Pareto-frontier
   movement, not one scalar "better".
3. **β diagnostics** (per fold, arms 2 and 3): β, sign(β), |β|; across folds:
   variance of β and sign-consistency (n/4). Stable sign + comparable
   magnitude ⇒ evidence for a transferable dynamical term. Flipping sign ⇒
   warning that "history helps" while the learned history rule itself isn't
   stable.
4. Timeout rate, overshoot count, max excursion, direction stability (as Exp
   19, secondary).
5. Settle-steps under the old relative tol (secondary, continuity column).

## Pre-registered bar (4D, held-out)

(a) Real-history median steps < memoryless median steps, same direction in all
4 folds.
(b) Real-history median steps < permuted-history median steps, same direction
in all 4 folds.
Path cost is Pareto-reported, not bar-gated. All numbers reported either way.

## Honest limits

- One 0.5B model, one layer, 4 hand-picked gradation chains — chain choice is
  still a confound until varied. Linear PID form; a null kills the linear
  tangent, not the tangent idea.
- The permuted reference comes from the memoryless arm — neutral by
  construction, but a different reference choice could shift the history
  marginals. Noted, not tested.
- The learner still sees X_t (position) alongside the residual; the "residual
  only" in the title refers to target information — no correct ΔX is ever
  shown, no per-step labels (Exp 11's teacher problem is not repeated).
- A strong result establishes one concrete mechanism consistent with the
  "remainder becomes the next correction signal" idea — not the philosophical
  proposition. Every experiment earns a slightly stronger claim; no single
  result gets promoted into a grand theory.

## Queued (gated on Exp 20's qualified outcome — not built now)

- **Exp 21 — Learned verifier:** can a reward/verifier model learn *which
  correction dynamics are productive*, replacing the fixed hand-defined metric?
- **Exp 22 — Unseen situations:** generalization of the resulting operator to
  semantic situations outside the chain family entirely.
