#!/usr/bin/env python3
"""
Exp 22 — Verifier Selection
Follows ~/workspace/ai-theory/semantic-tangent-exp22-spec.md exactly.

Directive from Adrian (2026-10-05): freeze the learner and substrate, vary
ONLY the verifier, and map verifier shape -> learned correction dynamics.
Four verifiers (V1..V4), same REINFORCE+Adam learner, same substrate/folds.

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
JSON_OUT = (REPO_ROOT / "exp22_results.json")

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

# ---------------------------------------------------------------- PG rollout (stochastic policy, records raw per-step data)
# The reward is computed AFTER the rollout by rewards_from_raw(), so the
# verifier shape is the clean independent variable (Exp 22).
def rollout_raw(X0, T, theta, n_params, sigma_pi, noise, rng, tol_new):
    """One episode with the stochastic PID policy. Records raw per-step data;
    the verifier maps it to rewards separately."""
    d = len(X0)
    X = X0.astype(np.float64).copy()
    n0 = float(np.linalg.norm(T - X0))
    ehat_prev = None
    dehat_prev = np.zeros(d)
    rec_grads = []   # (n_params,) per step
    rec_ehat_n = []  # noisy residual norm (the verifier's measurement)
    rec_etrue_n = [] # true residual norm (for penalty terms)
    rec_dX = []      # action vectors (for path/stability penalties)
    overshoot = 0
    etrue_prev = n0
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
        etrue_n = float(np.linalg.norm(T - X))
        if etrue_n > etrue_prev and etrue_prev < n0:
            overshoot += 1
        etrue_prev = etrue_n
        rec_ehat_n.append(ehat_n)
        rec_etrue_n.append(etrue_n)
        rec_dX.append(a.copy())
        ehat_prev = ehat
        dehat_prev = dehat
        if ehat_n < tol_new:
            consec += 1
            if consec >= SETTLE_M and t >= MIN_STEPS:
                settled_step = t + 1
                break
        else:
            consec = 0
    return {
        "grads": np.stack(rec_grads),                 # (T, n_params)
        "ehat_n": np.array(rec_ehat_n),               # (T,)
        "etrue_n": np.array(rec_etrue_n),             # (T,)
        "dX": np.stack(rec_dX),                       # (T, d)
        "steps": settled_step,
        "settled": settled_step < TIMEOUT,
        "path": path,
        "overshoot": overshoot,
        "efficiency": path / (n0 + 1e-300),
        "n0": n0,
    }

# ---------------------------------------------------------------- verifiers (the independent variable — pinned)
# V1: improvement only | V2: - overshoot | V3: - path cost | V4: - action jerk
LAM_OV = 5.0    # overshoot penalty per step (Exp-20 precedent)
MU_PC = 20.0    # path-cost penalty scale (Exp-20 precedent)
LAM_ST = 10.0   # stability (action-smoothing) penalty scale
VERIFIERS = ["V1", "V2", "V3", "V4"]
VERIFIER_DESC = {
    "V1": "improvement only",
    "V2": "improvement - overshoot penalty",
    "V3": "improvement - path-cost penalty",
    "V4": "improvement - stability (action-smoothing) penalty",
}

def rewards_from_raw(raw, vkey, med_eps0):
    """Map a rollout's raw per-step data to the verifier's reward signal,
    then to discounted returns-to-go. This is the ONLY thing that varies
    across verifiers in Exp 22."""
    ehat_n = raw["ehat_n"]; etrue_n = raw["etrue_n"]; dX = raw["dX"]; n0 = raw["n0"]
    T = len(ehat_n)
    r = np.zeros(T)
    for t in range(1, T):
        imp = ehat_n[t - 1] - ehat_n[t]                      # verifier's measurement
        ov = 1.0 if (etrue_n[t] > etrue_n[t - 1] and etrue_n[t - 1] < n0) else 0.0
        pc = float(np.linalg.norm(dX[t])) / med_eps0
        st = float(np.linalg.norm(dX[t] - dX[t - 1])) / med_eps0 if t >= 2 else 0.0
        if vkey == "V1":
            r[t] = imp
        elif vkey == "V2":
            r[t] = imp - LAM_OV * ov
        elif vkey == "V3":
            r[t] = imp - MU_PC * pc
        elif vkey == "V4":
            r[t] = imp - LAM_ST * st
        else:
            raise ValueError(vkey)
    G = np.zeros(T)
    acc = 0.0
    for t in range(T - 1, -1, -1):
        acc = r[t] + GAMMA_DISC * acc
        G[t] = acc
    return G

# ---------------------------------------------------------------- deterministic eval (mean policy)
def det_eval(X0, T, theta, n_params, noise, tol_new):
    d = len(X0)
    X = X0.astype(np.float64).copy()
    n0 = float(np.linalg.norm(T - X0))
    ehat_prev = None
    dehat_prev = np.zeros(d)
    consec = 0
    settled_step = TIMEOUT
    path = 0.0
    overshoot = 0
    etrue_prev = n0
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
        etrue_n = float(np.linalg.norm(T - X))
        if etrue_n > etrue_prev and etrue_prev < n0:
            overshoot += 1
        etrue_prev = etrue_n
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
            "efficiency": path / (n0 + 1e-300), "overshoot": overshoot}

# ---------------------------------------------------------------- REINFORCE + Adam trainer
def train_learner(n_params, train, tune_noise, eval_held, held, tol_new, sigma_pi,
                  rng, label, vkey, med_eps0):
    """Batch REINFORCE: one epoch = one sweep over the 18 training trials.
    The verifier (vkey) is the only independent variable. Returns final theta
    and the held-out learning curve (median steps)."""
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
            raw = rollout_raw(tr["X0"], tr["T"], theta, n_params, sigma_pi,
                              tune_noise[j], rng, tol_new)
            G = rewards_from_raw(raw, vkey, med_eps0)
            b = float(G.mean()) if len(G) else 0.0
            g_acc += (raw["grads"] * (G - b)[:, None]).sum(axis=0)
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
    print(f"\n{'='*60}\n== Exp 22 at {dim}D: verifier selection ==\n{'='*60}")
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
    med_eps0 = float(np.median([t["eps0"] for t in trials]))
    sigma = NOISE_FRAC * med_eps0
    tol_new = K_SIGMA * sigma * np.sqrt(dim)
    sigma_pi = EXPL_FRAC * med_eps0 / np.sqrt(dim)
    print(f"24 trials, median|eps_0|={med_eps0:.3f}, sigma={sigma:.4f}, "
          f"tol_new={tol_new:.4f}, sigma_pi={sigma_pi:.4f}")
    print("Verifiers: " + "; ".join(f"{k} ({v})" for k, v in VERIFIER_DESC.items()))

    all_results = {"gate": "PASSED", "dim": dim, "verifiers": {},
                   "penalties": {"LAM_OV": LAM_OV, "MU_PC": MU_PC, "LAM_ST": LAM_ST}}
    verifiers_to_run = ["V1"] if SMOKE else VERIFIERS
    folds_to_run = [0] if SMOKE else range(4)

    for vkey in verifiers_to_run:
        print(f"\n{'#'*60}\n## Verifier {vkey}: {VERIFIER_DESC[vkey]}\n{'#'*60}")
        v_res = {"desc": VERIFIER_DESC[vkey], "folds": []}
        vi = VERIFIERS.index(vkey)
        for fold in folds_to_run:
            train = [t for t in trials if t["chain"] != fold]
            held = [t for t in trials if t["chain"] == fold]
            cname_held = CHAINS[fold][0]
            print(f"\n-- {vkey} fold {fold}: held-out '{cname_held}' --")

            tune_rng = np.random.default_rng(SEED + 1000 + dim * 100 + fold)
            tune_noise = [tune_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in train]
            eval_rng = np.random.default_rng(SEED + 2000 + dim * 100 + fold)
            eval_noise_held = [eval_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in held]

            p_ref = np.array(exp20["dims"]["4"]["folds"][fold]["p_hist"])

            # per-(verifier, fold) pinned rng stream: verifier offset keeps
            # streams distinct across verifiers, identical across folds
            pg_rng = np.random.default_rng(SEED + 8000 + dim * 100 + fold * 10 + vi)
            th_hist, _ = train_learner(3, train, tune_noise, eval_noise_held,
                                       held, tol_new, sigma_pi, pg_rng,
                                       f"{vkey}-pg-history", vkey, med_eps0)
            th_mem, _ = train_learner(1, train, tune_noise, eval_noise_held,
                                      held, tol_new, sigma_pi, pg_rng,
                                      f"{vkey}-pg-memoryless", vkey, med_eps0)

            def fingerprint(theta, n_params):
                rs = [det_eval(tr["X0"], tr["T"], theta, n_params, nz, tol_new)
                      for tr, nz in zip(held, eval_noise_held)]
                med, q1, q3 = med_iqr([r["steps"] for r in rs])
                emed, _, _ = med_iqr([r["efficiency"] for r in rs])
                return {
                    "steps_med": med, "steps_q1": q1, "steps_q3": q3,
                    "eff_med": emed,
                    "overshoot_mean": float(np.mean([r["overshoot"] for r in rs])),
                    "timeout_rate": float(np.mean([0.0 if r["settled"] else 1.0 for r in rs])),
                }

            fold_res = {
                "held_chain": cname_held,
                "p_ref": [float(v) for v in p_ref],
                "theta_hist": [float(v) for v in th_hist],
                "theta_mem": [float(v) for v in th_mem],
                "ref": fingerprint(p_ref, 3),
                "pg_history": fingerprint(th_hist, 3),
                "pg_memoryless": fingerprint(th_mem, 1),
            }
            v_res["folds"].append(fold_res)
            print(f"  held-out: ref steps={fold_res['ref']['steps_med']:.1f} | "
                  f"pg-hist steps={fold_res['pg_history']['steps_med']:.1f} "
                  f"theta={[f'{x:+.3f}' for x in th_hist]} | "
                  f"pg-mem steps={fold_res['pg_memoryless']['steps_med']:.1f} "
                  f"alpha={th_mem[0]:+.3f}")
        all_results["verifiers"][vkey] = v_res

    if SMOKE:
        print("\nSMOKE DONE.")
        return all_results

    # ---- pre-registered bar (history learner, 4D, held-out)
    print("\n== PRE-REGISTERED BAR: verifier moves beta ==")
    b1 = [all_results["verifiers"]["V2"]["folds"][f]["theta_hist"][1] <
          all_results["verifiers"]["V1"]["folds"][f]["theta_hist"][1] for f in range(4)]
    b2 = [all_results["verifiers"]["V2"]["folds"][f]["theta_hist"][1] < 0 for f in range(4)]
    b3 = [all_results["verifiers"]["V1"]["folds"][f]["theta_hist"][1] > 0 for f in range(4)]
    for f in range(4):
        b1v = all_results["verifiers"]["V1"]["folds"][f]["theta_hist"][1]
        b2v = all_results["verifiers"]["V2"]["folds"][f]["theta_hist"][1]
        print(f"  fold {f}: beta(V1)={b1v:+.3f} beta(V2)={b2v:+.3f} -> "
              f"{'V2<V1' if b1[f] else 'NOT'} | V2<0: {'yes' if b2[f] else 'no'} | "
              f"V1>0: {'yes' if b3[f] else 'no'}")
    bar = all(b1) and sum(b2) >= 3 and all(b3)
    print(f"  BAR: {'PASSED' if bar else 'NOT PASSED'} "
          f"((a) V2<V1 all folds: {sum(b1)}/4, (b) V2<0 >=3/4: {sum(b2)}/4, "
          f"(c) V1>0 all: {sum(b3)}/4)")
    all_results["bar"] = {"passed": bool(bar),
                          "V2_lt_V1": [bool(x) for x in b1],
                          "V2_negative": [bool(x) for x in b2],
                          "V1_positive": [bool(x) for x in b3]}

    # ---- full behavioral fingerprint table (history learner)
    print("\n== BEHAVIORAL FINGERPRINT (held-out; history learner) ==")
    print(f"  {'ver':>4} | {'fold':>11} | {'alpha':>7} {'beta':>7} {'gamma':>7} | "
          f"{'steps':>6} {'eff':>6} {'ovsh':>5} {'timeout':>7}")
    for vkey in VERIFIERS:
        for fr in all_results["verifiers"][vkey]["folds"]:
            th = fr["theta_hist"]; s = fr["pg_history"]
            print(f"  {vkey:>4} | {fr['held_chain']:>11} | {th[0]:+7.3f} {th[1]:+7.3f} "
                  f"{th[2]:+7.3f} | {s['steps_med']:6.1f} {s['eff_med']:6.3f} "
                  f"{s['overshoot_mean']:5.1f} {s['timeout_rate']:7.2f}")

    with open(JSON_OUT, "w") as f:
        json.dump(all_results, f, indent=1)
    print(f"\nJSON saved: {JSON_OUT}")

    # ---- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        vcols = {"V1": "tab:blue", "V2": "tab:green", "V3": "tab:orange", "V4": "tab:red"}

        # (alpha, beta) selection map per verifier (4 folds as points)
        fig, ax = plt.subplots(figsize=(8.5, 6))
        for vkey in VERIFIERS:
            xs = [fr["theta_hist"][0] for fr in all_results["verifiers"][vkey]["folds"]]
            ys = [fr["theta_hist"][1] for fr in all_results["verifiers"][vkey]["folds"]]
            ax.scatter(xs, ys, s=120, color=vcols[vkey],
                       label=f"{vkey}: {VERIFIER_DESC[vkey]}", zorder=3)
            for fr, x, y in zip(all_results["verifiers"][vkey]["folds"], xs, ys):
                ax.annotate(fr["held_chain"], (x, y), fontsize=7,
                            xytext=(4, 4), textcoords="offset points")
        ax.axhline(0, color="k", lw=0.8); ax.axvline(0, color="k", lw=0.8)
        ax.set_xlabel("learned alpha (proportional gain)")
        ax.set_ylabel("learned beta (history term)")
        ax.set_title("Exp 22 (4D) — verifier selection map: where does each verifier "
                     "put (alpha, beta)?\n(one point per held-out fold; the verifier is "
                     "the only independent variable)")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp22_alphamap_4d.png", dpi=110); plt.close(fig)

        # convergence time by verifier
        fig, ax = plt.subplots(figsize=(10, 4.6))
        x = np.arange(4); w = 0.18
        for j, vkey in enumerate(VERIFIERS):
            meds = [fr["pg_history"]["steps_med"]
                    for fr in all_results["verifiers"][vkey]["folds"]]
            ax.bar(x + (j - 1.5) * w, meds, w, color=vcols[vkey], label=vkey)
        ax.set_xticks(x); ax.set_xticklabels([CHAINS[f][0] for f in range(4)])
        ax.set_ylabel("median steps to settle (held-out)")
        ax.set_title("Exp 22 (4D) — convergence time by verifier (history learner)")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp22_steps_4d.png", dpi=110); plt.close(fig)

        # path cost by verifier
        fig, ax = plt.subplots(figsize=(10, 4.6))
        for j, vkey in enumerate(VERIFIERS):
            meds = [fr["pg_history"]["eff_med"]
                    for fr in all_results["verifiers"][vkey]["folds"]]
            ax.bar(x + (j - 1.5) * w, meds, w, color=vcols[vkey], label=vkey)
        ax.set_xticks(x); ax.set_xticklabels([CHAINS[f][0] for f in range(4)])
        ax.set_ylabel("median path cost (held-out)")
        ax.set_title("Exp 22 (4D) — path cost by verifier (history learner)")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp22_eff_4d.png", dpi=110); plt.close(fig)
        print("Figures saved: exp22_alphamap_4d.png, exp22_steps_4d.png, exp22_eff_4d.png")
    except Exception as e:
        print(f"\n(figure generation skipped: {e})")

    return all_results


if __name__ == "__main__":
    res = main()
    print("\nDONE. gate =", res.get("gate"), "| bar =", res.get("bar", {}).get("passed"))
