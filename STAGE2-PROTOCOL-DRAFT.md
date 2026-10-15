# Stage 2 Protocol — Controller Comparison (DRAFT v13 for eval, not locked)

**Date:** 2026-10-11
**Status:** draft v13, Arm 3 phrasing frozen (ChatGPT's v11 review). Not pre-registered until locked.
**Scope:** scouting on gemini-flash-lite-latest (Amendment A1 applies throughout).
**Gate:** Stage 1 permits progression as a controlled comparison of correction
strategies. It does not establish that derivative information drives response.

**Headline change in v13:** Arm 3 command phrasing FROZEN (Design B, Adrian's
draft with sign convention e = target − measured; model receives text + u
only). Both cautions added to protocol (prompt states intent, Step 1 tests
implementation; Arm 3 ≠ derivative evidence, ≠ 0.69 observed gain). Open item 4
resolved.

---

## 1. Arms

1. **Fixed revision prompt** (baseline; noisy reading, no command).
2. **Best-of-8 resampling:** 8 candidates per round, each with its **own
   independent noise draw**. Select smallest |observed error| on noisy readings
   only; never true count. Record all candidates. Runs on the pre-registered
   40-text subset (seed 20261011); Arm 1 paired on those same 40.
   **Interpretation (pre-registered):** this tests best-of-8 as a *practical
   strategy under independently noisy readings*. The winner may benefit from a
   favorable noise draw (selection bias from noisy scores) — that bias is part
   of what is being tested, not a flaw in the test. True error is scored only
   after selection and never influences it. (Per-candidate noise chosen over
   shared noise because a real verifier re-reads per candidate; shared noise
   would prevent resampling from mitigating observation noise.)
3. **Tuned external α (pure command):** text + command u = α·ê_t, **not** the
   verifier reading. α tuned for the **post-transient regime** (§3).
   **Sign convention (frozen):** e = target − measured; u is the signed word
   adjustment delivered to the model. The model never receives e, the target,
   the measured value, or the gain — only the text and u.
   **Frozen phrasing:**

   > **Arm 3 — External Correction Command**
   >
   > You are revising a text's length under external control. An external
   > controller determines the adjustment for this round. Your task is to apply
   > that adjustment faithfully to the text, not to calculate a correction or
   > second-guess the controller.
   >
   > **Your adjustment this round: [signed integer] words**
   >
   > - **If positive (+):** Add approximately that many words. Expand
   >   descriptions or add relevant detail while preserving the text's style,
   >   topic, and meaning.
   > - **If negative (−):** Remove approximately that many words. Condense
   >   phrasing or cut redundancy while preserving the text's core content
   >   and style.
   > - **If zero (0):** Make no intentional length adjustment.
   >
   > **Rules**
   > 1. Apply only the signed adjustment supplied for this round.
   > 2. Do not estimate the text's current word count, infer a target length,
   >    or calculate your own correction.
   > 3. Do not accumulate adjustments across rounds, extrapolate trends, or
   >    introduce momentum or other multi-round correction strategies.
   > 4. Preserve the original topic, meaning, and writing style as you add or
   >    remove words.
   > 5. Return the full revised text only. Do not include a word-count report,
   >    explanation, or commentary.
   >
   > The external controller manages the target and evaluates the result. Your
   > role is to execute the supplied word adjustment.

   **Cautions (pre-registered):** (1) This wording states the *intent*; Step 1
   calibration measures whether the model actually follows the command — the
   prompt alone does not establish that it does. (2) Arm 3 measures the frozen,
   externally tuned command gain *in this setup*; it is not evidence for
   derivative control and not interchangeable with the earlier observed gain
   near 0.69 (that was the implicit response to a stated reading, a different
   quantity).
4. ~~α+β joint~~ — **dropped from primary** (scope-limited).
5. ~~α+β scrambled-history~~ — **dropped** (same).
6. **Frozen V4 law, raw transplant:** thetas verbatim, unscaled observations.
   **Exploratory transfer test** (outside the Holm family — 20 texts × 2 seeds
   is underpowered for a 5% SESOI claim; an inconclusive result is not evidence
   that raw transfer fails). A surprisingly good raw transfer would be
   scientifically interesting; the failure prediction is a prediction, not
   predetermined.
7. **Frozen V4 law, rescaled (γ-on):** σ₀ = 1.44 (**scouting choice**, A1),
   thetas incl. γ, g_sign from Step 1 on this substrate, u_task = σ₀·u′/g_sign,
   clip.
7b. **Frozen V4 law, rescaled (γ-off):** identical to Arm 7 except γ = 0.
   The γ ablation — P2's clean test. **Implementation identity (pre-registered
   code check):** the analysis pipeline asserts that Arms 7 and 7b use
   identical seeds, texts, noise draws, σ₀, clipping bounds, sign-specific
   gains, and all non-γ parameters; any mismatch aborts the run. An apparent γ
   effect must not be attributable to an accidental implementation difference.

