# Protocol Clarification Note — σ in the Step 1 Jitter Model

**Date:** 2026-10-15
**Protocol:** Stage 2 v13 (unchanged by this note)
**Decision:** Resolution (c) — document the limitation; jitter gate remains blocked.
**This note amends nothing.** It records an ambiguity and the reason for the
chosen handling. The ambiguity itself is unresolved.

---

## The ambiguity

Protocol v13, Step 1, describes the jitter comparison as:

> residual variance around a **linear fit of Δwords on the stated value**
> (u for commands, ê for readings) … **with σ as a covariate in the fit**.

Two passages pull in different directions on what σ denotes:

1. **σ as injected noise.** "8 noisy readings (**2 per σ level**: 0, 0.72,
   1.44, 2.88)" and "injected reading noise does not count as jitter (fit is
   on ê, not e)." Under this reading, σ is the noise level applied to an
   observation. Commands involve no observation and no injected noise, so
   σ = 0 for every command row — an honest description of the experiment.

2. **σ as a design variable.** The simulation provenance lists "8 commands
   and 8 readings (2 per σ) per text" as a balanced design. Under this
   reading, commands occupy matched σ slots, and σ varies across both
   interfaces by construction.

Reading (1) is supported by the protocol's explicit language about injected
noise. Reading (2) is supported by the simulation note and by the frozen
analysis code's test suite, which supplies varying σ for both interfaces.
The simulation note alone does not settle it: "two per σ" may describe the
reading-noise conditions rather than a matched command assignment.

## Why resolution (c)

Three candidate handlings were considered (see STEP1-INTERPRETATION.md §1.5):

- **(a) Drop σ from the command-side model.** Requires amending frozen
  analysis code. Declined: the code is frozen and the amendment would change
  the estimand after data were seen.
- **(b) Reinterpret σ as a design variable and re-run.** Requires new API
  calls. Declined: no new calls authorized, and retroactively assigning
  design-slot σ values to already-collected command rows would be inventing
  data.
- **(c) Document the limitation; keep the gate blocked.** Selected.

Resolution (c) was chosen because it is the only option that neither alters
frozen artifacts nor fabricates the missing variation. The 3,700 collected
rows are preserved as recorded (command σ = 0.0 throughout). The frozen
analysis code is preserved unmodified. The jitter gate has no valid estimate
under the frozen model, and none is presented.

## What "blocked" means — and does not mean

- **Blocked** = the pre-registered comparison could not be estimated from the
  collected data under the frozen model (rank-deficient design matrix; see
  `step1_results.json`, `jitter_gate.status = "BLOCKED"`).
- **Not passed.** No gate result was computed.
- **Not failed.** No evidence about the jitter ratio was obtained.
- **Not statistically inconclusive.** "Inconclusive" would imply an estimate
  with a wide interval; here there is no estimate.

## Status of the ambiguity

Unresolved. A future protocol version may define σ unambiguously (as injected
noise with a σ-free command-side model, or as a design variable with commands
assigned to σ slots *before* data collection). Doing so would be a protocol
revision, subject to the project's amendment rules — not a reinterpretation
of v13.

---

**Record:** Step 2 on hold · analysis code frozen · jitter gate blocked ·
3,700 rows preserved · no new calls authorized.
