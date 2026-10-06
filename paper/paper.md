# Verifier Shape Selects the Correction Law: Steering, Damping, and Transfer in a Frozen Language Model's Representation Geometry

**BTTMLSS**

*Draft — 2026-10-05. For review, not for submission.*

---

## Abstract

We study whether a verifier-driven learner can discover steerable correction dynamics inside a real language model's frozen representation geometry — and, critically, *which* dynamics it discovers. Using Qwen2.5-0.5B-Instruct (layer 23, observational only) projected to 4 PCA dimensions, we define 24 directed steering trials over four semantic gradation chains (size, temperature, brightness, speed) and train linear PID correction policies by REINFORCE on the verifier's reward signal, never showing the learner a correct step. We find: (1) temporal residual history (error, its change, its acceleration) carries usable signal — a history-aware policy beats memoryless and permuted-history controls on all held-out folds; (2) the verifier's reward *shape* selects which temporal law is learned — a bare "did the error shrink?" verifier induces a reactive (positive-β) or even degenerate law, while adding an overshoot, path-cost, or action-smoothing penalty induces damping, aggressive, or ultra-stable regimes respectively, mapped as a controlled experiment with the learner and substrate frozen; (3) the law induced by the smoothness verifier transfers to 40 unseen situations (new words, new pairings, new trajectory scales) with zero retraining — low overshoot, low jerk, zero timeouts — while laws induced by the minimal verifier transfer unreliably, one collapsing catastrophically off-distribution. The learner is the arrow; the verifier is the pointer. Every induced law is a valid maximizer of what its verifier asked for.

---

## 1. Introduction

A growing line of work treats language-model behavior as movement through representation space: steering vectors, activation addition, and representation engineering all presuppose that directions in hidden-state geometry are meaningful and manipulable. Less studied is the *dynamics* of correction — not whether a target direction exists, but what control law a system learns for traveling toward it, and what determines the shape of that law.

This paper reports a six-experiment program asking one question at increasing depth: **can a verifier-driven learner discover steerable correction dynamics in a real LLM's representation geometry, and what selects the dynamics it discovers?**

The program's central distinction, which emerged empirically rather than being assumed, is between the *pointer* and the *arrow*. The residual history available to a corrector — the error, how fast it is changing, how that change is changing — defines a *space* of possible correction behaviors (the arrow's possible flights). But the verifier's reward signal determines *which direction through that space is rewarded* (the pointer). Our headline result is that the verifier's shape selects the learned law more strongly than the learning rule does: identical substrate, identical architecture, identical optimizer — four verifier shapes produce four distinguishable dynamical regimes, and the induced laws differ in whether they transfer to unseen situations.

We are careful about what each experiment earns. Every claim below is scoped to its experiment: a linear PID policy class, 4 PCA dimensions, one model layer, four hand-picked semantic chains. Nothing here is a claim about intelligence, and no induced law is "the correct law" — each is named by what induced it, because each is a valid maximizer of what its verifier asked for.

---

## 2. Setup and Methodology

**Volunteer model (observational only).** All experiments use Qwen2.5-0.5B-Instruct as a *volunteer*: we read hidden states and never modify weights, never train the model, never touch its reward circuitry. We use layer 23 (of 24), chosen after a PCA distance-preservation ladder showed 4 dimensions suffice to preserve the model's pairwise word geometry (Section 3.1).

**Substrate construction.** Each of 12 chain words (four gradation chains × three words: size {small, medium, large}, temperature {cold, warm, hot}, brightness {dark, dim, bright}, speed {slow, steady, fast}) is embedded in three neutral carrier sentences ("The ___ sat on the table.", "I saw the ___ yesterday.", "She pointed at the ___."); we take the mean hidden state over the word's token span, average over carriers, center on 24 map words, and project onto the top 4 principal components. A directed trial is an ordered pair (X₀, T) of distinct chain words within one chain: 24 trials total.

**The correction task.** Starting at X₀, a controller emits steps ΔX_t in the 4-D space. It observes only the noisy residual ê_t = (T − X_t) + η_t, never the true target coordinates and never a correct step (the no-teacher rule). The verifier reports per-step reward. Settling is instrument-aware: ‖ê‖ < 2σ√d for three consecutive steps (minimum five steps), with σ = 0.05 · median|ε₀| pinned across experiments — the tolerance is sized from the verifier's noise floor, a lesson learned the hard way in Exp 19.