Call budgets differ by design (Arm 2: 8× candidates). Same rounds/texts/seeds/
conditions otherwise; generation counts reported separately.

## 2. Tasks, noise, and scoring

- **Text bank:** 100 source texts (~140 words). The 10 Stage-1 texts → train.
  Generate 90 more: 10 train + 80 held-out.
- **Split:** 20 train sources / 80 held-out sources. Steps 1–3 use train only.
- **Noise:** σ ∈ {0, 0.72, 1.44, 2.88}. Scoring on **true** error, external
  deterministic evaluator.
- **Trajectory:** 8 rounds per task per arm, e₀ ≈ −60.
- **Seeds (pre-registered):** Step 2 pilot [0, 1, 2]; Step 3 tuning [0, 1, 2];
  Step 4 confirmatory [0, 1, 2, 3, 4]; Arm 6 [0, 1]; subset RNG 20261011.

## 3. Gated sequence (pre-registered order)

**Step 1 — open-loop command calibration** (~3,700 calls), 20 train sources.
- *Small commands:* ~10 near-target texts/source (200) × u ∈ {±1,±2,±4,±8}
  (1,600). Reports k̂_u(small), saturation, sign-specific gains (g_sign).
- *Large commands:* ~2–3 far-from-target texts/source (50) ×
  u ∈ {±16,±24,±32,±48,±60} (500).
- *Jitter control (like-for-like):* the **same 200 near-target texts** × 8 noisy
  readings (**2 per σ level**: 0, 0.72, 1.44, 2.88), reading shown instead of
  command, open-loop (1,600).
- **Jitter computation:** residual variance around a **linear fit of Δwords on
  the stated value** (u for commands, ê for readings), fit **per source text**
  (text fixed effects), residuals pooled. Same model form, same df treatment
  for both conditions. Injected reading noise does not count as jitter
  (fit is on ê, not e).
- **Jitter interpretation (pre-registered):** this gate compares **residual
  response variability under the two tested interfaces** (explicit command vs
  noisy reading). It does not isolate intrinsic interface noisiness: the inputs
  differ in range and distribution (deterministic u vs noisy ê across 4 σ
  levels), so the ratio may partly reflect input differences rather than pure
  control-method randomness. To limit this, the ratio is computed on the
  **overlapping input range** (|stated| ≤ 8, where command and reading ranges
  coincide) with σ as a covariate in the fit. Lower residual variance under
  commands is promising but does not prove the command interface is
  intrinsically less noisy — the external true-error endpoint (§5) remains the
  ultimate measure.
- **Clustering:** paired cluster bootstrap over the 20 sources for the
  jitter-variance ratio's 95% CI. Held-out sources never appear in Step 1.
- **Simulation validation (2026-10-11):** the gate procedure was validated on
  simulated Step-1 data (20 sources × 10 texts, per-text linear fits, cluster
  bootstrap). Under the null (true ratio 1.0), P(CI-upper < 0.90) = 0.00 —
  the gate never passes on noise. When the true ratio is 0.69 (31% lower
  command jitter), P(pass) = 1.00. For a weak 15% reduction, P(pass) = 0.10.
  The 20 clusters suffice: the gate is conservative (no false positives) with
  full power for effects large enough to matter for the 5% SESOI.
- **Simulation provenance (pre-registered):** 40 independent simulation runs per
  condition; per-text linear fits (Δwords ~ stated value) with text fixed
  effects; 500 cluster-bootstrap resamples over sources per run; "zero false
  passes" means zero in the 40 simulated null runs, not a true probability of
  zero. Assumptions: command gain 0.9, reading gain 0.7, reading jitter
  variance 2.9 (ledger), text random-effect SD 0.5, 8 commands and 8 readings
  (2 per σ) per text. Code: simulation script archived with the protocol.
- **α regime rule:** α tuned for the **post-transient regime** using
  k̂_u(small). If |k̂_u(large) − k̂_u(small)| / k̂_u(small) > 0.15, use
  **piecewise α**: α(ê) = g_target/k̂_u(large) for |ê| > 10, else
  g_target/k̂_u(small).
  **Edge cases (pre-registered):** sign-specific slopes estimated separately
  (positive vs negative u) and averaged unless they differ by >20%, in which
  case both are reported and the smaller |k̂_u| is used (conservative).
  **Wrong-sign handling:** if a slope estimate is negative (model moves opposite
  the commanded direction), first check the command phrasing for sign ambiguity.
  If the phrasing is clear and the model still reverses → **calibration failure:
  stop and debug, do not take abs() and proceed silently.** A negative slope is
  only ever a sign-convention issue if the phrasing itself was ambiguous, in
  which case fix the phrasing and re-run Step 1 (one cycle). If either slope's
  95% CI includes zero, fall back to single-α using k̂_u(small) and report the
  uncertainty.

