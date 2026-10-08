"""Revision-loop atlas: frozen measurement pipeline (Stage 0).

Implements the spec's frozen mathematical definition of the error signal EXACTLY:
- a_t: complete round-t answer text, verbatim, truncated to 4000 chars.
- r: dataset reference solution text, verbatim.
- emb(x): L2-normalized embedding from pinned checkpoint
  sentence-transformers/all-MiniLM-L6-v2 (deterministic inference).
- exact_match: number after `####` if present, else last numeric token;
  normalized strings compared exactly.
- e_t = 0 if exact_match else clip(1 - cos(emb(a_t), emb(r)), 0, 1).
- Δe_t = e_t - e_{t-1}; m_t = clip(1 - cos(emb(a_t), emb(a_{t-1})), 0, 1).

Any change to these definitions = new spec version. Deterministic: fixed seeds,
model in eval mode (no dropout).
"""

import re
import numpy as np

TRUNCATE_CHARS = 4000
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

_NUM_AFTER_HASH = re.compile(r"####\s*([+-]?[\d,]*\.?\d+)")
_NUM_TOKEN = re.compile(r"([+-]?[\d,]*\.?\d+)")


def truncate(text: str, n: int = TRUNCATE_CHARS) -> str:
    return text[:n]


def _normalize_number_token(tok: str) -> str:
    # Frozen normalization: strip whitespace, drop thousands-separator commas.
    # "48.0" vs "48" intentionally does NOT match (documented edge; the
    # embedding path then yields a small but nonzero e).
    return tok.strip().replace(",", "")


def extract_final_number(text: str):
    """Frozen parser: number after `####` if present, else last numeric token."""
    m = _NUM_AFTER_HASH.search(text)
    if m:
        return _normalize_number_token(m.group(1))
    toks = _NUM_TOKEN.findall(text)
    if not toks:
        return None
    return _normalize_number_token(toks[-1])


def exact_match(answer: str, reference: str) -> bool:
    a = extract_final_number(answer)
    r = extract_final_number(reference)
    if a is None or r is None:
        return False
    return a == r


class EmbeddingModel:
    """Pinned embedding checkpoint, deterministic inference.

    Records the exact resolved revision (commit hash) at load time so the run
    plan pins it. Loads from LOCAL_MODEL_DIR env var if set (must contain the
    files of MODEL_ID at PINNED_REVISION, downloaded verbatim); otherwise from
    the Hub.
    """

    PINNED_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

    def __init__(self, model_id: str = MODEL_ID):
        import os
        from sentence_transformers import SentenceTransformer
        self.model_id = model_id
        local = os.environ.get("LOCAL_MODEL_DIR")
        if local:
            self.model = SentenceTransformer(local)
            self.revision = self.PINNED_REVISION + " (local verbatim copy)"
        else:
            self.model = SentenceTransformer(model_id)
            self.revision = self.PINNED_REVISION
            try:
                from huggingface_hub import HfApi
                info = HfApi().model_info(model_id)
                assert info.sha.startswith(self.PINNED_REVISION), \
                    f"Hub revision drift: {info.sha}"
            except AssertionError:
                raise
            except Exception as e:  # network may be unavailable; record honestly
                self.revision += f" (sha check skipped: {type(e).__name__})"
        # Deterministic inference: torch no-grad, eval mode, single thread for
        # full reproducibility on CPU.
        try:
            import torch
            torch.set_num_threads(1)
        except Exception:
            pass

    def embed(self, texts):
        """L2-normalized embeddings, shape (len(texts), dim). Deterministic."""
        if isinstance(texts, str):
            texts = [texts]
        embs = self.model.encode(
            [truncate(t) for t in texts],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embs, dtype=np.float64)

    @staticmethod
    def cos_distance(e1: np.ndarray, e2: np.ndarray) -> float:
        # Inputs are L2-normalized; clip guards float error. Values below 1e-9
        # are snapped to 0.0 (numerically identical; keeps "identical -> 0"
        # exact for the metric-layer checks).
        d = float(np.clip(1.0 - float(np.dot(e1, e2)), 0.0, 1.0))
        return 0.0 if d < 1e-9 else d


def error_trajectory(answers, reference, emb_model: EmbeddingModel):
    """Compute the frozen per-round signals.

    answers: list of round-t answer texts (round 0 = initial).
    Returns dict with e, delta_e, m (revision magnitude), exact flags.
    """
    answers = [truncate(a) for a in answers]
    ref = truncate(reference)
    E_ref = emb_model.embed(ref)[0]
    E = emb_model.embed(answers)

    exact = [exact_match(a, reference) for a in answers]
    d = np.array([emb_model.cos_distance(e, E_ref) for e in E])
    e = np.array([0.0 if xm else dd for xm, dd in zip(exact, d)])

    delta_e = np.zeros_like(e)
    delta_e[1:] = e[1:] - e[:-1]
    m = np.zeros_like(e)
    for t in range(1, len(E)):
        m[t] = emb_model.cos_distance(E[t], E[t - 1])

    return {
        "e": e.tolist(),
        "delta_e": delta_e.tolist(),
        "m": m.tolist(),
        "exact": [bool(x) for x in exact],
        "d": d.tolist(),  # raw embedding distance (pre-exact-match override)
        "n": len(answers),
    }


def seed_all(seed: int = 1907):
    np.random.seed(seed)
    try:
        import torch, random
        torch.manual_seed(seed)
        random.seed(seed)
    except Exception:
        pass
