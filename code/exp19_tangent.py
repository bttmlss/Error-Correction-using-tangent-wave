#!/usr/bin/env python3
"""
Exp 19 — Semantic Tangent (follows ~/workspace/ai-theory/semantic-tangent-spec.md exactly).

Exp 18 proved the world has geometry. Exp 19 asks whether a machine can move
through that world: three correction operators compete on semantic targets in
the Exp-18 contextual substrate (4D PCA primary, 16D robustness).

The substrate is OBSERVATIONAL ONLY (no model training, no reward modification,
no touching model weights). The only "learning" is black-box hill-climbing over
the operator parameters (1 param for direct, 3 for tangent), scored by a fixed,
hand-defined verifier metric. The operator NEVER sees a correct dX — only
(X_t, ehat_t, dehat_t, d2ehat_t) at step time and the per-trial verifier score.
No per-step labels (Exp 11's teacher problem), no policy gradients.

Leave-one-chain-out generalization: 4 folds, tune on 3 chains, test on held-out.
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
SEED = 17911254            # master seed (same as Exps 16/18)
MODEL_DIR = os.environ.get("MODEL_DIR", "Qwen/Qwen2.5-0.5B-Instruct")
WORDMAP = (REPO_ROOT / "word_number_map.json")
LAYER = 23                # final layer, same as Exp 18
CARRIERS = [              # Exp 18's carriers, verbatim
    "The ___ sat on the table.",
    "I saw the ___ yesterday.",
    "She pointed at the ___.",
]
LADDER_DIMS = [1, 4, 16, 64]
EXP18_LADDER = {1: 0.591, 4: 0.827, 16: 0.975, 64: 1.000}  # Exp-18 values
LADDER_TOL = 0.02         # reproduction tolerance; gate fails if exceeded
DIMS_TO_RUN = [4, 16]     # 4D primary, 16D robustness condition

CHAINS = [
    ("size",        ["small", "medium", "large"]),
    ("temperature", ["cold", "warm", "hot"]),
    ("brightness",  ["dark", "dim", "bright"]),
    ("speed",       ["slow", "steady", "fast"]),
]

# verifier / settle (pinned)
NOISE_FRAC = 0.05         # sigma = 0.05 * median|eps_0| across trials
SETTLE_TOL_FRAC = 0.10    # settled: |ehat| < 0.10*|eps_0| for 3 consecutive steps
SETTLE_K = 3
TIMEOUT = 200

# verifier metric: score = steps + LAM*overshoot + MU*efficiency (pinned)
LAM = 5.0
MU = 20.0

# hill-climbing (pinned): equal tuning budget for direct and tangent
BUDGET = 200              # evaluations per operator per fold
N_RESTART = 6
A_RANGE = (0.05, 2.0)     # direct gain alpha
B_RANGE = (-1.0, 1.0)     # tangent damping beta
G_RANGE = (-0.5, 0.5)     # tangent curvature gamma

FIG_DIR = (REPO_ROOT / "figures")

# ---------------------------------------------------------------- utilities
def pearson_r(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    a = a - a.mean(); b = b - b.mean()
    return float((a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300))

def med_iqr(x):
    x = np.asarray(x, float)
    return float(np.median(x)), float(np.percentile(x, 25)), float(np.percentile(x, 75))

# ---------------------------------------------------------------- substrate
def embed_words(tok, model, words):
    """Mean hidden state over the word's token span at LAYER, per carrier.
    Identical procedure to Exp 18 (overlap-based token selection for BPE)."""
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

# ---------------------------------------------------------------- trial runner
def run_trial(X0, T, step_fn, params, tol, noise, rng_dirs=None):
    """Run one trial. step_fn(ehat, dehat, d2ehat, params, rng_dirs) -> dX.
    Measurements on TRUE eps (recorded by harness); settle/timeout use the
    noisy verifier ehat per spec. rng_dirs supplies random unit vectors for
    the random control (None otherwise)."""
    d = len(X0)
    X = X0.astype(np.float64).copy()
    e0 = T - X0
    n0 = float(np.linalg.norm(e0))
    u = e0 / (n0 + 1e-300)
    ehat_prev = None
    dehat_prev = np.zeros(d)
    e_true_prev = n0
    overshoot = 0
    excursion = 0.0
    path = 0.0
    dX_hist = []
    d2_norms = []
    consec = 0
    settled_step = TIMEOUT
    settled = False
    for t in range(TIMEOUT):
        ehat = (T - X) + noise[t]
        ehat_n = float(np.linalg.norm(ehat))
        if t == 0:
            dehat = np.zeros(d); d2 = np.zeros(d)
        else:
            dehat = ehat - ehat_prev
            d2 = dehat - dehat_prev
        dX = step_fn(ehat, dehat, d2, params, rng_dirs)
        dX_hist.append(dX)
        X = X + dX
        path += float(np.linalg.norm(dX))
        e_true = T - X
        e_true_n = float(np.linalg.norm(e_true))
        # overshoot (pinned rule, on true eps): error grows after having shrunk
        if e_true_n > e_true_prev and e_true_prev < n0:
            overshoot += 1
        e_true_prev = e_true_n
        ex = float(np.dot(X - T, u))
        if ex > excursion:
            excursion = ex
        ehat_prev = ehat
        dehat_prev = dehat
        d2_norms.append(float(np.linalg.norm(d2)))
        if ehat_n < tol:
            consec += 1
            if consec >= SETTLE_K:
                settled = True
                settled_step = t + 1
                break
        else:
            consec = 0
    steps = settled_step
    cosines = []
    for i in range(1, len(dX_hist)):
        a, b = dX_hist[i - 1], dX_hist[i]
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        if na > 1e-300 and nb > 1e-300:
            cosines.append(float(a @ b / (na * nb)))
    dir_stab = float(np.mean(cosines)) if cosines else 0.0
    tt = np.arange(len(d2_norms))
    d2_slope = float(np.polyfit(tt, np.array(d2_norms), 1)[0]) if len(d2_norms) > 2 else 0.0
    half = len(d2_norms) // 2
    d2_first = float(np.mean(d2_norms[:half])) if half else 0.0
    d2_second = float(np.mean(d2_norms[half:])) if d2_norms else 0.0
    efficiency = path / (n0 + 1e-300)
    score = steps + LAM * overshoot + MU * efficiency
    return {
        "steps": steps, "settled": settled, "overshoot": overshoot,
        "excursion": excursion, "dir_stab": dir_stab,
        "d2_slope": d2_slope, "d2_first": d2_first, "d2_second": d2_second,
        "path": path, "efficiency": efficiency, "score": score,
        "step_mags": [float(np.linalg.norm(v)) for v in dX_hist],
        "e_true_final": e_true_n,
    }

def direct_step(ehat, dehat, d2, params, rng_dirs):
    return params[0] * ehat

def tangent_step(ehat, dehat, d2, params, rng_dirs):
    return params[0] * ehat + params[1] * dehat + params[2] * d2

def random_step_factory(s):
    def f(ehat, dehat, d2, params, rng_dirs):
        u = rng_dirs.normal(size=len(ehat))
        n = float(np.linalg.norm(u))
        return s * u / (n + 1e-300)
    return f

# ---------------------------------------------------------------- learning (no teacher)
def eval_params(params, kind, trials, noise_bank):
    """Mean verifier score + mean efficiency over the tuning trials."""
    step_fn = direct_step if kind == "direct" else tangent_step
    scores, effs = [], []
    for i, tr in enumerate(trials):
        r = run_trial(tr["X0"], tr["T"], step_fn, params, tr["tol"], noise_bank[i])
        scores.append(r["score"]); effs.append(r["efficiency"])
    return float(np.mean(scores)), float(np.mean(effs))

def random_config(kind, rng):
    if kind == "direct":
        return np.array([rng.uniform(*A_RANGE)])
    return np.array([rng.uniform(*A_RANGE), rng.uniform(*B_RANGE), rng.uniform(*G_RANGE)])

def perturb(p, kind, rng):
    ranges = {"direct": [A_RANGE], "tangent": [A_RANGE, B_RANGE, G_RANGE]}[kind]
    q = p.copy()
    i = int(rng.integers(0, len(p)))
    lo, hi = ranges[i]
    q[i] = float(np.clip(q[i] + rng.normal(0, 0.1 * (hi - lo)), lo, hi))
    return q

def hillclimb(kind, trials, noise_bank, rng):
    """Black-box hill-climbing, fixed budget. Returns best params and the
    best-so-far efficiency history (for the 'cleaner over training' measurement)."""
    best_p, best_s, best_eff = None, np.inf, np.inf
    eff_hist = []
    per_restart = BUDGET // N_RESTART
    for _ in range(N_RESTART):
        p = random_config(kind, rng)
        s, eff = eval_params(p, kind, trials, noise_bank)
        if s < best_s:
            best_p, best_s, best_eff = p.copy(), s, eff
        eff_hist.append(best_eff)
        for _ in range(per_restart - 1):
            q = perturb(p, kind, rng)
            sq, effq = eval_params(q, kind, trials, noise_bank)
            if sq < s:
                p, s = q, sq
            if sq < best_s:
                best_p, best_s, best_eff = q.copy(), sq, effq
            eff_hist.append(best_eff)
    xs = np.arange(len(eff_hist))
    slope = float(np.polyfit(xs, np.array(eff_hist), 1)[0]) if len(xs) > 2 else 0.0
    return best_p, best_s, eff_hist, slope

# ---------------------------------------------------------------- measurement aggregation
def summarize(results):
    steps = [r["steps"] for r in results]
    med, q1, q3 = med_iqr(steps)
    emed, eq1, eq3 = med_iqr([r["efficiency"] for r in results])
    return {
        "steps_med": med, "steps_q1": q1, "steps_q3": q3,
        "timeout_rate": float(np.mean([0.0 if r["settled"] else 1.0 for r in results])),
        "overshoot_mean": float(np.mean([r["overshoot"] for r in results])),
        "excursion_mean": float(np.mean([r["excursion"] for r in results])),
        "dir_stab_mean": float(np.mean([r["dir_stab"] for r in results])),
        "d2_slope_mean": float(np.mean([r["d2_slope"] for r in results])),
        "d2_first_mean": float(np.mean([r["d2_first"] for r in results])),
        "d2_second_mean": float(np.mean([r["d2_second"] for r in results])),
        "eff_med": emed, "eff_q1": eq1, "eff_q3": eq3,
        "n": len(results),
    }

# ---------------------------------------------------------------- main
def main():
    torch.manual_seed(SEED)
    with open(WORDMAP) as f:
        words = list(json.load(f)["words"].keys())
    assert len(words) == 24

    print("Loading tokenizer + model (fp16, CPU, no_grad, observational only)...")
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float16)
    model.eval()

    print("Embedding 24 base words x 3 carriers (Exp-18 rebuild)...")
    E_base = embed_words(tok, model, words)                      # (24,3,896)
    chain_words = [w for _, ws in CHAINS for w in ws]
    print(f"Embedding {len(chain_words)} chain words x 3 carriers (identical procedure)...")
    E_chain = embed_words(tok, model, chain_words)                # (12,3,896)

    # PCA refit on the original 72 contextual vectors only; chain words are
    # projected into the fitted basis (basis does not change).
    X = E_base.reshape(-1, 896)
    mu = X.mean(axis=0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)

    # ---- verification gate: ladder must reproduce Exp 18
    iu = np.triu_indices(len(X), 1)
    d_full = np.array([np.linalg.norm(X[i] - X[j]) for i, j in zip(*iu)])
    Z = Xc @ Vt.T
    ladder = {}
    print("\n== VERIFICATION GATE: PCA ladder reproduction ==")
    gate_ok = True
    for d in LADDER_DIMS:
        Zd = Z[:, :d]
        d_proj = np.array([np.linalg.norm(Zd[i] - Zd[j]) for i, j in zip(*iu)])
        ladder[d] = pearson_r(d_full, d_proj)
        drift = abs(ladder[d] - EXP18_LADDER[d])
        ok = drift <= LADDER_TOL
        gate_ok = gate_ok and ok
        print(f"  dim {d:>2}: r = {ladder[d]:+.4f}  (Exp18 {EXP18_LADDER[d]:+.4f}, drift {drift:.4f}) {'OK' if ok else 'DRIFT'}")
    if not gate_ok:
        print("\nGATE FAILED: ladder did not reproduce Exp 18. Stopping — procedure drifted.")
        return {"gate": "FAILED", "ladder": ladder}

    all_results = {"gate": "PASSED", "ladder": ladder, "dims": {}}

    for dim in DIMS_TO_RUN:
        print(f"\n{'='*60}\n== Exp 19 at {dim}D ==\n{'='*60}")
        P = Vt[:dim].T
        Wd = ((E_base - mu) @ P).mean(axis=1)     # (24, dim): mean over carriers
        Cd = ((E_chain - mu) @ P).mean(axis=1)    # (12, dim)
        cw = {w: Cd[i] for i, w in enumerate(chain_words)}

        # trials: 6 directed pairs per chain
        trials = []
        for ci, (cname, ws) in enumerate(CHAINS):
            for a in range(3):
                for b in range(3):
                    if a == b:
                        continue
                    X0, T = cw[ws[a]], cw[ws[b]]
                    trials.append({
                        "chain": ci, "cname": cname, "pair": f"{ws[a]}->{ws[b]}",
                        "X0": X0, "T": T,
                        "eps0": float(np.linalg.norm(T - X0)),
                    })
        assert len(trials) == 24
        sigma = NOISE_FRAC * float(np.median([t["eps0"] for t in trials]))
        for t in trials:
            t["tol"] = SETTLE_TOL_FRAC * t["eps0"]
        print(f"24 trials, median|eps_0| = {np.median([t['eps0'] for t in trials]):.3f}, "
              f"sigma = {sigma:.4f}")

        dim_res = {"sigma": sigma, "folds": []}

        for fold in range(4):
            train = [t for t in trials if t["chain"] != fold]
            held = [t for t in trials if t["chain"] == fold]
            assert len(train) == 18 and len(held) == 6
            cname_held = CHAINS[fold][0]
            print(f"\n-- fold {fold}: held-out chain '{cname_held}' --")

            # pinned noise banks: common random numbers across candidates during
            # tuning; fresh pinned noise for final train/held-out evaluation,
            # shared across operators (fair comparison).
            tune_rng = np.random.default_rng(SEED + 1000 + dim * 100 + fold)
            tune_noise = [tune_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in train]
            eval_rng = np.random.default_rng(SEED + 2000 + dim * 100 + fold)
            eval_noise_train = [eval_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in train]
            eval_noise_held = [eval_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in held]
            dir_rng = np.random.default_rng(SEED + 3000 + dim * 100 + fold)  # random-control directions

            # tune both operators, same budget
            hc_rng = np.random.default_rng(SEED + 4000 + dim * 100 + fold)
            p_dir, s_dir, eff_hist_dir, slope_dir = hillclimb("direct", train, tune_noise, hc_rng)
            p_tan, s_tan, eff_hist_tan, slope_tan = hillclimb("tangent", train, tune_noise, hc_rng)
            print(f"  tuned direct : alpha={p_dir[0]:.4f}  (train score {s_dir:.2f})")
            print(f"  tuned tangent: alpha={p_tan[0]:+.4f} beta={p_tan[1]:+.4f} gamma={p_tan[2]:+.4f}  (train score {s_tan:.2f})")

            # random control: step size matched to tuned direct's typical |dX|
            mags = []
            for i, tr in enumerate(train):
                r = run_trial(tr["X0"], tr["T"], direct_step, p_dir, tr["tol"], tune_noise[i])
                mags.extend(r["step_mags"])
            s_rand = float(np.median(mags))
            rand_step = random_step_factory(s_rand)
            print(f"  random control: matched step s = {s_rand:.4f}")

            # final evaluation on fresh pinned noise
            def ev(trials_, noise_):
                out = {"direct": [], "tangent": [], "random": []}
                for i, tr in enumerate(trials_):
                    out["direct"].append(run_trial(tr["X0"], tr["T"], direct_step, p_dir, tr["tol"], noise_[i]))
                    out["tangent"].append(run_trial(tr["X0"], tr["T"], tangent_step, p_tan, tr["tol"], noise_[i]))
                    rr = np.random.default_rng(SEED + 5000 + dim * 100 + fold * 100 + i)
                    out["random"].append(run_trial(tr["X0"], tr["T"], rand_step, None, tr["tol"], noise_[i], rr))
                return out
            ev_train, ev_held = ev(train, eval_noise_train), ev(held, eval_noise_held)

            fold_res = {
                "held_chain": cname_held,
                "p_dir": [float(v) for v in p_dir],
                "p_tan": [float(v) for v in p_tan],
                "s_rand": s_rand,
                "eff_slope_dir": slope_dir, "eff_slope_tan": slope_tan,
                "train": {k: summarize(v) for k, v in ev_train.items()},
                "held": {k: summarize(v) for k, v in ev_held.items()},
            }
            dim_res["folds"].append(fold_res)
            hs, he = fold_res["held"]["tangent"]["steps_med"], fold_res["held"]["tangent"]["eff_med"]
            ds, de = fold_res["held"]["direct"]["steps_med"], fold_res["held"]["direct"]["eff_med"]
            print(f"  held-out: direct steps={ds:.1f} eff={de:.3f} | tangent steps={hs:.1f} eff={he:.3f} "
                  f"| random steps={fold_res['held']['random']['steps_med']:.1f}")

        all_results["dims"][dim] = dim_res

    # ---- pre-registered bar (held-out, 4D primary): tangent beats direct on
    # steps-to-settle AND efficiency, same direction in all 4 folds.
    print("\n== PRE-REGISTERED BAR (4D, held-out) ==")
    bar_steps, bar_eff = [], []
    for f, fr in enumerate(all_results["dims"][4]["folds"]):
        s_win = fr["held"]["tangent"]["steps_med"] < fr["held"]["direct"]["steps_med"]
        e_win = fr["held"]["tangent"]["eff_med"] < fr["held"]["direct"]["eff_med"]
        bar_steps.append(s_win); bar_eff.append(e_win)
        print(f"  fold {f} ({fr['held_chain']:>11}): tangent steps {fr['held']['tangent']['steps_med']:.1f} "
              f"vs direct {fr['held']['direct']['steps_med']:.1f} -> {'WIN' if s_win else 'loss'} | "
              f"tangent eff {fr['held']['tangent']['eff_med']:.3f} vs direct {fr['held']['direct']['eff_med']:.3f} "
              f"-> {'WIN' if e_win else 'loss'}")
    bar = all(bar_steps) and all(bar_eff)
    print(f"  BAR: {'PASSED' if bar else 'NOT PASSED'} "
          f"(steps wins: {sum(bar_steps)}/4, efficiency wins: {sum(bar_eff)}/4)")
    all_results["bar"] = {"passed": bool(bar), "steps_wins": [bool(x) for x in bar_steps],
                          "eff_wins": [bool(x) for x in bar_eff]}

    # ---- detailed measurement tables (all six pinned measurements)
    for dim in DIMS_TO_RUN:
        print(f"\n== DETAILED MEASUREMENTS ({dim}D) ==")
        for f, fr in enumerate(all_results["dims"][dim]["folds"]):
            print(f"\nfold {f} held-out='{fr['held_chain']}' "
                  f"| p_dir={[f'{v:.4f}' for v in fr['p_dir']]} "
                  f"| p_tan={[f'{v:+.4f}' for v in fr['p_tan']]} "
                  f"| s_rand={fr['s_rand']:.4f} "
                  f"| eff_slope_dir={fr['eff_slope_dir']:+.6f} eff_slope_tan={fr['eff_slope_tan']:+.6f}")
            for split in ["train", "held"]:
                print(f"  [{split}]")
                for op in ["direct", "tangent", "random"]:
                    s = fr[split][op]
                    print(f"    {op:>8}: steps {s['steps_med']:6.1f} "
                          f"[{s['steps_q1']:.0f},{s['steps_q3']:.0f}] to={s['timeout_rate']:.2f} | "
                          f"ovsh {s['overshoot_mean']:6.1f} exc {s['excursion_mean']:7.2f} | "
                          f"dstab {s['dir_stab_mean']:+.3f} | "
                          f"d2slope {s['d2_slope_mean']:+.5f} "
                          f"(1st {s['d2_first_mean']:.3f} 2nd {s['d2_second_mean']:.3f}) | "
                          f"eff {s['eff_med']:.3f} [{s['eff_q1']:.2f},{s['eff_q3']:.2f}] n={s['n']}")

    # ---- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        for dim in DIMS_TO_RUN:
            folds = all_results["dims"][dim]["folds"]
            ops = ["direct", "tangent", "random"]
            cols = ["tab:blue", "tab:green", "tab:gray"]
            labels = ["direct (P)", "tangent (PID)", "random control"]

            fig, ax = plt.subplots(figsize=(8.5, 4.4))
            x = np.arange(4); w = 0.24
            for j, op in enumerate(ops):
                meds = [f["held"][op]["steps_med"] for f in folds]
                ax.bar(x + (j - 1) * w, meds, w, color=cols[j], label=labels[j])
            ax.set_xticks(x); ax.set_xticklabels([f["held_chain"] for f in folds])
            ax.set_ylabel("median steps to settle (held-out chain)")
            ax.set_title(f"Exp 19 ({dim}D) — held-out steps to settle by fold")
            ax.legend(); fig.tight_layout()
            fig.savefig(f"{FIG_DIR}/exp19_steps_{dim}d.png", dpi=110); plt.close(fig)

            fig, ax = plt.subplots(figsize=(8.5, 4.4))
            for j, op in enumerate(ops):
                meds = [f["held"][op]["eff_med"] for f in folds]
                ax.bar(x + (j - 1) * w, meds, w, color=cols[j], label=labels[j])
            ax.set_xticks(x); ax.set_xticklabels([f["held_chain"] for f in folds])
            ax.set_ylabel("median path_length / |eps_0| (held-out chain)")
            ax.set_title(f"Exp 19 ({dim}D) — held-out efficiency by fold")
            ax.legend(); fig.tight_layout()
            fig.savefig(f"{FIG_DIR}/exp19_efficiency_{dim}d.png", dpi=110); plt.close(fig)

        # tuned params across folds (4D)
        folds4 = all_results["dims"][4]["folds"]
        fig, ax = plt.subplots(figsize=(7.5, 4.2))
        xs = np.arange(4)
        ax.bar(xs - 0.25, [f["p_tan"][0] for f in folds4], 0.22, color="tab:blue", label="alpha (tangent)")
        ax.bar(xs, [f["p_tan"][1] for f in folds4], 0.22, color="tab:orange", label="beta (tangent)")
        ax.bar(xs + 0.25, [f["p_tan"][2] for f in folds4], 0.22, color="tab:red", label="gamma (tangent)")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xticks(xs); ax.set_xticklabels([f["held_chain"] for f in folds4])
        ax.set_ylabel("tuned parameter value")
        ax.set_title("Exp 19 (4D) — tuned tangent (PID) parameters per fold\n(did beta/gamma move away from zero?)")
        ax.legend(); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp19_params_4d.png", dpi=110); plt.close(fig)

        # example trajectories: |e_true| vs t for the three operators
        dim = 4
        P = Vt[:dim].T
        cw = {w: (((E_chain[i] - mu) @ P).mean(axis=0)) for i, w in enumerate(chain_words)}
        tr = {"X0": cw["cold"], "T": cw["hot"], "tol": SETTLE_TOL_FRAC * float(np.linalg.norm(cw["hot"] - cw["cold"]))}
        sigma = all_results["dims"][4]["sigma"]
        fr0 = all_results["dims"][4]["folds"][0]
        p_dir = np.array(fr0["p_dir"]); p_tan = np.array(fr0["p_tan"])
        nz = np.random.default_rng(SEED + 777).normal(0, sigma, (TIMEOUT, dim))
        fig, ax = plt.subplots(figsize=(8, 4.2))
        for name, fn, prm, col in [("direct", direct_step, p_dir, "tab:blue"),
                                   ("tangent", tangent_step, p_tan, "tab:green"),
                                   ("random", random_step_factory(fr0["s_rand"]), None, "tab:gray")]:
            X = tr["X0"].copy().astype(np.float64)
            errs = [float(np.linalg.norm(tr["T"] - X))]
            ehat_prev = None; dehat_prev = np.zeros(dim)
            rr = np.random.default_rng(42)
            for t in range(TIMEOUT):
                ehat = (tr["T"] - X) + nz[t]
                dehat = np.zeros(dim) if t == 0 else ehat - ehat_prev
                d2 = np.zeros(dim) if t == 0 else dehat - dehat_prev
                X = X + fn(ehat, dehat, d2, prm, rr)
                errs.append(float(np.linalg.norm(tr["T"] - X)))
                ehat_prev, dehat_prev = ehat, dehat
                if float(np.linalg.norm(ehat)) < tr["tol"] and t > 5:
                    break
            ax.plot(errs, color=col, label=name)
        ax.axhline(tr["tol"], ls="--", color="k", lw=0.8, label="settle tol")
        ax.set_xlabel("step"); ax.set_ylabel("|eps| (true)")
        ax.set_title("Exp 19 (4D) — example trajectory: cold -> hot (held-out chain)")
        ax.legend(); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp19_traj_4d.png", dpi=110); plt.close(fig)
        print("\nFigures saved: exp19_steps_{4,16}d.png, exp19_efficiency_{4,16}d.png, "
              "exp19_params_4d.png, exp19_traj_4d.png")
    except Exception as e:
        print(f"\n(figure generation skipped: {e})")

    return all_results


if __name__ == "__main__":
    res = main()
    print("\nDONE. gate =", res.get("gate"), "| bar =", res.get("bar", {}).get("passed"))
