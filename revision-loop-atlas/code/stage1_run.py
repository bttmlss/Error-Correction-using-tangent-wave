"""Stage 1: LLM revision-loop pilot — generation driver.

LOCKED (Adrian 2026-10-07 ~12:03):
- Model: local Ollama gemma2:2b, temperature 0, seed = 1907 + traj_id.
- 30 trajectories x 9 rounds (round 0 = initial) = 270 calls max.
- Round 0 prompt: solve + show reasoning.
- Rounds 1..8: SAME neutral revision prompt every round, verbatim:
  "Review your previous answer and revise it if you think it is wrong."
  (with the original question and previous answer as context — neutral scaffolding,
  no hints, no target leaked, no steering)

Checkpointing: results appended per-trajectory to revision_loop_raw.jsonl;
reruns resume from the checkpoint. Each call retried up to 3x on failure.

Deterministic: temperature 0, fixed per-trajectory seed. Model version recorded.
"""

import json
import os
import sys
import time
import urllib.request

SEED_BASE = 1907
N_ROUNDS = 9  # round 0 = initial, rounds 1..8 = revisions
MAX_CALLS = 270
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = "gemma2:2b"
NUM_PREDICT = 512
NUM_CTX = 2048
CALL_TIMEOUT_S = 600
RETRIES = 3

PROBLEMS = "/home/hatch/workspace/ai-theory/revision_loop/problems.json"
RAW_OUT = "/home/hatch/workspace/ai-theory/revision_loop/revision_loop_raw.jsonl"

ROUND0_TEMPLATE = (
    "Solve the following math problem. Show your reasoning step by step.\n\n{question}"
)
REVISE_TEMPLATE = (
    "Original problem:\n{question}\n\n"
    "Your previous answer:\n{prev_answer}\n\n"
    "Review your previous answer and revise it if you think it is wrong."
)


def ollama_generate(prompt: str, seed: int) -> dict:
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "seed": seed,
            "num_predict": NUM_PREDICT,
            "num_ctx": NUM_CTX,
        },
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    last_err = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=CALL_TIMEOUT_S) as resp:
                out = json.loads(resp.read().decode())
            dt = time.time() - t0
            return {
                "response": out.get("response", ""),
                "done": out.get("done", False),
                "eval_count": out.get("eval_count"),
                "eval_duration_ns": out.get("eval_duration"),
                "wall_s": dt,
                "attempt": attempt + 1,
            }
        except Exception as e:  # noqa: BLE001 - retry transient failures
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(5 * (attempt + 1))
    return {"response": "", "done": False, "error": last_err,
            "wall_s": time.time() - t0, "attempt": RETRIES}


def load_checkpoint():
    done = {}
    if os.path.exists(RAW_OUT):
        with open(RAW_OUT) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    done[rec["traj_id"]] = rec
    return done


def main():
    with open(PROBLEMS) as f:
        problems = json.load(f)["problems"]
    done = load_checkpoint()
    print(f"problems={len(problems)} already_done={len(done)}", flush=True)

    # Record model version once
    model_version = None
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/show",
            data=json.dumps({"model": MODEL}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            info = json.loads(resp.read().decode())
        model_version = info.get("modelinfo", {})
    except Exception as e:  # noqa: BLE001
        print(f"WARN: could not fetch model info: {e}", flush=True)

    n_calls = 0
    t_run0 = time.time()
    with open(RAW_OUT, "a") as out:
        for prob in problems:
            tid = prob["traj_id"]
            if tid in done:
                continue
            seed = SEED_BASE + tid
            rounds = []
            prev_answer = None
            for rnd in range(N_ROUNDS):
                if rnd == 0:
                    prompt = ROUND0_TEMPLATE.format(question=prob["question"])
                else:
                    prompt = REVISE_TEMPLATE.format(
                        question=prob["question"], prev_answer=prev_answer)
                res = ollama_generate(prompt, seed)
                n_calls += 1
                answer = res.get("response", "")
                rounds.append({
                    "round": rnd,
                    "prompt": prompt,
                    "answer": answer,
                    "seed": seed,
                    "temperature": 0.0,
                    "model": MODEL,
                    "eval_count": res.get("eval_count"),
                    "call_wall_s": res.get("wall_s"),
                    "call_error": res.get("error"),
                })
                prev_answer = answer
                tok_s = (res.get("eval_count") or 0) / max(res.get("wall_s", 1), 1e-6)
                print(f"traj {tid} round {rnd}: {len(answer)} chars, "
                      f"{tok_s:.1f} tok/s, err={res.get('error')}", flush=True)
                if n_calls >= MAX_CALLS:
                    break
            rec = {
                "traj_id": tid,
                "select_index": prob["select_index"],
                "question": prob["question"],
                "reference": prob["reference"],
                "ref_number": prob["ref_number"],
                "model": MODEL,
                "model_version": model_version,
                "seed": seed,
                "rounds": rounds,
                "n_calls": len(rounds),
            }
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(f"traj {tid} done ({len(rounds)} rounds), "
                  f"elapsed {(time.time()-t_run0)/60:.1f} min", flush=True)
            if n_calls >= MAX_CALLS:
                break
    print(f"DONE: {n_calls} calls in {(time.time()-t_run0)/3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
