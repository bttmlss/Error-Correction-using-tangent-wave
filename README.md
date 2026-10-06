# Verifier Shape Selects the Correction Law

**BTTMLSS** — independent research, October 2026.

Can a verifier-driven learner discover steerable correction dynamics inside a
real language model's frozen representation geometry — and *which* dynamics
does it discover? This repo contains the full six-experiment program and the
paper draft. The headline result: **the verifier's reward shape selects which
correction law the learner discovers** — identical substrate, identical
learner, identical optimizer; four verifier shapes produce four
distinguishable dynamical regimes. The learner is the arrow; the verifier is
the pointer.

- **Exp 18** — Contextual hidden states (Qwen2.5-0.5B-Instruct, layer 23) +
  PCA give a geometric world where word order is predictable (related beats
  shuffled, p = 0.0001). The substrate the rest stands on.
- **Exp 19** — A history-aware (PID/tangent) correction operator settles
  faster than direct correction on all held-out chains, but walks messier
  paths. Speed ≠ cleanliness: the split is the finding.
- **Exp 20** — Real residual history beats both memoryless and
  permuted-history controls on all folds (temporal structure, not extra
  parameters). The history term is consistently damping (β < 0, 4/4 folds).
- **Exp 21** — A REINFORCE learner discovers history-dependence from the
  verifier's bare "did the error shrink?" reward — but learns a *reactive*
  (positive-β) law, not damping. The verifier selects the law.
- **Exp 22** — The controlled map, learner and substrate frozen, verifier
  varied: improvement-only → underdetermined (reactive/damping/degenerate by
  seed); −overshoot → damping 4/4; −path-cost → aggressive α ≈ 0.75;
  −action-smoothing → the tightest damping cluster, cleanest paths.
- **Exp 23** — The smoothness-induced law transfers: frozen, zero retraining,
  it steers unseen words, unseen pairings, and unseen trajectory scales with
  low overshoot and zero timeouts — while minimal-verifier laws transfer
  unreliably (one mild law fine, one degenerate law catastrophic).

## Reproduce everything

```bash
pip install -r requirements.txt
bash run_all.sh
```

The first run downloads Qwen2.5-0.5B-Instruct from HuggingFace (~1 GB). To
use local weights instead: `MODEL_DIR=/path/to/weights bash run_all.sh`.
Expect roughly 30–60 minutes on a modern CPU machine (no GPU needed). All
figures regenerate into `code/figures/`; per-experiment results land in
`code/exp*_results.json`. Every seed is pinned in-file.

CPU-only PyTorch keeps it light: `pip install torch --index-url
https://download.pytorch.org/whl/cpu` before the rest if you want to skip
the CUDA build.

## Layout

- `code/` — the six experiment scripts (`exp18_contextual.py` … `exp23_generalization.py`), run in order; each rebuilds what it needs from the previous step's outputs. The volunteer model is **observational only**: we read hidden states, never train the model, never touch weights.
- `paper/paper.md` — the paper draft (Abstract → Experiments 18–23 → Limitations → Conclusion).
- `specs/` — the pinned per-experiment specifications the whole program was built against.
- `code/figures/` — regenerated figures, including the Exp-22 verifier-selection map.

## Honest limits (read before citing)

- Linear PID policy class throughout: every "law" is a point in (α, β, γ)-space.
- 4D PCA only; one volunteer model, one layer, four hand-picked semantic chains.
- Pinned seeds (one per fold); penalty scales pinned a priori, not tuned.
- No induced law is "the correct law" — each is named by what induced it, because each is a valid maximizer of what its verifier asked for.
- Toy scale throughout. A strong result here establishes that verifier shape reliably sculpts learned correction dynamics *in this setup* — not "intelligence," not a general claim about training.

## License

MIT — see `LICENSE`.
