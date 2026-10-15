#!/usr/bin/env python3
"""Stage 2 Step 1 — open-loop command calibration runner.

~3,700 Gemini API calls on 20 train sources only. Held-out sources never appear.

Design (protocol v13 §Step 1):
- Small commands: 20 texts × 10 reps × u∈{±1,±2,±4,±8} = 1,600 calls
- Large commands: 20 texts × ~2.5 reps × u∈{±16,±24,±32,±48,±60} = 500 calls
- Jitter control: 200 text-instances × 8 noisy readings (2 per σ) = 1,600 calls

Command phrasing: frozen Arm 3 Design B (protocol v13).
Reading phrasing: like-for-like, stated reading instead of command.

Auth: stored custom.gemini-api credential via dynamic_credentials helper.
Crash-safe: appends to JSONL immediately; resumes at first missing key.
"""
import argparse
import fcntl
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.request
import urllib.error

_DC_PATHS = [
    "/opt/muse/skills/custom-connector-setup/bin",  # current location
    "/opt/hatch/skills/skill-creator/bin",          # legacy location
]
for _p in _DC_PATHS:
    if os.path.isdir(_p):
        sys.path.insert(0, _p)
        break
from dynamic_credentials import add_surrogate_to_request, read_json_response

TDIR = os.path.dirname(os.path.abspath(__file__))
BANK_F = os.path.join(TDIR, "stage2_bank_v3_20261014.json")
PARTIAL = os.path.join(TDIR, "step1_partial.jsonl")
LOCKF = os.path.join(TDIR, "step1.lock")

HOST = "generativelanguage.googleapis.com"
CRED = "custom.gemini-api"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

SIGMAS = [0.0, 0.72, 1.44, 2.88]
SMALL_US = [1, -1, 2, -2, 4, -4, 8, -8]
LARGE_US = [16, -16, 24, -24, 32, -32, 48, -48, 60, -60]
N_SMALL_REPS = 10
# Large: 10 texts get 3 reps, 10 texts get 2 reps = 50 reps total
N_LARGE_REPS_A = 3  # for first 10 texts
N_LARGE_REPS_B = 2  # for last 10 texts

WORD_RE = re.compile(r"[A-Za-z0-9']+")
def count_words(s):
    return len(WORD_RE.findall(s))

# Frozen Arm 3 Design B phrasing (protocol v13)
COMMAND_PROMPT = """**Arm 3 — External Correction Command**

You are revising a text's length under external control. An external controller determines the adjustment for this round. Your task is to apply that adjustment faithfully to the text, not to calculate a correction or second-guess the controller.

**Your adjustment this round: {u:+d} words**

- **If positive (+):** Add approximately that many words. Expand descriptions or add relevant detail while preserving the text's style, topic, and meaning.
- **If negative (−):** Remove approximately that many words. Condense phrasing or cut redundancy while preserving the text's core content and style.
- **If zero (0):** Make no intentional length adjustment.

**Rules**
1. Apply only the signed adjustment supplied for this round.
2. Do not estimate the text's current word count, infer a target length, or calculate your own correction.
3. Do not accumulate adjustments across rounds, extrapolate trends, or introduce momentum or other multi-round correction strategies.
4. Preserve the original topic, meaning, and writing style as you add or remove words.
5. Return the full revised text only. Do not include a word-count report, explanation, or commentary.

The external controller manages the target and evaluates the result. Your role is to execute the supplied word adjustment.

Text to revise:
{text}"""

# Like-for-like reading prompt (stated reading, not command)
READING_PROMPT = """You are revising a text to a target length. An external evaluator has measured the text.

**The evaluator's measurement: {stated} words**
**Target length: 80 words**

Revise the text to be closer to the target length. If the measurement is above 80, shorten the text. If below 80, lengthen it. Preserve the topic, meaning, and writing style.

Return the full revised text only. Do not include a word-count report, explanation, or commentary.

Text to revise:
{text}"""


