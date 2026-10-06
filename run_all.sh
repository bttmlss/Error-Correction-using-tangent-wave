#!/usr/bin/env bash
# Reproduce the full experiment program, Exps 18 -> 23, and regenerate every figure.
# One command:  bash run_all.sh
# First run downloads Qwen2.5-0.5B-Instruct from HuggingFace (~1 GB).
# Override with a local checkout:  MODEL_DIR=/path/to/weights bash run_all.sh
# Expect roughly 30-60 minutes on a modern CPU machine (mostly model
# forward passes and the REINFORCE training loops; no GPU needed).
set -euo pipefail
cd "$(dirname "$0")/code"
PY="${PYTHON:-python3}"

echo "=== Exp 18: contextual substrate ==="
$PY exp18_contextual.py
echo "=== Exp 19: semantic tangent ==="
$PY exp19_tangent.py
echo "=== Exp 20: residual-only correction ==="
$PY exp20_residual.py
echo "=== Exp 21: verifier-driven learning ==="
$PY exp21_verifier.py
echo "=== Exp 22: verifier selection ==="
$PY exp22_verifiers.py
echo "=== Exp 23: verifier-induced law generalization ==="
$PY exp23_generalization.py

echo "DONE. Figures are in code/figures/, results JSON in code/."