**Step 2 — two-arm pilot** (3,840 calls = 20×3×4σ×8×2 arms, train sources).
Arm 1 vs Arm 3 (α from Step 1's regime rule and §4's windowed optima).
Reports: paired RMS difference + SE per σ, pooled + SE, convergence by
round 4 per arm (pooled across σ, |e₄|<5), per-σ SE at σ=0.

**STOP RULE (measured quantities; precedence-ordered).** Evaluate in order;
the first matching rule decides. Futility takes precedence over everything.

1. **Futility (highest precedence):** if pilot pooled difference < −2 SE, or
   pooled convergence gap (|e₄|<5 fraction) > 10pp → **STOP and debug** (one
   debug cycle on fresh train texts — re-estimate achieved gain, check command
   phrasing; the pilot must not become a tuning set). Overrides all below.
2. **Gate 1 (jitter):** if the 95% cluster-bootstrapped CI upper bound of
   (command jitter var / implicit jitter var) ≥ 0.90 → **STOP**. Inspect
   calibration and measurement procedure. No confirmatory spend.
3. **Gate 2 (pilot), given no futility and Gate 1 passes:**
   - Pooled improvement ≥ 2.5% (SESOI/2) → **PROCEED** to Steps 3–4.
   - Pooled SE > 2.5% (too noisy to discriminate):
     - jitter CI upper < 0.80 (strong) → **PROCEED**.
     - else → **STOP** (underpowered and weak jitter).
   - 0% ≤ pooled < 2.5% (inconclusive, not harmful), SE ≤ 2.5%:
     - jitter CI upper < 0.80 → **PROCEED**.
     - else → **STOP**.
   - Pooled < 0% but ≥ −2 SE (mildly negative, not futile) → **STOP**
     (no evidence of benefit; do not spend confirmatory budget).

**Design note (pre-registered):** the "mildly negative → STOP" rule makes the
gates asymmetric by design: the experiment proceeds on promising or
sufficiently-uncertain pilots (with strong jitter evidence), not merely on
absence of harm. This conserves the $4.85 budget for effects large enough to
clear the SESOI, at the accepted cost that a small true benefit (1–2%) could
be abandoned if the pilot lands slightly below zero. That tradeoff is
intentional for a scouting budget.

**CONVERGENCE TRIGGER (pre-registered).** Pooled gap > 10pp but no futility →
rounds 6–7 reported as a **labeled secondary steady-state result**
("steady-state: win/none, slower convergence"). Classification stays on 4–7.
Explicitly secondary — not a substitute primary if 4–7 disappoints.

If stopped at any rule, Arm 3's confirmatory runs small (diagnostic); budget
to arms 1/2/7/7b (Arm 6 exploratory).

**Step 3 — α tuning** (only if gates pass). g ∈ {0.5, 0.65, 0.8, 0.95, 1.1},
α = g/k̂_u per σ under the regime rule
(5×4σ×20×3×8 = 9,600, train). Freeze per-σ winners.

**Step 4 — confirmatory** (only if gates pass). §5.

## 4. Model validation and predictions

**Free checks on Stage 1 ledger:** first-round gain 0.875 (no cap); windowed
model reproduces RMS within 2–5% (headroom is order-of-magnitude); D5
cue-conflict strongly supported at matched |e| (honest 0.65/0.48/0.51 vs lied
0.38/0.33/0.30, non-overlapping CIs).

**Windowed optima** (rounds 4–7, e₀=−60; approximate — a *prediction* from
scouting/model analysis, not a confirmed law; Stage 2 tests whether the
pattern survives on held-out texts):

| σ | baseline g | windowed g* | headroom |
|---|---|---|---|
| 0.00 | 0.78 | 1.00 | ~2.5% |
| 0.72 | 0.81 | 0.87 | ~0.2% |
| 1.44 | 0.76 | 0.73 | ~0.1% |
| 2.88 | 0.57 | 0.64 | ~3.9% |

- **P0 — noise dependence:** optimal α per σ (Step 3) vs Bar 0 gains.
- **P1 — windowed optimal gain falls with σ (directional).**
- **P2 — the γ term hurts at σ > 0 (clean ablation):** Arm 7b (γ=0) performs
  ≥ Arm 7 (γ-on) at σ > 0; they match at σ = 0 (no noise for γ to inject).
  Pre-registered secondary comparison, outside Holm. Powered independently of
  the Arm 3 gate (both arms run full size regardless).
- **P3 — zero-noise equivalence (Arm 3 vs Arm 1):** ratio = (Arm 3 RMS)/(Arm 1
  RMS) at σ = 0; TOST for equivalence within [0.97, 1.03]. **Fallback:** if
  Step 2's SE at σ = 0 exceeds ~1.5%, the comparison is reported as
  **inconclusive** (not as equivalence, not as difference) unless sample size
  is increased under a pre-specified rule. Failure to reject ≠ equivalence.

