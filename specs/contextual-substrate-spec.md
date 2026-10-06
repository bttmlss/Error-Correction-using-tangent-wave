# Contextual Substrate Spec — Exp 18 (shared reference, DRAFT)

**Status:** draft, awaiting Adrian's kickoff (queued for 2026-10-05). Nothing runs until he says go.

## Why this experiment (plain language)

The frozen one-number word squash is measured-dead: 16b found r = 0.04 between real word-pair distances and line distances, and 17's null was entailed by it — one measured result, not two. The matcher could only see the *pointer* (which word), never the *territory* (how words relate). Exp 18 is the honest next rung: contextual hidden states, several dimensions instead of one, PCA instead of a random projection, a predictor that must first prove itself on a positive control, and a success bar written down *before* running. If meaning survives anywhere in the cheap substrate, it's here — and if it doesn't, we'll know exactly which part failed.

## The substrate (pinned)

- Model: **Qwen2.5-0.5B-Instruct**, local weights at `~/workspace/models/qwen2.5-0.5b-instruct/` (config.json, tokenizer.json, model.safetensors — all present)
- Runtime: `~/workspace/venvs/llm/bin/python` — torch 2.14.1+cpu, transformers 5.18.0, CPU only, fp16, batch of one. ~100 short forward passes ≈ minutes. (Feasibility re-verified 2026-10-05; the Exps 6.x fork work already ran this same stack.)
- Contextualization: each of the 24 Exp-16 words embedded in **3 short carrier sentences** (e.g. "The ___ sat on the table."); word vector = mean hidden state over the word's token positions at **layer 23** (final layer — richest contextual mixing; the fork experiments already read layers 8/16/23 successfully here).
- One spec for everyone: if ChatGPT, Claude, or Jim weigh in, they work from this file, not their own variables.

## Condition 1 — PCA dimension ladder (the gate)

- Fit PCA on the 24 × 3 = 72 contextual vectors.
- Measure Pearson r between 896-dim pairwise distances and projected distances at dims **{1, 4, 16, 64}**.
- **Gate (pre-registered):** build the predictor only on the *smallest* dimension scoring **r ≥ 0.70**. If no dimension passes, stop and report — no predictor.
- Report the full ladder either way (this is the Exp-16b question answered in the contextual substrate).

## Condition 2 — positive control (the validity test)

- Synthetic sequence whose order *definitely* carries information: a counting sequence using the words "one".."twenty-four", next-word fully determined by position.
- **Validity bar:** the predictor must beat the naive baseline on the control. If it can't, the prediction test is not a valid instrument — a null from it means nothing — and we fix the instrument, not the theory.
- This is the guardrail Exp 17 was missing.

## Condition 3 — pre-registered prediction test

- Task: learner sees a word sequence, predicts the next target. **Related order** (e.g. stone→rock→mountain) vs **shuffled order** (same words, order shuffled — shuffle the *order*, not the numbers, so the control is fair).
- **50+ sequences per condition**, seeds pinned in the code file.
- **Success bar (pre-registered):** mean prediction error on related < shuffled, permutation p < 0.05, **and** the predictor beats the naive baseline. Report the numbers whichever way they land.
- Naming: **Exp 18**; follow-ups get sub-numbers (18b, 19…) — the 16b naming tangle is not repeated.

## Honest limits

- One 0.5B instruct model, one layer choice, CPU budget — still observational (no training, no reward modification), per the bridge-then-jump discipline.
- The three carrier sentences are arbitrary; if the ladder fails, carrier diversity is the first suspect, not the concept.
- Positive control validates the *instrument*, not the claim that meaning is in the substrate.

## What this supersedes

- Exp 16's headline is corrected: the failure was the *random* one-number squash, not words-vs-numbers (16b, agreed with Claude).
- Exp 16b and 17 are one measured result, not two (logged in RESULTS.md).
- The 6-pair synonym finding (0.559 vs 0.785) did not replicate at n=55 and stays retracted.