def api_generate(prompt, temperature=0.7, timeout=120, tries=4):
    url = f"https://{HOST}/v1beta/models/{MODEL}:generateContent"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 400},
    }).encode()
    last = None
    for a in range(tries):
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"})
        try:
            add_surrogate_to_request(req, CRED, allowed_hosts=[HOST])
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = read_json_response(resp)
            cands = data.get("candidates", [])
            if cands:
                parts = cands[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"]
            last = f"no text in response: {str(data)[:200]}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"API failed after {tries} tries: {last}")


def build_work_items(train_texts):
    """Generate all (key, prompt, metadata) tuples for Step 1."""
    items = []
    # Small commands: 20 texts × 10 reps × 8 us
    for ti, t in enumerate(train_texts):
        for rep in range(N_SMALL_REPS):
            for u in SMALL_US:
                key = f"small|{t['text_id']}|rep{rep}|u{u:+d}"
                prompt = COMMAND_PROMPT.format(u=u, text=t['text'])
                items.append((key, prompt, {
                    "condition": "small_command",
                    "text_id": t['text_id'], "src_num": t['src_num'],
                    "rep": rep, "u": u, "stated_value": u,
                    "orig_words": count_words(t['text']),
                }))
    # Large commands: 50 reps × 10 us
    for ti, t in enumerate(train_texts):
        n_reps = N_LARGE_REPS_A if ti < 10 else N_LARGE_REPS_B
        for rep in range(n_reps):
            for u in LARGE_US:
                key = f"large|{t['text_id']}|rep{rep}|u{u:+d}"
                prompt = COMMAND_PROMPT.format(u=u, text=t['text'])
                items.append((key, prompt, {
                    "condition": "large_command",
                    "text_id": t['text_id'], "src_num": t['src_num'],
                    "rep": rep, "u": u, "stated_value": u,
                    "orig_words": count_words(t['text']),
                }))
    # Jitter: 200 instances × 8 readings (2 per sigma)
    # Use the same text-instances as small commands (20 texts × 10 reps)
    rng = random.Random(20261014)
    for ti, t in enumerate(train_texts):
        orig_wc = count_words(t['text'])
        for rep in range(N_SMALL_REPS):
            for sigma in SIGMAS:
                for j in range(2):  # 2 per sigma
                    # True error: pick a target error, add noise
                    # For open-loop, we state a reading; model responds to stated value
                    # Stated value should be in overlapping range |stated|<=8 for gate,
                    # but protocol says 8 readings (2 per sigma) — use varied stated values
                    # We'll use stated = true_error + noise, where true_error varies
                    true_err = rng.choice([-6, -4, -2, 2, 4, 6])
                    noise = rng.gauss(0, sigma) if sigma > 0 else 0.0
                    stated_err = true_err + noise
                    # Stated reading = target + stated_err; target=80
                    stated_reading = 80 + stated_err
                    # The 'stated_value' for jitter analysis is the implied correction
                    # (target - stated_reading) = -stated_err
                    stated_value = -stated_err
                    key = f"jitter|{t['text_id']}|rep{rep}|s{sigma}|j{j}|sv{stated_value:+.1f}"
                    prompt = READING_PROMPT.format(
                        stated=int(round(stated_reading)), text=t['text'])
                    items.append((key, prompt, {
                        "condition": "jitter_reading",
                        "text_id": t['text_id'], "src_num": t['src_num'],
                        "rep": rep, "sigma": sigma,
                        "stated_value": stated_value,
                        "stated_reading": stated_reading,
                        "interface": "reading",
                        "orig_words": orig_wc,
                    }))
    # Mark command items with interface='command' for jitter analysis
    for i, (key, prompt, meta) in enumerate(items):
        if meta["condition"] in ("small_command", "large_command"):
            meta["interface"] = "command"
            meta["sigma"] = 0.0  # commands have no noise
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-calls", type=int, default=0,
                    help="Stop after this many new calls (0=no limit)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Build work items and report counts without calling API")
    args = ap.parse_args()

    bank = json.load(open(BANK_F))['stage2_texts']
    train = [x for x in bank if x['text_id'].startswith('s1_') or
             x['text_id'].startswith('s2t_')]
    # Sort for determinism
    train = sorted(train, key=lambda x: x['text_id'])
    assert len(train) == 20, f"Expected 20 train texts, got {len(train)}"
    # Safety: never use held-out
    assert all(not x['text_id'].startswith('s2h_') for x in train)

    items = build_work_items(train)
    print(f"Work items: {len(items)}", file=sys.stderr)
    if args.dry_run:
        from collections import Counter
        print(Counter(k.split('|')[0] for k, _, _ in items), file=sys.stderr)
        return

    # Load completed keys
    done = set()
    if os.path.exists(PARTIAL):
        with open(PARTIAL) as f:
            for line in f:
                try:
                    done.add(json.loads(line)['key'])
                except Exception:
                    pass
    print(f"Already done: {len(done)}", file=sys.stderr)

    lock = open(LOCKF, 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Another runner holds the lock; exiting.", file=sys.stderr)
        return

    out = open(PARTIAL, 'a', buffering=1)
    new_calls = 0
    for key, prompt, meta in items:
        if key in done:
            continue
        if args.max_calls and new_calls >= args.max_calls:
            break
        try:
            response = api_generate(prompt, temperature=0.7)
        except Exception as e:
            print(f"ERROR {key}: {e}", file=sys.stderr)
            # Record error and continue
            rec = {"key": key, **meta, "error": str(e)[:500]}
            out.write(json.dumps(rec) + "\n"); out.flush()
            os.fsync(out.fileno())
            continue
        resp_wc = count_words(response)
        delta = resp_wc - meta["orig_words"]
        rec = {"key": key, **meta,
               "response_words": resp_wc, "delta_words": delta,
               # Don't store full response text (large); store hash for integrity
               "response_sha": hashlib.sha256(response.encode()).hexdigest()[:16]}
        out.write(json.dumps(rec) + "\n"); out.flush()
        os.fsync(out.fileno())
        new_calls += 1
        if new_calls % 50 == 0:
            print(f"  {new_calls} new calls...", file=sys.stderr)
        time.sleep(0.9)  # ~1 call/sec to respect rate limits

    print(f"Done. New calls this run: {new_calls}", file=sys.stderr)


if __name__ == "__main__":
    main()
