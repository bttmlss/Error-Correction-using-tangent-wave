#!/usr/bin/env python3
"""
Exp 21 — Verifier-Driven Correction Learning
Follows ~/workspace/ai-theory/semantic-tangent-exp21-spec.md exactly.

Unblocked by Exp 20 (bar passed both halves). The escalation: can a
verifier/reward mechanism discover the history advantage itself?

Three players on the frozen Exp-20 substrate (4D only):
  1. Frozen reference/expert: Exp 20's tuned history PID per fold (from
     exp20_results.json), deterministic.
  2. PG-history learner: stochastic linear PID, REINFORCE + Adam on the
     verifier's minimal improvement reward. Init (0.1, 0, 0).
  3. PG-memoryless learner: same, but mu = alpha*ehat only.

The verifier reports only per-step improvement r_t = |ehat_{t-1}| - |ehat_t|
on the NOISY residual. The learner NEVER sees a correct dX (Exp-11 rule).

Substrate is OBSERVATIONAL ONLY (no model training, no touching weights).
"""

import json
import os
import sys
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent
(REPO_ROOT / "figures").mkdir(parents=True, exist_ok=True)

SMOKE = "--smoke" in sys.argv  # 1 fold, few epochs, no figures (bug-catch run)
SMOKE_EPOCHS = int(os.environ.get("SMOKE_EPOCHS", "6"))
EMBED_CACHE = (REPO_ROOT / "exp21_embed_cache.npz")

# ---------------------------------------------------------------- pinned config (substrate: Exp 20 verbatim)
SEED = 17911254
MODEL_DIR = os.environ.get("MODEL_DIR", "Qwen/Qwen2.5-0.5B-Instruct")
WORDMAP = (REPO_ROOT / "word_number_map.json")
EXP20_JSON = (REPO_ROOT / "exp20_results.json")
LAYER = 23
CARRIERS = [
    "The ___ sat on the table.",
    "I saw the ___ yesterday.",
    "She pointed at the ___.",
]
LADDER_DIMS = [1, 4, 16, 64]
EXP18_LADDER = {1: 0.591, 4: 0.827, 16: 0.975, 64: 1.000}
LADDER_TOL = 0.02
DIM = 4  # 4D only: the effect to be rediscovered lives in the top PCs

CHAINS = [
    ("size",        ["small", "medium", "large"]),
    ("temperature", ["cold", "warm", "hot"]),
    ("brightness",  ["dark", "dim", "bright"]),
    ("speed",       ["slow", "steady", "fast"]),
]

NOISE_FRAC = 0.05
K_SIGMA = 2.0
SETTLE_M = 3
MIN_STEPS = 5
TIMEOUT = 200

# ---------------------------------------------------------------- pinned config (PG learner — new in Exp 21)
N_EPOCHS = 200 if not SMOKE else SMOKE_EPOCHS
ADAM_LR = 0.03
ADAM_B1, ADAM_B2, ADAM_EPS = 0.9, 0.999, 1e-8
GAMMA_DISC = 0.99
EXPL_FRAC = 0.10      # sigma_pi = EXPL_FRAC * median|eps_0| / sqrt(d)
INIT_THETA = (0.1, 0.0, 0.0)  # (alpha, beta, gamma): starts with no damping

FIG_DIR = (REPO_ROOT / "figures")
JSON_OUT = (REPO_ROOT / "exp21_results.json")