**Controllers.** The history (PID/tangent) controller is u_t = α·ê_t + β·Δê_t + γ·Δ²ê_t. The memoryless controller is u_t = α·ê_t. Learners are stochastic linear policies trained by REINFORCE with Adam (200 epochs × 18 trials, init (0.1, 0, 0), exploration σ_π = 0.10 · median|ε₀|/√d, discount 0.99). A hill-climbing tuner on a hand-shaped composite is used only as the Exp-20 reference.

**Verifier shapes (the independent variable of Exps 21–23).** V₁: improvement only, r_t = ‖ê_{t−1}‖ − ‖ê_t‖. V₂: improvement − 5.0·overshoot_t (a step counts as overshoot if the *true* error grows after shrinking). V₃: improvement − 20.0·(‖ΔX_t‖/median|ε₀|) (path-cost penalty). V₄: improvement − 10.0·(‖ΔX_t − ΔX_{t−1}‖/median|ε₀|) (action-smoothing/stability penalty). Penalty scales were pinned a priori to be comparable to a typical per-step improvement, not tuned.

**Evaluation protocol.** Leave-one-chain-out: train/tune on three chains, evaluate on the fourth's six held-out trials; four folds. Speed (median steps) and path cost (path length / |ε₀|) are reported as independent Pareto axes, never bundled. Pre-registered bars are stated per experiment and reported honestly whether passed or not — several of the program's key findings came from bars that failed informatively.

---

## 3. Experiments

### 3.1 Exp 18 — The world has geometry (bar passed)

*Question: does a frozen embedding substrate preserve enough geometric structure for a prediction task, once the representation is contextual and multi-dimensional?*

An earlier 1-D squash of static embeddings had measured dead (distance preservation r ≈ 0.04). Replacing it with contextual hidden states plus PCA revived the geometry:

| PCA dims | 1 | 4 | 16 | 64 |
|---|---|---|---|---|
| distance-preservation r | 0.591 | **0.827** | 0.975 | 1.000 |

The gate (smallest dim with r ≥ 0.70) passed at dim 4. A positive control (predicting a counting sequence "one"→"twenty-four") gave MSE 688.7 vs 791.1 naive — the instrument works. The prediction test: 60 related sequences vs 60 shuffled, related error 1862.5 < shuffled 2537.9, permutation p = 0.0001 (beat all 10,000 reshuffles), related also beating a naive baseline (2944.1). *Meaning:* the earlier null was the dead substrate's verdict, not the task's. Word order carries real predictive information in this geometry. The bridge rung is complete: we have a world with structure.

### 3.2 Exp 19 — The world is steerable (qualified yes; bar not passed)

*Question: can a correction operator move through the geometry? Three operators compete — direct (αε), tangent PID (f(ε, Δε, Δ²ε)), random control — tuned by hill-climbing on a fixed verifier metric.*

The tangent walker settled faster than direct correction on all four held-out chains, but walked messier paths — winning 4/4 on speed, losing 4/4 on efficiency:

| held-out chain | steps: tangent / direct | path cost: tangent / direct |
|---|---|---|
| size | 33.0 / 42.5 | 1.23 / 1.04 |
| temperature | 20.0 / 60.0 | 1.13 / 1.05 |
| brightness | 30.0 / 38.5 | 1.42 / 1.07 |
| speed | 91.5 / 200 (timeout) | 4.73 / 2.07 |

The tuner genuinely used history (β = −0.32/−0.30/+0.21/−0.38 — mostly damping, one sign flip, noted as a warning that the optimizer can exploit degrees of freedom). A hypothesized settling signature (|Δ²ε| → 0 near the target) was falsified — the residual near the target is noise-dominated. The 16D robustness condition went degenerate because the settle tolerance wasn't scaled to the verifier's σ√d noise floor. *Meaning:* residual history carries usable signal — the measured fact that motivated Exp 20. Advanced as a *qualified advancement*, not "Exp 19 passed": speed ≠ path efficiency, and the bar demanded both.

### 3.3 Exp 20 — History earns its inputs (bar passed)

*Question: is the history advantage real, or is it extra parameters? Three arms, same everything: memoryless u = f(ε) vs real history u = f(ε, Δε, Δ²ε) vs a permuted-history control (history features drawn from scrambled time indices — same marginals, destroyed temporal alignment).*

