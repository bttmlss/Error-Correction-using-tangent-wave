# Verifier-Induced Law Generalization — Exp 23 (shared reference)

**Status:** DIRECTIVE from Adrian (2026-10-05), building now. This is the first
"is it portable?" experiment rather than "does the mechanism exist?".

## Why this experiment (plain language)

Exp 22 showed the verifier can sculpt a correction law: V4's smoothness
verifier reliably induced a damping law (negative β, tight cluster, cleanest
paths). But that law was sculpted *on* the four training chains. Exp 23 takes
the sculpted law away from the environment that shaped it and asks: is it a
transferable operator, or did it just memorize the training neighborhood?
Freeze everything learned — no further training on the test situations — and
hit the frozen controllers with genuinely unseen semantic situations.

## The frozen pipeline (pinned)

- Substrate: Qwen2.5-0.5B L23, 4D PCA, identical embedding procedure
  (3 carriers, frozen PCA basis from Exp 18's 24 map words).
- Instrument: same σ, same settle tolerance as Exp 22 (the instrument
  doesn't change when the situations do).
- Controllers per fold (4 matched triples, thetas frozen from
  exp22_results.json, zero further learning):
  - **V4-history**: the V4-induced damping law (the candidate transferable operator)
  - **V4-memoryless**: same verifier, history ablated (α only)
  - **V1-history**: whatever the minimal verifier induced that fold
    (including fold 1's degenerate law — honest pairing, not cherry-picked)
- Terminology pinned: never "the correct law" — always "the law induced
  by V4". If it generalizes, the claim is "V4 induced a transferable
  correction policy".

## The three generalization types (pinned)

All test trials are deterministic evaluations (frozen thetas, pinned noise).
Training used all ordered pairs within each 3-word chain (24 trials).

- **Type 1 — new points, familiar geometry** (16 trials): 8 NEW words never
  embedded before (2 per chain: size tiny/enormous, temperature
  freezing/scorching, brightness gloomy/radiant, speed sluggish/rapid),
  paired within their chain (new→new both directions, new→familiar,
  familiar→new). Unseen points, familiar region.
- **Type 2 — new combinations** (12 trials): familiar chain words in
  cross-chain pairings whose |ε₀| falls WITHIN the training distance range.
  Semantic transitions never encountered, familiar movement scale.
- **Type 3 — new trajectory geometry** (12 trials): cross-chain pairings
  whose |ε₀| falls OUTSIDE the training range (substantially different
  movement through PCA space). Deterministic selection: all 108 cross-chain
  ordered pairs scored by |ε₀|, evenly spaced picks inside/outside the
  training [min, max].

Total: 40 unseen trials, none used in any training.

## Controls (pinned)

- **Label-shuffle control**: permute targets among the 40 test trials
  (pinned permutation), re-run all controllers. If the fingerprint is
  preserved, the law handles the geometry class rather than specific
  X₀→T pairings — evidence for a correction law over memorized identities.
  (All test words are unseen anyway; the shuffle tests pairing-specificity
  within the unseen set.)
- The V1-history arm is itself a control: does an underdetermined-verifier
  law transfer, or does it fall apart off-distribution?

## Measurements (pinned) — full fingerprint on unseen trials

Per (controller × type), pooled and per-type: median steps, median path
cost, mean overshoot (Exp-20 true-eps rule), mean action jerk
(|ΔX_t − ΔX_{t−1}|/|ε₀|, the V4 quantity), timeout rate. Thetas frozen —
reported for reference, not re-learned.

## Pre-registered bar (frozen controllers, unseen trials)

(a) V4-history overshoot_mean < V1-history overshoot_mean, pooled over all
    40 unseen trials, for all 4 folds (the induced damping transfers);
(b) V4-history eff_med < V4-memoryless eff_med, pooled, ≥3/4 folds
    (history helps off-distribution, not just on held-out chains);
(c) V4-history timeout_rate == 0 on all 40 trials (the law doesn't fall
    apart away from its training neighborhood).
Per-type breakdown (1/2/3) reported exploratory — which kind of novelty is
hardest is itself a finding. Shuffle-control fingerprint reported without a
directional bar.

## Honest limits

- 4D only; linear PID policy class frozen — generalization is over
  (α,β,γ)-space behavior, not architectures.
- "Unseen" is within one model's embedding space and one PCA projection;
  cross-model or cross-representation transfer is not tested.
- 40 trials is a probe, not a landscape survey; a null on one type bounds
  the claim, it doesn't end the program.
- If V4 generalizes: "V4 induced a transferable correction policy" —
  substrate / verifier / correction law / generalization separated as four
  distinct pieces of the architecture. Not "intelligence".
