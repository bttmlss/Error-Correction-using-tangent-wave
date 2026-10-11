# The Steerable Plant — Stage 0 + Bar 0 Spec (LOCKED 2026-10-07)

**Date:** 2026-10-07 · **Status:** LOCKED — Adrian's sign-off 2026-10-07 ~22:25, three
contract details verified in-file. No design changes without a new dated amendment
and explicit re-sign-off.
**Design authority:** Adrian's 2026-10-07 ~21:07 directive — yes to ChatGPT's "external
correction module" direction, with the plant-first change: the first question is not
"does β work on an LLM?" but "is an LLM revision loop a plant a controller can steer
at all?" ChatGPT's architecture (LLM → verifier → e,Δe,Δ²e → controller → revise) is
accepted as the target; Adrian's staging below is the gate it must pass through.
**Parent results:** EXP24/25/26/27 reports (transfer, ablation, sweep, control battery);
revision-loop atlas closeout (no assumed state grammar — the operator works on the
residual trajectory itself, not on discrete states).

**Amendments (Adrian's pre-lock reviews — integrated before lock):**

*2026-10-07 ~22:25 (LOCKED — Adrian's sign-off, three contract details verified in-file):*
L0. **Lock.** No further design changes without a new dated amendment and Adrian's
    explicit re-sign-off. Commit: `7719623e0e542600ea062fc7fbe0fb0415c081da` (spec + `prelock_bootstrap_sim.py`
    + `prelock_bootstrap_sim_results.json` +
    `prelock_bootstrap_sim_results_readability.json`, committed together).
    Contract details verified before lock: (1) shuffled-replicate t is the position
    index 1..T in the shuffled order — reassigned, never carried as π(t);
    (2) sign/start-length confound pre-registered — one-sign failure reads as
    operating-point failure, not actuator asymmetry; (3) every Stage 2 claim scoped
    to "under T1 wording," slope-ratio miss a recorded limitation, not a footnote.

*2026-10-07 ~21:17 (batch 1):*
1. Bar 0 moved into the noisy regime: trajectories logged once, noise added to the
   controller's observation offline (no extra LLM calls); M0/M1 fit per σ predicting
   the true e_{t+1}.
2. Stage 0 bars rebuilt: resolvability replaces the IQR rule (which fails at low
   command by construction); trial-level ρ with shuffled-u null, simulated gain-1
   positive control (the G2 lesson), gain band, saturation check; bootstrap CI on the
   template ρ difference instead of a fixed 0.15.
3. Actuator redefined in absolute units ("change length by u words") so Stage 0
   calibrates the same command Stage 2's law outputs; e₀ fixed per task; clipping
   specified.
4. Budget rewritten with the σ dimension; arms 1–2 reuse samples across σ; tuning
   grids and the second task counted; σ₀ defined from the Stage-0 step SD.
5. Best-of-8 selects on the noisy observation; trials vary temperature and source
   text; deterministic validity gate; e₀ added to M0; typo fixed.

*2026-10-07 ~21:26 (batch 2):*
6. Bar 0 retirement rule was self-contradictory (header retired on AND-both-fail;
   body retired on AND-rule-fails). Replaced with **three outcomes**: signal (gap ≥
   0.02 AND p ≤ 0.05), null (gap < 0.02 AND p > 0.05), ambiguous (exactly one).
   Only null-at-every-σ>0 retires; ambiguous gets a pre-registered path.
7. Pooled ρ is mostly a direction check (~0.87 for a sign-only plant on this ladder)
   — proportionality is tested per sign, with **bars derived from the simulated
   gain-1 control** (ρ_ideal,sign − 0.15, floored at 0.40), not picked; both signs
   failing is a hard stop.
8. Stage 0 loose ends closed: resolvability on the coarse ladder (fine pair
   diagnostic-only) with an empirical noise-floor probe first; the readability task
   gets a full actuator spec (units, ladder, e₀, clip, σ₀); the template bootstrap
   is paired and clustered by source text.
9. Stage 1 stats: grouped CV (trajectory = group) + permutation p with independent
   fresh shuffles per replicate (never one shared fixed shuffle — the G2 failure
   mode); σ=0 prediction worded as a trend (the plant carries σ₀ even at injected
   σ=0); e₀ enters M0/M1 as the noisy-observed e₀, like everything the controller sees.
10. Pre-registered **tuned-once-and-frozen** (at σ=1.0σ₀) vs per-σ tuning; grids
    equalized at 10 seeds (the 5-vs-10 asymmetry gave the joint grid higher
    winner's-curse risk); pilot **excluded** from confirmatory data, running on the
    transferred prior (α=0.2, β=−0.1).

*2026-10-07 ~21:33 (batch 3 — two arithmetic errors, one sign-convention hole):*
11. Readability actuator rebuilt to fit its clip: F* = 60, e₀ = −10 (start F≈70),
    ladder u ∈ {±10, ±20} Flesch points (implied range 50–90, inside achievable
    [20, 90]); u>0 = easier; resolvability via the pooled version (only one
    qualifying coarse pair). *(Single-e₀ design superseded by 22: each sign now
    starts from its corrective side; implied F range 50–70.)*
12. Bar (b)'s floor rule was unfalsifiable (bar = max(rule, floor) can never fail —
    the fiat move (a) forbids). Now: the empirical floor probe runs first; floor >
    bar → **FAIL (b) immediately**, finding recorded, pre-registered escalation
    branch taken; the ladder does not run.
13. Sign convention pinned toy-verbatim (**code-verified** in exp20_residual.py):
    e := target − actual, u = αê + βΔê (+γΔ²ê), applied as actual ← actual + u,
    thetas verbatim. Arms 6–7 include γ verbatim; arm 7's rescale procedure pinned.
14. Bar (c) was failure-to-reject on a wide CI. Now TOST-style equivalence: pass
    iff the 95% paired-cluster bootstrap CI ⊆ [−0.10, +0.10], with pre-registered
    simulator validation (identical plants must pass, deliberately different plants
    must fail).
15. Bar 0 gets a within-trajectory **time-shuffle** control: the primary gap is
    gap_real − gap_timeshuffled (temporal structure, not level offsets leaking
    through noisy Δe). The Stage-1 fixed prompt is pinned (target + residual stated,
    no step command). *(Formulation superseded by 20, then 23: gap is now the
    M1−M0 R² difference with the null from B fresh shuffles, both models refit.)*
16. Smaller: both tuning grids use the same 20 train tasks (the seed fix didn't
    cover tasks — the noisier selection hurt α+β); the 2.0σ₀ dip reading
    pre-registered (mis-tuning, not mechanism) **plus** one diagnostic local re-tune
    (top-5 cells, 8k calls/task); gain band per sign; the 0.40 floor dropped (if
    ρ_ideal,sign < 0.55 the substrate can't resolve proportionality → escalation,
    not re-derivation); Stage 1 budget line added (4,800 calls logging; analysis
    offline).

*2026-10-07 ~21:46 (batch 4 — four problems that change what gets run):*
17. **One prompt skeleton, all stages.** The old spec let the prompt state the true
    residual while the controller worked from noisy ê — the LLM would see through
    the noise and the noisy regime wouldn't exist. Now: the prompt always states
    the **noisy ê** (one noise draw per round; the stated residual and the
    controller's input are the same ê_t); the LLM never sees the true residual.
    Consequences: Stage 1 runs **live per σ** (the offline-noise construction is
    retired — 19,200 calls); arms 1–2 **cannot reuse samples across σ** (budget
    recomputed). Stage 0's prompt was command-only — it now uses the full skeleton
    (supersedes amendment 15's command-only prompt).
18. **"Task" defined; bank sized.** A task := (source text, task-type); splits are
    by source text. Bank of **100 source texts**, disjoint: 20 Stage 0 (default 10;
    the pre-lock null simulation decides) + 10 Stage 1 + 10 pilot + 20 train + 40
    held-out. With e₀, W* fixed, task diversity = text diversity (plus
    temperature) — recorded as a limitation (future: vary W*). Pre-lock gate: run
    the null-case bootstrap simulation (10 clusters, assumed noise scale — the
    floor probe hasn't run; see checklist); lock
    only if P(CI ⊆ ±0.10 | null) ≥ 0.8, else raise Stage-0 texts to 20 and
    re-simulate.
19. **Arm 7's gain was inverted.** (a) defines gain g = realized ÷ commanded, so
    u_task = σ₀·u′/g_sign (not gain·σ₀·u′, which realizes g²·σ₀·u′). Fixed, with
    the sign-specific gain.
20. **Bar 0's p now matches its statistic.** B fresh within-trajectory
    time-shuffles form the null for the gap directly: p = share of shuffled gaps ≥
    the observed gap. This single procedure replaces the gap_temp subtraction AND
    the cross-trajectory permutation p (the dither control stays — it tests
    content, a different question).
21. Pre-registered expectation (not a fix): readability will likely stop early —
    two levels per sign puts ρ_ideal near the 0.55 abort line, and a floor SD above
    6.7 fails (b) outright. A readability fail with a word-count pass is a finding
    about the actuator; bars are recorded per task and the program proceeds on the
    tasks that pass.

*2026-10-07 ~22:07 (batch 5 — three problems that change what gets run):*
22. Stage 0's positive sign tested defiance, not compliance: the prompt stated
    "60 over target" while commanding "lengthen by u" — a context Stage 2 never
    uses (u>0 only occurs when the residual says "under"). Now each sign starts
    from the side where it is corrective (word count: e₀=−60 for u<0, e₀=+40 for
    u>0; readability: e₀=−10 for u<0, e₀=+10 for u>0), same call count. A "one
    sign fails" outcome can no longer be a prompt artifact, nor can a corrupted
    g_sign feed arm 7.
23. Bar 0's null had two holes: (a) gap^(b) refit only M1 against the unshuffled
    M0 — a negatively biased null returning p ≈ 1/1001 for any positive gap; now
    both models are refit on the same shuffled sequences, one permutation applied
    to true and observed values together. (b) Fixed e₀'s shared decaying transient
    could signal alone once the time-shuffle destroys it; round index t added to
    both M0 and M1 (post-transient rounds reported as robustness check).
24. Template gain agreement: bar (c) is blind to gain (proven in simulation —
    ρ is scale-free), so T1 at gain 0.5 and T2 at gain 1.5 would pass (a) and (c)
    while changing arm 7's σ₀·u′/g threefold. **T1 pre-registered as the
    controller's template** (arm 7 uses T1's per-sign gains; T2 is shape-only for
    bar (c)), plus a reported slope-ratio CI with [0.75, 1.33] equivalence band
    as a diagnostic — a fail records "gain is prompt-sensitive," not "plant
    unsteerable."
25. Smaller: "empirical" → "assumed (5–15 words, within bar (b)'s cap)" in the
    checklist (the floor probe hasn't run); readability null simulation run
    (80 trials/template, 4 levels — see pre-lock checklist); pilot budget stated
    per task-type (5,600 × 2 = 11,200 both).

## The question this program answers

Can an external controller observing an LLM's revision error trajectory improve the
probability or efficiency of correction **without modifying the model's weights**?

It does NOT ask whether β is a universal "AI damping function" — that claim is not
earned and is not tested here. The narrow claim under test: a history term can act as
a noise-dependent correction/smoothing mechanism, with its sign controlling whether
history attenuates or reinforces the correction.

## Sequential structure (pre-registered, gated)

- **Stage 0 — plant check.** Is the loop steerable at all? Dose-response on the
  commanded step, at σ=0, with the full prompt skeleton. Nothing proceeds unless
  the bar passes.
- **Stage 1 — Bar 0 on uncontrolled loops, live per σ.** Fixed-prompt revision with
  no controller; the decisive null with three pre-registered outcomes (signal /
  null / ambiguous): does Δe carry temporal structure predicting the next true
  error beyond (e, e₀) at any σ>0? Null-at-every-σ>0 retires the controller program
  for this plant.
- **Stage 2 — controller comparison at matched LLM calls.** Runs ONLY if Stage 1
  yields signal at ≥1 σ>0 (ambiguous-only goes to the pre-registered extension/stop
  choice, not to a full launch). Arms, noise sweep, and pre-registered predictions
  below.

Numbering held: 24–27 are taken; no experiment number is assigned until Stage 0
is scoped and locked.

## Sign convention (pinned, toy-verbatim, code-verified)

exp20_residual.py: `ehat = (T−X) + noise`, `dehat = ehat − ehat_prev`,
`d2 = dehat − dehat_prev`, `dX = α·ehat + β·dehat + γ·d2`, `X += dX`. The spec
uses this convention verbatim — no sign juggling:
- **e_t := target − actual** (signed, task units). Word count: e = W* − words
  (e>0 = too short). Readability: e = F* − Flesch (e>0 = too hard).
- **u_t = α·ê_t + β·Δê_t** (+ γ·Δ²ê_t for arms 6–7), thetas verbatim as learned
  (V4: α>0, β<0, γ≈0; pilot prior α=0.2, β=−0.1).
- **Applied as actual ← actual + u_t** in task units.
- Check: e>0 (short of target) → u>0 → lengthen ✓.
- **Arms 6–7 include γ verbatim** — the transfer question is about the learned law
  as learned. Arm 7 (rescaled): e' = e/σ₀, Δe' = Δe/σ₀ (σ₀ from Stage 0, per task);
  u' = α·e' + β·Δe' + γ·Δ²e'; **u_task = σ₀·u′/g_sign** with **T1's** sign-specific
  gains g_sign = realized ÷ commanded from Stage 0(a) (the old gain·σ₀·u′ realized
  g²·σ₀·u′ — inverted); clip to the Stage-0 clip range. The code pins the
  arithmetic; this paragraph is the pre-registered contract.

Side finding (Adrian, code-verified): the toy's noise is **observation-only with a
perfect gain-1 actuator**. That matches the injected-σ design — but "σ=0" here is
not the toy's σ=0, because our actuator carries its own noise σ₀. This is why σ₀
is a separately calibrated quantity and why the σ=0 predictions below are worded
as trends.

## The prompt skeleton (one plant, all stages)

Every prompt in every stage is built from one skeleton. The plant is the LLM's
mapping from prompt to response — if the skeleton varied by stage, we'd be
calibrating a different plant than we drive:

[source text] + [target statement] + [residual statement] + [command]

- **Residual statement:** "The verifier measures you at ê_t (<units> <over/under>
  target)." ê_t is the controller's noisy observation — **one noise draw per round;
  the stated residual and the controller's input are the same ê_t.** The LLM never
  sees the true residual. (The old draft let the prompt state the true e while the
  controller worked from noisy ê — the LLM would see through the noise and the
  noisy regime wouldn't exist.)
- **Command** (controller arms and Stage 0 only): "Change your response by u_t
  <units> (<lengthen/shorten · easier/harder>)." Stage 1's fixed prompt is the
  skeleton minus the command.
- **Consequence:** trajectories depend on σ (the stated residual is noisy), so
  nothing is reused across σ — not in Stage 1 (the offline-noise construction is
  retired; Stage 1 runs live per σ) and not in Stage 2 arms 1–2. The true residual
  is used only for scoring, never stated.

## Stage 0 design — the dose-response check

**The crux.** In the toy, the controller sets position directly. An LLM only takes a
prompt, and nothing guarantees a given prompt produces a predictable step. Stage 0
measures whether a commanded step is a real control input or a fiction — using the
full skeleton, at σ=0 (ê = e truthfully; the calibration is of the actuator).

**Actuator (absolute units, matched to the Stage-2 controller).** The command is an
absolute signed step u in task units, per the sign convention above. The measured
object is the realized step per commanded u — realized-vs-commanded, the same curve
Stage 2 will drive.

**Corrective-side starts (per sign).** Each sign of u is tested from the side where
it is corrective — commanding "lengthen by u" while the prompt states "60 over
target" tests defiance of the stated residual, a context Stage 2 never uses (u>0
only occurs when the residual says "under"). Word count: e₀ = −60 (140 words vs
W* = 80) for u ∈ {−10, −20, −40, −60}; e₀ = +40 (40 words vs W* = 80) for u ∈
{+10, +20, +40, +60}. Readability: e₀ = −10 (F≈70 vs F* = 60) for u ∈ {−10, −20};
e₀ = +10 (F≈50 vs F* = 60) for u ∈ {+10, +20}. Same call count (8 levels × 20
trials word count; 4 × 20 readability). A fixed e₀ per sign keeps the step from
scaling with |e| and confounding the dose-response; and a "one sign fails"
outcome can no longer be a prompt artifact — nor can a corrupted g_sign feed
arm 7.

**Clipping (pre-registered).** Word count: implied target words clipped to
[10, 400]. Readability: implied Flesch clipped to the achievable [20, 90].

**Tasks (ground truth controlled, continuous residual, cheap deterministic scoring):**
1. **Word-count targeting (primary).** W* = 80; ladder u ∈ {±10, ±20, ±40, ±60}
   words. Directly measurable, no judge needed.
2. **Readability targeting (secondary).** F* = 60; ladder u ∈ {±10, ±20} Flesch
   points, u>0 = easier (implied F range 50–70 across both corrective-side starts,
   inside achievable [20, 90]).
   Same bar structure, its own σ₀. **Pre-registered expectation:** readability will
   likely stop early — two levels per sign puts ρ_ideal near the 0.55 abort line,
   and a floor SD above 6.7 fails (b) outright. A readability fail with a
   word-count pass is a finding about the actuator; bars are recorded per task and
   the program proceeds on the tasks that pass.

Fermi estimates (log-error scoring) are *excluded* from Stage 0 — they add semantic
reasoning noise on top of the compliance question. They become candidates in Stage 1
only if Stage 0 passes on the constraint tasks. Open-ended writing quality is excluded
everywhere in this program until a win is measured on the clean tasks.

**Task definition and bank.** A task := (source text, task-type); splits are by
source text and apply identically to both task-types. Bank of **100 source texts**,
disjoint: 10 Stage 0 (pre-lock simulation confirmed 10 suffice — null P(inside
±0.10) = 1.000; see bar (c)) + 10 Stage 1 + 10 pilot + 20 train + 40 held-out +
10 spare. With e₀, W* fixed, task
diversity = text diversity (plus temperature) — recorded as a limitation (future:
vary W*).

**Trial variation (all stages).** Trials vary sampling temperature (round-robin over
{0.3, 0.7, 1.0}) and draw the source prompt from the stage's text allocation — never
one text repeated 20 times, or we measure compliance on one prompt instead of a
plant. Report ρ within each temperature; a dose-response that exists only at one
temperature is a finding, not a pass.

**The prompt-template confound (pre-registered control).** The command is mediated by
wording. Run the full u-ladder under **two fixed templates** (T1: "change the length
of your response by u words"; T2: an independently worded equivalent, e.g. "make
your response u words shorter/longer"). The dose-response must hold under *both* —
a response that exists only under one phrasing is a wording artifact, not a
steerable plant.

**Bars (per task):**
- **(a) Dose-response: direction and proportionality, separated.** Pooled Spearman ρ
  over all trials (word count: n = 8 levels × 20 trials = 160 per template;
  readability: n = 4 × 20 = 80 per template) ≥ 0.70 is the **direction** check —
  necessary, not sufficient: a plant that only gets shorten-vs-lengthen right, with
  no magnitude control, scores ~0.87 pooled on the word-count ladder. The
  proportionality test is per sign. Pre-registered controls (the G2 lesson):
  (i) **shuffled-u null** — permute u labels independently; |ρ| must be < 0.15,
  else the correlation is a pipeline artifact; (ii) **simulated gain-1 positive
  control** — ideal plant (realized = u + the observed noise); if the ideal plant
  can't clear the bars under the measured noise, the bars re-derive from the
  control, never lowered by fiat. **Per-sign bars, derived not picked:** per-sign
  bar = ρ_ideal,sign − 0.15, where ρ_ideal,sign is the gain-1 simulation's per-sign
  ρ under the observed noise (range restriction attenuates within-sign ρ, so the
  bar is calibrated, not chosen). If ρ_ideal,sign < 0.55 the substrate noise is too
  high for any per-sign proportionality test to resolve — that is a bar-calibration
  failure: record it, take the escalation branch, do not run a ladder that cannot
  resolve proportionality. **Gain band, per sign:** the Theil–Sen slope of realized
  on commanded u must lie in [0.5, 1.5] **within each sign** — asymmetric gains
  average to a pooled pass. **Saturation check:** median |realized step| at max |u|
  strictly exceeds the next level down, per sign. **Outcomes:** both per-sign bars
  pass → proceed; exactly one fails → **that (sign, start-length) operating point
  fails** — pre-registered reading: sign and start length are now confounded
  (shortening starts at 140 words, lengthening at 40; counting noise typically
  scales with length), so a one-sign failure is NOT read as actuator asymmetry;
  amended scope only with Adrian's sign-off; **both fail → hard stop, not a
  plant.**
- **(b) Resolvability — floor probe first, then the coarse ladder.** **Empirical
  floor first:** before the ladder, estimate the step-noise floor from the existing
  270-call atlas data if word counts were logged, else run the 40-call probe
  (fixed prompt, no command, temperature round-robin). If the empirical floor SD
  already exceeds the bar below → **FAIL (b) immediately**: finding = "substrate
  noise floor exceeds resolvability on this substrate"; take the pre-registered
  escalation branch (separate Stage-0 rerun on a more capable model); the ladder
  does not run (this still saves the calls). The bar is never re-derived upward to
  meet the noise — that is the fiat move (a) forbids. **The bar:** word count —
  within-level SD ≤ 0.5 × adjacent-level median spacing on pairs with spacing ≥ 20
  (SD ≤ 10 words; the 10↔20 fine pair is diagnostic-only — a 2B model likely can't
  resolve 10-word steps even as a usable actuator). Readability — the pooled
  version (only one qualifying coarse pair exists: the −10↔+10 crossing at spacing
  20): pooled within-level SD ≤ 0.5 × mean adjacent spacing (≈13.3 → SD ≤ 6.7
  Flesch points).
- **(c) Template agreement: equivalence, not failure-to-reject.** 95% paired
  cluster bootstrap (10k resamples; resample the source texts with replacement,
  paired T1/T2 trials — same level, trial index, temperature — within):
  **pass iff the CI ⊆ [−0.10, +0.10]** (TOST-style; δ = 0.10 pre-registered). With
  10 clusters the CI is wide, so noisy data passes easily under failure-to-reject —
  equivalence requires the CI to actually fit inside the margin. **Simulator
  validation (pre-registered):** (i) null case — split T1's trials into two
  pseudo-templates (same plant) → CI must lie inside ±δ (pass); (ii) positive
  control — T1 vs gain-halved T1 (a deliberately different plant) → CI must NOT
  lie inside ±δ (fail). If either simulator check misbehaves, the bar is
  miscalibrated — diagnose, do not proceed. **Pre-lock gate:** run the null-case
  simulation (10 clusters, assumed noise scale — the floor probe hasn't run; see
  checklist) before lock; lock only if
  P(CI ⊆ ±0.10 | null) ≥ 0.8 — else raise Stage-0 texts to 20 (960 calls) and
  re-simulate. Compute-only, no LLM calls.

**Template gain agreement (pre-registered diagnostic).** Bar (c) is blind to gain —
the paired-cluster bootstrap simulation proved it (Spearman ρ is scale-free): T1 at
gain 0.5 and T2 at gain 1.5 would pass (a) and (c) while changing arm 7's
σ₀·u′/g threefold. So **T1 is the controller's template**: arm 7 uses **T1's**
per-sign gains; T2 is shape-only for bar (c). Separately, report the paired-cluster
bootstrap 95% CI (same resampling as (c)) on the gain ratio (Theil–Sen slope_T1 /
slope_T2) per sign, with equivalence band [0.75, 1.33]. A CI outside the band is
not a hard fail — it records "gain is prompt-sensitive; transfer uses T1's wording
exactly; do not generalize the gain to rephrased prompts." **Scope (pre-registered):
every Stage 2 claim is "under T1 wording."** A missed slope-ratio diagnostic is a
recorded limitation of the Stage-2 report — stated in the results, not a footnote.

All three bars must hold per task. Any hard fail → **not a plant: stop. Full stop.**

**Scale calibration (the rescaling lesson).** Stage 0 outputs the plant's native
scale, **per task**: **σ₀ := the pooled within-level SD of realized steps**, plus
the per-sign gains from (a). σ₀ is the noise unit for every later sweep (Stage 1's
σ ladder, Stage 2's injected σ); the gain replaces V4's magnitudes in arm 7.
Recalibrate per substrate — never transplant raw thetas.

**Model (locked parameter).** Default: local Gemma-2B via the atlas harness (270
calls, 0 errors — the known-good loop). Pre-registered branch: if Stage 0 fails on
bar (a) or (b), the finding is "not steerable on this substrate," and the escalation
option (a more capable model) is a *separate pre-registered Stage 0 rerun*, not a
rescue of this one. A small model that can't follow step commands is data about the
plant, not a reason to re-roll.

**Budget:** 8 levels × 20 trials × 2 templates (word count) + 4 levels × 20 × 2
(readability) = 320 + 160 = **480 calls** at the confirmed 10 texts (+40 for the
noise-floor probe if the atlas data lacks word counts). Sized to the question.

## Stage 1 design — Bar 0: does history predict anything?

**Setup.** Fixed-prompt revision loop — the skeleton **minus the command** —
**no controller, no imposed α/β/γ**. Each round: model revises from the prompt
stating the noisy ê_t; verifier measures the true residual (scoring only, never
stated). Fixed horizon of 8 rounds. Log (e_t, Δe_t, Δ²e_t) per round per trajectory.
Fixed e₀ per task: the Stage-0 negative-sign start (word count e₀ = −60,
readability e₀ = −10 — the "over target / too easy" side; uncontrolled revision
is naturally corrective in one direction). ~300 trajectories per task from the 10
Stage-1 texts (constraint tasks; Fermi candidates only on a clean Stage-0 pass).
Trial variation per the Stage-0 rule. **Live per σ** — the stated residual is noisy,
so trajectories depend on σ; the offline-noise construction is retired.

**Fixed prompt (pinned).** "Target: 80 words. The verifier measures you at ê_t words
(M over/under target). Revise your response to move toward the target." — target and
the *noisy* residual stated, no step command. (Readability: analogous with the
Flesch band.) This is the skeleton minus the command — the only difference between
Stage 1 and Stage 2's arms is the controller.

**The σ ladder.** σ ∈ {0, 0.5σ₀, 1.0σ₀, 2.0σ₀} with σ₀ from Stage 0 (per task) —
one noise draw per round, shared by the stated residual and the (future)
controller's input. At each σ, fit:
- M0: e_{t+1} ~ (e_t, e₀^obs, t) — e₀ included so persistent per-trajectory traits
  are not mistaken for dynamics (with fixed e₀ it acts as the per-task intercept;
  its value is realized if e₀ is ever varied); **t (round index) included so the
  shared decaying transient — identical e₀ across trajectories — cannot signal
  alone** (the time-shuffle destroys the transient, which would otherwise make any
  gap look significant);
- M1: e_{t+1} ~ (e_t, e₀^obs, t, Δe_t^obs);
where every ^obs quantity is the noisy observation at that σ (e₀ is observed with
noise like everything else the controller sees — the predictand is always the true
e_{t+1}). R² via grouped K-fold CV with **trajectory as the group**
(within-trajectory transitions never split across folds). Report per σ, per task.
Post-transient rounds (t ≥ 4) are reported as a secondary robustness check.

**Bar 0 — the null is the time-shuffle, both models refit.** B=1000 replicates;
each replicate applies an **independent fresh within-trajectory time-shuffle**,
then refits **both** models on the shuffled sequences and records gap^(b) =
R²(M1_shuffled) − R²(M0_shuffled). (The old draft refit only M1 against the
unshuffled M0 — a negatively biased null that returns p ≈ 1/1001 for any positive
gap_obs.) One permutation π is applied to the true and observed error sequences
**together** — e^true_shuffled[t] = e^true[π(t)], e^obs_shuffled[t] = e^obs[π(t)] —
so the joint noise structure is preserved while temporal order is destroyed;
Δe^obs_shuffled is recomputed from the shuffled observed sequence. **t in the
shuffled replicate is the position index 1..T in the shuffled order — reassigned
to the new positions, NOT carried with the values as π(t).** Carrying t would
smuggle the transient back into the null (the model could recover original round
order from t) and make the null too generous. Both models are refit on the same
shuffled data. **p = (1 + #{gap^(b) ≥ gap_obs}) /
(1 + B).** The time-shuffle null already accounts for offsets (they survive the
shuffle), so a significant p *is* temporal structure beyond offsets and beyond the
shared transient. (The old cross-trajectory permutation tested "Δe carries any
information, offsets included" — a different null than the decision statistic.
Fixed.)
- **Signal** at σ: gap_obs ≥ 0.02 (absolute cross-validated R²) AND p ≤ 0.05;
- **Null** at σ: gap_obs < 0.02 AND p > 0.05;
- **Ambiguous:** exactly one holds.
Pre-registered shape: gap **monotone increasing in σ, smallest at σ=0** — a trend,
not gap≈0 at σ=0, because the LLM carries plant noise σ₀ even at injected σ=0.
**Program outcomes:** signal at ≥1 σ>0 → proceed to Stage 2 (ambiguous σ levels
flagged; the caveat travels). **Null at every σ>0 → retire** the controller program
for this plant. Ambiguous somewhere with signal nowhere → **no full Stage-2
launch**; pre-registered options are (i) a Stage-1 extension (+n trajectories at the
ambiguous σ, n sized from observed variance for 80% power on the 0.02 gap, capped
at 2× the original 300), or (ii) stop — Adrian picks.

**Dither control (per σ, pre-registered — kept).** M1-xshuffled uses Δe from a
*different* trajectory's noisy observation, independent shuffles per replicate
(Exp-20's permuted-history logic). It tests content-vs-dither — a different question
than the time-shuffle null — so it stays: if M1-xshuffled ≈ M1 at some σ, any
history benefit there is dither, not content, and Stage 2's scrambled-history arm is
expected to match the real-history arm at that σ.

**Pre-registered null branch:** Bar 0 retires → write it up plainly: "an LLM
revision loop on these tasks carries no exploitable history signal, at any tested
noise level." The program does not proceed to Stage 2 on this plant. A clean null
is a publishable result.

**Budget:** ~300 trajectories × 8 rounds × 4 σ × 2 tasks = **19,200 LLM calls** for
logging. Grouped CV, B=1000 time-shuffles, and the dither control are offline
compute — zero marginal LLM calls.

## Stage 2 design — controller comparison (gated on Stage 1)

**Arms (matched LLM calls — every arm gets exactly 8 calls per task):**
1. **Fixed revision prompt** (the pinned Stage-1 prompt, unchanged — the baseline arm).
2. **Best-of-8 resampling** (8 independent samples; selection on the **noisy
   observation** — never the true residual, or it's an oracle arm; at σ=0 the two
   coincide). The averaging control — without it, a "noise benefit" may just be
   averaging.
3. **α-only, tuned** (commanded step u = α·ê_t; α grid-tuned; sign convention above).
4. **α+β, tuned jointly** (u = α·ê_t + β·Δê_t; joint grid like R2-1).
5. **α+β with scrambled history** (Δe taken from a different trajectory — tests
   whether history *content* matters or it's just dither).
6. **Frozen V4 law, raw transplant** — thetas verbatim, applied to unscaled
   observations; pre-registered to fail without recalibration (the scale-mismatch
   expectation, stated before running).
7. **Frozen V4 law, rescaled** — the Exp-24 procedure pinned in the sign-convention
   block (normalize by σ₀, thetas verbatim incl. γ, u_task = σ₀·u′/g_sign with T1's
   sign-specific gains, clip).
   The fair transfer test.

Arms 1–2 **regenerate per σ** (the prompt states the noisy ê — samples can't be
reused across σ). The prompt in arms 3–7 is the pinned Stage-1 prompt plus the u
command, in the Stage-0 units. (The actuator Stage 0 calibrates is the actuator
Stage 2 drives.)

**Tuning protocol (pre-registered: tuned once, frozen).** The α grid (10 values) and
the α×β joint grid (80 cells) run **once, at σ=1.0σ₀, on the train split** — then
frozen for evaluation at all σ. Rationale: the claim under test is a *portable*
operator, not a per-noise oracle; per-σ tuning would roughly triple the tuning bill
and quadruple the winner's-curse surface. Both grids use **10 seeds and the same 20
train tasks** — the first fix covered seeds but not tasks, and the noisier selection
was hurting α+β; equalized. Never tune on the test set. (α=0.2, β=−0.1) is the
starting prior for the pilot only (below), not the tuned value.

**The 2.0σ₀ reading (pre-registered).** Tuning at 1.0σ₀ means the α+β advantage may
peak at 1.0σ₀ and dip at 2.0σ₀ from mis-tuning — so "grows monotonically" could fail
for the wrong reason. Pre-registered reading: a dip at 2.0σ₀ after monotone growth
through 1.0σ₀ is **mis-tuning, not mechanism failure**. One diagnostic settles it: a
**local re-tune at 2.0σ₀** (top-5 cells from the 1.0σ₀ grid × 10 seeds × 20 tasks ×
8 calls = 8,000 calls/task-type, train split only). If the re-tuned controller
restores growth → mis-tuning confirmed; if the dip persists → mechanism, and the
monotone-growth prediction fails as stated.

**Verifier noise is the swept variable (the 27A shape).** The controller observes
residual + injected noise at σ ∈ {0, 0.5σ₀, 1.0σ₀, 2.0σ₀} with σ₀ from Stage 0
(per task) — one draw per round, shared by the stated residual and the controller's
input; **scoring always uses the true error.** Pre-registered predictions:
- at σ=0, α-only ties or beats α+β (the 27A2 result, now as a prediction);
- the α+β advantage over α-only appears and **grows monotonically with σ**
  (subject to the 2.0σ₀ mis-tuning reading above);
- if the advantage does not appear with noise, **that is the result** — the
  operator has no reason to exist, and the program retires the claim.

Do not pick a single noise level (Adrian's pushback on ChatGPT's draft): one level
cannot separate denoising from luck.

**Goodhart guard.** The controller's steering verifier and the scoring metric must
be distinct where the task allows it (e.g., Fermi: steer on a noisy estimator,
score on true log-error). Where the residual *is* the score (word count), add a
pre-registered **deterministic** validity gate — all three computed, no model
judge: word overlap with the source prompt ≥ 0.30 (content preservation), max
3-gram repetition rate ≤ 0.20, final sentence ends with terminal punctuation
(completeness). Degenerate compliance can't win.

**Primary outcome:** final true residual |e_8|. Secondary: calls-to-threshold
(rounds to |e| < tol). Report per noise level, per arm, with seed intervals —
never pooled across noise levels unlabeled.

**Budget (with the σ dimension).** No cross-σ reuse anywhere (the prompt carries
the noisy ê). Tuning grids are counted, and so is the second task-type. Full-size
formula: [7 arms × 20 seeds × 40 tasks × 8 calls × 4 σ]
+ [α grid: 10 values × 10 seeds × 20 train tasks × 8]
+ [α×β grid: 80 cells × 10 seeds × 20 train tasks × 8]
+ [diagnostic re-tune at 2.0σ₀: 5 cells × 10 seeds × 20 train tasks × 8]
≈ 179,200 + 16,000 + 128,000 + 8,000 ≈ **331k calls per task-type**,
≈ **662k both task-types**. **Pilot role (pre-registered):** the 5,600-call pilot
cell **per task-type** (7 arms × 5 seeds × 10 tasks × 8 calls × σ ∈ {0, 1.0σ₀} =
2,800 × 2; 11,200 both task-types) is
**excluded from the confirmatory data** — harness check and variance calibration
only (calibration data doesn't become confirmatory data; the G2 lesson). Pilot arms
run on the transferred prior (α=0.2, β=−0.1), not tuned values: the pilot tests the
prior, tuning happens post-pilot on the train split. Size the full run from the
pilot's variance and pre-register n before launching; if the pilot contradicts the
Stage-1 signal shape, stop and diagnose rather than scaling up.
No 662k-for-impressiveness.

## Standing constraints

- Plain-language-first write-ups; results in markdown. Call models under test
  "volunteers," not specimens.
- The LLM substrate stays observational in Stages 0–1 (no training, no reward
  modification — bridge-then-jump holds: the controller is external or it is nothing).
- Numbers verified against run JSONs, never invented. Failed bars are findings.
- Nothing here authorizes weight modification, fine-tuning, or any Phase-3-style
  manifold work. Stage 2's controller is an outer loop around frozen weights.
- Expect the first win to be modest. Do not start with open-ended writing quality.

## Deliverables

- `steerable_plant_stage0.py` (+ `stage1.py` after the Stage-0 gate; deterministic
  seeds; eval-only)
- `steerable_plant_stage0_results.json`, `STEERABLE-PLANT-STAGE0-REPORT.md`
  (markdown, plain-language-first, in the same report format as EXP24/25/26/27)
- This spec, locked with Adrian's sign-off and any amendments as dated entries.
- Pre-lock checklist: (1) null-case bootstrap simulation at 10 clusters —
  lock only if P(CI ⊆ ±0.10 | null) ≥ 0.8, else 20 texts and re-simulate;
  (2) positive controls — CI must NOT lie inside ±0.10 for deliberately
  different plants. Compute-only, no LLM calls.
  **Result 2026-10-07 ~21:55** (`prelock_bootstrap_sim.py`, 120 experiments ×
  500 bootstraps, numba; results in `prelock_bootstrap_sim_results.json`):
  null P(inside ±0.10) = **1.000** at σ ∈ {5, 10, 15} words, with and without
  text-level gain heterogeneity, plus the literal split-half variant (mean CI
  widths 0.007–0.047 — far inside the margin). **10 texts suffice; no raise
  needed.** Positive controls (5×-noise T2, command-ignoring T2) fail
  equivalence at P(inside) = 0.000 everywhere — the test has teeth. Note: an
  early gain-halved control was dropped mid-simulation — Spearman ρ is
  scale-free, so it correctly *passes* equivalence at low noise; bar (c) tests
  shape agreement while gain is bar (a)'s job. **Noise levels were assumed
  (the floor probe hasn't run); all within bar (b)'s SD ≤ 10 cap — "empirical"
  in the checklist is corrected to "assumed."**
  **Readability result 2026-10-07 ~22:10** (same script, `readability` mode: 4
  levels {±10, ±20}, 80 trials/template, σ ∈ {3, 6} Flesch points bracketing
  bar (b)'s SD ≤ 6.7 cap; results in
  `prelock_bootstrap_sim_results_readability.json`): null P(inside ±0.10) =
  **1.000 / 1.000 / 1.000 / 0.983** (σ=3/6 × tgsd 0/0.2; mean CI widths
  0.017–0.077). **10 texts suffice for readability too** — the 0.983 clears
  the 0.8 gate, though the margin is thinner at σ=6 (wider CIs from 4 levels),
  consistent with the pre-registered expectation that readability resolves
  less cleanly.
