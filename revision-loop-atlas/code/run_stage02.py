"""Stage 0.2 driver: calibrate detectors on nulls, validate on nulls + patterns.

Order (frozen): (1) generate null family, split cal/valid; (2) calibrate
thresholds on cal-half nulls ONLY to achieve <=5% FPR; (3) freeze; (4) report FPR
on valid-half nulls (per-detector + family-wise); (5) measure recovery on
independent gross-pattern synthetics; (6) gate verdict. No peeking at pattern
synthetics during calibration. Deterministic seed 1907.
"""

import json
import sys
import numpy as np

sys.path.insert(0, "/home/hatch/workspace/ai-theory")
from revision_stage02 import (
    SEED, N, gen_nulls, gen_stress_nulls, gen_patterns, gen_solve_patterns,
    b1_fire, b2_fire, b3_fire, b4_fire, trackA_fire,
)

rng = np.random.default_rng(SEED)
OUT = {}

# ---------- 1. Null family ----------
Ynull = gen_nulls(SEED + 1, n_per_cell=1500)          # (36000, 9)
idx = rng.permutation(len(Ynull))
Ycal, Yval = Ynull[idx[:18000]], Ynull[idx[18000:]]
Ystress = gen_stress_nulls(SEED + 2, n_per_cell=1500)  # gray zone, documented only
OUT["null_family"] = {
    "forms": ["exponential a*rho^t", "linear a-b*t"],
    "a": [0.6, 0.9], "rho": [0.85, 0.92], "b": [0.05, 0.10],
    "sigmas": [0.02, 0.05, 0.10], "n": 9,
    "n_cal": len(Ycal), "n_val": len(Yval), "n_stress": len(Ystress),
    "note": ("Null = unambiguous single-regime improvement. Very slow decays "
             "are a gray zone (stress subset, reported separately, not gated)."),
}

# ---------- 2. Calibration on cal-half nulls ----------
cal = {}
# B1: largest S with FPR <= 5%
S_grid = np.arange(0.005, 0.081, 0.005)
S_pick, fpr_at = None, None
for S in sorted(S_grid, reverse=True):
    f = float(b1_fire(Ycal, S).mean())
    if f <= 0.05:
        S_pick, fpr_at = float(S), f
        break
cal["B1"] = {"S_grid": [float(x) for x in S_grid],
             "S_frozen": S_pick, "fpr_cal": fpr_at}
# B2: smallest AMP with FPR <= 5%
AMP_grid = [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]
AMP_pick, fpr_at = None, None
for AMP in sorted(AMP_grid):
    f = float(b2_fire(Ycal, AMP).mean())
    if f <= 0.05:
        AMP_pick, fpr_at = float(AMP), f
        break
cal["B2"] = {"AMP_grid": AMP_grid, "AMP_frozen": AMP_pick, "fpr_cal": fpr_at}
# B3: smallest T with FPR <= 5%
T_grid = [0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30]
T_pick, fpr_at = None, None
for T in sorted(T_grid):
    f = float(b3_fire(Ycal, T).mean())
    if f <= 0.05:
        T_pick, fpr_at = float(T), f
        break
cal["B3"] = {"T_grid": T_grid, "T_frozen": T_pick, "fpr_cal": fpr_at}
# B4: fixed (Stage 0.1 threshold + |dslope| gate); measure only
cal["B4"] = {"note": "fixed: CPL dBIC>13.89 AND |Δslope|>=3σ̂; no calibration",
             "fpr_cal": float(b4_fire(Ycal).mean())}
OUT["calibration"] = cal
print("CALIBRATED:", {k: (v.get("S_frozen", v.get("AMP_frozen", v.get("T_frozen", "fixed"))),
                          round(v["fpr_cal"], 4)) for k, v in cal.items()})

# ---------- 3/4. Validation: FPR on valid-half nulls ----------
S, AMP, T = cal["B1"]["S_frozen"], cal["B2"]["AMP_frozen"], cal["B3"]["T_frozen"]
fpr = {}
fpr["B1"] = float(b1_fire(Yval, S).mean()) if S else None
fpr["B2"] = float(b2_fire(Yval, AMP).mean()) if AMP else None
fpr["B3"] = float(b3_fire(Yval, T).mean()) if T else None
fpr["B4"] = float(b4_fire(Yval).mean())
# Track A on nulls (no solve flags -> never fires by construction)
fpr["TrackA"] = 0.0
fires = np.zeros(len(Yval), dtype=bool)
if S: fires |= b1_fire(Yval, S)
if AMP: fires |= b2_fire(Yval, AMP)
if T: fires |= b3_fire(Yval, T)
fires |= b4_fire(Yval)
fpr["family_wise"] = float(fires.mean())
# stress subset (documented, not gated)
fpr_stress = {}
if S: fpr_stress["B1"] = float(b1_fire(Ystress, S).mean())
if AMP: fpr_stress["B2"] = float(b2_fire(Ystress, AMP).mean())
if T: fpr_stress["B3"] = float(b3_fire(Ystress, T).mean())
fpr_stress["B4"] = float(b4_fire(Ystress).mean())
OUT["null_fpr_valid"] = fpr
OUT["null_fpr_stress"] = fpr_stress
print("VALID FPR:", {k: round(v, 4) if v is not None else None for k, v in fpr.items()})
print("STRESS FPR:", {k: round(v, 4) for k, v in fpr_stress.items()})

