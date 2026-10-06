"""
Exp 23 — Verifier-Induced Law Generalization
Follows ~/workspace/ai-theory/semantic-tangent-exp23-spec.md exactly.

Directive from Adrian (2026-10-05): freeze everything learned in Exp 22 and
test whether the V4-induced damping law transfers to genuinely unseen
semantic situations. NO training in this script — frozen thetas only.

Three generalization types:
  T1: new words (never embedded before), familiar within-chain geometry
  T2: familiar words, cross-chain pairings within the training |eps0| range
  T3: familiar words, cross-chain pairings outside the training |eps0| range
Plus a label-shuffle control (pinned permutation of targets).

Controllers per fold (thetas from exp22_results.json, frozen):
  V4-history (candidate transferable operator), V4-memoryless (history
  ablated), V1-history (whatever the minimal verifier induced — honest).

Substrate is OBSERVATIONAL ONLY (no model training, no touching weights).
"""
import json
import os
import sys

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp22_verifiers as E22
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent
(REPO_ROOT / "figures").mkdir(parents=True, exist_ok=True)

SEED = E22.SEED
DIM = E22.DIM
CHAINS = E22.CHAINS
NEW_WORDS_CACHE = (REPO_ROOT / "exp23_new_words.npz")
JSON_OUT = (REPO_ROOT / "exp23_results.json")
FIG_DIR = E22.FIG_DIR
EXP22_JSON = (REPO_ROOT / "exp22_results.json")

# Type-1 probe words: 2 per chain, never embedded before (asserted below)
NEW_WORDS = {
    "size": ["tiny", "enormous"],
    "temperature": ["freezing", "scorching"],
    "brightness": ["gloomy", "radiant"],
    "speed": ["sluggish", "rapid"],
}

N_T2 = 12
N_T3 = 12


def eval_frozen(X0, T, theta, n_params, noise, tol_new):
    """Deterministic evaluation of a FROZEN controller. No learning.
    Returns the full fingerprint including action jerk."""
    d = len(X0)
    X = X0.astype(np.float64).copy()
    n0 = float(np.linalg.norm(T - X0))
    ehat_prev = None
    dehat_prev = np.zeros(d)
    consec = 0
    settled_step = E22.TIMEOUT
    path = 0.0
    overshoot = 0
    etrue_prev = n0
    jerks = []
    dX_prev = None
    for t in range(E22.TIMEOUT):
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
        if dX_prev is not None:
            jerks.append(float(np.linalg.norm(a - dX_prev)) / (n0 + 1e-300))
        dX_prev = a.copy()
        etrue_n = float(np.linalg.norm(T - X))
        if etrue_n > etrue_prev and etrue_prev < n0:
            overshoot += 1
        etrue_prev = etrue_n
        ehat_prev = ehat
        dehat_prev = dehat
        if ehat_n < tol_new:
            consec += 1
            if consec >= E22.SETTLE_M and t >= E22.MIN_STEPS:
                settled_step = t + 1
                break
        else:
            consec = 0
    return {"steps": settled_step, "settled": settled_step < E22.TIMEOUT,
            "efficiency": path / (n0 + 1e-300), "overshoot": overshoot,
            "jerk": float(np.mean(jerks)) if jerks else 0.0}


