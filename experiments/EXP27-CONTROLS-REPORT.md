# Exp-27 Control Battery — Report (27A / 27B / 27C)

*2026-10-07. Frozen evaluation only — no training, no new extraction.
Follows the amended spec (Adrian's five fixes). 27D (multi-seed pilot) is
a separate run; the 20-seed Stage 2 is on hold.*

---

## Plain-language summary

**27A-0 — The blow-up has a name, and it lives in fold 1.** Before running
a single simulation, the linear math says: fold 1's law (the most
aggressive α the learner ever produced, 0.728) is *deterministically
unstable* at m=−1.5 (spectral radius 1.042 > 1). The other three folds are
deterministically stable there. And the noiseless simulation agrees
exactly: fold 1 still blows up with zero noise; the others settle quietly.
So Exp-26's pooled "chaotic blow-up" was really one fold's linear
instability wearing a trench coat — it appeared on all three substrates
because the same fold-1 theta was transplanted everywhere. The sign
boundary itself (the actual Exp-26 finding) is untouched: it never needed
the blow-up.

**27A — β is mostly a noise filter, with a real transient-shaping
remainder.** As the injected noise shrinks to zero, the jerk gap between
the full law and the β-less law shrinks monotonically (0.035 → 0.013) but
does *not* vanish: about two-thirds of β's benefit scales away with the
noise (denoising), one-third persists at σ=0 (transient shaping) — exactly
the decomposition Adrian pre-registered. Overshoot tells the complementary
story: the full law keeps overshooting *more* at every noise level,
because low-pass lag is lag, with or without noise.

**27B — Steering doesn't care about geometry. At all.** Random clouds
with L23's exact magnitudes — and even a cloud where every trial starts
at the identical median distance — reproduce the L23 fingerprint on every
metric within a recalibrated tolerance. The V1-degenerate law's blow-up
replicates on the clouds too. Per the filed framing note, this is not a
loss: the finding is a *substrate-agnostic correction law* (conditional
on the geometry gate). It just isn't the current title. One methodological
catch surfaced along the way: the G2 gate false-positives on pure noise
~30–40% of the time in calibration (not the nominal 5%) — the real
substrates pass at p=0.0001, far outside that regime, but the gate is less
clean than "p < 0.05" suggests.

**27C — "Valid maximizer," tested, comes back qualified.** Scoring every
law under every verifier: V4's law ties for first under V4 (0.5% behind an
ablation — effectively the optimum); V3's and V2's laws do *not* maximize
their own verifiers (12–19% behind simpler laws). The V1 column confirms
the telescoping near-tie (3.6% spread), as shaping theory predicts. And
the learned β *is* V4's optimum: the 10-arm sweep under V4's reward peaks
within half a percent of m=+1.0. "The learner didn't land on a lucky
number" is now measured, not asserted.

---

## 27A-0 — Analytic pre-check (free)

Noise-free loop e_{t+1} = (1−α−β−γ)e_t + (β+2γ)e_{t−1} − γe_{t−2};
spectral radius ρ(m) per fold from learned (α, γ):

| m | fold 0 | fold 1 | fold 2 | fold 3 |
|---|---|---|---|---|
| +2.0 | 0.655 | 0.712 | 0.717 | 0.647 |
| +1.5 | 0.567 | 0.642 | 0.614 | 0.578 |
| +1.0 (learned) | 0.460 | 0.575 | 0.601 | 0.509 |
| +0.5 | 0.311 | 0.524 | 0.719 | 0.442 |
| 0.0 | 0.538 | 0.642 | 0.769 | 0.450 |
| −0.5 | 0.607 | 0.770 | 0.801 | 0.568 |
| −1.0 | 0.652 | 0.904 | 0.824 | 0.623 |
| −1.5 | 0.685 | **1.042** | 0.842 | 0.660 |

ρ < 1 at m=−1.5 fails only for fold 1 (1.042) → per the pre-registered
reading, fold 1's blow-up is *deterministic linear instability*; the
standing noise-driven hypothesis covers folds 0/2/3. Bonus sim (m=−1.5,
σ_noise=0, tol pinned): folds 0/2/3 settle (steps 8–15, zero overshoot);
fold 1: 90% timeouts, jerk 287. Prediction confirmed exactly.

Corollary: fastest deterministic convergence (min ρ) sits at m=+0.5 to
+1.0 per fold — the verifier drove the learner to the knee of *both* the
noise-free and the noisy curves. Cross-check against Exp-26 per-fold
m=−1.5 sims: only fold 1 timed out (0.90–0.93 on all substrates; other
folds 0.00) — the pooled "chaotic blow-up" was fold 1 alone. The Exp-26
sign-boundary result never depended on the blow-up arm and stands.

## 27A — Noise→0 sweep (PASSED)

gap(σ) = jerk(A1) − jerk(A0), tolerance pinned at 2σ₀√d, L23, 40 pairings:

| σ/σ₀ | 1.0 | 0.5 | 0.25 | 0.1 | 0.0 |
|---|---|---|---|---|---|
| gap (jerk) | +0.0348 | +0.0199 | +0.0143 | +0.0125 | +0.0127 |
| gap (overshoot) | −0.444 | −0.644 | −0.681 | −0.731 | −0.637 |

Monotone decreasing within one tie (single +0.0002 uptick at the last
step) → **PASSED**. Decomposition: denoising ≈ 0.022 (64%),
transient shaping ≈ 0.013 (36%, the σ=0 intercept — nonzero, as
pre-registered). No timeouts at any level; steps stable (A0 6.5, A1/A3
7.0). Overshoot gap stays negative throughout: the full law overshoots
more at *every* noise level — lag, not noise. (At σ=0 the memoryless A3
is actually smoothest, jerk 0.083 vs A0 0.093 — with nothing to filter,
the low-pass only costs.)

## 27B — Random-cloud controls (both MATCH under recalibrated tolerance)

Recalibrated tolerance per metric = max(between-substrate envelope,
L23 5-seed self-spread, 5-cloud spread), as max|r−1|:

| metric | envelope | L23 self | cloud spread | tolerance |
|---|---|---|---|---|
| jerk | 0.270 | 0.030 | 0.012 | **0.270** |
| overshoot | 0.040 | 0.140 | 0.079 | **0.140** |
| steps | 0.080 | 0.000 | 0.000 | **0.080** |
| path | 0.050 | 0.015 | 0.008 | **0.050** |

