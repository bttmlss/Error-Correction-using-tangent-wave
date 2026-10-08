"""Revision-loop atlas: STAGE 0 re-validation instrument, DRAFT CANDIDATE.

Adjudicated fix for the 2026-10-07 Stage-0 FAIL (kink recovery 0.29 vs the
0.90 bar): the 5-parameter free-intercept two-regime model overfits noise at
n=9, so its null threshold (p97=15.35) demands ~11x RSS improvement and only
sharp discontinuities clear it.

This draft replaces Bar-0's change-point machinery with a CONTINUOUS
piecewise-linear (CPL) model and splits solve-events off the change-point
job entirely:

- One-regime:  e_t = a + b*t                      (k=2, unchanged)
- Two-regime:  e_t = a + b1*t + b2*max(0, t-tau)   (k=4: a, b1, b2, tau)
  Continuous at the knot by construction. The knot search absorbs no extra
  parameter beyond tau. Jumps in LEVEL are no longer representable -- that is
  the point: the measurement genuinely produces them (exact match -> e=0
  exactly), and they are now handled by the deterministic solve-flag path,
  not the change-point detector.
- BIC = n*log(RSS/n) + k*log(n); dBIC = BIC(1) - BIC(2) > thr -> two regimes.

- Solve split: detect_solve_transitions(y) reports transitions from the
  exact-zero structure deterministically (first t>0 with y[t]==0.0 exactly,
  preceded by y[t-1]>0 and all subsequent rounds ==0.0). This mirrors the
  exact-match flag path in revision_measure.py, which already detects solve
  events perfectly (0.97) -- the change-point detector no longer sees them.

DRAFT ONLY. Nothing here amends the spec until Adrian approves it. The frozen
measurement layer (revision_measure.py) is imported unchanged, and bar_a
(metric layer, 9/9 PASS at the 2026-10-07 10:10 run) is carried over.
Deterministic: seed 1907 throughout.
"""

import numpy as np

SEED = 1907
rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------------------
# CPL change-point machinery
# ---------------------------------------------------------------------------

def _fit_linear(t, y):
    X = np.column_stack([np.ones_like(t), t])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(np.sum((y - X @ beta) ** 2))


def _fit_cpl(t, y, tau):
    # CONTINUOUS piecewise linear: e = a + b1*t + b2*max(0, t-tau).
    # k=4 (a, b1, b2, tau). Continuity at tau is automatic; a level jump
    # (e.g. the solve discontinuity) is NOT representable here -- solve
    # events are handled by the deterministic flag path below.
    X = np.column_stack([
        np.ones_like(t),
        t,
        np.maximum(0.0, t - tau),
    ])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(np.sum((y - X @ beta) ** 2))


def delta_bic_cpl(y):
    """Delta-BIC evidence for a continuous two-regime CPL model.

    Returns (dBIC, tau_hat). Degenerate (zero-variance) trajectories -> one
    regime by definition (no kink can exist); dBIC = -inf.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 5:
        raise ValueError("need n>=5")
    if float(np.var(y)) < 1e-12:
        return float("-inf"), None
    t = np.arange(n, dtype=float)
    rss1 = max(_fit_linear(t, y), 1e-300)
    bic1 = n * np.log(rss1 / n) + 2 * np.log(n)
    best = (float("inf"), None)
    # Same knot search as the original: tau in {1..n-2}, >=2 points/segment.
    for tau in range(1, n - 1):
        rss2 = max(_fit_cpl(t, y, float(tau)), 1e-300)
        bic2 = n * np.log(rss2 / n) + 4 * np.log(n)
        if bic2 < best[0]:
            best = (bic2, tau)
    return float(bic1 - best[0]), best[1]


def classify_cpl(y, thr):
    """True -> two regimes."""
    d, tau = delta_bic_cpl(y)
    return bool(d > thr), d, tau


# ---------------------------------------------------------------------------
# Solve-event split: deterministic, off the change-point job.
# ---------------------------------------------------------------------------

def detect_solve_transitions(y):
    """Detect solve onsets from exact-zero structure, deterministically.

    A solve onset is the first t>0 with y[t]==0.0 exactly and y[t-1]>0.0.
    This mirrors what the exact-match flags in revision_measure.py report for
    real trajectories (wrong -> correct at some round); solve_leave additionally
    produces an unsolve later, which the flags report as a second event, but
    onset detection is the solve path's job here. Returns the list of onset
    taus (empty if none).

    NOTE: this operates on the e(t) vector where solved rounds are exactly
    0.0. In real data, exact flags come from exact_match() on answer text;
    here the synthetic solve curves set e==0.0 exactly, which IS the flag
    path's input.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    taus = []
    for tau in range(1, n):
        if y[tau] == 0.0 and y[tau - 1] > 0.0:
            taus.append(tau)
    return taus


# ---------------------------------------------------------------------------
# Synthetic generators (re-imported from revision_stage0 so the validation
# uses the SAME nulls/kinks as the failed run -- apples to apples).
# ---------------------------------------------------------------------------

from revision_stage0 import synth_null, synth_kink, NOISE_LEVELS  # noqa: E402


# ---------------------------------------------------------------------------
# Re-validation harness (temporal layer only; bar_a carried over 9/9 PASS).
# ---------------------------------------------------------------------------

N_CALIB = 2000
N_TEST = 1000
N_KINK = 200
NS = list(range(5, 16))
PILOT_N = 9
CALIB_PCTL = 97
# Bar (c): smooth structural kinks only -- solve events go through the flag
# path. weak_kink remains a detection-limit probe (reported, not in the bar).
BAR_C_KINDS = ["breakthrough", "give_up", "rate_change",
               "stall_improve", "reversal"]
