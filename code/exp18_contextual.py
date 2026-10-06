#!/usr/bin/env python3
"""
Exp 18 — contextual hidden-state substrate (OBSERVATIONAL ONLY).

Follows ~/workspace/ai-theory/contextual-substrate-spec.md exactly.
No model training, no reward modification, no touching model weights.

The models under test are "volunteers", never "specimens".

Pipeline:
  Condition 1 (gate): PCA ladder on 72 contextual vectors (24 words x 3 carriers),
      Pearson r between 896-D pairwise distances and projected pairwise
      distances at dims {1, 4, 16, 64}. Predictor is built ONLY on the smallest
      dim with r >= 0.70. If none passes -> stop, no predictor.
  Condition 2 (validity): counting control "one".."twenty-four". Predictor must
      beat the naive running-mean baseline, else the instrument is invalid.
  Condition 3 (pre-registered test): related vs shuffled word order, 60 sequences
      per condition. Success = related error < shuffled, permutation p < 0.05,
      AND predictor beats naive baseline.
"""

import json
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import os
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent
(REPO_ROOT / "figures").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- pinned config
SEED = 17911254            # master seed (same as Exp 16 projection seed)
MODEL_DIR = os.environ.get("MODEL_DIR", "Qwen/Qwen2.5-0.5B-Instruct")
WORDMAP = (REPO_ROOT / "word_number_map.json")
LAYER = 23                # final layer per spec
N_CARRIERS = 3
CARRIERS = [
    "The ___ sat on the table.",
    "I saw the ___ yesterday.",
    "She pointed at the ___.",
]
DIMS = [1, 4, 16, 64]
GATE_R = 0.70
K = 3                     # predictor looks back K vectors
RIDGE_LAM = 1.0
N_SEQ = 60                # >= 50 sequences per condition (pre-registered)
N_TRAIN = 40
N_PERM = 10000

NUMBER_WORDS = [
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "twenty-one", "twenty-two",
    "twenty-three", "twenty-four",
]

# Related order: semantic chains (synonyms / related concepts adjacent).
RELATED_ORDER = [
    "stone", "rock", "mountain",        # hard earth
    "river", "stream", "water", "rain",  # water
    "tree",                              # growing thing
    "house", "home",                     # shelter
    "dog", "puppy",                      # animal
    "fire", "flame",                     # fire
    "love", "adore",                     # affection
    "journey", "freedom", "justice", "truth", "time", "key", "mirror", "bridge",
]

# ---------------------------------------------------------------- utilities
def pearson_r(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    a = a - a.mean(); b = b - b.mean()
    return float((a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300))

def ridge_fit(X, Y, lam=RIDGE_LAM):
    A = X.T @ X + lam * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ Y)

