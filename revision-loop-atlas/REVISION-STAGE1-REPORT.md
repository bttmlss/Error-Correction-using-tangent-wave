# REVISION-STAGE1-REPORT — LLM revision-loop pilot (30 trajectories × 9 rounds)

## Plain-language summary

We ran the first real-data pilot: local Gemma 2B (temperature 0, deterministic),
30 GSM8K problems, 9 rounds each (round 0 = initial answer, rounds 1–8 = the same
neutral prompt: *"Review your previous answer and revise it if you think it is wrong."*).
270 genuine LLM calls, zero errors, ~3 hours wall-clock.

**The headline is not about regimes — it is about the measurement.** In 74 of 270
rounds (27%), the volunteer did not revise at all: it responded with self-praise
("Your previous answer is perfectly correct! Well done! 👍") containing no numeric
answer. The frozen error math scores those rounds as e ≈ 0.9 (maximally wrong),
so the trajectory *looks* like violent oscillation/divergence when the model is
actually just declining to re-answer. Twenty of thirty trajectories contain at
least one such commentary round.

This is a productive failure in the established sequence: 0.0 discontinuity bias →
0.1 SNR wall → 0.2 curvature confound → **1.0 commentary confound**. The instrument's
measurement layer has a discovered validity gap, and the pilot cannot support a
regime conclusion in either direction until it is fixed.

## Pre-registered numbers (frozen pipeline, frozen 4-detector battery)

| Detector | Firings / 30 | Expected under calibrated null |
|---|---|---|
| Track A (solve onset) | 9 | 0.0 |
| B1 (stall) | 3 | 1.11 |
| B2 (oscillation) | 3 | 0.93 |
| B3 (divergence) | 4 | 0.0 |
| Informative trajectories | 22–23 | (≥20 = adequate power) |

Detector definitions and thresholds are byte-identical to the Stage-0.2 frozen
instrument (verified: 30/30 per-trajectory flags reproduced from the frozen code).

## The commentary confound (found by inspecting the data, not by retrofitting)

- 74/270 rounds contain no numeric token: pure commentary/affirmation.
- 6 of the 9 Track-A "solve onsets" are commentary→answer transitions
  (model goes from praising to answering), not wrong→right belief changes.
  Only 3 (trajs 11, 22, 29) are genuine wrong-number→right-number solves.
- B2/B3 firings are substantially driven by answer↔commentary alternation, which
  the frozen math renders as 0.0↔0.9 swings in e(t). E.g. traj 2's "divergence"
  is two wrong numbers followed by seven byte-identical praise repetitions.
- The 12→5 round-0→round-8 correctness drop is confounded the same way: many
  round-8 non-exact rounds are commentary, not wrong answers.

The exact-match parser was validated on answer-like text (Stage 0) but never on
commentary. "Declined to re-answer" is currently scored as "maximally wrong" —
a measurement decision the spec never made.

## Genuine residue (descriptive, not inferential)

After accounting for commentary: 3 genuine solve onsets; post-solve drift in
traj 29 (solved round 1, wrong numbers rounds 5–8); answer-to-answer changes in
traj 24. The volunteer also exhibits a real behavioral pattern worth naming for
the next stage: under the neutral prompt it frequently *affirms instead of
revising*, and once affirming it can get stuck repeating praise verbatim.

## Verdict

**Stage 1 as executed: INCONCLUSIVE on regimes — measurement validity gap.**
The pre-registered battery fired above calibrated rates, but the firings do not
license "single-regime inadequate": they are confounded by the commentary gap.
Per the frozen expansion rule: (a) informative ≥ 20 → power adequate, no
expansion on (a); (b) the battery's excess firings cannot honestly be read as a
rejection of the single-regime account → no expansion on (b).

## Recommendation: Stage 1.1 — fix the no-answer handling, then re-run the battery

Two candidate fixes (Adrian's call):
1. **Carry-forward rule (measurement fix):** a round with no numeric answer keeps
   e(t) = e(t−1), exact(t) = exact(t−1), flagged as non-revision. Principled: the
   model's answer did not change, so measured error should not jump to 0.9.
2. **Prompt fix:** require the revision prompt to demand a restated final answer
   every round (e.g. ending with `#### <number>`). Changes the prompt, so it is a
   spec amendment.

Either way, re-run the frozen 4-detector battery on the corrected measurement and
*then* evaluate the expansion criterion. No new LLM calls are needed for option 1
(the 270 rounds are already recorded); option 2 needs a fresh 270-call run.

## Files

- `revision_loop_raw.jsonl` — 30 trajectories × 9 rounds, full texts
- `revision_loop_results.json` — embeddings, e(t), Δe, revision magnitude,
  exact-match flags, detector classifications, seeds, thresholds
- `stage1_chart.html` — trajectory chart with detector firings
- `stage1_run.py` / `stage1_analyze.py` / `select_problems.py` — frozen pipeline
