# Step 1 Interpretation Memo — Protocol and Model Assumptions

**Date:** 2026-10-15
**Status:** Step 2 on hold. Analysis code frozen. No new calls authorized.
**Scope:** This document interprets the *existing* evidence — protocol v13, the frozen
analysis code (`step1_analysis_FROZEN_v13.py`, SHA `46c2ec68…`), and `step1_results.json`
from the 3,700-call Step 1 run. It performs no new estimation and modifies nothing.

---

## 1. What does σ mean in the jitter model?

### 1.1 What the protocol says

Protocol v13, Step 1 (jitter control):

> *Jitter control (like-for-like):* the **same 200 near-target texts** × 8 noisy
> readings (**2 per σ level**: 0, 0.72, 1.44, 2.88), reading shown instead of
> command, open-loop (1,600).

> **Jitter computation:** residual variance around a **linear fit of Δwords on
> the stated value** (u for commands, ê for readings), fit **per source text**
> (text fixed effects), residuals pooled. Same model form, same df treatment
> for both conditions. Injected reading noise does not count as jitter
> (fit is on ê, not e).

> To limit this, the ratio is computed on the **overlapping input range**
> (|stated| ≤ 8, where command and reading ranges coincide) **with σ as a
> covariate in the fit**.

The simulation provenance adds:

> Assumptions: command gain 0.9, reading gain 0.7, reading jitter variance 2.9
> (ledger), text random-effect SD 0.5, **8 commands and 8 readings (2 per σ)
> per text**.

### 1.2 What the frozen code does

`jitter_variance_ratio` fits, per interface:

```
Δwords ~ source fixed effects + stated_value + sigma
```

on rows with `|stated_value| ≤ 8`, then reports
`command_residual_variance / reading_residual_variance`.

`_fixed_effect_residual_variance` raises `ValueError("Jitter design matrix is
rank-deficient")` if the design matrix is not full column rank.

The frozen *test* suite supplies **both** interfaces with varying sigma
(`(value, sigma)` pairs `(-8, 0), (-4, .72), (-2, 1.44), (-1, 2.88), …` for
command rows and reading rows alike).

### 1.3 What the runner recorded

The Step 1 runner set `sigma = 0.0` for **every** command row — because no
reading noise is injected on the command interface. This is an honest
description of the experiment: commands are deterministic; there is no σ.

Reading rows carry `sigma ∈ {0, 0.72, 1.44, 2.88}` (two readings per level),
matching the protocol.

### 1.4 The disagreement