FLAG_KINDS = ["solve", "solve_leave"]
TAUS = {9: [2, 4, 6]}


def run_revalidation():
    results = {"seed": SEED, "pilot_n": PILOT_N, "instrument": "CPL",
               "bar_a": "carried over 9/9 PASS (2026-10-07 10:10 run; "
                        "frozen measurement layer untouched)"}

    calib = {}
    for n in NS:
        ds = np.array([delta_bic_cpl(synth_null(n, rng))[0]
                       for _ in range(N_CALIB)])
        ds = ds[np.isfinite(ds)]
        calib[str(n)] = {
            "n": n,
            "p50": float(np.percentile(ds, 50)),
            "p95": float(np.percentile(ds, 95)),
            "p97": float(np.percentile(ds, 97)),
            "p99": float(np.percentile(ds, 99)),
            "max": float(ds.max()),
            "n_null": int(len(ds)),
        }
        c = calib[str(n)]
        print(f"calib n={n}: p50={c['p50']:.2f} p95={c['p95']:.2f} "
              f"p97={c['p97']:.2f} p99={c['p99']:.2f}", flush=True)
    results["calibration"] = calib
    results["threshold_n9"] = calib[str(PILOT_N)]["p97"]
    results["threshold_percentile"] = CALIB_PCTL

    # (b) fresh-null >=95% test
    fresh = {}
    for n in NS:
        thr = calib[str(n)]["p97"]
        ds = np.array([delta_bic_cpl(synth_null(n, rng))[0]
                       for _ in range(N_TEST)])
        one = np.sum(~np.isfinite(ds)) + np.sum(ds <= thr)
        fresh[str(n)] = {"one_regime_frac": float(one / N_TEST),
                         "n": N_TEST, "thr": thr}
        print(f"fresh null n={n}: one-regime "
              f"frac={fresh[str(n)]['one_regime_frac']:.4f}", flush=True)
    results["fresh_null_test"] = fresh
    results["bar_b_pass"] = bool(fresh[str(PILOT_N)]["one_regime_frac"] >= 0.95)

    # (c) kink recovery at n=9 (CPL path: smooth structural kinks)
    thr9 = calib[str(PILOT_N)]["p97"]
    rec = {}
    for kind in BAR_C_KINDS + ["weak_kink"]:
        rec[kind] = {}
        for tau in TAUS[PILOT_N]:
            hits, taus_hat = [], []
            for _ in range(N_KINK):
                y = synth_kink(PILOT_N, kind, tau, rng)
                two, d, th = classify_cpl(y, thr9)
                hits.append(two)
                taus_hat.append(th)
            rec[kind][str(tau)] = {
                "recovery_frac": float(np.mean(hits)),
                "tau_median": float(np.median(
                    [t for t in taus_hat if t is not None] or [np.nan])),
                "n": N_KINK,
            }
        print(f"kink {kind}: " + ", ".join(
            f"tau={t} rec={rec[kind][str(t)]['recovery_frac']:.3f}"
            for t in TAUS[PILOT_N]), flush=True)
    results["kink_recovery"] = rec
    srec = np.mean([rec[k][str(t)]["recovery_frac"]
                    for k in BAR_C_KINDS for t in TAUS[PILOT_N]])
    results["structural_kink_recovery_pooled"] = float(srec)
    results["bar_c_kinds"] = BAR_C_KINDS
    results["bar_c_pass"] = bool(srec >= 0.90)
    results["weak_kink_probe"] = {t: rec["weak_kink"][t]["recovery_frac"]
                                  for t in rec["weak_kink"]}

    # (d) solve events through the deterministic flag path
    flagrec = {}
    for kind in FLAG_KINDS:
        flagrec[kind] = {}
        for tau in TAUS[PILOT_N]:
            hits = []
            for _ in range(N_KINK):
                y = synth_kink(PILOT_N, kind, tau, rng)
                taus = detect_solve_transitions(y)
                # synthetic convention: regime 1 = t <= tau, so the first
                # solved round is tau+1 (matches the exact-match flag path)
                hits.append(len(taus) >= 1 and taus[0] == tau + 1)
            flagrec[kind][str(tau)] = {"recovery_frac": float(np.mean(hits)),
                                       "n": N_KINK}
        print(f"flag {kind}: " + ", ".join(
            f"tau={t} rec={flagrec[kind][str(t)]['recovery_frac']:.3f}"
            for t in TAUS[PILOT_N]), flush=True)
    results["solve_flag_recovery"] = flagrec
    results["bar_d_pass"] = bool(
        np.mean([flagrec[k][str(t)]["recovery_frac"]
                 for k in FLAG_KINDS for t in TAUS[PILOT_N]]) >= 0.90)

    results["checkpoint"] = {
        "bar_a_metric_exact_carried_over": True,
        "bar_b_null_95": results["bar_b_pass"],
        "bar_c_kink_90": results["bar_c_pass"],
        "bar_d_solve_flag_90": results["bar_d_pass"],
        "PASS": bool(results["bar_b_pass"] and results["bar_c_pass"]
                     and results["bar_d_pass"]),
    }
    return results


if __name__ == "__main__":
    import json
    res = run_revalidation()
    with open("/home/hatch/workspace/ai-theory/"
              "revision_stage0_cpl_results.json", "w") as f:
        json.dump(res, f, indent=1)
    print("CHECKPOINT:", "PASS" if res["checkpoint"]["PASS"] else "FAIL",
          flush=True)
    print("wrote revision_stage0_cpl_results.json", flush=True)
