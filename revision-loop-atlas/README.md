# Revision-Loop Atlas

Do LLM correction trajectories pass through recurring, ordered dynamical states —
a "universal grammar of correction"? This directory holds the complete record of
the investigation, from instrument validation through scope-bound retirement.

**Verdict (2026-10-07):** the state hypothesis is retired for local Gemma 2B ×
GSM8K-style numeric math tasks × the neutral revision prompt × the frozen
exact-match/embedding measurement pipeline × the 9-round horizon. Total spend:
270 LLM calls.

## The story in order

1. `ATLAS-ONE-PAGER.md` — dense one-page brief of the whole arc.
2. `revision-loop-atlas-SPEC.md` — the full preregistered spec with dated entries.
3. `REVISION-STAGE0-REPORT.md` — synthetic validation FAIL: discontinuity bias.
4. `REVISION-STAGE01-REPORT.md` — re-validation FAIL: the SNR wall at n=9.
5. `REVISION-STAGE0-CPL-REPORT.md` — CPL instrument fix, still FAIL.
6. `REVISION-STAGE02-REPORT.md` — targeted pattern battery: B4 FAILS (curvature
   confound, 28.6% FPR, dropped); 4-detector battery validated (family-wise 6.7%).
7. `REVISION-STAGE1-REPORT.md` — 270-call pilot: INCONCLUSIVE, commentary confound
   discovered (27% of rounds are self-praise, scored as e≈0.9).
8. `REVISION-STAGE11-REPORT.md` — carry-forward reprocessing, zero new calls:
   Track A 6 (genuine solves) / B1 0 / B2 0 / B3 0. Bar 0 fires at 80%.
9. `REVISION-ATLAS-CLOSEOUT.md` — formal scope-bound retirement + the
   four-failure methodological ledger.

## Layout

- `code/` — frozen measurement (`revision_measure.py`), the three Stage-0
  instruments, the Stage-1 runner/analyzer, the Stage-1.1 carry-forward script.
- `results/` — machine-readable results JSONs for every stage.

The large raw trajectory file (`revision_loop_raw.jsonl`, 30×9 full texts) and the
per-round embedding dump are omitted for size; the corrected per-trajectory
measurements are in `results/revision_loop_results_11.json`.

Built mostly by AI, steered by Adrian (BTTMLSS). Failed bars are findings.
