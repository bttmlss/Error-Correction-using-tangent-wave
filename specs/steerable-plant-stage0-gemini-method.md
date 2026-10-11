# The Steerable Plant — Stage 0 Word-Count Actuator Ladder Method Specification

**Document Date:** 2026-10-10  
**Status:** APPROVED METHOD SPECIFICATION / EXECUTION PROTOCOL  
**Substrate:** Gemini (Task Mode / Agent Environment)  
**Design Authority & Authorizations:**
- Adrian's Directive via Agent A (Muse), 2026-10-10 (`gemini_stage0_ladder_directive.md`)
- Parent Spec: `STEERABLE-PLANT-STAGE0-SPEC.md` (Locked 2026-10-07, Commit `7719623e0e542600ea062fc7fbe0fb0415c081da`)
- Pre-requisite Floor Probe: `STEERABLE-PLANT-GEMINI-STAGE0-SPEC.md` (Word count SD = 1.44 <= 10 -> PASS; Readability SD = 11.87 > 6.7 -> FAIL)

---

## 1. Objective & Scope

This specification establishes the exact experimental method for executing the **Stage 0 Word-Count Actuator Dose-Response Ladder** on the Gemini substrate. The objective of this stage is to measure whether a commanded step $u$ (in absolute words) acts as a physical, resolvable control input to the LLM revision loop at $\sigma = 0$, or whether the response is insensitive to command magnitude.

Per the accepted Bar (b) floor-probe ruling and Amendment 21 of the locked spec:
- Word-count targeting noise floor is pinned at **$\sigma_0 = 1.44$ words**.
- Readability targeting failed Bar (b) ($SD = 11.87 > 6.7$) and is strictly excluded from this run.
- The actuator ladder is evaluated across 320 calls (8 levels $\times$ 20 trials $\times$ 2 prompt templates).

---

## 2. Experimental Design & Factorial Structure

### 2.1 The Actuator Ladder Levels
The ladder evaluates 8 signed command levels in absolute word count units:
$$u \in \{-60, -40, -20, -10, +10, +20, +40, +60\} \text{ words}$$

- **Contraction Sub-Ladder ($u < 0$):** Commands $\{-10, -20, -40, -60\}$ words.
- **Expansion Sub-Ladder ($u > 0$):** Commands $\{+10, +20, +40, +60\}$ words.

### 2.2 Corrective-Side Starts & Sign-Confound Isolation
Per Amendment 22 of the locked spec, testing command compliance from a defiant state (e.g., commanding lengthening while 60 words over target) tests defiance rather than plant steerability. To guarantee that every command is evaluated in its natural corrective context:
- **For all $u < 0$ (Contraction):**
  - Source text length: **exactly 140 words** (verified via `count_words`).
  - Target length: $W^* = 80$ words.
  - Initial error offset: $e_0 = W^* - W_{\text{start}} = 80 - 140 = -60$ words.
  - Stated residual: `The verifier measures you at 60 words over target.`
- **For all $u > 0$ (Expansion):**
  - Source text length: **exactly 40 words** (verified via `count_words`).
  - Target length: $W^* = 80$ words.
  - Initial error offset: $e_0 = W^* - W_{\text{start}} = 80 - 40 = +40$ words.
  - Stated residual: `The verifier measures you at 40 words under target.`

At $\sigma = 0$, the stated residual is truthful.

### 2.3 Starting Text Operationalization (Documented Implementation Choice)
The 10 source texts from the Stage 0 bank (Texts 0–9) were expanded to exactly 140 words and contracted to exactly 40 words using in-domain narrative completions, verified strictly against the regular-expression word counter:
$$\text{count\_words}(s) := \text{len}(\text{re.findall}(r"[A-Za-z0-9']+", s))$$
All 20 starting texts were verified to achieve $W = 140$ and $W = 40$ with zero deviation.

---

## 3. Prompt Skeleton & Template Pairing

### 3.1 Prompt Skeleton
Every call uses the exact invariant skeleton:

```text
Revise the text below to be exactly 80 words long.

Text:
{src}

Target: 80 words.
The verifier measures you at {residual}.
{command}
```

### 3.2 Command Templates
- **Template $T_1$ (Canonical Controller Template):**
  `Change the length of your response by {u} words.`  
  *(where $u$ is signed, e.g., `by -20 words` or `by +20 words`)*
- **Template $T_2$ (Alternative Equivalence Template):**
  - For $u < 0$: `Make your response {abs(u)} words shorter.`
  - For $u > 0$: `Make your response {abs(u)} words longer.`

### 3.3 Strict Pairing Scheme
To support the downstream Bar (c) paired-cluster bootstrap, every trial $t \in \{0, \dots, 19\}$ is strictly paired across templates:
- For each combination of level $u$ and trial $t$:
  - The source text is identical: $\text{text\_id} = t \pmod{10}$.
  - The sampling temperature is identical: $T = \{0.3, 0.7, 1.0\}[t \pmod 3]$.
  - $T_1$ and $T_2$ are executed on the identical starting text at that exact temperature.

---

## 4. Execution Protocol & Ledger Output

### 4.1 Call Budget
- 8 command levels $\times$ 20 trials $\times$ 2 templates = **320 LLM calls**.
- Output generation capped at ~400 tokens per call.
- Documented deviation: Unseeded execution (Gemini API does not support integer seed pinning).

### 4.2 Data Ledger Schema
Per Section 6 of the directive, the execution generates a comprehensive 320-row ledger recording the following fields for each call:
1. `u`: Commanded step (integer, signed words)
2. `trial_t`: Trial index ($0 \dots 19$)
3. `template`: Template identifier (`T1` or `T2`)
4. `temperature`: Sampling temperature ($0.3, 0.7, 1.0$)
5. `text_id`: Source text index ($0 \dots 9$)
6. `starting_words`: Verified word count of prompt text ($140$ or $40$)
7. `realized_words`: Measured word count of generated response ($W$)
8. `realized_step`: Realized step $\Delta W = \text{realized\_words} - \text{starting\_words}$

### 4.3 Downstream Gating (Bar Evaluation)
Per Section 6 of the directive, this ledger is output in full without inline bar adjudication. Downstream evaluation of Bar (a) (direction $\rho \ge 0.70$, shuffled-u null, gain band $\beta_{\text{TS}} \in [0.5, 1.5]$, saturation check) and Bar (c) (paired-cluster bootstrap CI $\subseteq [-0.10, +0.10]$) will be performed against the locked specification.

---

## 5. Summary of Implementation Constraints
- Do NOT reword the prompts, texts, or templates.
- Do NOT run a readability ladder.
- Do NOT mix Gemini results with Gemma-2B data.
- Output the complete 320-row ledger to the specification document upon run completion.
