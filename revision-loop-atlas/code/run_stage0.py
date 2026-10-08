"""Stage 0 driver: n-conditional calibration + temporal validation + metric layer.

Writes revision_stage0_results.json. Deterministic (seed 1907).
Exit code 0 always; the PASS/FAIL verdict is in the JSON and report.
"""

import json
import sys
import numpy as np

sys.path.insert(0, "/home/hatch/workspace/ai-theory")
from revision_stage0 import (
    SEED, NOISE_LEVELS, delta_bic, classify, synth_null, synth_kink,
    run_metric_layer,
)

rng = np.random.default_rng(SEED)
N_CALIB = 2000   # null trajectories per n for calibration
N_TEST = 1000    # fresh nulls per n for the >=95% test
N_KINK = 200     # reps per (kink kind, tau, noise)
NS = list(range(5, 16))
PILOT_N = 9
KINK_KINDS = ["breakthrough", "give_up", "rate_change", "weak_kink", "solve",
              "solve_leave", "stall_improve", "reversal"]
# (c) bar: realistic structural kinks. weak_kink is a detection-limit probe
# (reported separately, not in the bar). solve/solve_leave are characterized
# separately (measurement discreteness with exact zeros).
BAR_C_KINDS = ["breakthrough", "give_up", "rate_change", "stall_improve", "reversal"]
TAUS = {9: [2, 4, 6]}

results = {"seed": SEED, "pilot_n": PILOT_N}

# Operational threshold: p97 of the null per n (stricter than 1a's p95, deliberately:
# the (b) bar is stated at 95%, so calibrating at p97 gives the fresh-null test real
# margin while making the (c) kink-recovery bar harder. The tension between the two
# bars is the actual test of the detector. p95 is reported alongside for the table.)
CALIB_PCTL = 97
calib = {}
for n in NS:
    ds = np.array([delta_bic(synth_null(n, rng))[0] for _ in range(N_CALIB)])
    ds = ds[np.isfinite(ds)]
    calib[str(n)] = {
        "n": n,
        "p50": float(np.percentile(ds, 50)),
        "p95": float(np.percentile(ds, 95)),
        "p99": float(np.percentile(ds, 99)),
        "max": float(ds.max()),
        "p97": float(np.percentile(ds, 97)),
        "n_null": int(len(ds)),
    }
    print(f"calib n={n}: p50={calib[str(n)]['p50']:.2f} "
          f"p95={calib[str(n)]['p95']:.2f} p97={calib[str(n)]['p97']:.2f} "
          f"p99={calib[str(n)]['p99']:.2f}",
          flush=True)
results["calibration"] = calib
thr9 = calib[str(PILOT_N)]["p97"]
results["threshold_n9"] = thr9
results["threshold_percentile"] = CALIB_PCTL
results["threshold_n9"] = thr9
print(f"pilot n=9 calibrated threshold (p95): {thr9:.2f}", flush=True)

# ------------------------------------------------- (b) fresh-null >=95% test
fresh = {}
for n in NS:
    thr = calib[str(n)]["p97"]
    ds = np.array([delta_bic(synth_null(n, rng))[0] for _ in range(N_TEST)])
    one = np.sum(~np.isfinite(ds)) + np.sum(ds <= thr)
    fresh[str(n)] = {"one_regime_frac": float(one / N_TEST), "n": N_TEST,
                     "thr": thr}
    print(f"fresh null n={n}: one-regime frac={fresh[str(n)]['one_regime_frac']:.4f}",
          flush=True)
results["fresh_null_test"] = fresh
results["bar_b_pass"] = bool(fresh[str(PILOT_N)]["one_regime_frac"] >= 0.95)

# ------------------------------------------------- (c) kink recovery at n=9
rec = {}
for kind in KINK_KINDS:
    rec[kind] = {}
    for tau in TAUS[PILOT_N]:
        hits = []
        taus_hat = []
        for _ in range(N_KINK):
            y = synth_kink(PILOT_N, kind, tau, rng)
            two, d, th = classify(y, thr9)
            hits.append(two)
            taus_hat.append(th)
        rec[kind][str(tau)] = {
            "recovery_frac": float(np.mean(hits)),
            "tau_median": float(np.median([t for t in taus_hat if t is not None] or [np.nan])),
            "n": N_KINK,
        }
    print(f"kink {kind}: " +
          ", ".join(f"tau={t} rec={rec[kind][str(t)]['recovery_frac']:.3f}"
                    for t in TAUS[PILOT_N]), flush=True)
results["kink_recovery"] = rec
srec = np.mean([rec[k][str(t)]["recovery_frac"]
                for k in BAR_C_KINDS for t in TAUS[PILOT_N]])
results["structural_kink_recovery_pooled"] = float(srec)
results["bar_c_kinds"] = BAR_C_KINDS
results["bar_c_pass"] = bool(srec >= 0.90)
# weak kink: detection-limit probe (not in the bar)
results["weak_kink_probe"] = {t: rec["weak_kink"][t]["recovery_frac"]
                              for t in rec["weak_kink"]}
# solve events: characterization, not part of the bar
results["solve_characterization"] = {
    k: {t: rec[k][t]["recovery_frac"] for t in rec[k]} for k in ["solve", "solve_leave"]
}

# ------------------------------------------------- (a) metric layer
print("loading embedding model (pinned checkpoint)...", flush=True)
from revision_measure import EmbeddingModel, seed_all
seed_all(SEED)
emb = EmbeddingModel()
print("model revision:", emb.revision, flush=True)
results["embedding_model"] = {"id": emb.model_id, "revision": emb.revision}
metric = run_metric_layer(emb)
results["metric_layer"] = metric
results["bar_a_pass"] = bool(metric["pass"])
for k, v in metric["checks"].items():
    print(f"  metric {k}: {'PASS' if v else 'FAIL'}", flush=True)

results["checkpoint"] = {
    "bar_a_metric_exact": results["bar_a_pass"],
    "bar_b_null_95": results["bar_b_pass"],
    "bar_c_kink_90": results["bar_c_pass"],
    "PASS": bool(results["bar_a_pass"] and results["bar_b_pass"]
                 and results["bar_c_pass"]),
}
print("CHECKPOINT:", "PASS" if results["checkpoint"]["PASS"] else "FAIL", flush=True)

with open("/home/hatch/workspace/ai-theory/revision_stage0_results.json", "w") as f:
    json.dump(results, f, indent=1)
print("wrote revision_stage0_results.json", flush=True)
