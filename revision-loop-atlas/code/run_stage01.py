"""Stage 0.1 driver: CPL instrument fix + re-validation for the LLM Revision-Loop Atlas.

Authorized 2026-10-07 ~10:45 (spec: revision-loop-atlas-SPEC.md, "Stage 0.1" section).
ZERO LLM calls — pure synthetic re-validation.

Instrument: continuous piecewise-linear change-point
    e(t) = a + m1*t               for t <= tau
    e(t) = a + m1*tau + m2*(t-tau) for t >  tau
(4 params: a, m1, m2, tau; continuity at tau by construction.)
Dual-track Bar 0: Track A = deterministic exact-match solve flags;
Track B = CPL change-point on e(t) for continuous dynamics.

Strict gate (BOTH sides, Adrian's addition):
  (1) Null protection: single-regime synthetics >=95% one-regime at n=9.
  (2) Smooth-transition power: EACH of rate_change, stall_improve, give_up,
      reversal >= 0.90 kink recovery at n=9.
Plus: metric layer stays 9/9; solve flags deterministic (>=0.90).

Writes revision_stage01_results.json. Deterministic (seed 1907).
Exit code 0 always; the PASS/FAIL verdict is in the JSON and report.
"""

import json
import sys
import numpy as np

sys.path.insert(0, "/home/hatch/workspace/ai-theory")
from revision_stage0_cpl import (
    SEED, delta_bic_cpl, classify_cpl, detect_solve_transitions,
)
from revision_stage0 import (
    NOISE_LEVELS, synth_null, synth_kink, run_metric_layer,
)

rng = np.random.default_rng(SEED)
N_CALIB = 2000   # null trajectories per n for calibration (from scratch)
N_TEST = 1000    # fresh nulls per n for the >=95% test
N_KINK = 200     # reps per (kink kind, tau)
NS = list(range(5, 16))
PILOT_N = 9
CALIB_PCTL = 97  # operational threshold percentile (same convention as Stage 0)

# Gate kinds: the four smooth, CPL-representable transition classes.
SMOOTH_KINDS = ["rate_change", "stall_improve", "give_up", "reversal"]
# Informational only: breakthrough (0.35 level jump — NOT CPL-representable by
# design; falls between Track A (no exact zeros) and Track B (no jumps)) and
# weak_kink (detection-limit probe).
REPORT_KINDS = ["breakthrough", "weak_kink"]
FLAG_KINDS = ["solve", "solve_leave"]
TAUS = [2, 4, 6]

results = {"seed": SEED, "pilot_n": PILOT_N, "instrument": "CPL-continuous",
           "model": "e(t)=a+m1*t (t<=tau); a+m1*tau+m2*(t-tau) (t>tau); k=4"}

# ------------------------------------------------- 1. calibration from scratch
print("== 1. n-conditional calibration (from scratch, CPL model) ==", flush=True)
calib = {}
for n in NS:
    ds = np.array([delta_bic_cpl(synth_null(n, rng))[0] for _ in range(N_CALIB)])
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
    print(f"  n={n}: p50={c['p50']:.2f} p95={c['p95']:.2f} "
          f"p97={c['p97']:.2f} p99={c['p99']:.2f}", flush=True)
results["calibration"] = calib
results["threshold_n9"] = calib[str(PILOT_N)]["p97"]
results["threshold_percentile"] = CALIB_PCTL
thr9 = results["threshold_n9"]

# ------------------------------------------------- 2. null protection >=95%
print("== 2. fresh-null one-regime test ==", flush=True)
fresh = {}
for n in NS:
    thr = calib[str(n)]["p97"]
    ds = np.array([delta_bic_cpl(synth_null(n, rng))[0] for _ in range(N_TEST)])
    one = np.sum(~np.isfinite(ds)) + np.sum(ds <= thr)
    fresh[str(n)] = {"one_regime_frac": float(one / N_TEST), "n": N_TEST,
                     "thr": thr}
    print(f"  n={n}: one-regime frac={fresh[str(n)]['one_regime_frac']:.4f}",
          flush=True)
results["fresh_null_test"] = fresh
results["bar_null_pass"] = bool(fresh[str(PILOT_N)]["one_regime_frac"] >= 0.95)

# ------------------------------------------------- 3. smooth-transition power
print("== 3. kink recovery at n=9 (Track B) ==", flush=True)
rec = {}
for kind in SMOOTH_KINDS + REPORT_KINDS:
    rec[kind] = {}
    for tau in TAUS:
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
    print(f"  kink {kind}: " + ", ".join(
        f"tau={t} rec={rec[kind][str(t)]['recovery_frac']:.3f}" for t in TAUS),
        flush=True)
