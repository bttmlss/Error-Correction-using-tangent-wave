# LLM Revision-Loop Atlas — Spec (DRAFT)

**Date:** 2026-10-07 · **Status:** DESIGN GREEN-LIT ~09:35 — freezes applied (error-signal
math, expansion criterion, H1/H2 exploratory, feature freeze). Stage 0 (synthetic
validation, zero LLM calls) authorized — FAILED its checkpoint; Stage 0.1 (constrained
model + dual-track, re-validation) authorized 2026-10-07 ~10:45. LLM pilot still needs
substrate confirmation. Stage 0.2 (targeted pattern battery) authorized 2026-10-07 ~11:20.
**STAGE 1 AUTHORIZED + FIRED 2026-10-07 ~12:03** (Adrian: 'go ahead and launch it, muse').
**STAGE 1 COMPLETE 2026-10-07 ~15:07 — VERDICT: INCONCLUSIVE (measurement validity gap).**
270 real LLM calls, 0 errors, ~3 h wall-clock. Pre-registered battery on the frozen
pipeline: Track A 9 / B1 3 / B2 3 / B3 4 firings (calibrated null expectations
0.0 / 1.11 / 0.93 / 0.0); informative 22-23/30 (power adequate). BUT 74/270 rounds
(27%) are commentary — no numeric answer, the volunteer praises/affirms instead of
revising — present in 20/30 trajectories. The frozen error math scores 'declined to
re-answer' as e≈0.9, manufacturing oscillation/divergence/solve-onset firings
(6 of 9 Track-A firings are commentary→answer transitions, not wrong→right).
Fourth productive failure in the sequence: the 1.0 commentary confound.
Expansion criterion: (a) power adequate → no; (b) firings are measurement-confounded,
cannot honestly be read as rejecting the single-regime account → no.
RECOMMENDATION (Adrian's call): Stage 1.1 — carry-forward rule for no-answer rounds
(e(t)=e(t-1), flagged non-revision; no new LLM calls needed) OR restated-answer
revision prompt (spec amendment; fresh 270-call run). Then re-run the frozen battery
and re-evaluate expansion.
**STAGE 1.1 COMPLETE 2026-10-07 ~16:00 — carry-forward reprocessing, zero new LLM calls.**
74 rounds carried forward (frozen parser; exactly the 74 commentary rounds). Battery on
corrected trajectories: Track A 6 / B1 0 / B2 0 / B3 0 (null expectations 0 / 1.11 /
0.93 / 0); the 3 killed Track-A firings were commentary flicker, the 6 survivors are
genuine wrong→right onsets. Informative 18/30. Bar 0: 24/30 = 80% zero-firing ≥ 75%
→ FIRES → retire for scope. CONFLICT: frozen expansion ground (a) trips (18 < 20
informative → 'power inadequate'). Adjudication notes: 12 of the 24 clean trajs are
non-informative (vacuous zeros); among informative, clean fraction 12/18 = 67%; but
power vs exotic patterns was adequate (20% true rate → 98% detection prob over 18
informative; observed 0). All 6 non-clean trajs are solve onsets (desired behavior,
not exotic states). RECOMMENDATION: retire per Bar 0 with the power caveat
documented — or hold the 18<20 tripwire binding and expand toward 100 (~9 h).
Adrian adjudicates.
**ATLAS RETIRED 2026-10-07 ~19:37 — Bar 0 execution (Adrian's adjudication).**
The 18<20 tripwire was overruled as a mechanical misapplication of a power rule
designed for edge cases: 0/18 exotic firings gives 98.2% confidence against ≥20%
true prevalence; the 6 non-clean trajectories are functional solves, not exotic
states; 80% clears the bar with compute efficiency considered. Scope-bound
retirement: "The state hypothesis is retired for local Gemma 2B × GSM8K-style
numeric math tasks × the neutral revision prompt × the frozen exact-match/embedding
measurement pipeline × the 9-round horizon." Power caveat documented in
revision_loop/REVISION-ATLAS-CLOSEOUT.md (18 informative < 20 tripwire; 12/24 clean
are non-informative; informative-clean 12/18 = 67%; retirement strong vs exotic
regimes, weaker vs 'no nontrivial dynamics' — never the hypothesis under test).
Total spend: 270 LLM calls. The revision-loop atlas is CLOSED.
Substrate LOCKED: local Ollama Gemma 2B, temperature 0, deterministic; GSM8K filtered
subset; 30 trajectories × 9 rounds = 270 calls; 4-detector battery (A+B1+B2+B3 — B4
dropped, curvature confound); family-wise FPR 6.7%.
**Parent:** the synthetic Correction Trajectory Atlas is FROZEN (ATLAS-PHASE1A-CLOSEOUT.md).
**Design authority:** Adrian's pivot ~09:00 — stop asking a simulator to reveal a law we
encoded; observe a correction process whose temporal policy is genuinely unknown.

## The question

Does an LLM's multi-round self-revision pass through recurring dynamical regimes
("states"), or does a single-regime model suffice?

The unknown is the model's own revision policy — what it does when asked to revise,
round after round, with no controller imposed. Nobody programmed the trajectory.

## Why this is the right next substrate (and what died)

Phase 1a retired the two-state grammar *and* showed the synthetic atlas cannot discover
what it programmed: every trajectory's temporal structure came from our loop; the LLM
supplied only static coordinates. The steering results (Exps 18–26) survive — those are
about controllability of real neural geometry. But a discovery program needs its unknown
in the process itself. Here the unknown is genuine: revision behavior, verifier
interaction, semantic movement, overshoot, stagnation, oscillation, give-up — none of it
is ours.

## Architecture: three separated layers

Adrian's framing, adopted as the spec's load-bearing structure:

- **Task correctness → exact-match signal.** Deterministic, frozen, zero noise floor.
- **Continuous measurement → frozen embedding distance.** Deterministic given the pinned
  checkpoint; supplies continuity the binary signal lacks.
- **Temporal inference → Bar 0.** Operates only on the frozen measurement; never on
  raw model outputs.

The verifier must never become an unacknowledged participant in the dynamics. Each layer
is frozen before the next is calibrated.

## Design

**Task (pre-register exactly one family for the pilot).** Needs a measurable target with
a *continuous* error signal — binary right/wrong is too coarse for trajectory analysis.
Decision: math word problems with verifiable answers (GSM8K-style), pre-filtered for
clean numerical/algebraic reference answers.

**Error metric (tightened per Adrian's review — the σ=0 lesson must not recur in a new
costume).** Two signals, both with *frozen semantics* fixed before any collection:
- **Exact match** on the final numeric answer (deterministic; noise floor = 0).
- **Frozen embedding distance** to the reference solution (deterministic given a frozen
  embedding model; the embedding model checkpoint is pinned in the run plan BEFORE the
  synthetic validation, so the validation exercises the entire measurement pipeline,
  not just the change-point fitter).

Primary trajectory signal: `e = 0` if exact match, else the normalized frozen embedding
distance, yielding a continuous scalar in [0,1]. **No LLM-as-judge scoring anywhere in
the measurement path** — a probabilistic verifier would let us "discover" the verifier's
scoring behaviors and mistake them for revision states.

**Continuous task error vs continuous measurement of task error (distinguished
explicitly).** Exact-match alone gives 1→0 step functions, and change-point detectors
will "find" kinks at the jump — measurement discreteness, not dynamics. The embedding
component supplies continuity of *measurement*. Known limitation, documented not hidden:
a correct answer phrased differently from the reference carries nonzero distance — a
*frozen* floor effect. Frozen means it cannot manufacture *temporal* structure, but it
is a floor, and floors are reported as floors.

**Frozen mathematical definition of the error signal (locked before synthetic
validation; any later change = new spec version, recalibration from scratch):**
- Let `a_t` = the model's complete round-t output text, verbatim (truncate to 4000
  characters if longer; truncation rule frozen here).
- Let `r` = the dataset reference solution text (GSM8K answer field), verbatim.
- `emb(x)` = L2-normalized embedding from pinned checkpoint
  `sentence-transformers/all-MiniLM-L6-v2` (exact revision pinned in the run plan;
  deterministic inference, no dropout).
- `exact_match(a_t) = 1` iff the final numeric answer extracted from `a_t` equals the
  reference numeric answer. Parser (frozen): take the number after `####` if present,
  else the last numeric token in the text; compare normalized strings exactly.
- **What is embedded: the full generated answer text** (reasoning + final answer) —
  because the scientific object is revision behavior: what the model says and how it
  moves across rounds. Not the final number alone (too coarse), not reasoning-only
  (arbitrary cut).
- `d_t = 1 − cos(emb(a_t), emb(r))`, clipped to [0, 1].
- `e_t = 0` if `exact_match(a_t) = 1`, else `d_t`.
- `Δe_t = e_t − e_{t−1}`; revision magnitude `m_t = 1 − cos(emb(a_t), emb(a_{t−1}))`,
  clipped to [0, 1].

**Loop (fixed, neutral).** Round 0 = initial answer. Rounds 1..8: the same neutral
revision prompt every round (e.g. "Review your previous answer and revise it if you
think it is wrong."). Fixed prompt, fixed round count — record ALL rounds even after
apparent convergence (stagnation and oscillation are data). No target leaked, no hints,
no steering.

**Record per round:** answer text; embedding; exact-match flag; e (per the metric above);
Δe; revision magnitude (embedding distance between consecutive answers); round
index. Feature set frozen at spec time — no adding signals after seeing data. Resist collecting extra signals just because they are available: the frozen set is answer → embedding → exact match → e → Δe → revision magnitude, nothing more.

**The anti-circularity rule (hard constraint).** Do NOT impose α/β/γ, a desired
trajectory, a target correction rate, or any controller. The model's revision policy is
the unknown. Violating this re-runs the synthetic atlas's failure.

**Vary (pilot keeps it small):** task difficulty strata (easy/medium/hard, pre-registered
bins); prompt framing as *labeled* arms (neutral "revise" vs "check your work carefully"
— never pooled unlabeled); one model for the pilot (which model = open decision).

**Trajectory budget (pilot):** ~100 trajectories × 9 calls ≈ 900 LLM calls. Staged:
~30 trajectories first (≈270 calls), expand to 100 only under the frozen expansion
criterion below.

**Frozen expansion criterion (no "interesting-looking states").** Expand from ~30 to 100
iff, on the preregistered analysis of the 30-trajectory pilot, EITHER:
(a) **Power inadequacy:** fewer than 20 trajectories exhibit ≥1 non-trivial revision
(revision magnitude > 0.05 and |Δe| > 0.02 at least once) — too few informative
trajectories to estimate the preregistered quantities; OR
(b) **Bar 0 rejects one-regime:** the validated detector indicates a potentially
non-single-regime process worth powering.
Explicitly NOT a trigger: trajectories appearing "stage-like" at n=30. Appearance of
states is never an expansion criterion. If Bar 0 retires within the pinned scope
(≥75% one-regime), do NOT expand — the question is answered for this substrate and
measurement.

## Bar 0 — decisive, runs first, can kill the program

Pinned scope (Adrian's wording, verbatim): *"The state hypothesis is retired for the
specified model × task family × revision prompt under the preregistered measurement and
trajectory horizon."* A retirement here means retired *for this pilot substrate under
this measurement* — not "LLMs don't have correction states." The 100-trajectory pilot
is sized for discovery, not for universal evidence.

Same change-point machinery as 1a, ported: fit e(t) with one regime vs two; ΔBIC with
**n-conditional calibration** (the close-out's methodological finding — null dBIC grows
with n; calibrate per trajectory length, never one global threshold). Pre-register the
retirement rule in the same form as 1a (≥75% one-regime → retired *within the pinned
scope*; 50–75% → conditional).

**Pipeline validation before real data (cheap, required, strict checkpoint).** Run the
full Bar-0 machinery — measurement pipeline included, embedding model already frozen —
on *synthetic* revision-like trajectories: pure single-regime decay with noise (must
overwhelmingly classify as one regime) and trajectories with injected kinks (must
reliably recover two regimes across the trajectory lengths and noise levels the pilot
will actually produce). **If either fails, no LLM calls happen — fix the instrument
first.** The detector must prove itself on data with known ground truth before it
touches the unknown process. This is the calibration step 1a taught us to never skip.

**On qualitative behaviors (Adrian's discipline).** The loop may produce wrong→corrected→
stable, wrong→better→worse→better, stalled, increasingly-confident→increasingly-wrong,
or overshoot→counter-correction→stabilization — none of it programmed. If such patterns
emerge, the first discovery is only: *"Revision trajectories are not adequately
described by a single dynamical regime."* State labels come later, and only through the
hardened machinery. That sequence is more powerful than starting with "find stages." 

## Stage 0.1 — instrument fix and re-validation (authorized 2026-10-07 ~10:45)

**Why:** Stage 0 (synthetic validation) FAILED its strict checkpoint: kink recovery 0.29
vs the 0.90 bar, selectively on smooth transitions (metric layer 9/9, nulls 95.5%,
solve events 0.97 all passed). Diagnosis: the 5-parameter free-intercept two-regime
model overfits noise at n=9 — the null threshold demands ~11× RSS improvement, so only
sharp discontinuities clear it. Power degrades with n; more rounds cannot fix it.
Per the checkpoint rule, zero LLM calls were spent. Stage 0's failure is preserved as a
documented finding: the original instrument had a **discontinuity bias** — strong on
abrupt changes, blind to smooth ones.

**The fix (Adrian-adjudicated): continuous piecewise-linear change-point model.**
Force continuity at the change point τ:

    e(t) = a + m1·t                 for t ≤ τ
    e(t) = a + m1·τ + m2·(t − τ)    for t > τ

One intercept, two slopes, and the change point (4 parameters, not 5). This matches the
phenomenon: a change in correction *rate*, not a teleportation in error.

**Dual-track Bar 0.** Track A — discrete solve events: handled deterministically by the
exact-match flag (wrong→correct→correct needs no statistical detector). Track B —
continuous dynamics: the continuous piecewise-linear change-point model on e(t), spending
its statistical budget on the harder question: *did the model's continuous correction
dynamics change?*

**Instrument contract — BOTH sides required (Adrian's addition).** Stage 0.1 passes iff:
1. **Null protection:** single-regime synthetic trajectories remain overwhelmingly
   classified as one regime (≥95% — the original 95.5% must not be sacrificed to buy
   power; lowering the threshold until everything is a kink is not a fix); AND
2. **Smooth-transition power:** each of rate-change, stall-improve, give-up, reversal
   reaches ≥0.90 kink recovery at the pilot's n and noise levels.

**Recalibration:** n-conditional ΔBIC null thresholds recomputed from scratch for the
amended model (the old table belonged to the retired 5-parameter version).

**Gate:** both contract sides pass → instrument validated → Stage 1 (LLM pilot) may be
proposed. Either side fails → report the failure mode, no LLM calls, fix again.
Stage 0.1 makes no LLM calls.

## Stage 0.2 — targeted pattern battery (authorized 2026-10-07 ~11:20)

**Why:** Stage 0.1 proved generic change-point detection is not a viable primary
instrument here — even an oracle with the true τ recovers only 8–38% at realistic SNR.
The synthetic suite had drifted from the science: it tested subtle slope changes while
the phenomena of interest are coarse behavioral patterns. Stage 0.2 stops asking a
generic model to discover them and gives each pattern its own operational definition.

**Failure sequence, preserved as a methodological result:**
- Stage 0.0: generic two-regime detector had discontinuity bias (solve events 0.97,
  smooth transitions 0.09–0.44).
- Stage 0.1: removing the bias exposed the SNR wall (oracle-efficient yet 0.11–0.38;
  σ=0.02 → 0.92–0.99, σ≥0.05 → collapse).
- Stage 0.2: operational definitions for coarse behavioral phenomena.

**The battery (frozen before synthetic results):**
- **Track A — Solve:** exact-match transition e>0 → e=0 via the deterministic flag.
  No statistical detector.
- **Track B1 — Stall:** pre-defined high-error persistence (e(t) > e_floor, e.g. 0.4,
  for t ≥ 4) with change over the final rounds small relative to the frozen
  measurement-noise scale. Exact statistic and threshold frozen before validation.
- **Track B2 — Oscillation:** repeated directional reversals
  (sign(Δe_t) ≠ sign(Δe_{t+1})) with amplitudes exceeding a pre-registered noise
  criterion — noise must not be allowed to manufacture oscillation. Count threshold
  frozen (e.g. ≥3) before validation.
- **Track B3 — Divergence:** sustained deterioration over a pre-registered number of
  rounds and magnitude (e.g. Δe_t > 0 for ≥5 of 8 rounds and e_8 − e_0 above threshold).
- **Track B4 — Residual kink:** the CPL change-point detector retained strictly as an
  auxiliary for transitions demonstrably above the empirically established SNR boundary
  (|Δslope| ≥ 3σ_empirical). Not a primary instrument.

**Null discipline (Adrian's tightening):** thresholds are set by EMPIRICAL null
calibration, never by theoretical claims. "Single-regime decay forbids positive drift"
is not a premise — noisy finite trajectories produce local positive differences, and
the null family (single-regime exponential/linear decay, σ ∈ {0.02, 0.05, 0.10}, n=9)
must establish the false-positive behavior empirically. Same null family for every
detector.

**Contract:**
1. ≤5% false-positive rate PER DETECTOR on the null family.
2. Family-wise FPR reported (P(any detector fires | null)) — five individually
   respectable detectors can collectively over-generate; if family-wise exceeds 15%,
   it is a documented limitation on Stage 1 interpretation.
3. ≥90% recovery on synthetic gross patterns (stalls, divergence, oscillation, solve
   events) at the pilot's n and noise levels.

**Scope (hard limit):** Stage 0.2 does NOT discover states. It establishes only: *"If a
trajectory really contains pattern X, can our frozen measurement pipeline reliably
recognize X without calling ordinary trajectories X?"* Only Stage 1 asks whether real
LLM revision trajectories actually contain those patterns.

**Gate:** all three contract items pass → instrument validated for gross behavioral
regime detection → Stage 1 may be proposed. Any item fails → report, no LLM calls.

## If Bar 0 fails — state discovery with the hardened pipeline

Only then: k-sweep with k=1 allowed (BIC, n-conditional); no-grammar controls
(synthetic nulls + a round-shuffled control — the analog of 1a's shuffled-step null,
with its purpose stated as: *"Does the apparent state structure survive destruction of
temporal adjacency?"* Shuffling destroys the trajectory while also destroying the
answer/score/revision relationship, so it is a strong negative control whose exact role
is this question, not a generic no-grammar control); directionality bar (≥10× asymmetry,
~1 crossing/trajectory);
correspondence across tasks and models (centroid cosine > 0.8); negative controls
(a control arm where the "revision" prompt is a paraphrase request with no correction
intent — predicts no regimes). **Never silhouette alone on wide-dynamic-range decay**
(1a's manufacture mode). Per-trajectory weighting in any pooling. Labeled arms never
pooled unlabeled.

## The H1/H2 lens — EXPLORATORY until a stall variable is defined

Status: exploratory, not confirmatory. The old "verifier level" phrasing is retired —
the primary continuous signal is now the frozen embedding-derived `e`, so hypotheses
are written in terms of the measured error variable.

Operational stall definition (pre-registered, exploratory only): |Δe| < 0.05 for ≥3
consecutive rounds with e_t > 0.05. Given stalled trajectories:
- H1: stall error level scales with e_0 (fixed fraction — linear-like);
- H2: stall sits at a fixed absolute e (floor-like; cf. the 1a forensics — a fixed
  absolute scale has many parents: noise floor, saturation, quantization, not just
  nonlinearity).
Report descriptively; no confirmatory claims attach until the stall variable is
validated as a real behavioral category rather than a threshold artifact.

## Carry-forwards from the synthetic atlas (non-negotiable)

- Bar 0 must be *capable of killing* the state hypothesis before any clustering
  interprets trajectories.
- Don't ask for states until a state model is demonstrated necessary.
- Pre-register everything, including null branches and the retirement rule.
- Numbers verified against outputs, never invented; failed bars are findings.
- Models under test are "volunteers"; plain-language-first write-ups.

## Open decisions (Adrian's call)

1. **Model substrate (recommended: local Ollama Gemma 2B — pending environment check).**
   Recommendation: local Gemma 2B, deterministic decoding (temperature 0, fixed seed),
   via Ollama. Rationale: no API budget or rate-limit confound (reruns and calibration
   are free); deterministic execution compatible with the spec; and a 2B model makes
   enough errors to produce trajectories worth analyzing — a frontier model would
   flatline near e=0 on a filtered GSM8K subset. Environment reality (checked
   2026-10-07): this sandbox is 2 CPU cores, no GPU, Ollama not installed — Gemma 2B
   here runs ≈5–10 tok/s, so 900 calls ≈ 9–15 hours. Staged plan: (a) synthetic
   validation fires immediately (zero LLM calls); (b) first LLM pilot shrinks to
   ~30 trajectories × 9 rounds ≈ 270 calls (≈3–5 h, background run); (c) scale to 100
   only if the first read is interesting. Alternative: Adrian's own hardware if it has
   Ollama/GPU, or API after all — his call.
2. **Task family:** math word problems (recommended for the pilot — clean deterministic
   verifier) vs coding tasks.
3. **Budget:** local = wall-clock, not money. If API is chosen instead, authorize the
   estimated spend for ~900 pilot calls before firing.

## Deliverables

- `revision_loop_atlas.py` (deterministic seeds; the *process* is the model's, the
  *analysis* is ours and reproducible)
- `revision_loop_results.json`, `REVISION-LOOP-REPORT.md` (markdown, plain-language-first)
- chart in the established three-panel format (real data only)

## Standing constraints

Nothing here trains models or modifies rewards — pure observation of revision behavior.
Does not authorize Phase-3 manifold work. Pre-registration locks at green-light; amend
by dated entry only, never after data.
