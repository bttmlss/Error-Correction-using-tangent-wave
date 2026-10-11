#!/usr/bin/env python3
"""Pre-lock bootstrap simulation for bar (c) — compute-only, no LLM calls.

Simulates the paired-cluster bootstrap of spec bar (c):
  resample the N source texts with replacement; paired T1/T2 trials
  (same level, trial index) within; 95% CI on (rho_T1 - rho_T2);
  pass iff CI subset of [-0.10, +0.10].

Null case: T1 and T2 are two independent runs of the same gain-1 plant
  (+ a literal split-half variant) -> P(pass | null). Lock iff >= 0.8.
Positive controls (must FAIL equivalence = CI not inside +/-0.10):
  (a) T2 with 5x the noise, (b) T2 ignoring the command (pure noise).
  NOTE on an earlier draft: gain-halved T2 was tried as the positive control,
  but Spearman rho is scale-free, so it correctly passes equivalence at low
  noise. Bar (c) tests shape agreement, not gain (gain is bar (a)'s job) —
  so the positive controls must break the rank structure, not the scale.
"""
import numpy as np, json, time, sys
import numba

LEVELS = np.array([-60., -40., -20., -10., 10., 20., 40., 60.])
N_LEVELS = len(LEVELS)
DELTA = 0.10


@numba.njit
def rank_avg(x, out):
    n = x.shape[0]
    idx = np.argsort(x)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and x[idx[j + 1]] == x[idx[i]]:
            j += 1
        r = (i + j) * 0.5 + 1.0
        for k in range(i, j + 1):
            out[idx[k]] = r
        i = j + 1


@numba.njit
def pearson_of(rx, y, ry):
    n = y.shape[0]
    rank_avg(y, ry)
    mx = 0.0
    my = 0.0
    for i in range(n):
        mx += rx[i]
        my += ry[i]
    mx /= n
    my /= n
    sxy = 0.0
    sxx = 0.0
    syy = 0.0
    for i in range(n):
        dx = rx[i] - mx
        dy = ry[i] - my
        sxy += dx * dy
        sxx += dx * dx
        syy += dy * dy
    den = np.sqrt(sxx * syy)
    if den == 0.0:
        return np.nan
    return sxy / den


@numba.njit
def boot_ci(U, R1, R2, n_boot, seed):
    T = U.shape[0]
    K = U.shape[1]
    n = T * K
    np.random.seed(seed)
    fu = np.empty(n)
    f1 = np.empty(n)
    f2 = np.empty(n)
    ru = np.empty(n)
    r1 = np.empty(n)
    r2 = np.empty(n)
    diffs = np.empty(n_boot)
    for b in range(n_boot):
        p = 0
        for j in range(T):
            t = np.random.randint(0, T)
            for k in range(K):
                fu[p] = U[t, k]
                f1[p] = R1[t, k]
                f2[p] = R2[t, k]
                p += 1
        rank_avg(fu, ru)  # u ranked once; reused for both correlations
        diffs[b] = pearson_of(ru, f1, r1) - pearson_of(ru, f2, r2)
    s = np.sort(diffs)
    return s[int(0.025 * n_boot)], s[int(0.975 * n_boot)]


def gen_experiment(n_texts, kcell, sigma, text_gain_sd, mode, seed):
    rng = np.random.default_rng(seed)
    T, L, Kc = n_texts, N_LEVELS, kcell
    g_text = 1.0 + rng.normal(0.0, text_gain_sd, size=T)
    U = np.empty((T, L * Kc))
    R1 = np.empty((T, L * Kc))
    R2 = np.empty((T, L * Kc))
    for c in range(T):
        for l in range(L):
            uu = LEVELS[l]
            if mode == 'splithalf':
                draws = g_text[c] * uu + rng.normal(0.0, sigma, size=2 * Kc)
                for k in range(Kc):
                    j = l * Kc + k
                    U[c, j] = uu
                    R1[c, j] = draws[k]
                    R2[c, j] = draws[Kc + k]
                continue
            for k in range(Kc):
                j = l * Kc + k
                U[c, j] = uu
                R1[c, j] = g_text[c] * uu + rng.normal(0.0, sigma)
                if mode == 'null':
                    R2[c, j] = g_text[c] * uu + rng.normal(0.0, sigma)
                elif mode == 'noisy5x':
                    R2[c, j] = g_text[c] * uu + rng.normal(0.0, 5.0 * sigma)
                elif mode == 'ignore':
                    R2[c, j] = rng.normal(0.0, sigma)
    return U, R1, R2