def main():
    torch.manual_seed(SEED)
    with open(EXP22_JSON) as f:
        exp22 = json.load(f)
    assert exp22["gate"] == "PASSED"

    print("Loading tokenizer + model (fp16, CPU, no_grad, observational only)...")
    tok = AutoTokenizer.from_pretrained(E22.MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(E22.MODEL_DIR, torch_dtype=torch.float16)
    model.eval()

    chain_words = [w for _, ws in CHAINS for w in ws]
    new_words = [w for _, ws in NEW_WORDS.items() for w in ws]
    assert len(set(new_words) & set(chain_words)) == 0, "new-word collision with chain words"
    assert len(new_words) == 8 and len(set(new_words)) == 8

    # --- substrate verification gate (same PCA ladder check as Exp 21/22)
    with open(E22.WORDMAP) as f:
        words = list(json.load(f)["words"].keys())
    assert len(words) == 24
    cache = np.load(E22.EMBED_CACHE)
    E_base, E_chain = cache["E_base"], cache["E_chain"]
    X = E_base.reshape(-1, 896)
    mu = X.mean(axis=0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    iu = np.triu_indices(len(X), 1)
    d_full = np.array([np.linalg.norm(X[i] - X[j]) for i, j in zip(*iu)])
    Z = Xc @ Vt.T
    print("\n== VERIFICATION GATE: PCA ladder reproduction ==")
    gate_ok = True
    for d in E22.LADDER_DIMS:
        Zd = Z[:, :d]
        d_proj = np.array([np.linalg.norm(Zd[i] - Zd[j]) for i, j in zip(*iu)])
        r = E22.pearson_r(d_full, d_proj)
        drift = abs(r - E22.EXP18_LADDER[d])
        ok = drift <= E22.LADDER_TOL
        gate_ok = gate_ok and ok
        print(f"  dim {d:>2}: r = {r:+.4f} (drift {drift:.4f}) {'OK' if ok else 'DRIFT'}")
    if not gate_ok:
        print("\nGATE FAILED. Stopping.")
        return {"gate": "FAILED"}

    dim = DIM
    P = Vt[:dim].T
    Cd = ((E_chain - mu) @ P).mean(axis=1)
    cw = {w: Cd[i] for i, w in enumerate(chain_words)}

    # --- embed the 8 new Type-1 words through the IDENTICAL pipeline
    if os.path.exists(NEW_WORDS_CACHE):
        print(f"Loading cached new-word embeddings from {NEW_WORDS_CACHE} ...")
        Cn = np.load(NEW_WORDS_CACHE)["C_new"]
    else:
        print(f"Embedding {len(new_words)} new words x 3 carriers (identical procedure)...")
        E_new = E22.embed_words(tok, model, new_words)
        Cn = ((E_new - mu) @ P).mean(axis=1)
        np.savez_compressed(NEW_WORDS_CACHE, C_new=Cn)
        print(f"New-word embeddings cached to {NEW_WORDS_CACHE}")
    nw = {w: Cn[i] for i, w in enumerate(new_words)}

    # --- training trials (to pin the |eps0| range; same 24 as Exp 22)
    train_trials = []
    for ci, (cname, ws) in enumerate(CHAINS):
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                train_trials.append((cw[ws[a]], cw[ws[b]]))
    train_r = sorted(float(np.linalg.norm(T - X0)) for X0, T in train_trials)
    rmin, rmax = train_r[0], train_r[-1]
    med_eps0 = float(np.median([t for t in train_r]))
    sigma = E22.NOISE_FRAC * med_eps0
    tol_new = E22.K_SIGMA * sigma * np.sqrt(dim)
    print(f"\nTraining |eps0|: min={rmin:.3f} max={rmax:.3f} median={med_eps0:.3f} "
          f"(n=24); sigma={sigma:.4f}, tol_new={tol_new:.4f}")

    # --- Type 1: new words, familiar within-chain geometry (16 trials)
    t1 = []
    for cname, ws in CHAINS:
        n0, n1 = NEW_WORDS[cname]
        t1 += [(nw[n0], nw[n1], f"{n0}->{n1}"),
               (nw[n1], nw[n0], f"{n1}->{n0}"),
               (nw[n0], cw[ws[2]], f"{n0}->{ws[2]}"),
               (cw[ws[0]], nw[n1], f"{ws[0]}->{n1}")]

    # --- Types 2/3: cross-chain pairings split by training |eps0| range
    cross = []
    for ci, (cname, ws) in enumerate(CHAINS):
        for dj, (dname, vs) in enumerate(CHAINS):
            if ci == dj:
                continue
            for a in ws:
                for b in vs:
                    r = float(np.linalg.norm(cw[b] - cw[a]))
                    cross.append((cw[a], cw[b], r, f"{a}->{b}"))
    cross.sort(key=lambda t: t[2])
    inside = [t for t in cross if rmin <= t[2] <= rmax]
    outside = [t for t in cross if t[2] < rmin or t[2] > rmax]
    print(f"Cross-chain pairs: {len(cross)} total, {len(inside)} inside training range, "
          f"{len(outside)} outside")

    def even_pick(lst, n):
        if len(lst) <= n:
            return lst
        idx = np.linspace(0, len(lst) - 1, n).round().astype(int)
        return [lst[i] for i in idx]

    t2 = [(X0, T, tag) for X0, T, r, tag in even_pick(inside, N_T2)]
    t3 = [(X0, T, tag) for X0, T, r, tag in even_pick(outside, N_T3)]
    print(f"Type 2 (new combos, familiar scale): {len(t2)} trials, "
          f"|eps0| {[f'{float(np.linalg.norm(T-X0)):.1f}' for X0,T,_ in t2]}")
    print(f"Type 3 (new geometry): {len(t3)} trials, "
          f"|eps0| {[f'{float(np.linalg.norm(T-X0)):.1f}' for X0,T,_ in t3]}")

    test_types = {"T1": t1, "T2": t2, "T3": t3}
    all_tests = [(ty, X0, T, tag) for ty, ts in test_types.items() for X0, T, tag in ts]
    n_test = len(all_tests)
    print(f"Total unseen test trials: {n_test}")

    # pinned test noise (frozen instrument, new pinned streams)
    test_noise = [np.random.default_rng(SEED + 9000 + ti).normal(0, sigma, (E22.TIMEOUT, dim))
                  for ti in range(n_test)]

    # --- frozen controllers from Exp 22 (paired by fold)
    controllers = {}
    for fold in range(4):
        f22 = exp22["verifiers"]
        controllers[fold] = {
            "V4-history": (np.array(f22["V4"]["folds"][fold]["theta_hist"]), 3),
            "V4-memoryless": (np.array(f22["V4"]["folds"][fold]["theta_mem"]), 1),
            "V1-history": (np.array(f22["V1"]["folds"][fold]["theta_hist"]), 3),
        }
    print("\nFrozen controllers (from Exp 22):")
    for fold in range(4):
        th = controllers[fold]["V4-history"][0]
        print(f"  fold {fold}: V4-hist {[f'{x:+.3f}' for x in th]}")

    def run_suite(trials, noises, label):
        """Evaluate all controllers on a trial list. Returns nested results."""
        res = {}
        for fold in range(4):
            res[fold] = {}
            for cname, (theta, np_) in controllers[fold].items():
                evs = [eval_frozen(X0, T, theta, np_, nz, tol_new)
                       for (X0, T), nz in zip(trials, noises)]
                res[fold][cname] = {
                    "steps_med": float(np.median([e["steps"] for e in evs])),
                    "eff_med": float(np.median([e["efficiency"] for e in evs])),
                    "overshoot_mean": float(np.mean([e["overshoot"] for e in evs])),
                    "jerk_mean": float(np.mean([e["jerk"] for e in evs])),
                    "timeout_rate": float(np.mean([0.0 if e["settled"] else 1.0 for e in evs])),
                }
        return res

    trials_only = [(X0, T) for _, X0, T, _ in all_tests]
    suite = run_suite(trials_only, test_noise, "unseen")
    # per-type suites
    suite_by_type = {}
    for ty, ts in test_types.items():
        idx = [i for i, (t, _, _, _) in enumerate(all_tests) if t == ty]
        suite_by_type[ty] = run_suite([trials_only[i] for i in idx],
                                      [test_noise[i] for i in idx], ty)

    # --- label-shuffle control (pinned permutation)
    perm = np.random.default_rng(SEED + 555).permutation(n_test)
    shuf_trials = [(trials_only[i][0], trials_only[perm[i]][1]) for i in range(n_test)]
    suite_shuf = run_suite(shuf_trials, test_noise, "shuffled")

    results = {"gate": "PASSED", "dim": dim, "n_test": n_test,
               "train_eps0_range": [rmin, rmax],
               "suite": suite, "suite_by_type": suite_by_type,
               "suite_shuffled": suite_shuf,
               "thetas": {str(f): {c: [float(x) for x in th]
                                   for c, (th, _) in controllers[f].items()}
                          for f in range(4)}}

    # ---- pre-registered bar (pooled over all 40 unseen trials)
    print("\n== PRE-REGISTERED BAR (frozen controllers, unseen trials) ==")
    a = [suite[f]["V4-history"]["overshoot_mean"] < suite[f]["V1-history"]["overshoot_mean"]
         for f in range(4)]
    b = [suite[f]["V4-history"]["eff_med"] < suite[f]["V4-memoryless"]["eff_med"]
         for f in range(4)]
    c = [suite[f]["V4-history"]["timeout_rate"] == 0.0 for f in range(4)]
    for f in range(4):
        s = suite[f]
        print(f"  fold {f}: V4-hist ov={s['V4-history']['overshoot_mean']:.2f} vs "
              f"V1-hist ov={s['V1-history']['overshoot_mean']:.2f} -> {'WIN' if a[f] else 'loss'} | "
              f"V4-hist eff={s['V4-history']['eff_med']:.3f} vs V4-mem eff={s['V4-memoryless']['eff_med']:.3f} "
              f"-> {'WIN' if b[f] else 'loss'} | timeouts: {'0' if c[f] else 'PRESENT'}")
    bar = all(a) and sum(b) >= 3 and all(c)
    print(f"  BAR: {'PASSED' if bar else 'NOT PASSED'} "
          f"((a) V4<V1 overshoot all folds: {sum(a)}/4, "
          f"(b) V4-hist<V4-mem path >=3/4: {sum(b)}/4, "
          f"(c) zero timeouts: {sum(c)}/4)")
    results["bar"] = {"passed": bool(bar),
                       "V4hist_lt_V1hist_overshoot": [bool(x) for x in a],
                       "V4hist_lt_V4mem_path": [bool(x) for x in b],
                       "V4hist_zero_timeouts": [bool(x) for x in c]}

    # ---- per-type fingerprint table
    print("\n== FINGERPRINT BY GENERALIZATION TYPE (pooled across folds) ==")
    for ty in ["T1", "T2", "T3"]:
        print(f"  -- {ty} --")
        for cname in ["V4-history", "V4-memoryless", "V1-history"]:
            ov = np.mean([suite_by_type[ty][f][cname]["overshoot_mean"] for f in range(4)])
            ef = np.median([suite_by_type[ty][f][cname]["eff_med"] for f in range(4)])
            st = np.median([suite_by_type[ty][f][cname]["steps_med"] for f in range(4)])
            jk = np.mean([suite_by_type[ty][f][cname]["jerk_mean"] for f in range(4)])
            to = np.mean([suite_by_type[ty][f][cname]["timeout_rate"] for f in range(4)])
            print(f"    {cname:>14}: steps={st:5.1f} eff={ef:.3f} ov={ov:5.2f} "
                  f"jerk={jk:.4f} timeout={to:.2f}")

    # ---- shuffle control table
    print("\n== LABEL-SHUFFLE CONTROL (pooled across folds) ==")
    for cname in ["V4-history", "V4-memoryless", "V1-history"]:
        ov = np.mean([suite_shuf[f][cname]["overshoot_mean"] for f in range(4)])
        ef = np.median([suite_shuf[f][cname]["eff_med"] for f in range(4)])
        st = np.median([suite_shuf[f][cname]["steps_med"] for f in range(4)])
        to = np.mean([suite_shuf[f][cname]["timeout_rate"] for f in range(4)])
        print(f"    {cname:>14}: steps={st:5.1f} eff={ef:.3f} ov={ov:5.2f} timeout={to:.2f}")

    with open(JSON_OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"\nJSON saved: {JSON_OUT}")

    # ---- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        cnames = ["V4-history", "V4-memoryless", "V1-history"]
        ccols = ["tab:green", "tab:olive", "tab:blue"]

        def pooled(suite_d, metric, agg):
            return [agg([suite_d[f][c][metric] for f in range(4)]) for c in cnames]

        # overshoot by type
        fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
        for ax, ty, title in zip(axes, ["T1", "T2", "T3"],
                                 ["T1: new words, familiar geometry",
                                  "T2: new combos, familiar scale",
                                  "T3: new trajectory geometry"]):
            vals = pooled(suite_by_type[ty], "overshoot_mean", np.mean)
            ax.bar(cnames, vals, color=ccols)
            ax.set_title(title, fontsize=9)
            ax.set_ylabel("mean overshoot (unseen trials)")
            ax.tick_params(axis="x", labelrotation=15, labelsize=8)
        fig.suptitle("Exp 23 — overshoot on unseen situations by controller "
                     "(frozen thetas, no test-time learning)")
        fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp23_overshoot_4d.png", dpi=110); plt.close(fig)

        # path cost by type
        fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
        for ax, ty, title in zip(axes, ["T1", "T2", "T3"],
                                 ["T1: new words, familiar geometry",
                                  "T2: new combos, familiar scale",
                                  "T3: new trajectory geometry"]):
            vals = pooled(suite_by_type[ty], "eff_med", np.median)
            ax.bar(cnames, vals, color=ccols)
            ax.set_title(title, fontsize=9)
            ax.set_ylabel("median path cost (unseen trials)")
            ax.tick_params(axis="x", labelrotation=15, labelsize=8)
        fig.suptitle("Exp 23 — path cost on unseen situations by controller "
                     "(frozen thetas, no test-time learning)")
        fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp23_eff_4d.png", dpi=110); plt.close(fig)
        print("Figures saved: exp23_overshoot_4d.png, exp23_eff_4d.png")
    except Exception as e:
        print(f"\n(figure generation skipped: {e})")

    return results


if __name__ == "__main__":
    res = main()
    print("\nDONE. gate =", res.get("gate"), "| bar =", res.get("bar", {}).get("passed"))