(Note: L23's *self*-spread on overshoot (0.140) dominates — the old 4%-
wide envelope was miscalibrated, exactly Adrian's concern.)

| cloud | jerk | overshoot | steps | path | verdict |
|---|---|---|---|---|---|
| Cloud-M primary | 1.012 | 0.934 | 1.000 | 1.002 | **MATCH** |
| Cloud-0 (median only) | 1.111 | 0.939 | 0.923 | 1.023 | **MATCH** |

Raw ratios for all 5 Cloud-M clouds: jerk 1.007–1.028, overshoot
0.930–1.013, steps 1.000, path 0.993–1.005. V1-degenerate blow-up
replicates on the signature metrics (vs L23's ov 19.2 / eff 10.04 /
steps 33): Cloud-M 0.93x/0.93x/0.73x, Cloud-0 0.99x/1.25x/0.86x —
*timeouts were 0.00 on L23 too, so the timeout-based expectation in the
first implementation was miscalibrated; corrected here.*

**Reading:** Cloud-M matching means directional/semantic structure is
irrelevant to steering; Cloud-0 matching means even the magnitude
*distribution* barely matters. The LLM contributes essentially a scale
number to the steering experiments. Substrate-agnostic correction law —
clean finding, title changes.

*Secondary (G1/G2 on 72 Gaussian 896-D vectors):* G1 r=0.463 → FAIL
(as expected); G2 p=0.029 → PASS on the pinned seed — a false positive.
10-seed calibration: 3/10 passes (4/10 with fully independent
sequences) — the gate's effective false-positive rate exceeds the nominal
5%. Real substrates pass at p=0.0001, orders of magnitude outside this
regime, but the paper should note the gate is less clean than "p<0.05"
implies.

## 27C — Cross-verifier matrix (diagonal: V4 ✓, V2 ✗, V3 ✗)

Pooled mean discounted returns, per-fold own-18 training trials
(rank within column; * = tied within 2%):

| law | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| V1 | +22.53 (#7) | +0.99 (#7) | −57.36 (#7) | −49.02 (#7) |
| V2 | +23.25 (#5*) | +15.06 (#5) | +9.06 (#5) | +16.22 (#5) |
| V3 | +23.30 (#2*) | +13.73 (#6) | +9.70 (#3) | +15.92 (#6) |
| V4 | +23.26 (#4*) | +16.80 (#3) | +9.54 (#4) | +18.58 (#2*) |
| A1 | +23.11 (#6*) | +18.80 (#2*) | +8.90 (#6) | +16.83 (#4) |
| A3 | +23.27 (#3*) | +19.10 (#1*) | +10.79 (#2) | +18.67 (#1*) |
| V4mem | +23.38 (#1*) | +15.65 (#4) | +12.04 (#1*) | +17.42 (#3) |

- (i) Diagonal with 2% ties: **V4 ✓** (tied, 0.5% behind A3), V2 ✗
  (12% behind A3), V3 ✗ (19% behind V4mem) → NOT PASSED as stated.
- (ii) V1 near-tie: spread 0.036 < 0.15 → **PASSED** (telescoping
  confirmed); V1's own law ranks last *within* the tie.
- (iii) A1/A3 ranks: not as expected — A3 ranks **#1 under V4**,
  A1 #6/#4. The cautious ablation beats purpose-built laws under
  overshoot- and jerk-penalizing verifiers.
- Held-out-6 returns: same pattern (reported in JSON).

**Q2 — sweep under V4 (10 arms):** m=+0.75: +18.66; m=+1.0: +18.58;
m=+1.25: +18.41; m=+1.5: +17.85; m=+2.0: +15.94; m=+0.5: +18.47;
m=0: +16.83; negatives collapse (m=−1.5: −54508). **m=+1.0 within 1%
of best (0.4% behind m=+0.75) → "at the optimum"** per the
pre-registered rule (not a flat plateau: m=1.25 is 1.3% back). The
learner sits on V4's optimum to within half a percent — measured, not
asserted.

*Caveat (framing, not a bug):* the matrix scores *mean* policies while
the learners maximized *expected* return under exploration noise — part
of the V2/V3 gaps may be the mean-vs-stochastic difference rather than
pure under-optimization. The V4 near-tie bounds how large that effect
can be.

---

## Technical appendix

- **Specs/code:** `semantic-tangent-exp27-spec.md` (amended); code
  `tangent_experiment/exp27_controls.py`; results `exp27_results.json`;
  figures `figures/exp27_{spectral,noise_gap,cloud,matrix,v4_argmax}.png`.
  Env: `~/workspace/venvs/llm/bin/python`. Pure frozen evaluation; the
  models were not loaded in this run (all substrates cached).
- **27A-0 derivation:** with Δê_t = ê_t−ê_{t−1}, Δ²ê_t = ê_t−2ê_{t−1}+
  ê_{t−2}, the noise-free loop is e_{t+1} = (1−α−β−γ)e_t +
  (β+2γ)e_{t−1} − γe_{t−2}; characteristic λ³ − (1−α−β−γ)λ² −
  (β+2γ)λ + γ = 0 (numpy.roots per fold × multiplier; γ=0 case reduces
  to the earlier hand-derived bound).
- **27A noise:** common random numbers — one standard-normal draw set
  per trial, scaled per σ level; tolerance pinned at 2σ₀√d throughout.
- **27B clouds:** X₀ = 0, T = ε₀ (translation invariance: the
  controller only ever sees ε₀). Cloud-M magnitudes = L23's exact 40
  test |ε₀|; Cloud-0 all = 26.613. Same pinned noise draws as the L23
  runs (SEED+9000), so direction is the *only* difference vs L23.
- **27C trials:** per fold, its own 18 training trials (3 non-held-out
  chains; held chains per fold: size/temperature/brightness/speed);
  noise pinned per global trial index (SEED+9500). Return = discounted
  (γ=0.99) sum from `rewards_from_raw` (Exp-22 verbatim); med_eps0 =
  26.613 (training median, matching Exp-22).
- **Pooling:** Exp-24/25 precedent (mean across folds for mean-metrics,
  median for median-metrics; mean across folds for returns).
- **Judgment calls:** (1) V1deg replication re-based on the true L23
  signature (ov/eff/steps) after the timeout expectation proved
  miscalibrated — first implementation's print fixed, numbers unchanged.
  (2) G2-null 10-seed calibration added as exploratory follow-up to the
  pinned single-seed check. (3) Q2 verdict uses the spec's labels
  ("at the optimum" for within-1%, "plateau" only if 0.75–1.5 all flat).

---

## Late-fix delta (Claude's four fixes, 2026-10-07) — COMPLETE

*Plain language first.* Four surgical additions, all pre-registered before
running. **(1)** The boundary arms (m=−1.5, −1.0) were run at every noise
level: fold 1 blows up at *all* of them including zero noise — it's
deterministically unstable, exactly as the spectral math said — while the
other folds settle quietly everywhere and get calmer as noise falls. The
m=−1.0 arm never blows up anywhere. So the Exp-26 "chaotic blow-up" is
fully decomposed: one fold's linear instability plus noise, everywhere
else just a reactive-but-stable controller. **(2)** The w table shows
Claude's vocabulary correction was right but narrower than estimated:
only the brightness fold (smallest α) ever crosses into delay-dominated
(w>1), from m=+1.0 upward; the other three folds stay low-pass across the
whole ladder. And the m=+2.0 overshoot rise happens in *all* folds, so
delay-domination sharpens the story for brightness but lag alone explains
the rest. **(3)** Tightening every 27C verdict from 2% to 1% changes
almost nothing: V4's diagonal tie holds (0.5%), V2/V3 still fail by miles,
the sweep optimum holds (0.4%), the V1 near-tie holds — only A1's
membership in the V1 tie drops out (1.2% back). The verdicts are not
knife-edge artifacts. **(4)** The G2 false-positive calibration
(~30–40% on pure noise, 10-seed) is already recorded above in the 27B
section and stands as the methodological caveat: the gate is less clean
than "p < 0.05" implies, though the real substrates pass at p=0.0001,
orders of magnitude outside the suspect regime.

### Delta-1 — Boundary arms × σ (pre-registered three-way: CONFIRMED)

m ∈ {−1.5, −1.0} × σ/σ₀ ∈ {1.0, 0.5, 0.25, 0.1, 0.0}, L23, tol pinned,
common random numbers. Per (arm × σ × fold): timeout_rate / jerk_mean /
overshoot_mean / steps_med.

m=−1.5 (timeout / jerk per fold):

| fold | σ=1.0 | 0.5 | 0.25 | 0.1 | 0.0 |
|---|---|---|---|---|---|
| 0 (size) | 0.00 / 0.20 | 0.00 / 0.13 | 0.00 / 0.10 | 0.00 / 0.09 | 0.00 / 0.08 |
| 1 (temp) | 0.93 / 507 | 0.88 / 334 | 0.85 / 278 | 0.90 / 284 | 0.90 / 287 |
| 2 (bright) | 0.00 / 0.14 | 0.00 / 0.07 | 0.00 / 0.04 | 0.00 / 0.03 | 0.00 / 0.02 |
| 3 (speed) | 0.00 / 0.24 | 0.00 / 0.17 | 0.00 / 0.14 | 0.00 / 0.12 | 0.00 / 0.12 |

m=−1.0: zero timeouts everywhere, all folds, all σ (jerk 0.02–0.62,
falling with σ) — stable, as ρ<1 predicted.

Fold 1 blows up at *every* σ including zero (ρ=1.042, deterministic
instability — no noise needed); folds 0/2/3 settle at every σ and calm
down as σ→0. The pooled Exp-26 "chaotic blow-up" is now fully
decomposed, and the σ=0 row matches the 27A-0 bonus sim exactly
(bit-identical draws). **[Figure: `figures/exp27_boundary_sigma.png` —
timeout per fold vs σ for m=−1.5; pooled jerk vs σ for both arms.]**

### Delta-2 — w table: low-pass vs delay-dominated (analytic)

w(m) = |β(m)|/α per fold × m (10-arm ladder). Vocabulary adopted:
**low-pass when w ≤ 1, delay-dominated when w > 1.**

| m | size | temp | bright | speed |
|---|---|---|---|---|
| +2.0 | 0.93 | 0.73 | **2.24** | 0.83 |
| +1.5 | 0.70 | 0.54 | **1.68** | 0.63 |
| +1.25 | 0.58 | 0.45 | **1.40** | 0.52 |
| +1.0 | 0.46 | 0.36 | **1.12** | 0.42 |
| +0.75 | 0.35 | 0.27 | 0.84 | 0.31 |
| +0.5 | 0.23 | 0.18 | 0.56 | 0.21 |

(Bold = w>1; negative-m side mirrors the positive side since w uses
|β|.) Only **brightness** crosses w=1 — at m=+1.0 upward (and m=−1.0
downward). Claude's "w exceeds 1 in most folds for m ≥ 1.5" does not
hold: 1 of 4 folds. The correction to the vocabulary stands; its
empirical footprint is narrower than estimated. Note the consequence for
the m=+2.0 overshoot story: per-fold Exp-26 overshoot rises at m=+2.0
in *all* folds (size 1.40→2.98, temp 2.25→3.33, bright 0.35→2.67, speed
1.48→2.65) — delay-domination sharpens brightness's rise (7.6×) but
low-pass lag alone explains the rest. Both mechanisms are real; neither
suffices alone.

### Delta-3 — 27C at 1% ties (sensitivity re-analysis, no new runs)

Every 27C verdict re-evaluated with ties-within-1% (matrix used 2%):

| verdict | at 2% | at 1% | delta |
|---|---|---|---|
| V4 diagonal tie | ✓ (0.5% back) | ✓ (0.5%) | none |
| V2 diagonal fail | ✗ (21% back) | ✗ | none |
| V3 diagonal fail | ✗ (19% back) | ✗ | none |
| V1 near-tie | ✓ (6/7 tied) | ✓ (5/7 tied) | **A1 drops out** (1.2% back) — holds at 2% only |
| A3 #1 under V4 | ✓ | ✓ | none |
| sweep "at the optimum" | ✓ (0.4%) | ✓ (0.4%) | none |

Only one label changes: A1's membership in the V1 near-tie holds at 2%
but fails at 1%. All headline verdicts are insensitive to the tie
choice. (V1's own law remains last within the tie at both levels.)

### Delta-4 — G2 calibration note

Already recorded in the 27B section above (10-seed calibration: 3–4/10
false positives on pure Gaussian noise vs the nominal 5%; real
substrates at p=0.0001). Retained here by reference as the standing
methodological caveat. No new runs.

*Delta status: COMPLETE. Code: `exp27_delta.py` (reuses
`exp27_controls.py` harness verbatim). Results: `exp27_results.json`
keys `27A_delta_boundary`, `27A0_wtable`, `27C_1pct_sensitivity`
(backup: `exp27_results.json.predelta_bak`). Figure:
`figures/exp27_boundary_sigma.png`.*

---

# Follow-up battery I — Adrian's 2026-10-07 ~00:44 review (COMPLETE)

*Pre-registered in `semantic-tangent-exp27-spec.md` ("Follow-up battery")
before running. 27A2 + best-α are new frozen runs (same harness,
`exp27_controls.py`, verbatim); 27C corrections and the small analytics
are re-analysis / pencil-and-paper, no new runs.*

## Plain-language summary

**27A2 — against the right counterfactual, β's profile flips with the
noise.** The old 27A compared the full law to A1 (α,0,γ) — an arm that
keeps an *orphaned* γ and is the worst arm at every noise level. Against
the clean α-only arm A3: at full noise β helps (A0 jerk 0.107 vs A3
0.115); at half noise and below β *hurts* (A3 8–11% smoother, zero
overshoot at σ=0 vs 0.89 for the full law). So β buys speed (0.5 fewer
steps, everywhere) and buys smoothness only when there is noise to
filter — at σ=0 it is pure cost on jerk. Meanwhile A2 (α,β,0) shows γ is
a small jerk *benefit* at the operating point (A2 slightly worse than A0
without it), not dead weight — while A1 shows γ *without* β is actively
harmful. The honest decomposition: β is a noise-dependent speed/smoothness
trade, γ is a small operating-point smoothing term that turns toxic
without β, and the original "β smooths" claim survives only at σ>0.

**Best-α — a plain proportional controller beats the learned law under
V4's own reward.** Gridding α ∈ {0.1,…,1.0} with β=γ=0: pooled α*=0.2
scores +19.62 vs the full V4 law's +18.58 — 5.6% *above* it, far outside
the 2% tie band, and above the sweep's best β-tuning (+18.66 at m=0.75).
Per the pre-registered rule this is the strong form of "history adds
nothing under V4's reward": not a tie — a tuned α-only law wins. The
reward-level reading of "β is the portable ingredient" does not survive.
(The jerk-specific finding — β lowers jerk at σ>0 — stands as a separate
measured fact; and both are mean-policy comparisons, the same caveat as
the 27C matrix.)

**27C corrections — the diagonal is 1/4, not 3/4.** V1's own law ranks
*last* under V1 (+22.53 vs +23.38 best, 3.6% back, outside the 2% band) —
V1 **fails** the diagonal, exactly as spec prediction (ii) feared it
wouldn't ("small edge to V1's own law" was wrong). Only V4 of 4
verifiers passes diagonal dominance. The "<0.15" near-tie threshold is
labeled post-hoc as it should have been: raw V1-column numbers for the
six non-V1 laws are range 0.263, std 0.078. And the percentages are
fixed: V2's law is **21.2%** behind its column best (the report's "12%"
was wrong), V3's **19.5%** behind (the report's 19% was right).

**Small analytics — one expectation broke, honestly.** V1's fold-1 theta
(α=0.420, β=+0.405, γ=+0.165) has ρ=0.949 < 1 — deterministically
*stable*, not unstable as pre-registered. Its degenerate behavior
(elevated overshoot/efficiency/steps, zero timeouts on L23) is therefore
noise-amplified near-boundary dynamics, not deterministic instability —
still not "chaotic," but a different mechanism than V4's fold-1
(ρ=1.042, deterministic). Min-ρ sits at m=+0.5 in 3/4 folds, not at the
learned +1.0 — "knee of both curves" is softened as Adrian said: the
verifier optimized the noisy objective, and the deterministic and noisy
knees differ. γ-scoping confirmed: at V4's temperature fold, m=−1.5,
γ=+0.140 gives ρ=1.042 while γ=0 gives ρ=0.694 (and β=+0.396 < 1−α/2 =
0.636 satisfies the noiseless bound) — γ is load-bearing *at the
instability boundary* while negligible at the learned operating point.

## 27A2 — the right counterfactuals (new runs)

Pooled metrics per (arm × σ), 40 L23 pairings, pinned noise, tol pinned:

| σ/σ₀ | arm | jerk | overshoot | steps | timeouts |
|---|---|---|---|---|---|
| 1.0 | A0 (α,β,γ) | 0.1073 | 1.425 | 6.5 | 0.00 |
| 1.0 | A1 (α,0,γ) | 0.1421 | 0.981 | 7.0 | 0.00 |
| 1.0 | A2 (α,β,0) | 0.1056 | 1.394 | 6.5 | 0.00 |
| 1.0 | A3 (α,0,0) | 0.1149 | 0.925 | 7.0 | 0.00 |
| 0.5 | A0 | 0.0986 | 1.100 | 6.5 | 0.00 |
| 0.5 | A1 | 0.1184 | 0.456 | 7.0 | 0.00 |
| 0.5 | A2 | 0.1003 | 1.094 | 6.5 | 0.00 |
| 0.5 | A3 | 0.0958 | 0.519 | 7.0 | 0.00 |
| 0.25 | A0 | 0.0948 | 0.975 | 6.5 | 0.00 |
| 0.25 | A1 | 0.1091 | 0.294 | 7.0 | 0.00 |
| 0.25 | A2 | 0.0985 | 0.944 | 6.5 | 0.00 |
| 0.25 | A3 | 0.0878 | 0.300 | 7.0 | 0.00 |
| 0.1 | A0 | 0.0935 | 0.981 | 6.5 | 0.00 |
| 0.1 | A1 | 0.1060 | 0.250 | 7.0 | 0.00 |
| 0.1 | A2 | 0.0980 | 0.963 | 6.5 | 0.00 |
| 0.1 | A3 | 0.0842 | 0.188 | 7.0 | 0.00 |
| 0.0 | A0 | 0.0931 | 0.887 | 6.5 | 0.00 |
| 0.0 | A1 | 0.1058 | 0.250 | 7.0 | 0.00 |
| 0.0 | A2 | 0.0979 | 1.000 | 6.5 | 0.00 |
| 0.0 | A3 | 0.0832 | 0.000 | 7.0 | 0.00 |

**A3 vs A0 (the right comparison):** jerk — A3 is 7.1% *worse* at σ=1.0,
then 2.8%/7.4%/10.0%/10.6% *better* at σ=0.5/0.25/0.1/0.0. Overshoot —
A3 is lower at every level (0.925→0.000 vs 1.425→0.887). Steps — A3
costs 0.5 everywhere (7.0 vs 6.5). Reading: β buys speed always, buys
smoothness only when noise is present, costs overshoot always.
**A2 vs A0:** jerk within ±5% (A2 slightly better at σ=1.0, slightly
worse below) — γ is a small operating-point smoothing term, not dead
weight. **A1:** worst jerk at every σ — γ without β is actively
harmful; the original 27A gap conflated "removing β" with "orphaning γ."

## Best-α baseline (new runs)

α ∈ {0.1,…,1.0}, β=γ=0, under V4's reward on each fold's own 18 L23
training trials (27C sweep code path; pinned noise):

| α | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| pooled | +18.93 | **+19.62** | +19.52 | +19.45 | +18.85 | +18.06 | +17.24 | +16.17 | +14.91 | +13.32 |

Per-fold α*: 0.2 / 0.2 / 0.2 / 0.4. Pooled α*=0.2 (+19.62) vs full V4 law
(+18.58): **+5.6%, outside the 2% band upward**. Pre-registered verdict:
"history adds nothing under V4's reward" — confirmed in the strong form
(a tuned α-only law *beats* the learned history law; the pre-registered
bar was a tie). Also above the sweep's best β-tuning (+18.66 at m=0.75,
fixed per-fold α): under V4's reward, tuning α beats tuning β. The
reward-level reading of "β is the portable ingredient" does not survive;
the jerk-specific finding (β lowers jerk at σ>0 vs A3) stands separately.

## 27C corrections (re-analysis)

- **V1 diagonal → FAIL.** Own law +22.53 vs column best +23.38 = 3.6%
  back (outside 2%), rank #7/7 — last. Spec prediction (ii)'s "small
  edge to V1's own law" was wrong. **Diagonal dominance: 1/4 (V4 only).**
- **Near-tie threshold post-hoc.** The "<0.15" bar was not in the spec —
  labeled as such. Raw V1-column values for the six non-V1 laws:
  range 0.263, std 0.078, relative range 1.13% (V2 +23.25, V3 +23.30,
  V4 +23.26, A1 +23.11, A3 +23.27, V4mem +23.38).
- **Percentages fixed (verified from JSON).** V2's law is **21.2%**
  behind its column best (+15.06 vs +19.10, A3) — the report's "12%"
  was wrong. V3's law is **19.5%** behind (+9.70 vs +12.04, V4mem) —
  the report's 19% was correct.

## Small analytic points

- **V1 fold-1 ρ = 0.949 < 1** (θ = [0.420, +0.405, +0.165]). The
  pre-registered expectation (>1) did **not** hold: V1's degenerate law
  is deterministically stable but near the boundary — its elevated
  overshoot/efficiency/steps with zero timeouts on L23 are
  noise-amplified near-boundary dynamics, a different mechanism than
  V4's fold-1 (ρ=1.042, deterministic). Not chaotic either way.
- **Min-ρ at m=+0.5 in 3/4 folds** (f2 at +1.0): the deterministic knee
  and the noisy knee differ — the verifier optimized the noisy
  objective. "Knee of both curves" softened per Adrian.
- **γ-scoping confirmed.** V4 temperature fold at m=−1.5: ρ=1.042 with
  γ=+0.140 vs ρ=0.694 with γ=0 (and β=+0.396 < 1−α/2 = 0.636 satisfies
  the noiseless bound). γ is load-bearing at the instability boundary,
  negligible at the learned operating point — "dead weight" only with
  the operating-point qualifier (manuscript checklist item 14).

*Follow-up I status: COMPLETE. Code: `exp27_followup1.py` (+
`exp27_followup1_figs.py`; reuses `exp27_controls.py` harness verbatim).
Results: `exp27_results.json` keys `27A2_arms`, `best_alpha`,
`27C_corrections`, `V1fold1_rho` (backup:
`exp27_results.json.prefollowup1_bak`). Figures:
`figures/exp27_followup1_jerk_sigma.png`,
`figures/exp27_followup1_bestalpha.png`.*

---

# Follow-up battery II — Adrian's 2026-10-07 ~00:44 review (27B2 + G2 null)

*2026-10-07. Pre-registered in `semantic-tangent-exp27-spec.md` ("Follow-up
battery") before running. Code: `tangent_experiment/exp27_followup2.py`.
Results merged into `exp27_results.json` (`27B2_cloudS2`,
`27B2_cloud0_reframe`, `27B2_S3`, `G2_empirical_null`). Pure frozen
evaluation; no model was loaded (S3 cache pre-extracted in Exp-24).*

## Plain-language summary

**27B2a — A substrate is its magnitude list *plus its instrument*; direction
is irrelevant.** The pre-registered test did not reproduce S2: five clouds
built from SmolLM2's exact 40 magnitudes, steered under L23's instrument,
came out at 2.22× L23's jerk instead of S2's measured 1.27×. But the miss
has a clean explanation, and the follow-up diagnostic nails it: re-running
the *same five clouds* under S2's own instrument (σ/tolerance rescaled to
S2's magnitude scale) reproduces S2's absolute metrics to **under 1%** on
every metric (jerk 0.1363 vs 0.1359, overshoot 1.44 vs 1.43, steps 6.0 vs
6.0, eff 1.14 vs 1.13). So: direction contributes nothing (Cloud-M, and
now this); magnitude *scale* is the instrument and must be recalibrated
per substrate (exactly what Exp-24's rescaling did — load-bearing again);
magnitude *distribution* contributes modestly (see Cloud-0 reframe). The
pre-registered binary ("reproduces 1.27× → just its magnitude list") is
recorded as NOT reproduced in the form stated; the refined, measured
statement is stronger and more precise.

**27B2b — Cloud-0's "match" was a tolerance artifact.** Re-analysis of the
existing 27B numbers: Cloud-0's +11.1% jerk is 3.7× L23's own 3%
self-spread, and its −7.7% steps move is likewise outside L23's noise. It
passed only because the jerk tolerance (0.27) was dominated by S2's 27%
envelope. Honest verdict: the magnitude *distribution* matters — just less
than the scale.

**27B2c — S3 (Pythia-70M) steers; the G1 exclusion was moot.** G1 still
fails at r=0.698 (the famous 0.002 miss), but the frozen V4 law steers
Pythia's final layer cleanly: 0 timeouts, overshoot 1.28, eff 1.08,
jerk 0.114 — passing the same bar S1/S2 passed, with jerk squarely inside
the L23/S1/S2 family (0.107/0.107/0.136). The α-only A3 law also steers
(0 timeouts, overshoot 0.98). Per the pre-registration: drop "conditional
on the geometry gate." The gate kept out a perfectly steerable substrate
over two thousandths of a correlation point.

**G2 empirical null — the gate is miscalibrated.** 200 Gaussian null
substrates (896-D, L23-matched scale) through the exact Exp-18 G2
machinery: **43% false-positive rate** at p<0.05 (full bar: 43%), and 3 of
200 nulls reach the real substrates' floor (p=0.0001) — above the
pre-registered ≤1/200 bar, so the gate does **not** stand on empirical
grounds. The fixed-order-shuffled diagnostic (all 60 sequences sharing one
fixed *random* permutation) false-positives at 43.5% — identical to the
related condition. That pins the mechanism: train and test share a fixed
sequence order in the related condition, so position-specific ridge fits
transfer; shuffled train/test orders differ. It operates on pure noise —
Adrian's shared-token hypothesis isn't needed, and the 27B "orders of
magnitude outside" framing is retired: the permutation test cannot resolve
below its 1/10001 floor, so "p=0.0001" was never orders of magnitude
anywhere. Note for the manuscript: the counting control also "beats naive"
on 100% of pure-noise nulls — it is a non-gate on noise.

## 27B2a — Cloud-S2 detail

S2's 40 test |ε₀| (4D PCA space): median 8.614, range [3.18, 15.99] —
much smaller scale than L23's 26.6, hence the instrument question. Five
clouds, SEED+28000+i, L23 instrument (σ₀=1.3306, tol₀=5.3226), pinned
noise draws (SEED+9000+ti, common with L23 runs):

| metric | Cloud-S2 ratio vs L23 | cross-cloud spread | S2 measured |
|---|---|---|---|
| jerk | **2.219** | 0.036 | 1.27 |
| overshoot | 1.096 | 0.048 | 1.00 |
| steps | 0.923 | 0.000 | 0.92 |
| path (eff) | 1.262 | 0.054 | 1.05 |

Pre-registered verdict: **DOES_NOT_REPRODUCE_S2** (2.22 ≠ 1.27 ± 0.05).
Post-hoc diagnostic (same clouds, S2 instrument σ=0.5374/tol=2.1495):
absolute metrics reproduce S2 to <1% on all four metrics. The 2.22× was
instrument mismatch — S2-scale magnitudes under L23-scale noise — not a
magnitude-list failure. Figure: `figures/exp27_cloudS2.png`.

## 27B2c — S3 detail

Per-substrate rescaling exactly per `exp24_cross_substrate.py`
(PCA→4D on S3's 72 map vectors; instrument from S3's training trials:
median|ε₀|=4.836, σ=0.2418, tol=0.9671; pinned noise SEED+9000+ti):

| arm | timeout | overshoot | eff | steps | jerk |
|---|---|---|---|---|---|
| A0 (frozen V4) | 0.00 | 1.28 | 1.079 | 6.5 | 0.1143 |
| A3 (α-only) | 0.00 | 0.98 | 1.074 | 7.0 | 0.1234 |

Bar (b): PASSED (0 timeouts, ov<2.0, eff<1.5). Jerk in family
(L23 0.107, S1 0.107, S2 0.136). **Verdict: S3 STEERS — the G1 exclusion
was moot; "conditional on the geometry gate" is dropped.**

## G2 empirical null — detail

200 nulls, scale matched to L23 E_base std (9.372), full G2 machinery
(control validity + related/shuffled + 10,000-permutation p, seed-pinned):

- Empirical FPR (p<0.05): **0.430**; full-bar pass rate: 0.430
- Fixed-order-shuffled FPR: **0.435** (≈ related — mechanism identified)
- Nulls at/below the real floor (p≤1.0001e-04): **3/200** (bar: ≤1/200)
- Control validity on nulls: 1.000 (non-gate); null G1 r@4D median 0.461
- Real stats: L23/S1/S2/S3 all at p=0.0001 (permutation floor)

**Verdict: GATE MISCALIBRATED.** Figure: `figures/exp27_g2_null.png`
(null p histogram, real stats marked). Manuscript note: Exp-18's G2
"p=0.0001" must be re-reported against the empirical null (empirical
p ≈ 0.015 for reaching the floor — suggestive, not decisive), and the
G1/G2 gate narrative needs the calibration caveat.

---

## Round 2.3 — the 80 V4 thetas through the harnesses (Adrian's ~01:19 review)

*Exps 23–26 rested on four single-seed draws. Stage 2 saved all 80 V4
thetas (4 folds × 20 reps); this section evaluates every one of them.
All frozen eval; rep-0 bit-exact vs Exp-22.*

### Plain-language summary

**The β→smoothness link survives, but α is the first-order knob and the
ablation pattern was partly a 4-draw artifact.** Across all 80 seeds, β
alone explains almost none of the jerk variation (R² = 0.008, slope
non-significant) — because α varies independently across seeds and
dominates jerk (partial coefficient 0.37 vs β's 0.12, R² = 0.955 with
α,γ in the model). *Conditional* on α, the β slope is positive and
highly significant with the same sign as the Exp-26 ladder (+0.12 vs the
ladder's +0.03): more negative β → less jerk, holding α fixed. So the
ladder's knee was not an artifact of co-adaptation — but it was measured
*at fixed α*, and across the natural seed distribution α swamps β. That
is the same lesson as the best-α result, seen from the other side.
Overshoot tells the cleaner seed story: more negative β → more
overshoot, significant even unconditionally (−2.2, p = 0.0015) —
"β costs overshoot" reproduces across all 80 seeds.

**V3 really is aggressive — in α, not β.** V3's α distribution sits far
above V2/V4 (mean 0.754 vs 0.549, Welch p ≈ 1e-20) while its β is noise
around zero (median −0.026). "V3 aggressive" was always an α claim; now
it's measured. V4 pairs moderate α (median 0.534) with reliably negative
β (median −0.176); V2 pairs moderate α (0.515) with β ≈ 0.

**The ablation spot check partially holds.** On 10 thetas spanning the
β range (−0.375 to +0.066), A1 (orphaned γ) has the worst jerk in 60%
of runs and A3 (α-only) is smoothest at σ=0 in 70% — real tendencies
(well above 25% chance) but not the clean 4/4 pattern of the original
four draws. The 27A2 conclusion stands; its crispness was partly a
4-draw artifact.

**Portability holds across all 80 thetas**, not just the original four:
zero timeouts on every substrate (L23/S1/S2/S3); pooled jerk
0.143/0.142/0.184/0.152 — S2's elevation matches its 1.27× envelope,
S3 (Pythia) steers fine on all 80.

### 80-theta steering eval (L23/S1/S2/S3, per-substrate instruments)

| substrate | pooled jerk | overshoot | steps_med | timeout_rate |
|---|---|---|---|---|
| L23 | 0.1426 | 1.54 | 6.0 | 0.000 |
| S1 (L12) | 0.1424 | 1.48 | 6.0 | 0.000 |
| S2 (SmolLM2) | 0.1836 | 1.57 | 6.0 | 0.000 |
| S3 (Pythia) | 0.1520 | 1.50 | 6.0 | 0.000 |

(Note: the 80-theta pooled jerk 0.143 exceeds the 4-draw pooled 0.107 —
the original four draws sat at the strong-β end of the seed
distribution.)

### Regression: jerk/overshoot on β across 80 seeds (L23)

β range [−0.375, +0.066]; corr(β,α) = −0.06, corr(β,γ) = −0.03
(near-independent seed variation).

| outcome | simple d/dβ | p | R² | partial d/dβ (α,γ held) | p | R² |
|---|---|---|---|---|---|---|
| jerk_mean | +0.074 | 0.42 | 0.008 | +0.120 | 4e-08 | 0.955 |
| overshoot_mean | −2.218 | 0.0015 | 0.121 | −1.923 | 5e-08 | 0.813 |

Partial coefficients (jerk): α +0.369 (p≈0), β +0.120 (p≈0),
γ +0.029 (p=0.21, n.s.). Partial (overshoot): α +2.470, β −1.923,
γ n.s. Ladder local slope near the knee (m=+0.5→+1.5, L23): +0.031 —
same sign as the seed partial slope.

**Pre-registered reading, resolved honestly:** the unconditional
seed-natural β→jerk slope is flat (p=0.42) — so a naive "more negative
β ⇒ smoother" does not reproduce across seeds. But the ladder held
(α,γ) fixed, and the correct comparison is the *partial* slope: +0.120,
significant, same sign as the ladder's +0.031 (steeper, in fact). The
knee was not a co-adaptation artifact — it was a fixed-α measurement,
and across seeds α is the first-order knob. The overshoot leg needs no
such qualification: it reproduces unconditionally.

### (α,β,γ) distributions per verifier (320 Stage-2 thetas; median [p5, p95])

| verifier | α | β | γ |
|---|---|---|---|
| V1 | 0.346 [0.097, 0.834] | −0.042 | −0.098 |
| V2 | 0.515 [0.333, 0.736] | +0.026 | −0.023 |
| V3 | **0.746 [0.533, 0.946]** | −0.026 | −0.010 |
| V4 | 0.534 [0.280, 0.881] | −0.176 | +0.020 |

V3's α mean 0.754 vs V2/V4 pooled mean 0.549 (Welch p≈1e-21) — "V3
aggressive" is an α finding, now measured at n=80/verifier.

### Ablation spot check (10 thetas, β −0.375…+0.066; L23, σ=1.0 and σ=0)

A1 worst jerk: 12/20 runs (0.60). A3 smoothest at σ=0: 7/10 (0.70).
Verdict: **partially holds across seeds** — real tendency, seed-dependent
crispness. The 27A2 decomposition (β helps jerk only with noise present;
A1's orphaned γ is worst everywhere) survives; its 4/4 cleanliness does
not.

### Files

Code `exp27_r23.py`; results in `exp27_results.json` (`R23_80theta_eval`,
`R23_regression`, `R23_alpha_gamma_dist`, `R23_ablation_spotcheck`;
backup `/tmp/exp27_results.preR23_bak.json`); figures
`figures/exp27_r23_{jerk_vs_beta,overshoot_vs_beta,alpha_gamma_hist}.png`.

## Round 2.1 — joint (α,β) grid: is the learner just a weak optimizer? (Adrian's ~01:19 review)

**Plain language: yes — the learner got stuck, and history is not useless.**
Grinding α and β together (γ=0) under V4's own reward finds a joint
optimum at **(α=0.2, β=−0.1) scoring +20.83** — beating the α-only best
(+19.62) by 6.2% and the learned V4 law (+18.58) by 12.1%. All four
folds independently agree on the same optimum. So V4's reward genuinely
favors β<0: history *adds* 6% at the optimum. The learner just never
found it — its α ran up to 3.6× too large (0.73 vs 0.2) and its |β| 2–2.6×
too large (0.20–0.26 vs 0.1). Battery I's strong-form "history adds
nothing under V4's reward" is overturned: it compared the learned law
against the wrong baseline (α-only at β=0, which is itself not optimal).

**Branch verdict: A fired cleanly** (optimum β**=−0.1 < 0 and +20.83 >
+19.62; the β<0-vs-β=0 gain is +6.2%, far above the 1% flatness bar).
Step 2 (re-inits) was pre-registered for Branch B only — not run.

**Nuance on the mechanism.** Adrian's hypothesis was "β was repairing
oversized α." The ridge says something blunter: the optimal β sits at
≈−0.1 at *nearly every* α (0.1–1.0), so β doesn't grow more negative as
α grows in this slice. The learner didn't trade α against β along a
ridge — it overshot *both* coordinates independently. It is a weak
optimizer, full stop.

**Exploratory γ check (not pre-registered).** Scanning γ at the joint
optimum (0.2,−0.1): γ=0 is optimal (+20.83); γ=±0.05/±0.10 only hurts,
and γ=+0.14 (the learned fold-1 value) drops it to +17.41. γ is not the
missing piece — the learner is just far from the optimum.

**Reworded claim.** "V4 *plus this init and optimizer* induces negative
β (76/80 runs) — but the induced thetas sit far from V4's reward
optimum (α up to 3.6×, |β| up to 2.6× too large). The learning-rule
comparison (Exp-21's hill-climber vs alternatives) is untested and back
on the table."

### Details

Grid: α ∈ {0.1,…,1.0} × β ∈ {−0.5,…, +0.2}, γ=0 — 80 cells, each scored
as pooled mean V4 reward over 4 folds × own-18 training trials (same
pinned setup/noise as the 27C sweep and best-α; ~5 s total). Optimum is
interior (β**=−0.1, not at the −0.5 grid edge — no extension needed).

| point | (α, β) | pooled V4 return |
|---|---|---|
| joint optimum | (0.2, −0.1) | **+20.83** |
| α-only best | (0.2, 0) | +19.62 |
| sweep best (m=0.75, fixed α) | per-fold α, β≈−0.16..−0.20 | +18.66 |
| learned V4 law | per-fold (0.23–0.73, −0.20..−0.26) | +18.58 |

Per-fold optima: all four folds (0.2, −0.1) — unanimous. Neighborhood:
(0.2,−0.2) +20.23, (0.2,0) +19.62, (0.3,−0.2) +20.55, (0.1,−0.1) +19.46 —
the optimum is a genuine peak, not a knife-edge, and β<0 beats β=0 at
every α ≤ 0.5.

### Files

Code `exp27_r21.py` (+ `exp27_r21_fig.py`); results in
`exp27_results.json` (`R21_joint_grid`, `R21_gamma_exploratory`; backup
`exp27_results.json.prer21_bak`); figure
`figures/exp27_r21_surface.png` (heatmap with joint optimum, α-only
best, and the four learned thetas marked).

## Round 2.2 — α-only Pareto front, not A3 (2026-10-07 ~01:22)

**Plain language.** Adrian's objection was that A3 (α-only at the *learned* α, 0.23–0.73) is the wrong baseline — the fair comparison is the full law against the best α-only controllers at *every* speed. So we swept 20 α-only controllers (α = 0.05…1.00, β=γ=0) on the 40 L23 test pairings and drew their tradeoff curve: as α rises, steps fall 47→6, jerk rises 0.005→0.33, overshoot rises 0.03→2.83 — a clean monotone frontier, no timeouts anywhere. Then we placed the four frozen V4 laws on the same plot.

**Three of the four laws sit outside the α-only frontier.** Fold 0 does 6 steps at jerk 0.10 — every α-only controller that fast has jerk ≥0.14. Fold 3 does 6 steps at jerk 0.11. Fold 2 does 9 steps at jerk 0.043 and overshoot 0.53 — it outright *dominates* the α=0.35 point (same steps, less jerk, less overshoot). Only fold 1 (the aggressive α=0.73 fold) sits inside the frontier, dominated by four α-only points: its profile really is achievable without history — it looks like a big-α controller with extra jerk.

**Reading.** Strictly, neither pre-registered branch fires cleanly (not all four inside; no law dominates every α). The measured middle case is the informative one: history doesn't beat α-only everywhere, but it *shifts the tradeoff curve inward* — β lets the controller be fast without paying the full large-α jerk/overshoot price. "β buys speed" is not "small α is slow"; it's "at matched speed, β buys smoothness." This is consistent with R2-1's joint optimum (α=0.2, β=−0.1) beating α-only best: β<0 helps at fixed α.

**Steps at α=0.2: 13.5 vs A0's 6.5.** The reward-optimal α is nearly twice as slow as the learned law. V4's reward (discount 0.99) barely values speed, so the optimizer happily trades 7 steps for smoothness.

**What the speed edge is worth (paper note).** Discount-bite decomposition (G(1.0)−G(0.99) per trial): the 0.5-step edge (A0 vs A3) buys **+0.094** return under V4's reward — and A0 still loses by 0.47 overall, so A3's smoothness is worth ~0.56. The 7-step edge (A0 vs α=0.2) buys **+0.76** — and A0 still loses by 1.24, so α=0.2's smoothness is worth ~2.0. Even a seven-step speed advantage can't overcome the jerk deficit under discount 0.99. "Fast" was never V4-selected; the paper should not claim it was.

### Files

Code `exp27_r22_pareto.py` (+ `exp27_r22_speed.py` for the A0-vs-A3 edge); results in `exp27_results.json` (`R22_pareto`, backup `exp27_results.json.prer22_bak`; A0-vs-A3 edge merged under `R22_pareto.speed_edge.A0_vs_A3`, raw in `r22_speed_edge_a0a3.json`); figure `figures/exp27_pareto_alpha.png` (jerk-vs-steps and overshoot-vs-steps panels, front traced, four A0 stars, α=0.2 diamond).

## Round 2.4 — fix G2, don't caveat it (Adrian's ~01:19 review)

*R2-4: re-run real-related vs fixed-order-shuffled using Exp-18's exact
G2 machinery on the REAL sequences. Pre-registered: separates (real at
the extreme of the fixed-order-shuffled null, p ≤ 0.005) → gate
repairable; doesn't separate → cut "word order carries predictive
information." Code `exp27_r24.py`; results in `exp27_results.json`
(`R24_G2_repaired`; backup `exp27_results.json.prer24_bak`); figure
`figures/exp27_r24_g2_repaired.png`. All frozen eval; ~15 s wall.*

### Plain-language summary

**The gate doesn't repair — the word-order claim is cut.** The repaired
test asks the right question: is the *semantic* word order more
predictive than *any* fixed order, or was the original result just
"fixed order beats reshuffled-per-sequence"? On the real embeddings,
across all four substrates, the semantic order lands at empirical p =
0.21 (L23), 0.045 (S1), 0.015 (S2), 0.010 (S3) against 200 random fixed
orders — nowhere near the pre-registered ≤0.005 extreme bar. Per the
pre-registration, **"word order carries predictive information" is cut
from the paper.**

Two honest qualifications, neither of which changes the verdict. First,
the reconstruction is faithful: the original machinery (related vs
per-sequence-shuffled) reproduces p = 0.0001 on all four substrates, so
the failure to separate is about the comparator, not a broken
replication. Second, all four empirical p-values sit on the "better than
a typical fixed order" side — consistent with a modest real word-order
effect this test can't establish, and equally consistent with noise. The
paper cuts the claim; it does not assert the negative.

**The counting control is a confirmed non-gate.** "Predictor beats
naive" holds for the counting order *and* for a fixed random order on
S1/S2/S3, and on L23 it holds for related order, fixed random order, and
per-sequence-shuffled alike. The predictor beats the running-mean naive
baseline regardless of order — a regularization effect (ridge shrunk
toward the mean beats a noisy running mean on any i.i.d.-ish data), not
evidence the instrument detects structure. It never validated anything.

### Detail

Repaired G2 per substrate (N = 200 fixed-order null draws, seed-pinned;
statistic = mean test MSE of the related condition; one-sided empirical
p = (1 + #{null ≤ real})/201):

| substrate | G1 r@4D | validation (orig. p) | real related | null mean ± sd | empirical p | verdict |
|---|---|---|---|---|---|---|
| L23 | 0.827 | 0.00010 | 1831.3 | 1917.9 ± 111.5 | 0.2090 | no separation |
| S1 (L12) | 0.763 | 0.00010 | 6.539 | 7.800 ± 0.707 | 0.0448 | no separation |
| S2 (SmolLM2) | 0.849 | 0.00010 | 44.46 | 52.69 ± 3.20 | 0.0149 | no separation |
| S3 (Pythia) | 0.698 | 0.00010 | 68.18 | 81.70 ± 6.13 | 0.0100 | no separation |

Bar: empirical p ≤ 0.005 (real at the ≤1/200 extreme, same bar as
Battery II). 0/4 substrates separate → **CUT**.

Counting control under the fixed comparator:

| substrate | counting order beats naive | fixed-random order beats naive | verdict |
|---|---|---|---|
| S1 | yes (1.76 vs 2.14) | yes (2.08 vs 2.36) | non-gate: order-independent |
| S2 | yes (11.64 vs 18.64) | yes (16.23 vs 20.02) | non-gate: order-independent |
| S3 | yes (12.00 vs 13.49) | yes (12.17 vs 13.53) | non-gate: order-independent |
| L23 (no E_nums; word embeddings) | related: yes | fixed-random: yes; per-seq shuffled: yes | non-gate: holds regardless of order |

### Repaired procedure (for the manuscript record)

The repaired G2, had it separated, would have been: (1) PCA on the 72
map vectors → 4D, exactly as Exp-18; (2) 60 sequences in RELATED_ORDER
with seed-pinned carrier picks → ridge(K=3, λ=1.0) fit on 40, mean MSE
on 20 → observed statistic; (3) null: 200 draws, each one fixed random
permutation shared across 60 fresh sequences → null distribution of mean
MSE; (4) one-sided empirical p, bar ≤ 0.005. It is documented here
because the negative result is informative — future word-order tests in
this paradigm must use a fixed-order comparator, not per-sequence
shuffling — but the gate itself is not repaired, and the paper makes no
word-order claim.

### Manuscript implication

Checklist item 20 resolved as the cut branch: remove "word order carries
predictive information" and the G2 gate narrative; the geometry section
reports the miscalibration (43% FPR on noise; mechanism: shared fixed
train/test order) with this R2-4 result as the closer. The counting
control is described as a non-gate, not as validity evidence.
