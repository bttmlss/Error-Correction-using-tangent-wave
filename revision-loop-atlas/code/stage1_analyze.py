"""Stage 1 analysis: frozen measurement + validated 4-detector battery.

PRE-REGISTERED ONLY (Adrian's checkpoint rule):
1. Frozen measurement pipeline (revision_measure) on all rounds.
2. Validated 4-detector battery (Track A + B1 + B2 + B3) with Stage-0.2
   calibrated thresholds. B4 is DROPPED.
3. Informative-trajectory count for the frozen expansion criterion.
4. NO state labels. NO clustering. NO interpretation beyond preregistered
   quantities. Numbers first; the only permitted discovery statement is
   "single-regime inadequate" IF a detector fires clearly above its calibrated
   FPR — otherwise the null is reported plainly.

Calibrated thresholds (revision_stage02_results.json, frozen):
  B1: mean(e[3:9]) > 0.4 AND |OLS_slope| < 0.055
  B2: >=3 reversals with |de| > 0.10 on both sides
  B3: #{de>0} >= 5 AND (e[8]-e[0]) > 0.03
  Track A: exact[t-1]==False -> exact[t]==True for t in 1..8 (deterministic)
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, "/home/hatch/workspace/ai-theory")
from revision_measure import EmbeddingModel, error_trajectory, seed_all
import revision_stage02 as det

SEED = 1907
RAW = "/home/hatch/workspace/ai-theory/revision_loop/revision_loop_raw.jsonl"
OUT_JSON = "/home/hatch/workspace/ai-theory/revision_loop/revision_loop_results.json"
OUT_REPORT = "/home/hatch/workspace/ai-theory/REVISION-STAGE1-REPORT.md"

B1_S = 0.055
B2_AMP = 0.10
B3_T = 0.03


def main():
    seed_all(SEED)
    trajs = []
    with open(RAW) as f:
        for line in f:
            line = line.strip()
            if line:
                trajs.append(json.loads(line))
    print(f"loaded {len(trajs)} trajectories", flush=True)

    os.environ.setdefault(
        "LOCAL_MODEL_DIR",
        "/home/hatch/workspace/ai-theory/revision_loop/embed_model")
    emb = EmbeddingModel()
    print(f"embedding model: {emb.revision}", flush=True)

    E_all, X_all = [], []
    results = []
    for tr in trajs:
        answers = [r["answer"] for r in tr["rounds"]]
        sig = error_trajectory(answers, tr["reference"], emb)
        E_all.append(sig["e"])
        X_all.append(sig["exact"])
        results.append({
            "traj_id": tr["traj_id"],
            "select_index": tr["select_index"],
            "question": tr["question"],
            "reference": tr["reference"],
            "ref_number": tr["ref_number"],
            "model": tr["model"],
            "model_version": tr.get("model_version"),
            "seed": tr["seed"],
            "rounds": [
                {"round": r["round"], "answer": r["answer"],
                 "exact": sig["exact"][r["round"]],
                 "e": sig["e"][r["round"]],
                 "d": sig["d"][r["round"]],
                 "delta_e": sig["delta_e"][r["round"]],
                 "m": sig["m"][r["round"]],
                 "seed": r["seed"], "temperature": r["temperature"],
                 "eval_count": r.get("eval_count"),
                 "call_wall_s": r.get("call_wall_s"),
                 "call_error": r.get("call_error")}
                for r in tr["rounds"]
            ],
            "e": sig["e"],
            "delta_e": sig["delta_e"],
            "m": sig["m"],
            "exact": sig["exact"],
        })

    E_all = np.array(E_all)  # (M, 9)
    X_all = np.array(X_all, dtype=bool)
    M = len(results)
    print(f"measurement complete: {M} trajectories x {E_all.shape[1]} rounds",
          flush=True)

    # ---- Frozen 4-detector battery ----
    fire_A = det.trackA_fire(X_all)
    fire_B1 = det.b1_fire(E_all, B1_S)
    fire_B2 = det.b2_fire(E_all, B2_AMP)
    fire_B3 = det.b3_fire(E_all, B3_T)
    for i, tr in enumerate(results):
        tr["detectors"] = {
            "TrackA_solve": bool(fire_A[i]),
            "B1_stall": bool(fire_B1[i]),
            "B2_oscillation": bool(fire_B2[i]),
            "B3_divergence": bool(fire_B3[i]),
        }

    # ---- Informative trajectories (frozen expansion criterion) ----
    m_arr = np.array([r["m"] for r in results])
    de_arr = np.array([r["delta_e"] for r in results])
    informative = [bool(np.any((m_arr[i] > 0.05) & (np.abs(de_arr[i]) > 0.02)))
                   for i in range(M)]
    for i, tr in enumerate(results):
        tr["informative"] = informative[i]

    # ---- Aggregate counts vs calibrated FPR expectations ----
    counts = {
        "n_trajectories": M,
        "TrackA_solve": int(fire_A.sum()),
        "B1_stall": int(fire_B1.sum()),
        "B2_oscillation": int(fire_B2.sum()),
        "B3_divergence": int(fire_B3.sum()),
        "informative": int(sum(informative)),
    }
    # Expected false firings under null at calibrated FPR (n=30):
    # B1 3.7%, B2 3.1%, B3 0.0%, A 0.0% -> expected counts
    counts["expected_null_firings"] = {
        "TrackA_solve": 0.0 * M,
        "B1_stall": 0.037 * M,
        "B2_oscillation": 0.031 * M,
        "B3_divergence": 0.0 * M,
    }

    out = {
        "experiment": "revision-loop-atlas stage 1 pilot",
        "date": "2026-10-07",
        "spec": "revision-loop-atlas-SPEC.md (STAGE 1 AUTHORIZED 2026-10-07 ~12:03)",
        "model": "gemma2:2b (local Ollama, temperature 0)",
        "embedding_model": emb.revision,
        "seed_base": SEED,
        "detector_thresholds": {"B1_S": B1_S, "B2_AMP": B2_AMP, "B3_T": B3_T,
                                "B4": "DROPPED (curvature confound)"},
        "aggregate_counts": counts,
        "trajectories": results,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {OUT_JSON}", flush=True)
    print("aggregate:", json.dumps(counts, indent=1), flush=True)
    return out, counts


if __name__ == "__main__":
    main()
