"""Stage 1: GSM8K problem selection (frozen).

Filter (documented, pre-registered):
  F1. Reference answer contains '####' followed by a parseable numeric token
      (via the frozen parser in revision_measure.extract_final_number).
  F2. Question text is non-empty after stripping.
Excluded otherwise. No difficulty stratification for the 30-trajectory pilot
(per locked parameters 2026-10-07 ~12:03).

Selection: filter, then shuffle with numpy Generator(seed=1907), take first 30.
Output: problems.json with the filter spec recorded.
"""
import json
import re
import sys

import numpy as np

sys.path.insert(0, "/home/hatch/workspace/ai-theory")
from revision_measure import extract_final_number

SEED = 1907
N_SELECT = 30
SRC = "/home/hatch/workspace/ai-theory/revision_loop/gsm8k_test.jsonl"
OUT = "/home/hatch/workspace/ai-theory/revision_loop/problems.json"


def main():
    rows = []
    with open(SRC) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print(f"loaded {len(rows)} raw problems")

    kept = []
    dropped_no_hash = 0
    dropped_empty_q = 0
    dropped_unparseable = 0
    for r in rows:
        q = (r.get("question") or "").strip()
        a = r.get("answer") or ""
        if not q:
            dropped_empty_q += 1
            continue
        if "####" not in a:
            dropped_no_hash += 1
            continue
        if extract_final_number(a) is None:
            dropped_unparseable += 1
            continue
        kept.append({"question": q, "reference": a,
                     "ref_number": extract_final_number(a)})

    print(f"kept={len(kept)} dropped_no_hash={dropped_no_hash} "
          f"dropped_empty_q={dropped_empty_q} dropped_unparseable={dropped_unparseable}")

    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(kept))[:N_SELECT]
    selected = [kept[i] for i in idx]
    for i, s in enumerate(selected):
        s["traj_id"] = i
        s["select_index"] = int(idx[i])

    out = {
        "filter": {
            "F1": "reference contains '####' + parseable numeric token "
                  "(revision_measure.extract_final_number)",
            "F2": "non-empty question",
            "seed": SEED,
            "n_select": N_SELECT,
            "n_kept": len(kept),
            "n_raw": len(rows),
            "dropped": {"no_hash": dropped_no_hash,
                        "empty_q": dropped_empty_q,
                        "unparseable": dropped_unparseable},
        },
        "problems": selected,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {OUT} with {len(selected)} problems")


if __name__ == "__main__":
    main()