The pre-registered bar (history < memoryless AND history < permuted on median steps, all four folds) passed both halves:

| held-out chain | steps: history / memoryless / permuted |
|---|---|
| size | 7.0 / 8.0 / 9.0 |
| temperature | 6.5 / 9.5 / 9.0 |
| brightness | 8.5 / 10.0 / 9.5 |
| speed | 6.0 / 8.0 / 8.0 |

Timeout rate 0.00 throughout. The permuted arm performed about like memoryless (its β fit near zero in 3/4 folds) — so the win is *temporal structure*, not extra parameters or inputs. The β diagnostic: −0.16/−0.19/−0.07/−0.10, negative in 4/4 folds with variance 0.0023 — a stable, transferable damping term (no Exp-19-style sign flip); α tuned nearly equal across arms, so the β term does the work. Path costs stayed ~1.01 for both history and memoryless — faster without messier paths. *Meaning:* one concrete mechanism consistent with "the remainder of correction becomes the next correction signal" — not the philosophical proposition. A 16D follow-up confirmed the tolerance fix but showed the history advantage attenuating (2W/1T/1L, β shrinking): correction dynamics live in the top PCs; dims 5–16 are mostly verifier noise.

### 3.4 Exp 21 — The verifier selects the law (bar not passed; the failure is the finding)

*Question: can a verifier-driven learner discover the history advantage by itself — with no teacher, no demonstrations, no hand-shaped penalties?*

Frozen Exp-20 history PIDs served as reference. Two REINFORCE+Adam learners — history (α, β, γ) and memoryless (α only), init (0.1, 0, 0) — trained on the verifier's minimal signal r_t = ‖ê_{t−1}‖ − ‖ê_t‖. The bar (history beats memoryless all folds; |β| > 0.05 all folds; within 1.5× of reference) was not passed (1/4; 3/4; 3/4). But both learners *did* learn (28 → 6–12 steps), and the history learner *did* discover history-dependence with a consistent sign — **positive** β in all four folds (+0.033/+0.227/+0.060/+0.087):

| fold | learned (α, β, γ) | steps vs memoryless-learner | steps vs frozen ref |
|---|---|---|---|
| size | (+0.394, +0.033, −0.092) | 8.0 v 6.0 (loss) | 8.0 v 7.0 |
| temperature | (+0.288, +0.227, +0.035) | 12.0 v 10.0 (loss) | 12.0 v 7.0 |
| brightness | (+0.389, +0.060, +0.106) | 7.5 v 6.0 (loss) | 7.5 v 8.5 |
| speed | (+0.609, +0.087, +0.055) | 6.0 v 10.5 (win) | 6.0 v 6.0 |

The learner discovered the *reactive/lead* law, not Exp 20's damping law. A pre-run pilot head-to-head explains why: under the minimal reward, the reactive law scores +23.73 vs +23.27 for the smoothing law — nearly indifferent (2% gap); under the hand-shaped composite they separate 2× (68.7 vs 30.8). The overshoot/path penalties were load-bearing for discovering damping. Meanwhile the memoryless learner went bimodal: α ≈ 0.86 (hyper-aggressive, 6 steps, path 1.34–1.45) on two folds vs α ≈ 0.25 (cautious, 10+ steps) on two — the bare verifier rewards recklessness inconsistently. *Meaning:* Exp 21 did not fail at the capability question; it failed at the hoped-for law-recovery question, and the failure explains why. A verifier can identify improvement without uniquely specifying what good correction looks like. The honest conclusion: *there was no uniquely correct correction law specified by the verifier, and the learner discovered one of the behaviors that the verifier rewarded.* The machine understood the verifier. The question is what the verifier asked for.

### 3.5 Exp 22 — The selection map (bar not passed as literally stated; the map is clean)

*Question: does changing only the verifier reliably move the discovered (α, β) toward different dynamical regimes?*

Learner, substrate, folds, seeds, and instrument frozen; only the reward varied across V₁–V₄ (Section 2). Both learners trained under each verifier; full behavioral fingerprint per cell. The pre-registered bar — (a) β(V₂) < β(V₁) all folds, (b) β(V₂) < 0 in ≥3/4, (c) β(V₁) > 0 all folds — came out 3/4, **4/4**, 3/4. Both misses are the same fold (brightness), where the *minimal* verifier itself discovered damping (β = −0.380) — predicted by Exp 21's indifference finding, not a refutation. The bar had assumed V₁ was a stable "reactive" endpoint; Exp 22 shows V₁ is not an endpoint at all. It is an underdetermined region.