def run_scenario(n_texts, kcell, sigma, text_gain_sd, mode, n_exp, n_boot, seed):
    rng = np.random.default_rng(seed)
    n_pass = 0
    widths = []
    for e in range(n_exp):
        U, R1, R2 = gen_experiment(n_texts, kcell, sigma, text_gain_sd, mode,
                                   seed=int(rng.integers(2**31)))
        lo, hi = boot_ci(U, R1, R2, n_boot, int(rng.integers(2**31)))
        if lo >= -DELTA and hi <= DELTA:
            n_pass += 1
        widths.append(hi - lo)
    return n_pass / n_exp, float(np.mean(widths))


def main():
    t0 = time.time()
    n_exp = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    n_boot = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    readability = len(sys.argv) > 3 and sys.argv[3] == "readability"
    global LEVELS, N_LEVELS
    if readability:
        # readability actuator: 4 levels, u>0 = easier; noise in Flesch points
        LEVELS = np.array([-20., -10., 10., 20.])
        N_LEVELS = len(LEVELS)
        sigmas = (3.0, 6.0)  # brackets bar (b)'s SD <= 6.7 cap
        kcell = 2            # 4 levels x 20 trials / 10 texts = 2 per cell
    else:
        sigmas = (5.0, 10.0, 15.0)
        kcell = 2
    # warm up numba
    U0, R10, R20 = gen_experiment(4, kcell, sigmas[0], 0.0, 'null', seed=1)
    boot_ci(U0, R10, R20, 20, 1)
    results = {}
    scenarios = []
    for sigma in sigmas:
        for tgsd in (0.0, 0.2):
            scenarios.append((f"null_10t_s{sigma:g}_tg{tgsd}", 10, kcell, sigma, tgsd, 'null'))
    if not readability:
        scenarios.append(("null_10t_splithalf_s10_tg0.2", 10, 2, 10.0, 0.2, 'splithalf'))
        for sigma in (5.0, 10.0, 15.0):
            scenarios.append((f"pos_noisy5x_10t_s{sigma:g}_tg0.2", 10, 2, sigma, 0.2, 'noisy5x'))
        scenarios.append(("pos_ignore_10t_s10_tg0.2", 10, 2, 10.0, 0.2, 'ignore'))
        for tgsd in (0.0, 0.2):
            scenarios.append((f"null_20t_s10_tg{tgsd}", 20, 3, 10.0, tgsd, 'null'))
    for label, nt, kc, sigma, tgsd, mode in scenarios:
        p, w = run_scenario(nt, kc, sigma, tgsd, mode, n_exp, n_boot,
                            seed=hash(label) % (2**31))
        results[label] = {"P_inside_pm0.10": p, "mean_ci_width": w,
                          "n_texts": nt, "sigma": sigma,
                          "text_gain_sd": tgsd, "mode": mode}
        print(f"{label}: P(inside)={p:.3f} mean_ci_width={w:.4f} "
              f"[{time.time()-t0:.0f}s]", flush=True)
    results["_meta"] = {"n_exp": n_exp, "n_boot": n_boot,
                        "note": "real analysis uses n_boot=10000; sim uses "
                                f"{n_boot} (decision only needs CI-width scale)",
                        "elapsed_s": time.time() - t0, "date": "2026-10-07"}
    out = ("/home/hatch/workspace/ai-theory/tangent_experiment/"
           + ("prelock_bootstrap_sim_results_readability.json"
              if readability else "prelock_bootstrap_sim_results.json"))
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print("wrote", out)


if __name__ == "__main__":
    main()