def permutation_p(a, b, n_perm=N_PERM, seed=SEED + 7):
    """One-sided: is mean(a) < mean(b)? Returns (p, observed_diff)."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    obs = a.mean() - b.mean()
    pooled = np.concatenate([a, b]); n = len(a)
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_perm):
        p = rng.permutation(pooled)
        if p[:n].mean() - p[n:].mean() <= obs:
            cnt += 1
    return (cnt + 1) / (n_perm + 1), float(obs)

# ---------------------------------------------------------------- main
def main():
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)

    with open(WORDMAP) as f:
        words = list(json.load(f)["words"].keys())
    assert len(words) == 24, f"expected 24 words, got {len(words)}"
    assert set(RELATED_ORDER) == set(words), "RELATED_ORDER must be a permutation of the 24 words"
    assert len(NUMBER_WORDS) == 24

    print("Loading tokenizer + model (fp16, CPU, no_grad, observational only)...")
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float16)
    model.eval()

    def embed_word(word):
        """Mean hidden state over the word's token positions at LAYER, per carrier."""
        vecs = []
        for template in CARRIERS:
            sent = template.replace("___", word)
            start = sent.index(word)
            end = start + len(word)
            enc = tok(sent, return_tensors="pt", return_offsets_mapping=True)
            offsets = enc["offset_mapping"][0].tolist()
            # BPE merges the leading space into the word token (e.g. "Ġstone"
            # has offsets (3,9)), so select tokens by OVERLAP with the word's
            # char span, not containment. Zero-width special tokens (0,0) are
            # excluded by e > start.
            idx = [i for i, (s, e) in enumerate(offsets) if e > start and s < end]
            assert idx, f"no tokens found for {word!r} in {sent!r}"
            ids = enc["input_ids"]
            with torch.no_grad():
                h = model(ids, output_hidden_states=True).hidden_states[LAYER + 1]
            vecs.append(h[0, idx, :].mean(dim=0).float().numpy())
        return np.stack(vecs)  # (3, 896)

    print("Embedding 24 experiment words x 3 carriers...")
    E_words = np.stack([embed_word(w) for w in words])          # (24, 3, 896)
    print("Embedding 24 number words x 3 carriers (positive control)...")
    E_nums = np.stack([embed_word(w) for w in NUMBER_WORDS])    # (24, 3, 896)
    assert E_words.shape == (24, 3, 896)

    # ------------------------------------------------- Condition 1: PCA ladder
    X = E_words.reshape(-1, 896)                                 # (72, 896)
    mu = X.mean(axis=0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    Z = Xc @ Vt.T                                                # PC scores

    # pairwise distances in 896-D
    from numpy.linalg import norm
    iu = np.triu_indices(len(X), 1)
    d_full = np.array([norm(X[i] - X[j]) for i, j in zip(*iu)])

    ladder = {}
    for d in DIMS:
        Zd = Z[:, :d]
        d_proj = np.array([norm(Zd[i] - Zd[j]) for i, j in zip(*iu)])
        ladder[d] = pearson_r(d_full, d_proj)

    print("\n== Condition 1: PCA distance-preservation ladder ==")
    for d in DIMS:
        flag = "  <-- GATE" if ladder[d] >= GATE_R else ""
        print(f"  dim {d:>2}: r = {ladder[d]:+.4f}{flag}")

    pass_dims = [d for d in DIMS if ladder[d] >= GATE_R]
    if not pass_dims:
        print("\nGATE FAILED: no dimension reaches r >= 0.70. Stopping — no predictor, no prediction test.")
        return {"ladder": ladder, "gate_dim": None}
    d_gate = min(pass_dims)
    print(f"\nGATE PASSED at dim {d_gate} (r = {ladder[d_gate]:+.4f}). Predictor built at dim {d_gate} only.")

    # project everything to the gated dim (PCA fitted on the 72 word vectors only)
    P = Vt[:d_gate].T  # (896, d_gate)
    def proj(E):
        return (E - mu) @ P
    Pw = proj(E_words)   # (24, 3, d)
    Pn = proj(E_nums)    # (24, 3, d)

    # ------------------------------------------------- predictor machinery
    def seq_features(seq):
        """seq: (T, d) -> (X, Y, t_idx): predict next from previous K."""
        T = seq.shape[0]
        Xs = np.stack([seq[t - K:t].reshape(-1) for t in range(K, T)])
        Ys = seq[K:]
        return Xs, Ys

    def naive_errors(seq):
        """Running-mean baseline: predict running mean of all previous vectors."""
        T = seq.shape[0]
        errs = []
        run = seq[0].copy()
        for t in range(1, T):
            if t >= K:
                errs.append(float(np.mean((run - seq[t]) ** 2)))
            run = run + (seq[t] - run) / (t + 1)
        return errs

    def run_condition(seqs):
        """Fit ridge on N_TRAIN seqs, evaluate on the rest. Returns per-seq test errors
        for predictor and naive baseline."""
        tr, te = seqs[:N_TRAIN], seqs[N_TRAIN:]
        Xtr = np.concatenate([seq_features(s)[0] for s in tr])
        Ytr = np.concatenate([seq_features(s)[1] for s in tr])
        W = ridge_fit(Xtr, Ytr)
        pred_errs, naive_errs = [], []
        for s in te:
            Xs, Ys = seq_features(s)
            pred = Xs @ W
            pred_errs.append(float(np.mean((pred - Ys) ** 2)))
            ne = naive_errors(s)
            naive_errs.append(float(np.mean(ne)))
        return np.array(pred_errs), np.array(naive_errs)

    # ------------------------------------------------- Condition 2: positive control
    print("\n== Condition 2: positive control (counting sequence) ==")
    order = np.arange(24)
    ctrl_seqs = []
    for _ in range(N_SEQ):
        picks = rng.integers(0, N_CARRIERS, size=24)
        ctrl_seqs.append(np.stack([Pn[i, picks[i]] for i in order]))
    c_pred, c_naive = run_condition(ctrl_seqs)
    print(f"  predictor mean MSE: {c_pred.mean():.6f}  |  naive mean MSE: {c_naive.mean():.6f}")
    ctrl_pass = c_pred.mean() < c_naive.mean()
    print(f"  predictor beats naive: {ctrl_pass}")
    if not ctrl_pass:
        print("\nVALIDITY FAILED: predictor cannot beat naive on the counting control.")
        print("The prediction test is an invalid instrument — stopping, no semantic claim made.")
        return {"ladder": ladder, "gate_dim": d_gate,
                "control": (float(c_pred.mean()), float(c_naive.mean()), False)}

    # ------------------------------------------------- Condition 3: related vs shuffled
    print("\n== Condition 3: related vs shuffled ==")
    widx = {w: i for i, w in enumerate(words)}
    rel_order = [widx[w] for w in RELATED_ORDER]
    rel_seqs, shuf_seqs = [], []
    for _ in range(N_SEQ):
        picks = rng.integers(0, N_CARRIERS, size=24)
        base = np.stack([Pw[rel_order[i], picks[i]] for i in range(24)])
        rel_seqs.append(base)
        shuf_seqs.append(base[rng.permutation(24)])
    r_pred, r_naive = run_condition(rel_seqs)
    s_pred, s_naive = run_condition(shuf_seqs)
    p_val, diff = permutation_p(r_pred, s_pred)
    beats_naive = r_pred.mean() < r_naive.mean()
    success = (r_pred.mean() < s_pred.mean()) and (p_val < 0.05) and beats_naive

    print(f"  related:   predictor {r_pred.mean():.6f} | naive {r_naive.mean():.6f}")
    print(f"  shuffled:  predictor {s_pred.mean():.6f} | naive {s_naive.mean():.6f}")
    print(f"  related < shuffled: {r_pred.mean() < s_pred.mean()} | permutation p = {p_val:.4f} | beats naive: {beats_naive}")
    print(f"  PRE-REGISTERED SUCCESS BAR: {'PASSED' if success else 'NOT PASSED'}")

    # ------------------------------------------------- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.2))
        xs = [str(d) for d in DIMS]
        rs = [ladder[d] for d in DIMS]
        bars = ax.bar(xs, rs, color=["tab:green" if r >= GATE_R else "tab:red" for r in rs])
        ax.axhline(GATE_R, ls="--", color="k", label="gate r = 0.70")
        ax.set_ylim(0, 1.02)
        ax.set_xlabel("PCA dimensions")
        ax.set_ylabel("Pearson r (896-D vs projected pairwise distances)")
        ax.set_title("Exp 18 — Condition 1: PCA distance-preservation ladder\n(contextual hidden states, layer 23, 72 vectors)")
        for b, r in zip(bars, rs):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{r:.3f}", ha="center", fontsize=10)
        ax.legend()
        fig.tight_layout()
        fig.savefig((REPO_ROOT / "figures/exp18_pca_ladder.png"), dpi=110)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
        axes[0].bar(["predictor", "naive"], [c_pred.mean(), c_naive.mean()], color=["tab:blue", "tab:gray"])
        axes[0].set_title("Condition 2: positive control (counting)")
        axes[0].set_ylabel("mean MSE on held-out sequences")
        axes[1].bar(["related\npredictor", "related\nnaive", "shuffled\npredictor", "shuffled\nnaive"],
                    [r_pred.mean(), r_naive.mean(), s_pred.mean(), s_naive.mean()],
                    color=["tab:blue", "tab:gray", "tab:orange", "tab:gray"])
        axes[1].set_title(f"Condition 3: related vs shuffled (p={p_val:.4f})")
        axes[1].set_ylabel("mean MSE on held-out sequences")
        fig.suptitle("Exp 18 — instrument validity and prediction test")
        fig.tight_layout()
        fig.savefig((REPO_ROOT / "figures/exp18_prediction.png"), dpi=110)
        plt.close(fig)
        print("\nFigures saved to figures/exp18_pca_ladder.png and figures/exp18_prediction.png")
    except Exception as e:
        print(f"\n(figure generation skipped: {e})")

    return {"ladder": ladder, "gate_dim": d_gate,
            "control": (float(c_pred.mean()), float(c_naive.mean()), True),
            "related": (float(r_pred.mean()), float(r_naive.mean())),
            "shuffled": (float(s_pred.mean()), float(s_naive.mean())),
            "p": float(p_val), "success": bool(success)}


if __name__ == "__main__":
    res = main()
    print("\nRESULT:", json.dumps({k: (v if not isinstance(v, dict) else {str(kk): vv for kk, vv in v.items()})
                                  for k, v in res.items()}, indent=2))