| verifier | β per fold | α per fold | steps | path cost | induced regime |
|---|---|---|---|---|---|
| V₁ improvement only | +0.03/+0.41/−0.38/+0.10 | 0.33–0.71 | 7–19.5 | 1.07–5.70 | **underdetermined** — reactive, damping, or degenerate (one fold: 17.5 overshoots, path 5.7× — a chaotic attractor the bare verifier tolerates) |
| V₂ − overshoot penalty | −0.22/−0.03/−0.06/−0.05 | 0.48–0.73 | 6.0 ×4 | 1.08–1.53 | **damping, fast** — the clean law recovered by the verifier alone, no teacher |
| V₃ − path-cost penalty | −0.20/−0.08/+0.01/−0.03 | 0.67–0.83 | 6.0 ×4 | 1.19–1.79 | **aggressive** — for clean proportional control total path ≈ |ε₀| regardless of α, so the penalty is ~constant and improvement drives α up; the reactive law's wasted path is what gets punished |
| V₄ − action-smoothing penalty | −0.22/−0.26/−0.26/−0.20 | 0.23–0.73 | 6–8 | 1.03–1.39 | **damping, tightest cluster** (β range 0.06), cleanest paths — penalizing action-jerk directly selects low-pass smoothing |

The memoryless learner moved too: V₁ bimodal again (α = 0.854 vs 0.175–0.367); V₃ uniformly aggressive (α = 0.68–0.81, 6 steps everywhere). *Meaning:* verifier shape → incentive landscape → correction dynamics, as a controlled map. Four readings of the same world: "Did it help?" → no unique law; the seed picks reactive, damping, or chaos. "Did it help, without overshooting?" → damping, reliably, 4/4. "Did it help, cheaply?" → aggression, fast but messy. "Did it help, smoothly?" → the cleanest damping of all. None of these laws is wrong — each is a valid maximizer of what its verifier asked.

**[Figure 1 placeholder: `tangent_experiment/figures/exp22_alphamap_4d.png` — the selection map: one (α, β) point per fold per verifier. V₁ scattered; V₂/V₄ tight damping clusters; V₃ far right.]**

### 3.6 Exp 23 — The induced law transfers (bar not passed as literally stated; the transfer is real)

*Question: once sculpted, is the law a transferable operator?*

Everything from Exp 22 frozen — thetas, substrate, instrument, **zero test-time learning** — and three frozen controllers per fold (the V4-induced damping law, the V4-trained memoryless law, and whatever V₁ had induced) evaluated on 40 genuinely unseen trials: **T1**, eight brand-new words never embedded before (tiny/enormous, freezing/scorching, gloomy/radiant, sluggish/rapid) paired within-chain (new points, familiar geometry); **T2**, cross-chain pairings within the training |ε₀| range [12.33, 43.27] (new combinations, familiar scale); **T3**, cross-chain pairings outside that range (new trajectory geometry). Plus a label-shuffle control (pinned permutation of targets).

The pre-registered bar — (a) V4-history overshoot < V1-history overshoot all folds, (b) V4-history path < V4-memoryless path ≥3/4 folds, (c) zero timeouts — came out 3/4, 3/4, **4/4**. Pooled across folds: V4-history overshoot ≈ 1.43 vs V1-history ≈ 5.97. Per type, the V4-induced law was best-or-tied on every metric:

| type | V4-history steps / path / overshoot / jerk | V1-history overshoot |
|---|---|---|
| T1 new words | 6.5 / 1.08 / 1.28 / 0.111 | 6.48 |
| T2 new combos | 6.2 / 1.12 / 1.46 / 0.116 | 3.90 |
| T3 new geometry | 7.0 / 1.07 / 1.58 / 0.093 | 7.52 |

The smoothness property itself transfers (jerk 2–3× lower than V1 on every type). The shuffle control preserved V4's fingerprint almost exactly (path 1.076, overshoot 1.27) — a correction law over geometry, not memorized word pairs.

