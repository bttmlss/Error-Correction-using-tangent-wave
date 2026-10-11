# Steerable Plant — Stage 0 (Gemini substrate): the actuator answers

**Verdict: Stage 0 PASSES on the Gemini substrate (word-count task).**
All three pre-registered bars hold. A commanded step in words is a real,
resolvable control input to the revision loop.

## Program context

The steerable-plant program asks a plant-first question: *can an external
controller steer an LLM revision loop at all?* Stage 0 is the actuator
calibration gate — it establishes a resolvable command→response dose-response
before anything larger runs. The governing design is the locked program spec
(`STEERABLE-PLANT-STAGE0-SPEC.md`, Adrian's sign-off 2026-10-07); this report
covers the Stage 0 execution on the Gemini substrate (scouting run — the locked
program names a local small-model substrate, so these results are reported
per-substrate and never transplanted).

## What was run

**Bar (b) — floor probe (40 calls).** Fixed prompt, no command, temperature
round-robin {0.3, 0.7, 1.0}, 10 source texts × 4 reps. Measures the substrate's
step-noise floor before the ladder may run.

| Task | SD (ddof=1) | Bar | Result |
|---|---|---|---|
| Word count | 1.44 words | ≤ 10 | **PASS** |
| Flesch Reading Ease | 11.87 | ≤ 6.7 | **FAIL** |

Per Amendment 21 of the program spec, the readability failure halts the
readability track (a finding about the actuator, not the program); the program
proceeds on word count. Plant scale pinned: **σ₀ = 1.44 words**.

**Bar (a)/(c) — actuator ladder (320 calls).** Command levels
u ∈ {−60, −40, −20, −10, +10, +20, +40, +60} words × 20 trials × 2 prompt
templates (T1: "change the length of your response by u words"; T2: "make your
response u words shorter/longer"), T1/T2 strictly paired (same level, trial,
temperature, text). Corrective-side starts: u < 0 from 140-word sources
(e₀ = −60, "60 words over target"); u > 0 from 40-word sources (e₀ = +40,
"40 words under target"). σ = 0 (stated residual truthful). Temperature
round-robin {0.3, 0.7, 1.0}. Full prompt skeleton: source + target (80 words)
+ residual + command.

## Results — bar (a): dose-response

| Check | T1 | T2 | Bar |
|---|---|---|---|
| Pooled Spearman ρ (n=160) | 0.993 | 0.993 | ≥ 0.70 ✓ |
| Shuffled-u null |ρ| | 0.032 | 0.044 | < 0.15 ✓ |
| Per-sign ρ, u < 0 | 0.971 | 0.970 | ≥ 0.818 ✓ |
| Per-sign ρ, u > 0 | 0.970 | 0.971 | ≥ 0.818 ✓ |
| Theil–Sen gain, u < 0 | 0.950 | 0.967 | ∈ [0.5, 1.5] ✓ |
| Theil–Sen gain, u > 0 | 0.925 | 0.920 | ∈ [0.5, 1.5] ✓ |
| Saturation med|ΔW|: 60 vs 40, u < 0 | 58 > 38.5 ✓ | 58 > 38.5 ✓ | strict ✓ |
| Saturation med|ΔW|: 60 vs 40, u > 0 | 56 > 37 ✓ | 56 > 37 ✓ | strict ✓ |

- Per-sign bars (0.818) are calibrated, not picked: gain-1 positive control
  (ideal plant = u + observed noise) gives ρ_ideal ≈ 0.969 per sign; bar =
  ρ_ideal − 0.15. The plant sits at the ideal-plant ceiling.
- The dose-response holds at every temperature (ρ ≈ 0.993 at 0.3, 0.7, 1.0).
- Null context: 10k shuffles give |ρ| centered at 0.063 (SD 0.047) — exactly
  as independence predicts; no pipeline artifact.

## Results — bar (c): template equivalence

- 95% paired-cluster bootstrap (10k resamples over the 10 source texts):
  CI on (ρ_T1 − ρ_T2) = **(−0.0003, +0.0005)** ⊆ [−0.10, +0.10] ✓
- Gain-ratio diagnostic: 0.9825, CI (0.979, 0.994) ⊆ [0.75, 1.33] ✓ —
  no limitation recorded.

## Pinned parameters (Gemini word-count track)

- **σ₀ = 1.44 words** — native plant scale.
- **T1 per-sign gains** (feed the Stage 2 controller law
  u_task = σ₀·u′/g): g_neg = 0.95, g_pos = 0.925.
- Empirical mean gain ≈ 0.93–0.96 across levels; no sign asymmetry
  (and per the locked contract, a one-sign miss would read as an
  operating-point result, not actuator asymmetry — both signs passed).

## Plain-language summary

We asked the model 320 times to change a text's length by a commanded number
of words (±10 to ±60) and measured what it actually did. It did almost exactly
what it was told — about **0.95 words of movement per word commanded**, in
both directions, at every temperature, under both phrasings, with ~1.5 words
of noise on commands up to 60. The revision loop is a steerable plant on this
substrate, at least for word count.

## Reproducing the evaluation

- `experiments/steerable_plant_stage0_gemini_ladder_ledger.csv` — 320-row
  ledger: u, trial, template, temperature, text_id, starting_words,
  realized_words, realized_step.
- `experiments/steerable_plant_stage0_gemini_floor_ledger.csv` — 40-row floor
  probe ledger: k, text_id, rep, temperature, words, flesch.
- `code/stage0_gemini_bar_eval.py` — recomputes every bar (a)/(c) statistic
  from the ladder ledger (needs `code/prelock_bootstrap_sim.py` alongside it
  for the paired-cluster bootstrap).
- Scoring standard (word counts, Flesch) is the pinned regex implementation
  in the program spec; the ledgers carry already-scored values.

## What comes next

Stage 0 is the "does the actuator answer" gate — answered yes, on Gemini, for
word count. The next gate is Stage 1: does the prediction error Δe carry
information about the next residual beyond the current residual and initial
condition (with a clean retirement rule if the null holds at every σ > 0)?
Stage 1 is a separate design-and-authorization step.