## 5. Primary endpoint and decision rule

**Endpoint computation (frozen):**
1. Per trajectory: RMS of true error over rounds 4–7.
2. Per source text: mean over the pre-registered seeds and σ conditions.
3. **Pooled primary: mean over the 4 σ levels with equal weight per σ.**
4. Per-σ results reported regardless of pooled outcome.

**Endpoint:** paired difference (candidate − Arm 1) in the pooled RMS; text as
cluster (wild bootstrap CIs).

**SESOI:** 5% pooled relative reduction (practical threshold, frozen before
confirmatory data; not independently proven — a decision threshold).

**Decision rule (Holm over the 3 named comparisons; unadjusted CIs alongside):**
1. Arm 2 vs Arm 1 (40-text subset, paired).
2. Arm 3 vs Arm 1 (80 texts, paired).
3. Arm 7 vs Arm 1 (80 texts, paired).
→ meaningful win / statistical-but-not-practical / no worthwhile benefit /
inconclusive, on the adjusted CI vs SESOI.
P2 (A7 vs A7b) and Arm 6 are pre-registered secondaries outside Holm.

## 6. Validity and exclusions

- Automated checks (words in [40,160], no repeated n-grams > 5) are basic
  validity checks, not fluency certification.
- **Invalid-rate rule:** if every arm's invalid rate < 2% and balanced within
  1pp → intention-to-treat primary. Otherwise per-protocol primary, ITT as
  sensitivity. Report both and rates by arm, always.
- **Worst-RMS rule (deterministic, frozen):** an invalid trajectory receives the
  **maximum trajectory RMS observed in its (source text, σ) cell across all
  arms**; if the cell has no valid trajectories, 3× the global median
  trajectory RMS. Computed after all data are in, before any comparison.
- API errors: one retry, then the cell drops as a block (pairing preserved).

## 7. Cost accounting (pre-registered)

Per arm: API requests, candidate generations, in/out tokens, $, $ per 1% RMS
reduction vs baseline. Lower jitter does not automatically mean lower true
error — the external true-error endpoint is the ultimate measure.

**Budget** ($0.04/1k; 100-call probe confirms):

| Phase | Calls | $ |
|---|---|---|
| Step 1 | ~3,700 | $0.15 |
| Step 2 pilot | 3,840 | $0.15 |
| Step 3 tuning | 9,600 | $0.38 |
| Step 4: arms 1, 3, 7, 7b | 51,200 | $2.05 |
| Step 4: arm 2 (40 texts) | 51,200 | $2.05 |
| Step 4: arm 6 (exploratory) | 1,280 | $0.05 |
| **Total (gates pass)** | **≈ 121,000** | **≈ $4.85** |

**Cut list ($0.10/1k):** Arm 2 → 20 texts × 4 seeds (save ~31k); arms 1/3/7/7b
→ 3 seeds (save ~20k); total ~70k ≈ $7.00. (Exceeds $6 — if the probe reads
$0.10, drop Arm 6 and halve Step 3's grid to reach ~$5.90.)

## 8. What this protocol does not do

- No β arms in primary (scope-limited exclusion).
- No retuning on confirmatory data (one debug cycle on fresh texts only, §3);
  no oracle selectors; no oracle noise.
- No claim beyond lite scouting (A1); target-substrate confirmation owed —
  keep this qualification prominent in any report.
- The σ = 0 second-order Bar 0 cell is not pursued (own pre-reg needed).

## 9. Open items before locking

1. Generate + verify 90 source texts: 10 train + 80 held-out (with the 10
   Stage-1 texts → 20 train). Step 1 needs ~10 near-target + ~2–3
   far-from-target texts per train source.
2. Freeze SESOI (5% proposed), Holm family (3 named), RMS aggregation
   (equal-σ pooled), invalid-rate thresholds, worst-RMS rule.
3. Freeze the α*(σ) rule form (per-σ winners vs fitted curve; piecewise
   threshold |ê|=10; edge-case handling §3).
4. ~~Arm 3's exact command phrasing~~ — **FROZEN 2026-10-14** (see §1, Arm 3).
   Design B (pure command); sign convention e = target − measured.
5. Run the 100-call billing probe — measuring the **actual billable unit**:
   cost per API request, per candidate generation, and per 1k input/output
   tokens separately (these are not necessarily interchangeable).
6. Lock **all** analysis code — including Step 1–2 gate code (jitter-ratio
   cluster bootstrap, pilot SE, stop-rule evaluation) — before Step 1 runs.
7. Pre-register the Arm 2 subset indices (seed 20261011 draw from 80 held-out)
   once the held-out bank exists.