The bar's misses are the underdetermination result made visible. Fold 0's V₁ law was *mild* (β = +0.033), not reactive — and the mild law transferred fine, even slightly beating V4 on raw overshoot. Fold 1's V₁ law was the *degenerate* attractor — and off-distribution it disintegrated: 33 steps, path cost 10.04, 19.2 overshoots. Same verifier, same learner, different seed: one law travels, the other collapses. *Meaning:* Exp 22 showed the verifier can sculpt a law; Exp 23 shows the sculpted law is a transferable operator. The pinned claim: **V4 induced a transferable correction policy.** Substrate (where the world is represented), verifier (what counts as improvement), correction law (how the system moves), and generalization (whether the law survives elsewhere) are now four separated pieces of the architecture.

**[Figure 2 placeholder: `tangent_experiment/figures/exp23_overshoot_4d.png` — mean overshoot on unseen situations by controller × generalization type (frozen thetas, no test-time learning).]**

---

## 4. Limitations

These are scope conditions, not apologies — they are pinned so every claim above stays attached to its evidence.

- **Linear PID policy class throughout.** Every "law" in this paper is a point in (α, β, γ)-space. A null here kills claims about this policy class, not about correction learning in general.
- **4D only.** The effects live in the top principal components (Exp 20's 16D attenuation: dims 5–16 are mostly verifier noise). Nothing here is shown above 4D.
- **One volunteer, one layer, four hand-picked chains.** Qwen2.5-0.5B-Instruct, layer 23; chain choice is a confound until varied. The substrate phase stayed observational throughout — no model training, no reward modification.
- **Pinned seeds, one per fold.** Seed sensitivity is measured where it appeared (Exp 21's bimodal memoryless learner; Exp 22's V₁ scatter; Exp 23's fold-0 vs fold-1 V₁ divergence) but not systematically explored.
- **Penalty scales pinned a priori** (λ_ov = 5.0, μ_pc = 20.0, λ_st = 10.0), not tuned. The experiments test whether these move the regime, not optimal tuning.
- **Toy scale throughout.** 24 training trials, 40 test trials, a 0.5B model. The honest reading of a strong result here is "verifier shape reliably sculpts learned correction dynamics *in this toy*" — not a claim about intelligence, and not the philosophical proposition that motivated the program.

---

## 5. Conclusion

This program established, link by link, an empirical demonstration of the pointer-vs-arrow principle for learned correction:

1. **Exp 18** — Representation geometry carries structure (once the substrate is contextual and multi-dimensional).
2. **Exp 19** — The geometry is steerable, and steering trades speed against path cleanliness.
3. **Exp 20** — Temporal residual structure genuinely improves steering — and it is the *timing*, not the parameter count, as the permuted-history control shows.
4. **Exp 21** — A verifier-driven learner discovers temporal correction, but the verifier's shape selects *which* temporal law emerges; a bare "did it help?" verifier is nearly indifferent between laws.
5. **Exp 22** — Varying only the verifier maps to distinguishable dynamical regimes as a controlled experiment: underdetermined (V₁), damping (V₂), aggressive (V₃), ultra-stable damping (V₄).
6. **Exp 23** — The law induced by the smoothness verifier transfers to unseen words, pairings, and trajectory scales with zero retraining, while minimally-verified laws transfer unreliably.

Each experiment earned only its own claim, and several of the deepest findings arrived as informative bar failures rather than clean passes. The through-line is the one stated in the abstract: the residual history gives the learner a space of possible correction behaviors; the verifier determines which direction through that space is rewarded. The learner is never confused about what it was asked. The question is always what was asked.

**Open next question.** Exp 23's transfer stayed inside one model's embedding space and one PCA basis. The sharp follow-up is a harder distribution shift: does the V4-induced operator survive different embeddings (another model, another layer), a different projection basis, or non-gradation semantics — or is transfer bounded by the representation it was sculpted in? That experiment would separate the portability of the *law* from the portability of the *geometry* — the next natural link in the chain.

---

## Reproducibility note (for the repository release)

All experiments are single-file Python scripts with pinned seeds (`tangent_experiment/exp18_contextual.py` through `exp23_generalization.py`), a shared spec per experiment under `~/workspace/ai-theory/`, cached embeddings, and a running log (`tangent_experiment/RESULTS.md`) with full per-fold tables. Figures regenerate from the saved JSON result files. The volunteer model weights are read-only throughout; the substrate phase is strictly observational.