The protocol describes σ as the **injected reading-noise level** ("2 per σ
level", "injected reading noise does not count as jitter"). Under that
meaning, σ = 0 for all command rows is correct, and the design matrix for the
command interface has a constant sigma column — rank-deficient by
construction, not by accident.

The frozen code's test, by contrast, treats sigma as a **shared
design/stratification variable** that varies across both interfaces. Under
that meaning, the command rows should have been assigned the design σ values
— but doing so after the fact would be inventing data, since no noise was
actually injected.

These two meanings are not interchangeable:

| | σ = injected noise | σ = design variable |
|---|---|---|
| Command σ | 0 (constant) — honest | Varies by design slot — but no noise was injected |
| Model estimable? | No (rank-deficient) | Yes |
| What σ controls for | Nothing on command side | Matched-condition stratification |

The protocol text supports the first meaning ("injected reading noise", "2 per
σ level" describing the *readings*). The frozen test supports the second. The
simulation's "8 commands and 8 readings (2 per σ) per text" is ambiguous — it
can be read either as a matched design or as loose phrasing.

### 1.5 Candidate resolutions (for Adrian's decision — not selected here)

- **(a) Drop σ from the command-side model.** Keeps the honest σ = 0
  recording; estimates each interface with the covariates that actually vary.
  Requires amending the frozen analysis (versioned, both results reported).
  Changes the estimand slightly: the command residual variance no longer
  partials out a (constant) σ.

- **(b) Reinterpret σ as a design variable and re-run.** Assign commands to σ
  slots at design time. Requires new calls — currently not authorized — and
  answers a slightly different question than the protocol's "injected noise"
  framing.

- **(c) Document the limitation and hold the gate unresolved.** The comparison
  the protocol specified cannot be estimated from the data as collected under
  the frozen model. The gate stays blocked; the record shows why.

What must **not** happen: assigning artificial nonzero σ values to already-
collected command rows to satisfy the matrix rank, or judging the gate from
reading-side data alone. Both would produce a number that is not the
protocol's comparison.

---

## 2. Can a single-gain controller survive the sign asymmetry?

### 2.1 What the calibration measured

From `step1_results.json` (frozen code, unmodified; `g_target = 0.69`):

| Quantity | Value |
|---|---|
| Small-command slope (pooled) | 0.8703 |
| Large-command slope (pooled) | 0.7541 |
| Small-vs-large relative difference | 13.3% (< 15% → no piecewise α) |
| Positive-command small slope | 0.1808 |
| Negative-command small slope | 1.7903 |
| Sign relative difference | 163.3% (>> 20% → warning, conservative selection) |
| Selected small gain | 0.1808 |
| α_small (= 0.69 / 0.1808) | 3.8167 |
| Saturation flag | True (median \|Δ\| 39.5 → 38.0 from \|u\|=48 to 60) |

Raw means (small commands, n=200 each):

| u | mean Δwords |
|---|---|
| −8 | −13.36 |
| −4 | −2.69 |
| −2 | −1.79 |
| −1 | −1.03 |
| +1 | +0.96 |
| +2 | +1.02 |
| +4 | +1.29 |
| +8 | +2.19 |

### 2.2 Reading the positive-direction response

The positive-direction means do not describe a low-gain linear response. They
describe a **nearly flat** response: u = +1 through +8 all produce roughly +1
to +2 words. The fitted slope of 0.18 is the best linear approximation to a
relationship that is approximately constant — the model adds about a word
whenever it is asked to revise upward, nearly independently of how many words
were requested.

This matters because a slope of 0.18 *with zero intercept* would imply
proportional (if weak) control. The data instead suggest the model does not
proportionally implement positive commands in this setup.

### 2.3 Reading the negative-direction response

The negative direction is closer to proportional at small magnitudes
(u = −1, −2, −4 track with gain ≈ 0.7–1.0) but overshoots severely at u = −8
(mean Δ = −13.36, gain ≈ 1.67). The fitted slope of 1.79 is pulled upward by
the −8 point.

### 2.4 The 15% and 20% rules are not contradictory

- The **15% rule** compares small-vs-large *magnitudes* (0.87 vs 0.75):
  13.3% → no piecewise α by magnitude. It asks whether gain changes with
  command *size*.
- The **20% rule** compares positive-vs-negative *signs* (0.18 vs 1.79):
  163% → warning and conservative selection. It asks whether gain changes
  with command *direction*.

Both rules fired correctly on the questions they ask. The data happen to show
magnitude-stability alongside sign-instability.

### 2.5 α = 3.82 is a rule output, not a calibration success

The frozen rule selected the smaller gain (0.1808) and computed
α_small = 0.69 / 0.1808 ≈ 3.82. This is the *output of the pre-registered
procedure*. It is not evidence that α = 3.82 would control the plant in both
directions.

Direct arithmetic shows the problem: at α = 3.82, a removal command's
effective correction scales with the negative-direction gain (≈1.79),
implying ≈ 6.8× the intended adjustment — the overshoot concern. Tuning to
the weak direction destabilizes the strong one; tuning to the strong direction
(α ≈ 0.39) would leave addition effectively unmoved (0.39 × 0.18 ≈ 0.07 per
unit error). No single α is adequate in both directions under these
measurements.

### 2.6 Definable vs demonstrated-adequate

A single gain is **mathematically definable**: the frozen rule produced one
(3.82). What has **not been demonstrated** is any single gain providing
adequate control over the tested range in both directions. That is the
experimentally defensible statement: the evidence challenges single-gain
control on this interface; it does not prove no gain could ever suffice over
some narrower range.

### 2.7 What the data do and do not establish

- **Established in this setup:** the model, under the frozen Design B command
  phrasing, adds ≈1–2 words nearly regardless of positive command magnitude,
  removes words approximately proportionally at small negative magnitudes with
  severe overshoot at −8, and plateaus in absolute response between |u| = 48
  and 60.
- **Not established:** that the model *cannot* add words under any phrasing or
  setup. These are calibration findings about this interface and wording, not
  a universal limit on the model. A different phrasing, a different task
  framing, or a sign-dependent controller might behave differently — but those
  are new experiments, none authorized.

---

## 3. Response-function analysis (2026-10-15; from existing Step 1 rows, no new data)

### 4.1 Distributions, not just means

| u | n | mean Δ | median | sd | min | max |
|---|---|---|---|---|---|---|
| −8 | 200 | −13.36 | −11.0 | 10.12 | −56 | −1 |
| −4 | 200 | −2.69 | −2.0 | 1.85 | −9 | 0 |
| −2 | 200 | −1.79 | −1.0 | 1.38 | −7 | 0 |
| −1 | 200 | −1.03 | −1.0 | 0.64 | −4 | 0 |
| +1 | 200 | +0.96 | +1.0 | 0.20 | 0 | +1 |
| +2 | 200 | +1.02 | +1.0 | 0.23 | 0 | +2 |
| +4 | 200 | +1.29 | +1.0 | 0.55 | 0 | +3 |
| +8 | 200 | +2.19 | +2.0 | 1.51 | +1 | +7 |

### 4.2 Positive direction: quantized, not proportional

At u = +8, the modal responses are +1 (87/200) and +2 (57/200); at u = +1,
+2, +4 the model returns almost exactly +1 word every time (sd 0.20–0.55).
The "gain" of 0.18 is a linear fit to what is effectively a **constant
function**: the model appears to have a single "add a word" behavior that it
applies nearly independently of the requested magnitude.

This is structurally, not parametrically, non-proportional. A larger α cannot
elicit a larger addition if the response function itself does not scale with
u — it can only command larger u values against the same flat response.

### 4.3 Negative direction: proportional at small |u|, unstable at −8

At u = −1, −2, −4 the response is approximately proportional (gain ≈ 0.7–1.0)
with modest variance. At u = −8 the standard deviation explodes to 10.1 and
responses range from −1 to −56. The distribution is broad and heavy-tailed
(modes at −10, −4, −18, −11, −3…), consistent with the model sometimes
switching strategies — e.g., from trimming words to excising whole sentences
or passages — rather than scaling a single behavior.

### 4.4 Implication for proportional-control assumptions

Proportional control assumes a plant of the form Δ ≈ k·u with k > 0
approximately constant over the operating range. The measured response
function violates this in three distinct ways:

1. **Positive side:** Δ ≈ +1 (constant). Not weak-proportional;
   non-proportional. Gain tuning cannot create proportionality.
2. **Negative side, small |u|:** Δ ≈ 0.85·u. Approximately proportional —
   the only regime where the assumption holds.
3. **Negative side, large |u|:** variance-dominated with strategy-switching
   behavior. The gain is not a stable parameter here.

A single-gain controller is therefore not merely mis-tuned. What the data
support is the narrower, defensible claim: no single gain has been
demonstrated to provide adequate control over the tested range in both
directions. The plant's measured response — constant in one direction,
proportional-but-noisy in a narrow band, strategy-switching beyond it — does
not present the structure a proportional gain is designed to scale.

### 4.5 Scope limit (unchanged)

These findings describe the model's behavior under the frozen Design B
command phrasing on 135–143-word source texts. They challenge single-gain
proportional control *on this interface*. They do not establish that no
prompt, no operating range, and no controller structure could succeed.

---

## 4. Record (unchanged)

- **Calibration:** sign-asymmetry warning triggered (163%); saturation flagged;
  piecewise α not triggered. α_small = 3.82 is the frozen rule's output, not a
  validated controller.
- **Strongest current conclusion (Adrian 2026-10-15):** "Under the frozen
  Design B interface, command magnitude does not reliably determine response
  magnitude across directions." Substantive in its own right; the jitter gate
  remains blocked and broader claims about other prompts/setups untested.
  Careful framing: no single gain has been *demonstrated* adequate — not a
  proof that none could exist over some narrower range.
- **Jitter gate:** blocked — rank-deficient design matrix documented in
  `step1_results.json`. Not passed, not failed, not statistically
  inconclusive: unestimated due to a protocol/implementation σ mismatch.
- **Step 2:** on hold.
- **Code:** frozen (`step1_analysis_FROZEN_v13.py`, SHA `46c2ec68…`).
  Unmodified before, during, and after Step 1 data collection.
- **Calls:** no new API calls authorized.
- **Data:** 3,700/3,700 rows, 0 errors, 0 held-out rows. Preserved in
  `step1_partial.jsonl`; summary in `step1_results.json`.
