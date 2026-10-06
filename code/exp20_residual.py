#!/usr/bin/env python3
"""
Exp 20 — Residual-Only Correction
Follows ~/workspace/ai-theory/semantic-tangent-exp20-spec.md exactly.

Qualified advancement from Exp 19 (qualified yes; pre-registered bar NOT
passed — speed won 4/4 held-out folds, efficiency lost 4/4). Three arms
compete on the Exp-18 contextual substrate (4D primary, 16D robustness with
noise-scaled tolerance):

  memoryless : u_t = alpha * ehat_t
  history    : u_t = alpha * ehat_t + beta * dehat_t + gamma * d2ehat_t
  permuted   : u_t = alpha * ehat_t + beta * dehat_{pi(t)}^ref
                                     + gamma * d2ehat_{pi(t)}^ref

The permuted arm receives history features from a reference trajectory (the
tuned memoryless arm on the same trial + noise, full horizon) with time
indices scrambled by a fixed per-trial permutation: same marginals,
destroyed temporal alignment. Same tuning budget, same ranges.

Settling is instrument-aware: ||ehat_t|| < k * sigma * sqrt(d) for m
consecutive steps (k=2, m=3). The |d2|->0 settling signature is retired
(Exp 19 falsified it: near-target the verifier shows its noise floor).

Substrate is OBSERVATIONAL ONLY (no model training, no reward modification).
The only "learning" is black-box hill-climbing over operator parameters,
scored by the fixed hand-defined verifier metric. The operator NEVER sees a
correct dX — only (X_t, ehat_t, dehat_t, d2ehat_t) at step time and the
per-trial verifier score.

Leave-one-chain-out generalization: 4 folds, tune on 3 chains, test held-out.
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
SEED = 17911254            # master seed (same as Exps 16/18/19)
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
DIMS_TO_RUN = [4, 16]     # 4D primary, 16D robustness (noise-scaled tol)

CHAINS = [
    ("size",        ["small", "medium", "large"]),
    ("temperature", ["cold", "warm", "hot"]),
    ("brightness",  ["dark", "dim", "bright"]),
    ("speed",       ["slow", "steady", "fast"]),
]

# verifier / settle (pinned)
NOISE_FRAC = 0.05         # sigma = 0.05 * median|eps_0| across trials (per dim)
K_SIGMA = 2.0             # instrument-aware tol = K_SIGMA * sigma * sqrt(d)
SETTLE_M = 3              # ...for m consecutive steps
MIN_STEPS = 5             # settle may not trigger before step 5 (guard)
SETTLE_TOL_FRAC_OLD = 0.10  # old relative tol, secondary column only
TIMEOUT = 200

# verifier metric for TUNING (scalar, unchanged from Exp 19):
# score = steps + LAM*overshoot + MU*efficiency (pinned)
LAM = 5.0
MU = 20.0

# hill-climbing (pinned): equal tuning budget for all three arms
BUDGET = 200              # evaluations per operator per fold
N_RESTART = 6
A_RANGE = (0.05, 2.0)     # gain alpha
B_RANGE = (-1.0, 1.0)     # damping beta
G_RANGE = (-0.5, 0.5)     # curvature gamma

FIG_DIR = (REPO_ROOT / "figures")
JSON_OUT = (REPO_ROOT / "exp20_results.json")

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
def run_trial(X0, T, step_fn, params, tol_new, tol_old, noise, rng_dirs=None,
              full_horizon=False, return_histories=False):
    """Run one trial. step_fn(ehat, dehat, d2, params, rng_dirs, t) -> dX.
    Measurements on TRUE eps (recorded by harness); settle/timeout use the
    noisy verifier ehat per spec. Instrument-aware settle: ||ehat|| <
    tol_new for SETTLE_M consecutive steps, not before MIN_STEPS. tol_old
    (Exp-19 relative tol) tracked as a secondary column with Exp-19's exact
    rule (3 consecutive steps, no min-step guard)."""
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
    consec = 0
    consec_old = 0
    settled_step = TIMEOUT
    settled = False
    settled_step_old = TIMEOUT
    de_hist, d2_hist = [], []
    for t in range(TIMEOUT):
        ehat = (T - X) + noise[t]
        ehat_n = float(np.linalg.norm(ehat))
        if t == 0:
            dehat = np.zeros(d); d2 = np.zeros(d)
        else:
            dehat = ehat - ehat_prev
            d2 = dehat - dehat_prev
        if return_histories:
            de_hist.append(dehat.copy()); d2_hist.append(d2.copy())
        dX = step_fn(ehat, dehat, d2, params, rng_dirs, t)
        dX_hist.append(dX)
        X = X + dX
        path += float(np.linalg.norm(dX))
        e_true = T - X
        e_true_n = float(np.linalg.norm(e_true))
        if e_true_n > e_true_prev and e_true_prev < n0:
            overshoot += 1
        e_true_prev = e_true_n
        ex = float(np.dot(X - T, u))
        if ex > excursion:
            excursion = ex
        ehat_prev = ehat
        dehat_prev = dehat
        # instrument-aware settle (primary)
        if ehat_n < tol_new:
            consec += 1
            if consec >= SETTLE_M and t >= MIN_STEPS and not settled:
                settled = True
                settled_step = t + 1
                if not full_horizon:
                    break
        else:
            consec = 0
        # Exp-19 relative tol (secondary, exact Exp-19 rule)
        if ehat_n < tol_old:
            consec_old += 1
            if consec_old >= SETTLE_K_OLD and settled_step_old == TIMEOUT:
                settled_step_old = t + 1
        else:
            consec_old = 0
    steps = settled_step
    cosines = []
    for i in range(1, len(dX_hist)):
        a, b = dX_hist[i - 1], dX_hist[i]
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        if na > 1e-300 and nb > 1e-300:
            cosines.append(float(a @ b / (na * nb)))
    dir_stab = float(np.mean(cosines)) if cosines else 0.0
    efficiency = path / (n0 + 1e-300)
    score = steps + LAM * overshoot + MU * efficiency
    out = {
        "steps": steps, "settled": settled, "overshoot": overshoot,
        "excursion": excursion, "dir_stab": dir_stab,
        "path": path, "efficiency": efficiency, "score": score,
        "steps_oldtol": settled_step_old,
        "e_true_final": e_true_n,
    }
    if return_histories:
        out["de_hist"] = np.stack(de_hist)
        out["d2_hist"] = np.stack(d2_hist)
    return out

SETTLE_K_OLD = 3  # Exp-19 rule: 3 consecutive steps under the relative tol

def direct_step(ehat, dehat, d2, params, rng_dirs, t):
    return params[0] * ehat

def tangent_step(ehat, dehat, d2, params, rng_dirs, t):
    return params[0] * ehat + params[1] * dehat + params[2] * d2

def permuted_step_factory(ref_de, ref_d2, perm):
    """History features from the reference trajectory at scrambled time
    indices. ref_de/ref_d2: (TIMEOUT, d); perm: fixed permutation of time."""
    def f(ehat, dehat, d2, params, rng_dirs, t):
        idx = int(perm[t])
        return params[0] * ehat + params[1] * ref_de[idx] + params[2] * ref_d2[idx]
    return f

# ---------------------------------------------------------------- learning (no teacher)
def eval_params(params, step_fns, trials, noise_bank):
    """Mean verifier score + mean efficiency over the tuning trials."""
    scores, effs = [], []
    for i, tr in enumerate(trials):
        r = run_trial(tr["X0"], tr["T"], step_fns[i], params,
                      tr["tol_new"], tr["tol_old"], noise_bank[i])
        scores.append(r["score"]); effs.append(r["efficiency"])
    return float(np.mean(scores)), float(np.mean(effs))

def random_config(ranges, rng):
    return np.array([rng.uniform(lo, hi) for lo, hi in ranges])

def perturb(p, ranges, rng):
    q = p.copy()
    i = int(rng.integers(0, len(p)))
    lo, hi = ranges[i]
    q[i] = float(np.clip(q[i] + rng.normal(0, 0.1 * (hi - lo)), lo, hi))
    return q

def hillclimb(step_fns, ranges, trials, noise_bank, rng):
    """Black-box hill-climbing, fixed budget. Returns best params + score."""
    best_p, best_s = None, np.inf
    per_restart = BUDGET // N_RESTART
    for _ in range(N_RESTART):
        p = random_config(ranges, rng)
        s, _ = eval_params(p, step_fns, trials, noise_bank)
        if s < best_s:
            best_p, best_s = p.copy(), s
        for _ in range(per_restart - 1):
            q = perturb(p, ranges, rng)
            sq, _ = eval_params(q, step_fns, trials, noise_bank)
            if sq < s:
                p, s = q, sq
            if sq < best_s:
                best_p, best_s = q.copy(), sq
    return best_p, best_s

# ---------------------------------------------------------------- measurement aggregation
def summarize(results):
    steps = [r["steps"] for r in results]
    med, q1, q3 = med_iqr(steps)
    emed, eq1, eq3 = med_iqr([r["efficiency"] for r in results])
    omed, oq1, oq3 = med_iqr([r["steps_oldtol"] for r in results])
    return {
        "steps_med": med, "steps_q1": q1, "steps_q3": q3,
        "steps_oldtol_med": omed,
        "timeout_rate": float(np.mean([0.0 if r["settled"] else 1.0 for r in results])),
        "overshoot_mean": float(np.mean([r["overshoot"] for r in results])),
        "excursion_mean": float(np.mean([r["excursion"] for r in results])),
        "dir_stab_mean": float(np.mean([r["dir_stab"] for r in results])),
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

    all_results = {"gate": "PASSED", "ladder": {str(k): v for k, v in ladder.items()}, "dims": {}}
    R1, R3 = [A_RANGE], [A_RANGE, B_RANGE, G_RANGE]

    for dim in DIMS_TO_RUN:
        print(f"\n{'='*60}\n== Exp 20 at {dim}D ==\n{'='*60}")
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
        tol_new = K_SIGMA * sigma * np.sqrt(dim)   # instrument-aware, same for all trials
        for t in trials:
            t["tol_new"] = tol_new
            t["tol_old"] = SETTLE_TOL_FRAC_OLD * t["eps0"]
        n_inside = sum(1 for t in trials if t["eps0"] < tol_new)
        print(f"24 trials, median|eps_0| = {np.median([t['eps0'] for t in trials]):.3f}, "
              f"sigma = {sigma:.4f}, instrument-aware tol = {tol_new:.4f} "
              f"({n_inside} trials start inside tol -> MIN_STEPS guard applies)")

        dim_res = {"sigma": sigma, "tol_new": float(tol_new), "folds": []}

        for fold in range(4):
            train_idx = [i for i, t in enumerate(trials) if t["chain"] != fold]
            held_idx = [i for i, t in enumerate(trials) if t["chain"] == fold]
            train = [trials[i] for i in train_idx]
            held = [trials[i] for i in held_idx]
            assert len(train) == 18 and len(held) == 6
            cname_held = CHAINS[fold][0]
            print(f"\n-- fold {fold}: held-out chain '{cname_held}' --")

            # pinned noise banks: common random numbers during tuning; fresh
            # pinned noise for final evaluation, shared across arms (fair).
            tune_rng = np.random.default_rng(SEED + 1000 + dim * 100 + fold)
            tune_noise = [tune_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in train]
            eval_rng = np.random.default_rng(SEED + 2000 + dim * 100 + fold)
            eval_noise_train = [eval_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in train]
            eval_noise_held = [eval_rng.normal(0, sigma, (TIMEOUT, dim)) for _ in held]
            # fixed per-trial permutations for the permuted arm (seeded)
            perm_rng = np.random.default_rng(SEED + 6000 + dim * 100 + fold)
            perms = {i: perm_rng.permutation(TIMEOUT) for i in range(24)}

            hc_rng = np.random.default_rng(SEED + 4000 + dim * 100 + fold)

            # arm 1: memoryless (tune first — its trajectory is the reference)
            mem_fns = [direct_step] * len(train)
            p_mem, s_mem = hillclimb(mem_fns, R1, train, tune_noise, hc_rng)
            print(f"  tuned memoryless: alpha={p_mem[0]:.4f}  (train score {s_mem:.2f})")

            # reference banks: tuned memoryless on the tune/eval noise, full horizon
            def ref_bank(trials_, noise_):
                refs = []
                for i, tr in enumerate(trials_):
                    r = run_trial(tr["X0"], tr["T"], direct_step, p_mem,
                                  tr["tol_new"], tr["tol_old"], noise_[i],
                                  full_horizon=True, return_histories=True)
                    refs.append((r["de_hist"], r["d2_hist"]))
                return refs
            ref_tune = ref_bank(train, tune_noise)

            # arm 2: real history
            hist_fns = [tangent_step] * len(train)
            p_hist, s_hist = hillclimb(hist_fns, R3, train, tune_noise, hc_rng)
            print(f"  tuned history   : alpha={p_hist[0]:+.4f} beta={p_hist[1]:+.4f} "
                  f"gamma={p_hist[2]:+.4f}  (train score {s_hist:.2f})")

            # arm 3: permuted history (same budget, same ranges, scrambled refs)
            perm_fns = [permuted_step_factory(ref_tune[i][0], ref_tune[i][1],
                                              perms[train_idx[i]])
                        for i in range(len(train))]
            p_perm, s_perm = hillclimb(perm_fns, R3, train, tune_noise, hc_rng)
            print(f"  tuned permuted  : alpha={p_perm[0]:+.4f} beta={p_perm[1]:+.4f} "
                  f"gamma={p_perm[2]:+.4f}  (train score {s_perm:.2f})")

            # final evaluation on fresh pinned noise (reference rebuilt per bank)
            ref_eval_train = ref_bank(train, eval_noise_train)
            ref_eval_held = ref_bank(held, eval_noise_held)

            def ev(trials_, idx_, noise_, refs_):
                out = {"memoryless": [], "history": [], "permuted": []}
                for j, tr in enumerate(trials_):
                    i = idx_[j]
                    out["memoryless"].append(run_trial(
                        tr["X0"], tr["T"], direct_step, p_mem,
                        tr["tol_new"], tr["tol_old"], noise_[j]))
                    out["history"].append(run_trial(
                        tr["X0"], tr["T"], tangent_step, p_hist,
                        tr["tol_new"], tr["tol_old"], noise_[j]))
                    pf = permuted_step_factory(refs_[j][0], refs_[j][1], perms[i])
                    out["permuted"].append(run_trial(
                        tr["X0"], tr["T"], pf, p_perm,
                        tr["tol_new"], tr["tol_old"], noise_[j]))
                return out
            ev_train = ev(train, train_idx, eval_noise_train, ref_eval_train)
            ev_held = ev(held, held_idx, eval_noise_held, ref_eval_held)

            fold_res = {
                "held_chain": cname_held,
                "p_mem": [float(v) for v in p_mem],
                "p_hist": [float(v) for v in p_hist],
                "p_perm": [float(v) for v in p_perm],
                "train": {k: summarize(v) for k, v in ev_train.items()},
                "held": {k: summarize(v) for k, v in ev_held.items()},
            }
            dim_res["folds"].append(fold_res)
            mh, hh, ph = (fold_res["held"]["memoryless"]["steps_med"],
                          fold_res["held"]["history"]["steps_med"],
                          fold_res["held"]["permuted"]["steps_med"])
            print(f"  held-out steps: memoryless={mh:.1f} history={hh:.1f} permuted={ph:.1f}")

        all_results["dims"][str(dim)] = dim_res

    # ---- pre-registered bar (4D, held-out):
    # (a) history < memoryless on steps, same direction all 4 folds
    # (b) history < permuted on steps, same direction all 4 folds
    print("\n== PRE-REGISTERED BAR (4D, held-out, median steps) ==")
    win_a, win_b = [], []
    for f, fr in enumerate(all_results["dims"]["4"]["folds"]):
        h, m, p = (fr["held"]["history"]["steps_med"],
                   fr["held"]["memoryless"]["steps_med"],
                   fr["held"]["permuted"]["steps_med"])
        wa, wb = h < m, h < p
        win_a.append(wa); win_b.append(wb)
        print(f"  fold {f} ({fr['held_chain']:>11}): hist {h:6.1f} vs mem {m:6.1f} "
              f"-> {'WIN' if wa else 'loss'} | hist {h:6.1f} vs perm {p:6.1f} "
              f"-> {'WIN' if wb else 'loss'}")
    bar = all(win_a) and all(win_b)
    print(f"  BAR: {'PASSED' if bar else 'NOT PASSED'} "
          f"((a) history<memoryless: {sum(win_a)}/4, (b) history<permuted: {sum(win_b)}/4)")
    all_results["bar"] = {"passed": bool(bar),
                          "wins_vs_memoryless": [bool(x) for x in win_a],
                          "wins_vs_permuted": [bool(x) for x in win_b]}

    # ---- beta diagnostics (pinned): per fold beta, sign, |beta|; across folds
    # variance + sign consistency, for the history and permuted arms
    print("\n== BETA DIAGNOSTICS (4D) ==")
    beta_diag = {}
    for arm, key in [("history", "p_hist"), ("permuted", "p_perm")]:
        betas = [fr[key][1] for fr in all_results["dims"]["4"]["folds"]]
        signs = [1 if b > 0 else (-1 if b < 0 else 0) for b in betas]
        diag = {
            "betas": [float(b) for b in betas],
            "signs": signs,
            "abs": [float(abs(b)) for b in betas],
            "var": float(np.var(betas)),
            "sign_consistency": f"{max(signs.count(1), signs.count(-1))}/4",
        }
        beta_diag[arm] = diag
        print(f"  {arm:>9}: beta={[f'{b:+.3f}' for b in betas]} "
              f"signs={signs} var={diag['var']:.4f} "
              f"sign-consistency={diag['sign_consistency']}")
    all_results["beta_diagnostics_4d"] = beta_diag

    # ---- detailed measurement tables
    for dim in DIMS_TO_RUN:
        dkey = str(dim)
        print(f"\n== DETAILED MEASUREMENTS ({dim}D, held-out) ==")
        for f, fr in enumerate(all_results["dims"][dkey]["folds"]):
            print(f"\nfold {f} held-out='{fr['held_chain']}' "
                  f"| p_mem={[f'{v:.4f}' for v in fr['p_mem']]} "
                  f"| p_hist={[f'{v:+.4f}' for v in fr['p_hist']]} "
                  f"| p_perm={[f'{v:+.4f}' for v in fr['p_perm']]}")
            for op in ["memoryless", "history", "permuted"]:
                s = fr["held"][op]
                print(f"  {op:>10}: steps {s['steps_med']:6.1f} "
                      f"[{s['steps_q1']:.0f},{s['steps_q3']:.0f}] "
                      f"(oldtol {s['steps_oldtol_med']:.0f}) to={s['timeout_rate']:.2f} | "
                      f"ovsh {s['overshoot_mean']:6.1f} exc {s['excursion_mean']:7.2f} | "
                      f"dstab {s['dir_stab_mean']:+.3f} | "
                      f"eff {s['eff_med']:.3f} [{s['eff_q1']:.2f},{s['eff_q3']:.2f}] n={s['n']}")

    # ---- Pareto table: time-to-settle vs path cost, independent axes
    print("\n== PARETO (4D, held-out medians per fold) ==")
    for f, fr in enumerate(all_results["dims"]["4"]["folds"]):
        row = " | ".join(
            f"{op[:4]}: steps={fr['held'][op]['steps_med']:.1f} "
            f"eff={fr['held'][op]['eff_med']:.3f}"
            for op in ["memoryless", "history", "permuted"])
        print(f"  fold {f} ({fr['held_chain']:>11}): {row}")

    with open(JSON_OUT, "w") as f:
        json.dump(all_results, f, indent=1)
    print(f"\nJSON saved: {JSON_OUT}")

    # ---- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ops = ["memoryless", "history", "permuted"]
        cols = ["tab:blue", "tab:green", "tab:orange"]
        labels = ["memoryless f(eps)", "real history f(eps,Deps,D2eps)",
                  "permuted history (control)"]

        for dim in DIMS_TO_RUN:
            dkey = str(dim)
            folds = all_results["dims"][dkey]["folds"]
            x = np.arange(4); w = 0.24

            fig, ax = plt.subplots(figsize=(9, 4.4))
            for j, op in enumerate(ops):
                meds = [f["held"][op]["steps_med"] for f in folds]
                ax.bar(x + (j - 1) * w, meds, w, color=cols[j], label=labels[j])
            ax.set_xticks(x); ax.set_xticklabels([f["held_chain"] for f in folds])
            ax.set_ylabel("median steps to settle (held-out chain)")
            ax.set_title(f"Exp 20 ({dim}D) — held-out steps to settle by fold\n"
                         f"(instrument-aware tol = {all_results['dims'][dkey]['tol_new']:.3f})")
            ax.legend(fontsize=8); fig.tight_layout()
            fig.savefig(f"{FIG_DIR}/exp20_steps_{dim}d.png", dpi=110); plt.close(fig)

            fig, ax = plt.subplots(figsize=(9, 4.4))
            for j, op in enumerate(ops):
                meds = [f["held"][op]["eff_med"] for f in folds]
                ax.bar(x + (j - 1) * w, meds, w, color=cols[j], label=labels[j])
            ax.set_xticks(x); ax.set_xticklabels([f["held_chain"] for f in folds])
            ax.set_ylabel("median path_length / |eps_0| (held-out chain)")
            ax.set_title(f"Exp 20 ({dim}D) — held-out path cost by fold (Pareto axis 2)")
            ax.legend(fontsize=8); fig.tight_layout()
            fig.savefig(f"{FIG_DIR}/exp20_efficiency_{dim}d.png", dpi=110); plt.close(fig)

        # beta diagnostics figure (4D)
        folds4 = all_results["dims"]["4"]["folds"]
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
        for ax, (arm, key, col) in zip(axes, [("real history", "p_hist", "tab:green"),
                                             ("permuted history", "p_perm", "tab:orange")]):
            xs = np.arange(4)
            betas = [f[key][1] for f in folds4]
            barcols = ["tab:green" if b < 0 else "tab:red" for b in betas]
            ax.bar(xs, betas, 0.5, color=barcols)
            ax.axhline(0, color="k", lw=0.8)
            ax.set_xticks(xs); ax.set_xticklabels([f["held_chain"] for f in folds4],
                                                  rotation=20, ha="right")
            ax.set_ylabel("tuned beta")
            ax.set_title(f"{arm}: beta per fold\n(green=damping<0, red=>0)")
        fig.suptitle("Exp 20 (4D) — beta sign stability: stable sign = transferable "
                     "dynamical term; flipping = tuner exploiting DOF")
        fig.tight_layout(); fig.savefig(f"{FIG_DIR}/exp20_beta_4d.png", dpi=110); plt.close(fig)

        # Pareto scatter (4D held-out medians)
        fig, ax = plt.subplots(figsize=(7.5, 5.2))
        for j, op in enumerate(ops):
            xs = [f["held"][op]["steps_med"] for f in folds4]
            ys = [f["held"][op]["eff_med"] for f in folds4]
            ax.scatter(xs, ys, s=90, color=cols[j], label=labels[j], zorder=3)
            for f, (xx, yy) in enumerate(zip(xs, ys)):
                ax.annotate(folds4[f]["held_chain"], (xx, yy), fontsize=7,
                            xytext=(4, 4), textcoords="offset points")
        ax.set_xlabel("median steps to settle (held-out)  [fewer = faster]")
        ax.set_ylabel("median path cost  [lower = cleaner]")
        ax.set_title("Exp 20 (4D) — Pareto: time-to-settle vs path cost\n"
                     "(lower-left dominates; no bundled scalar)")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp20_pareto_4d.png", dpi=110); plt.close(fig)

        # example trajectories: |e_true| vs t (cold -> hot)
        dim = 4
        P = Vt[:dim].T
        cw = {w: (((E_chain[i] - mu) @ P).mean(axis=0)) for i, w in enumerate(chain_words)}
        Tt, X0t = cw["hot"], cw["cold"]
        tol = all_results["dims"]["4"]["tol_new"]
        sigma = all_results["dims"]["4"]["sigma"]
        fr0 = all_results["dims"]["4"]["folds"][0]
        p_mem = np.array(fr0["p_mem"]); p_hist = np.array(fr0["p_hist"])
        p_perm = np.array(fr0["p_perm"])
        nz = np.random.default_rng(SEED + 777).normal(0, sigma, (TIMEOUT, dim))
        # reference for the permuted example: memoryless full-horizon run
        rr0 = run_trial(X0t, Tt, direct_step, p_mem, tol,
                        SETTLE_TOL_FRAC_OLD * float(np.linalg.norm(Tt - X0t)), nz,
                        full_horizon=True, return_histories=True)
        perm0 = np.random.default_rng(SEED + 6001).permutation(TIMEOUT)
        fig, ax = plt.subplots(figsize=(8.5, 4.2))
        arms = [("memoryless", direct_step, p_mem, "tab:blue"),
                ("history", tangent_step, p_hist, "tab:green"),
                ("permuted", permuted_step_factory(rr0["de_hist"], rr0["d2_hist"], perm0),
                 p_perm, "tab:orange")]
        for name, fn, prm, col in arms:
            X = X0t.copy().astype(np.float64)
            errs = [float(np.linalg.norm(Tt - X))]
            ehat_prev = None; dehat_prev = np.zeros(dim)
            for t in range(TIMEOUT):
                ehat = (Tt - X) + nz[t]
                dehat = np.zeros(dim) if t == 0 else ehat - ehat_prev
                d2 = np.zeros(dim) if t == 0 else dehat - dehat_prev
                X = X + fn(ehat, dehat, d2, prm, None, t)
                errs.append(float(np.linalg.norm(Tt - X)))
                ehat_prev, dehat_prev = ehat, dehat
                if float(np.linalg.norm(ehat)) < tol and t >= MIN_STEPS:
                    break
            ax.plot(errs, color=col, label=name)
        ax.axhline(tol, ls="--", color="k", lw=0.8, label="instrument-aware tol")
        ax.set_xlabel("step"); ax.set_ylabel("|eps| (true)")
        ax.set_title("Exp 20 (4D) — example trajectory: cold -> hot")
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(f"{FIG_DIR}/exp20_traj_4d.png", dpi=110); plt.close(fig)
        print("Figures saved: exp20_steps_{4,16}d.png, exp20_efficiency_{4,16}d.png, "
              "exp20_beta_4d.png, exp20_pareto_4d.png, exp20_traj_4d.png")
    except Exception as e:
        print(f"\n(figure generation skipped: {e})")

    return all_results


if __name__ == "__main__":
    res = main()
    print("\nDONE. gate =", res.get("gate"), "| bar =", res.get("bar", {}).get("passed"))