results["kink_recovery"] = rec
per_class = {k: float(np.mean([rec[k][str(t)]["recovery_frac"] for t in TAUS]))
             for k in SMOOTH_KINDS}
results["smooth_class_recovery"] = per_class
results["bar_power_pass"] = bool(all(v >= 0.90 for v in per_class.values()))
# breakthrough / weak_kink: informational
results["breakthrough_recovery"] = float(np.mean(
    [rec["breakthrough"][str(t)]["recovery_frac"] for t in TAUS]))
results["weak_kink_probe"] = {str(t): rec["weak_kink"][str(t)]["recovery_frac"]
                               for t in TAUS}

# ------------------------------------------------- 4. Track A: solve flags
print("== 4. Track A solve-flag determinism ==", flush=True)
flagrec = {}
for kind in FLAG_KINDS:
    flagrec[kind] = {}
    for tau in TAUS:
        hits = []
        for _ in range(N_KINK):
            y = synth_kink(PILOT_N, kind, tau, rng)
            taus = detect_solve_transitions(y)
            # synthetic convention: regime 1 = t <= tau -> first solved round tau+1
            hits.append(len(taus) >= 1 and taus[0] == tau + 1)
        flagrec[kind][str(tau)] = {"recovery_frac": float(np.mean(hits)),
                                   "n": N_KINK}
    print(f"  flag {kind}: " + ", ".join(
        f"tau={t} rec={flagrec[kind][str(t)]['recovery_frac']:.3f}" for t in TAUS),
        flush=True)
results["solve_flag_recovery"] = flagrec
results["bar_solveflag_pass"] = bool(
    np.mean([flagrec[k][str(t)]["recovery_frac"]
             for k in FLAG_KINDS for t in TAUS]) >= 0.90)

# ------------------------------------------------- 5. Track B characterization on solve curves
# (informational: what does the CPL detector do with a jump it cannot represent?
#  In real data Track A claims these first; this characterizes the interaction.)
print("== 5. Track B characterization on solve-event curves ==", flush=True)
tb = {}
for kind in FLAG_KINDS:
    tb[kind] = {}
    for tau in TAUS:
        twos, taus_hat = [], []
        for _ in range(N_KINK):
            y = synth_kink(PILOT_N, kind, tau, rng)
            two, d, th = classify_cpl(y, thr9)
            twos.append(two)
            taus_hat.append(th)
        tb[kind][str(tau)] = {
            "trackB_two_regime_frac": float(np.mean(twos)),
            "trackB_tau_median": float(np.median(
                [t for t in taus_hat if t is not None] or [np.nan])),
            "n": N_KINK,
        }
    print(f"  trackB on {kind}: " + ", ".join(
        f"tau={t} twofrac={tb[kind][str(t)]['trackB_two_regime_frac']:.3f}"
        for t in TAUS), flush=True)
results["trackB_on_solve_characterization"] = tb

# ------------------------------------------------- 6. metric layer re-run (must stay 9/9)
print("== 6. metric layer re-run ==", flush=True)
from revision_measure import EmbeddingModel, seed_all
seed_all(SEED)
emb = EmbeddingModel()
print("  model revision:", emb.revision, flush=True)
results["embedding_model"] = {"id": emb.model_id, "revision": emb.revision}
metric = run_metric_layer(emb)
results["metric_layer"] = metric
results["bar_metric_pass"] = bool(metric["pass"])
for k, v in metric["checks"].items():
    print(f"  metric {k}: {'PASS' if v else 'FAIL'}", flush=True)

# ------------------------------------------------- gate
results["checkpoint"] = {
    "bar_metric_9of9": results["bar_metric_pass"],
    "bar_null_95": results["bar_null_pass"],
    "bar_power_smooth_90_each": results["bar_power_pass"],
    "bar_solveflag_90": results["bar_solveflag_pass"],
    "PASS": bool(results["bar_metric_pass"] and results["bar_null_pass"]
                 and results["bar_power_pass"] and results["bar_solveflag_pass"]),
}

with open("/home/hatch/workspace/ai-theory/revision_stage01_results.json",
          "w") as f:
    json.dump(results, f, indent=1)
print("CHECKPOINT:", "PASS" if results["checkpoint"]["PASS"] else "FAIL",
      flush=True)
print("wrote revision_stage01_results.json", flush=True)