# ---------------------------------------------------------------- utilities
def pearson_r(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    a = a - a.mean(); b = b - b.mean()
    return float((a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300))

def med_iqr(x):
    x = np.asarray(x, float)
    return float(np.median(x)), float(np.percentile(x, 25)), float(np.percentile(x, 75))

# ---------------------------------------------------------------- substrate (identical procedure to Exps 18/19/20)
def embed_words(tok, model, words):
    """Mean hidden state over the word's token span at LAYER, per carrier."""
    E = []
    for word in words:
        vecs = []
        for template in CARRIERS:
            sent = template.replace("___", word)
            start = sent.index(word)
            end = start + len(word)
            enc = tok(sent, return_tensors="pt", return_offsets_mapping=True)
            offsets = enc["offset_mapping"][0].tolist()
            idx = [i for i, (s, e) in enumerate(offsets) if e > start and s < end]
            assert idx, f"no tokens found for {word!r} in {sent!r}"
            ids = enc["input_ids"]
            with torch.no_grad():
                h = model(ids, output_hidden_states=True).hidden_states[LAYER + 1]
            vecs.append(h[0, idx, :].mean(dim=0).float().numpy())
        E.append(np.stack(vecs))
    return np.stack(E)  # (n_words, 3, 896)

# ---------------------------------------------------------------- PG rollout (stochastic policy, records everything)
def rollout(X0, T, theta, n_params, sigma_pi, noise, rng, tol_new):
    """One episode with the stochastic PID policy.
    Returns dict with per-step records for the REINFORCE update."""
    d = len(X0)
    X = X0.astype(np.float64).copy()
    ehat_prev = None
    dehat_prev = np.zeros(d)
    ehat_norm_prev = None
    rec_ehat_n = []
    rec_grads = []   # (n_params,) per step
    rec_rewards = []
    consec = 0
    settled_step = TIMEOUT
    path = 0.0
    for t in range(TIMEOUT):
        ehat = (T - X) + noise[t]
        ehat_n = float(np.linalg.norm(ehat))
        if t == 0:
            dehat = np.zeros(d); d2 = np.zeros(d)
        else:
            dehat = ehat - ehat_prev
            d2 = dehat - dehat_prev
        feats = [ehat, dehat, d2][:n_params]
        mu = sum(th * f for th, f in zip(theta, feats))
        a = mu + sigma_pi * rng.normal(size=d)
        # score-function gradients: (a-mu).feat / sigma_pi^2
        diff = a - mu
        rec_grads.append(np.array([float(diff @ f) / (sigma_pi ** 2) for f in feats]))
        X = X + a
        path += float(np.linalg.norm(a))
        r = 0.0 if t == 0 else (ehat_norm_prev - ehat_n)
        rec_rewards.append(r)
        rec_ehat_n.append(ehat_n)
        ehat_prev = ehat
        dehat_prev = dehat
        ehat_norm_prev = ehat_n
        if ehat_n < tol_new:
            consec += 1
            if consec >= SETTLE_M and t >= MIN_STEPS:
                settled_step = t + 1
                break
        else:
            consec = 0
    rec_rewards = np.array(rec_rewards)
    # discounted returns-to-go
    G = np.zeros_like(rec_rewards)
    acc = 0.0
    for t in range(len(rec_rewards) - 1, -1, -1):
        acc = rec_rewards[t] + GAMMA_DISC * acc
        G[t] = acc
    return {
        "grads": np.stack(rec_grads),           # (T, n_params)
        "G": G,                                 # (T,)
        "steps": settled_step,
        "settled": settled_step < TIMEOUT,
        "path": path,
        "efficiency": path / (float(np.linalg.norm(T - X0)) + 1e-300),
    }

# ---------------------------------------------------------------- deterministic eval (mean policy)
def det_eval(X0, T, theta, n_params, noise, tol_new):
    d = len(X0)
    X = X0.astype(np.float64).copy()
    ehat_prev = None
    dehat_prev = np.zeros(d)
    consec = 0
    settled_step = TIMEOUT
    path = 0.0
    for t in range(TIMEOUT):
        ehat = (T - X) + noise[t]
        ehat_n = float(np.linalg.norm(ehat))
        if t == 0:
            dehat = np.zeros(d); d2 = np.zeros(d)
        else:
            dehat = ehat - ehat_prev
            d2 = dehat - dehat_prev
        feats = [ehat, dehat, d2][:n_params]
        a = sum(th * f for th, f in zip(theta, feats))
        X = X + a
        path += float(np.linalg.norm(a))
        ehat_prev = ehat
        dehat_prev = dehat
        if ehat_n < tol_new:
            consec += 1
            if consec >= SETTLE_M and t >= MIN_STEPS:
                settled_step = t + 1
                break
        else:
            consec = 0
    return {"steps": settled_step, "settled": settled_step < TIMEOUT,
            "efficiency": path / (float(np.linalg.norm(T - X0)) + 1e-300)}

# ---------------------------------------------------------------- REINFORCE + Adam trainer
def train_learner(n_params, train, tune_noise, eval_held, held, tol_new, sigma_pi,
                  rng, label):
    """Batch REINFORCE: one epoch = one sweep over the 18 training trials.
    Returns final theta and the held-out learning curve (median steps)."""
    theta = np.array(INIT_THETA[:n_params], dtype=np.float64)
    m = np.zeros(n_params); v = np.zeros(n_params)
    n_upd = 0
    order_rng = np.random.default_rng(rng.integers(0, 2 ** 31))
    curve = []
    n_ep = len(train)
    for epoch in range(N_EPOCHS):
        order = order_rng.permutation(n_ep)
        g_acc = np.zeros(n_params)
        for j in order:
            tr = train[j]
            ep = rollout(tr["X0"], tr["T"], theta, n_params, sigma_pi,
                         tune_noise[j], rng, tol_new)
            b = float(ep["G"].mean()) if len(ep["G"]) else 0.0
            g_acc += (ep["grads"] * (ep["G"] - b)[:, None]).sum(axis=0)
        g_acc /= n_ep
        # Adam ascent step
        n_upd += 1
        m = ADAM_B1 * m + (1 - ADAM_B1) * g_acc
        v = ADAM_B2 * v + (1 - ADAM_B2) * g_acc ** 2
        mhat = m / (1 - ADAM_B1 ** n_upd)
        vhat = v / (1 - ADAM_B2 ** n_upd)
        theta = theta + ADAM_LR * mhat / (np.sqrt(vhat) + ADAM_EPS)
        if (epoch + 1) % 10 == 0 or epoch == 0:
            steps = [det_eval(tr["X0"], tr["T"], theta, n_params, nz, tol_new)["steps"]
                     for tr, nz in zip(held, eval_held)]
            curve.append((epoch + 1, float(np.median(steps))))
            if not SMOKE:
                print(f"    [{label}] epoch {epoch+1:>3}/{N_EPOCHS}: held-out median "
                      f"steps={curve[-1][1]:.1f} theta={[f'{x:+.3f}' for x in theta]}",
                      flush=True)
    if SMOKE:
        print(f"    [{label}] SMOKE final theta={[f'{x:+.3f}' for x in theta]}", flush=True)
    return theta, curve

# ---------------------------------------------------------------- main
def main():
    torch.manual_seed(SEED)
    with open(WORDMAP) as f:
        words = list(json.load(f)["words"].keys())
    assert len(words) == 24
    with open(EXP20_JSON) as f:
        exp20 = json.load(f)
    assert exp20["gate"] == "PASSED"

    print("Loading tokenizer + model (fp16, CPU, no_grad, observational only)...")
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float16)
    model.eval()

    chain_words = [w for _, ws in CHAINS for w in ws]
    if os.path.exists(EMBED_CACHE):
        print(f"Loading cached embeddings from {EMBED_CACHE} ...")
        cache = np.load(EMBED_CACHE)
        E_base, E_chain = cache["E_base"], cache["E_chain"]
        assert E_base.shape == (24, 3, 896) and E_chain.shape == (12, 3, 896)
    else:
        print("Embedding 24 base words x 3 carriers (Exp-18 rebuild)...")
        E_base = embed_words(tok, model, words)
        print(f"Embedding {len(chain_words)} chain words x 3 carriers (identical procedure)...")
        E_chain = embed_words(tok, model, chain_words)
        np.savez_compressed(EMBED_CACHE, E_base=E_base, E_chain=E_chain)
        print(f"Embeddings cached to {EMBED_CACHE}")

    X = E_base.reshape(-1, 896)
    mu = X.mean(axis=0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)

    iu = np.triu_indices(len(X), 1)
    d_full = np.array([np.linalg.norm(X[i] - X[j]) for i, j in zip(*iu)])
    Z = Xc @ Vt.T
    print("\n== VERIFICATION GATE: PCA ladder reproduction ==")
    gate_ok = True
    for d in LADDER_DIMS:
        Zd = Z[:, :d]
        d_proj = np.array([np.linalg.norm(Zd[i] - Zd[j]) for i, j in zip(*iu)])
        r = pearson_r(d_full, d_proj)
        drift = abs(r - EXP18_LADDER[d])
        ok = drift <= LADDER_TOL
        gate_ok = gate_ok and ok
        print(f"  dim {d:>2}: r = {r:+.4f}  (Exp18 {EXP18_LADDER[d]:+.4f}, drift {drift:.4f}) {'OK' if ok else 'DRIFT'}")
    if not gate_ok:
        print("\nGATE FAILED. Stopping.")
        return {"gate": "FAILED"}

    dim = DIM
    print(f"\n{'='*60}\n== Exp 21 at {dim}D ==\n{'='*60}")
    P = Vt[:dim].T
    Cd = ((E_chain - mu) @ P).mean(axis=1)
    cw = {w: Cd[i] for i, w in enumerate(chain_words)}

    trials = []
    for ci, (cname, ws) in enumerate(CHAINS):
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                X0, T = cw[ws[a]], cw[ws[b]]
                trials.append({"chain": ci, "cname": cname,
                               "pair": f"{ws[a]}->{ws[b]}", "X0": X0, "T": T,
                               "eps0": float(np.linalg.norm(T - X0))})
    assert len(trials) == 24
    sigma = NOISE_FRAC * float(np.median([t["eps0"] for t in trials]))
    tol_new = K_SIGMA * sigma * np.sqrt(dim)
    sigma_pi = EXPL_FRAC * float(np.median([t["eps0"] for t in trials])) / np.sqrt(dim)
    print(f"24 trials, median|eps_0|={np.median([t['eps0'] for t in trials]):.3f}, "
          f"sigma={sigma:.4f}, tol_new={tol_new:.4f}, sigma_pi={sigma_pi:.4f}")

    all_results = {"gate": "PASSED", "dim": dim, "folds": []}
    folds_to_run = [0] if SMOKE else range(4)

    for fold in folds_to_run:
        train = [t for t in trials if t["chain"] != fold]
        held = [t for t in trials if t["chain"] == fold]
        cname_held = CHAINS[fold][0]
        print(f"\n-- fold {fold}: held-out chain '{cname_held}' --")

        tune_rng = np.random.default_rng(SEED + 1000 + dim * 100 + fold)
        tune_noise = [tune_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in train]
        eval_rng = np.random.default_rng(SEED + 2000 + dim * 100 + fold)
        eval_noise_held = [eval_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in held]

        # frozen reference: Exp 20's tuned history PID for this fold
        p_ref = np.array(exp20["dims"]["4"]["folds"][fold]["p_hist"])
        ref_steps = [det_eval(tr["X0"], tr["T"], p_ref, 3, nz, tol_new)["steps"]
                     for tr, nz in zip(held, eval_noise_held)]
        print(f"  frozen reference (Exp20): theta={[f'{x:+.3f}' for x in p_ref]} "
              f"held-out median steps={np.median(ref_steps):.1f}")

        # PG learners (shared rng stream per fold, pinned)
        pg_rng = np.random.default_rng(SEED + 8000 + dim * 100 + fold)
        th_hist, curve_hist = train_learner(3, train, tune_noise, eval_noise_held,
                                           held, tol_new, sigma_pi, pg_rng, "pg-history")
        th_mem, curve_mem = train_learner(1, train, tune_noise, eval_noise_held,
                                          held, tol_new, sigma_pi, pg_rng, "pg-memoryless")

        def summ(theta, n_params):
            rs = [det_eval(tr["X0"], tr["T"], theta, n_params, nz, tol_new)
                  for tr, nz in zip(held, eval_noise_held)]
            med, q1, q3 = med_iqr([r["steps"] for r in rs])
            emed, _, _ = med_iqr([r["efficiency"] for r in rs])
            return {"steps_med": med, "steps_q1": q1, "steps_q3": q3,
                    "eff_med": emed,
                    "timeout_rate": float(np.mean([0.0 if r["settled"] else 1.0 for r in rs]))}

        fold_res = {
            "held_chain": cname_held,
            "p_ref": [float(v) for v in p_ref],
            "theta_hist": [float(v) for v in th_hist],
            "theta_mem": [float(v) for v in th_mem],
            "ref": summ(p_ref, 3),
            "pg_history": summ(th_hist, 3),
            "pg_memoryless": summ(th_mem, 1),
            "curve_hist": curve_hist,
            "curve_mem": curve_mem,
        }
        all_results["folds"].append(fold_res)
        print(f"  held-out: ref steps={fold_res['ref']['steps_med']:.1f} | "
              f"pg-history steps={fold_res['pg_history']['steps_med']:.1f} "
              f"theta={[f'{x:+.3f}' for x in th_hist]} | "
              f"pg-memoryless steps={fold_res['pg_memoryless']['steps_med']:.1f} "
              f"alpha={th_mem[0]:+.3f}")

    if SMOKE:
        print("\nSMOKE DONE.")
        return all_results

    # ---- pre-registered bar (4D, held-out)
    print("\n== PRE-REGISTERED BAR (4D, held-out) ==")
    wa, wb, wc = [], [], []
    for f, fr in enumerate(all_results["folds"]):
        h, m, r = (fr["pg_history"]["steps_med"], fr["pg_memoryless"]["steps_med"],
                   fr["ref"]["steps_med"])
        a = h < m
        b = abs(fr["theta_hist"][1]) > 0.05   # history-dependence discovered (sign reported separately)
        c = h <= 1.5 * r
        wa.append(a); wb.append(b); wc.append(c)
        print(f"  fold {f} ({fr['held_chain']:>11}): pg-hist {h:6.1f} vs pg-mem {m:6.1f} "
              f"-> {'WIN' if a else 'loss'} | |beta|={abs(fr['theta_hist'][1]):.3f} "
              f"(beta={fr['theta_hist'][1]:+.3f}) -> {'DISC' if b else 'not-disc'} | "
              f"pg-hist {h:.1f} <= 1.5x ref {r:.1f} -> {'OK' if c else 'miss'}")
    bar = all(wa) and all(wb) and all(wc)
    print(f"  BAR: {'PASSED' if bar else 'NOT PASSED'} "
          f"((a) hist<mem: {sum(wa)}/4, (b) |beta|>0.05: {sum(wb)}/4, (c) within 1.5x ref: {sum(wc)}/4)")
    all_results["bar"] = {"passed": bool(bar),
                          "wins_vs_pgmemoryless": [bool(x) for x in wa],
                          "beta_discovered": [bool(x) for x in wb],
                          "beta_signs": [1 if fr["theta_hist"][1] > 0 else -1 for fr in all_results["folds"]],
                          "within_1p5x_ref": [bool(x) for x in wc]}

    # ---- beta rediscovery table
    print("\n== BETA REDISCOVERY (learned from zero; sign = verifier's inductive bias) ==")
    for f, fr in enumerate(all_results["folds"]):
        th = fr["theta_hist"]
        print(f"  fold {f} ({fr['held_chain']:>11}): alpha={th[0]:+.3f} "
              f"beta={th[1]:+.3f} gamma={th[2]:+.3f} "
              f"(ref: {', '.join(f'{x:+.3f}' for x in fr['p_ref'])})")

    with open(JSON_OUT, "w") as f:
        json.dump(all_results, f, indent=1)
    print(f"\nJSON saved: {JSON_OUT}")

    # ---- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        folds = all_results["folds"]
        ops = ["ref", "pg_history", "pg_memoryless"]
        cols = ["tab:gray", "tab:green", "tab:blue"]
        labels = ["frozen ref (Exp20)", "PG history learner", "PG memoryless learner"]
        x = np.arange(4); w = 0.24

        fig, ax = plt.subplots(figsize=(9, 4.4))
        for j, op in enumerate(ops):
            meds = [f[op]["steps_med"] for f in folds]
            ax.bar(x + (j - 1) * w, meds, w, color=cols[j], label=labels[j])
        ax.set_xticks(x); ax.set_xticklabels([f["held_chain"] for f in folds])
        ax.set_ylabel("median steps to settle (held-out chain)")
        ax.set_title("Exp 21 (4D) — held-out steps: frozen reference vs PG learners")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp21_steps_4d.png", dpi=110); plt.close(fig)

        # learning curves
        fig, ax = plt.subplots(figsize=(9, 4.6))
        for f in folds:
            ep_h = [e for e, _ in f["curve_hist"]]; st_h = [s for _, s in f["curve_hist"]]
            ep_m = [e for e, _ in f["curve_mem"]]; st_m = [s for _, s in f["curve_mem"]]
            ax.plot(ep_h, st_h, color="tab:green", alpha=0.55)
            ax.plot(ep_m, st_m, color="tab:blue", alpha=0.55, ls="--")
        ax.plot([], [], color="tab:green", label="PG history learner")
        ax.plot([], [], color="tab:blue", ls="--", label="PG memoryless learner")
        ax.set_xlabel("epoch"); ax.set_ylabel("held-out median steps to settle")
        ax.set_title("Exp 21 (4D) — learning curves per fold (does history pull away?)")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp21_curves_4d.png", dpi=110); plt.close(fig)

        # learned thetas vs reference
        fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharey=False)
        xs = np.arange(4)
        for axi, (pi, pname, col) in zip(axes, [(0, "alpha", "tab:blue"),
                                               (1, "beta", "tab:orange"),
                                               (2, "gamma", "tab:red")]):
            pg = [f["theta_hist"][pi] for f in folds]
            rf = [f["p_ref"][pi] for f in folds]
            axi.bar(xs - 0.2, pg, 0.38, color=col, alpha=0.85, label="PG learned")
            axi.bar(xs + 0.2, rf, 0.38, color="tab:gray", alpha=0.85, label="frozen ref")
            axi.axhline(0, color="k", lw=0.8)
            axi.set_xticks(xs); axi.set_xticklabels([f["held_chain"] for f in folds],
                                                    rotation=20, ha="right")
            axi.set_ylabel(pname); axi.legend(fontsize=8)
        fig.suptitle("Exp 21 (4D) — learned (α,β,γ) vs frozen Exp-20 reference per fold\n"
                     "(did the learner discover history-dependence? sign = verifier bias)")
        fig.tight_layout(); fig.savefig(f"{FIG_DIR}/exp21_thetas_4d.png", dpi=110); plt.close(fig)
        print("Figures saved: exp21_steps_4d.png, exp21_curves_4d.png, exp21_thetas_4d.png")
    except Exception as e:
        print(f"\n(figure generation skipped: {e})")

    return all_results


if __name__ == "__main__":
    res = main()
    print("\nDONE. gate =", res.get("gate"), "| bar =", res.get("bar", {}).get("passed"))
