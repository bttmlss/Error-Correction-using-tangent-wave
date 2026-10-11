#!/usr/bin/env python3
"""Evaluate locked-spec bars (a) and (c) on the 320-call Gemini ladder ledger.

Reads ../experiments/steerable_plant_stage0_gemini_ladder_ledger.csv
(requires prelock_bootstrap_sim.py alongside for the paired-cluster bootstrap).
Bar definitions: STEERABLE-PLANT-STAGE0-SPEC.md (locked 2026-10-07).
Bar (b) already ruled: word PASS (1.44), readability FAIL (11.87) — word only.
"""
import csv
import json
from pathlib import Path
import numpy as np
import numba
from scipy import stats
from prelock_bootstrap_sim import boot_ci, rank_avg, pearson_of

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "experiments" / "steerable_plant_stage0_gemini_ladder_ledger.csv"
OUT = HERE / "stage0_gemini_bar_eval.json"
LEVELS = [-60, -40, -20, -10, 10, 20, 40, 60]
N_BOOT = 10000


def parse_ledger(path):
    rows = []
    with open(path, newline="") as f:
        for d in csv.DictReader(f):
            rows.append(dict(u=int(d["u"]), t=int(d["trial"]), tpl=d["template"],
                             temp=float(d["temperature"]), text=int(d["text_id"]),
                             w0=int(d["starting_words"]), w=int(d["realized_words"]),
                             dw=int(d["realized_step"])))
    return rows


def check_structure(rows):
    issues = []
    if len(rows) != 320:
        issues.append(f"row count {len(rows)} != 320")
    seen = {}
    for r in rows:
        # step arithmetic
        if r["dw"] != r["w"] - r["w0"]:
            issues.append(f"step arithmetic mismatch at {r}")
        # starting words
        exp0 = 140 if r["u"] < 0 else 40
        if r["w0"] != exp0:
            issues.append(f"wrong start {r['w0']} for u={r['u']}")
        # temp schedule: {0.3,0.7,1.0}[t mod 3]
        if abs(r["temp"] - [0.3, 0.7, 1.0][r["t"] % 3]) > 1e-9:
            issues.append(f"temp schedule break at {r}")
        # text schedule: t mod 10
        if r["text"] != r["t"] % 10:
            issues.append(f"text schedule break at {r}")
        key = (r["u"], r["t"], r["tpl"])
        if key in seen:
            issues.append(f"duplicate trial {key}")
        seen[key] = r
    # pairing: each (u,t) has T1+T2 with same temp+text
    pairs = {}
    for r in rows:
        pairs.setdefault((r["u"], r["t"]), []).append(r)
    for k, v in pairs.items():
        if len(v) != 2 or {x["tpl"] for x in v} != {"T1", "T2"}:
            issues.append(f"pairing break at {k}")
        elif v[0]["temp"] != v[1]["temp"] or v[0]["text"] != v[1]["text"]:
            issues.append(f"pair temp/text mismatch at {k}")
    if len(pairs) != 160:
        issues.append(f"pair count {len(pairs)} != 160")
    return issues


def spearman(x, y):
    return float(stats.spearmanr(x, y).statistic)


def shuffled_null(u, dw, n_perm=10000, seed=7):
    """Faithful reading of the locked bar: 'permute u labels independently;
    |rho| must be < 0.15'. One representative shuffle (fixed seed) is the
    verdict statistic; the full permutation distribution is reported as
    context (a pipeline artifact would elevate the whole distribution, not
    just its far tail — max-over-10k is not the specified statistic).
    """
    rng = np.random.default_rng(seed)
    primary = abs(spearman(rng.permutation(u), dw))
    dist = np.empty(n_perm)
    for i in range(n_perm):
        dist[i] = abs(spearman(rng.permutation(u), dw))
    return {
        "primary_abs_rho": float(primary),
        "pass": bool(primary < 0.15),
        "dist_mean": float(dist.mean()),
        "dist_sd": float(dist.std(ddof=1)),
        "frac_ge_015": float((dist >= 0.15).mean()),
        "n_perm": n_perm,
        "seed": seed,
    }


def gain1_control(u, dw, n_sim=2000, seed=11):
    """Ideal plant realized = u + observed noise (resampled pooled residuals)."""
    rng = np.random.default_rng(seed)
    resid = dw - u
    out = {}
    for sign, m in (("neg", u < 0), ("pos", u > 0)):
        uu = u[m]; rr = []
        for _ in range(n_sim):
            eps = rng.choice(resid, size=m.sum(), replace=True)
            rr.append(spearman(uu, uu + eps))
        out[sign] = float(np.mean(rr))
    return out


def theil_sen(x, y):
    s, _, _, _ = stats.theilslopes(y, x)
    return float(s)


@numba.njit
def theil_sen_nb(x, y, buf):
    n = x.shape[0]
    c = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[j] - x[i]
            if dx != 0.0:
                buf[c] = (y[j] - y[i]) / dx
                c += 1
    s = np.sort(buf[:c])
    m = c // 2
    if c % 2 == 1:
        return s[m]
    return 0.5 * (s[m - 1] + s[m])