# ---------- 5. Recovery on gross-pattern synthetics ----------
P = gen_patterns(SEED + 3, n_per_cell=400)
flags, es = gen_solve_patterns(SEED + 4, n_per_cell=400)
rec = {}
# B1 on stalls (both variants pooled)
Ystall = np.vstack([P["stall_flat"], P["stall_improve"]])
rec["stall_B1"] = float(b1_fire(Ystall, S).mean()) if S else None
# B2 on oscillation
rec["oscillation_B2"] = float(b2_fire(P["oscillation"], AMP).mean()) if AMP else None
# B3 on divergence
rec["divergence_B3"] = float(b3_fire(P["divergence"], T).mean()) if T else None
# Track A on solve patterns (has-transition vs never-solves)
has_solve = np.array([True] * 800 + [False] * 400)
rec["solve_TrackA_recovery"] = float(trackA_fire(flags[has_solve]).mean())
rec["solve_TrackA_fpr"] = float(trackA_fire(flags[~has_solve]).mean())
# B4 on large kinks (only where |Δslope| >= 3σ, i.e. its defined operating region)
Yk, params = P["large_kink"]
ok = []
for y, (dsl, sig) in zip(Yk, params):
    if dsl >= 3 * sig:  # above SNR boundary: B4's operating region
        ok.append(b4_fire(y[None])[0])
rec["large_kink_B4_recovery"] = float(np.mean(ok)) if ok else None
rec["large_kink_B4_n"] = len(ok)
# per-noise breakdowns for the report
def by_sigma(Y, fire_fn, n_per_cell=400, n_variants=2):
    out = {}
    # layout: variants outer, sigmas inner (see gen_patterns)
    idx = 0
    for v in range(n_variants):
        for si, sig in enumerate([0.02, 0.05, 0.10]):
            blk = Y[idx:idx + n_per_cell]; idx += n_per_cell
            out.setdefault(f"sigma_{sig}", []).append(float(fire_fn(blk).mean()))
    return {k: [round(x, 3) for x in v] for k, v in out.items()}
rec["by_sigma"] = {
    "stall_flat_B1": by_sigma(P["stall_flat"], lambda b: b1_fire(b, S), n_variants=2) if S else None,
    "stall_improve_B1": by_sigma(P["stall_improve"], lambda b: b1_fire(b, S), n_variants=1) if S else None,
    "oscillation_B2": by_sigma(P["oscillation"], lambda b: b2_fire(b, AMP), n_variants=2) if AMP else None,
    "divergence_B3": by_sigma(P["divergence"], lambda b: b3_fire(b, T), n_variants=2) if T else None,
}
OUT["recovery"] = rec
print("RECOVERY:", {k: (round(v, 3) if isinstance(v, float) else v)
                    for k, v in rec.items() if k != "by_sigma"})

# ---------- 6. Gate ----------
per_det_ok = all([
    fpr["B1"] is not None and fpr["B1"] <= 0.05,
    fpr["B2"] is not None and fpr["B2"] <= 0.05,
    fpr["B3"] is not None and fpr["B3"] <= 0.05,
    fpr["B4"] <= 0.05,
    fpr["TrackA"] <= 0.05,
])
fam = fpr["family_wise"]
fam_ok_or_documented = fam <= 0.15
rec_ok = all([
    rec["stall_B1"] is not None and rec["stall_B1"] >= 0.90,
    rec["oscillation_B2"] is not None and rec["oscillation_B2"] >= 0.90,
    rec["divergence_B3"] is not None and rec["divergence_B3"] >= 0.90,
    rec["solve_TrackA_recovery"] >= 0.90,
])
gate = {
    "per_detector_fpr_le_5": bool(per_det_ok),
    "family_wise_fpr": round(fam, 4),
    "family_wise_le_15": bool(fam_ok_or_documented),
    "recovery_ge_90_per_class": bool(rec_ok),
    "PASS": bool(per_det_ok and fam_ok_or_documented and rec_ok),
}
OUT["gate"] = gate
print("GATE:", gate)

with open("/home/hatch/workspace/ai-theory/revision_stage02_results.json", "w") as f:
    json.dump(OUT, f, indent=1)
print("saved -> revision_stage02_results.json")