@numba.njit
def boot_ratio_ci(U, R1, R2, n_boot, seed, buf):
    T = U.shape[0]; K = U.shape[1]; n = T * K
    np.random.seed(seed)
    fu = np.empty(n); f1 = np.empty(n); f2 = np.empty(n)
    ratios = np.empty(n_boot)
    for b in range(n_boot):
        p = 0
        for j in range(T):
            t = np.random.randint(0, T)
            for k in range(K):
                fu[p] = U[t, k]; f1[p] = R1[t, k]; f2[p] = R2[t, k]
                p += 1
        s1 = theil_sen_nb(fu, f1, buf)
        s2 = theil_sen_nb(fu, f2, buf)
        ratios[b] = s1 / s2 if s2 != 0.0 else np.nan
    s = np.sort(ratios)
    return s[int(0.025 * n_boot)], s[int(0.975 * n_boot)]


def main():
    rows = parse_ledger(SRC)
    issues = check_structure(rows)
    res = {"n_rows": len(rows), "structure_issues": issues}

    U = np.array([r["u"] for r in rows], float)
    DW = np.array([r["dw"] for r in rows], float)
    TPL = np.array([r["tpl"] for r in rows])
    TEMP = np.array([r["temp"] for r in rows])
    TEXT = np.array([r["text"] for r in rows])

    bars_a = {}
    for tpl in ("T1", "T2"):
        m = TPL == tpl
        u, dw = U[m], DW[m]
        rho_pool = spearman(u, dw)
        # per-sign
        per_sign = {}
        for sign, sm in (("neg", u < 0), ("pos", u > 0)):
            per_sign[sign] = {
                "n": int(sm.sum()),
                "spearman": spearman(u[sm], dw[sm]),
                "theil_sen": theil_sen(u[sm], dw[sm]),
            }
        # gain-1 control bars
        ideal = gain1_control(u, dw)
        for sign in ("neg", "pos"):
            per_sign[sign]["rho_ideal"] = ideal[sign]
            per_sign[sign]["bar"] = ideal[sign] - 0.15
            per_sign[sign]["pass_proportion"] = bool(
                per_sign[sign]["spearman"] >= per_sign[sign]["bar"])
            per_sign[sign]["pass_gainband"] = bool(
                0.5 <= per_sign[sign]["theil_sen"] <= 1.5)
        # saturation per sign
        sat = {}
        for sign, sm in (("neg", u < 0), ("pos", u > 0)):
            med60 = float(np.median(np.abs(dw[sm & (np.abs(u) == 60)])))
            med40 = float(np.median(np.abs(dw[sm & (np.abs(u) == 40)])))
            sat[sign] = {"med60": med60, "med40": med40,
                         "pass": bool(med60 > med40)}
        # shuffled null
        null = shuffled_null(u, dw)
        # per-temperature rho (diagnostic)
        temp_rho = {str(t): spearman(u[TEMP[m] == t], dw[TEMP[m] == t])
                    for t in (0.3, 0.7, 1.0)}
        bars_a[tpl] = {
            "n": int(m.sum()),
            "pooled_spearman": rho_pool,
            "pass_direction": bool(rho_pool >= 0.70),
            "per_sign": per_sign,
            "saturation": sat,
            "shuffled_null": null,
            "per_temp_spearman": temp_rho,
        }
    res["bar_a"] = bars_a

    # ---- bar (c): paired cluster bootstrap ----
    # organize: texts 0..9 x 16 pairs (8 levels x trials t=c, c+10)
    Uc = np.zeros((10, 16)); R1 = np.zeros((10, 16)); R2 = np.zeros((10, 16))
    for c in range(10):
        k = 0
        for u in LEVELS:
            for t in (c, c + 10):
                r1 = next(r for r in rows if r["u"] == u and r["t"] == t
                          and r["tpl"] == "T1")
                r2 = next(r for r in rows if r["u"] == u and r["t"] == t
                          and r["tpl"] == "T2")
                Uc[c, k] = u; R1[c, k] = r1["dw"]; R2[c, k] = r2["dw"]
                k += 1
    lo, hi = boot_ci(Uc, R1, R2, N_BOOT, 20261010)
    # buffer must hold n*(n-1)/2 slopes for n=160 resampled points
    buf = np.empty(160 * 159 // 2)
    rlo, rhi = boot_ratio_ci(Uc, R1, R2, N_BOOT, 4242, buf)
    s1 = theil_sen(Uc.ravel(), R1.ravel())
    s2 = theil_sen(Uc.ravel(), R2.ravel())
    res["bar_c"] = {
        "n_boot": N_BOOT,
        "rho_T1": spearman(Uc.ravel(), R1.ravel()),
        "rho_T2": spearman(Uc.ravel(), R2.ravel()),
        "ci_lo": float(lo), "ci_hi": float(hi),
        "pass": bool(lo >= -0.10 and hi <= 0.10),
        "gain_ratio_point": float(s1 / s2),
        "gain_ratio_ci": [float(rlo), float(rhi)],
        "gain_ratio_in_diagnostic": bool(rlo >= 0.75 and rhi <= 1.33),
    }

    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1)[:3000])
    print("...")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
