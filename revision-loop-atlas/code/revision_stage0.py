"""Revision-loop atlas: STAGE 0 synthetic validation (zero LLM calls).

Two layers:
  (a) Metric layer: synthetic (answer, reference) text pairs with known
      relationships -> verifies the frozen measurement pipeline outputs the
      expected e values.
  (b) Temporal layer: synthetic e(t) curves -> n-conditional calibration of the
      Bar-0 change-point detector on single-regime nulls, then kink-recovery
      measurement on injected two-regime trajectories.

Strict checkpoint (pre-registered):
  (a) metric layer exact on all synthetic pairs;
  (b) >=95% correct one-regime classification on FRESH single-regime nulls
      (threshold calibrated on an independent null ensemble);
  (c) >=90% kink recovery on injected two-regime synthetics at pilot n/noise.
If ANY fails: report the failure mode precisely and STOP.

Deterministic: seed 1907 throughout.
"""

import json
import numpy as np

SEED = 1907
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Bar-0 change-point machinery (ported from the 1a close-out; fit on e(t)
# directly since e hits exact 0 and log is undefined there).
# One-regime: e_t = a + b*t            (k=2)
# Two-regime: DISCONTINUOUS piecewise linear, free intercepts per segment
#   (k=5: a1,b1,a2,b2,tau) — jumps representable (exact match -> e=0 exactly).
# BIC = n*log(RSS/n) + k*log(n); dBIC = BIC(1) - BIC(2) > thr -> two regimes.
# ---------------------------------------------------------------------------

def _fit_linear(t, y):
    X = np.column_stack([np.ones_like(t), t])
    beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
    rss = float(np.sum((y - X @ beta) ** 2))
    return rss


def _fit_piecewise(t, y, tau):
    # DISCONTINUOUS two-regime model: e = a1 + b1*t for t<=tau,
    # e = a2 + b2*t for t>tau (free intercepts). Jumps are representable
    # because the measurement genuinely produces them (exact match -> e=0
    # exactly). k=5 (a1,b1,a2,b2,tau); the null calibration absorbs the
    # extra flexibility.
    seg1 = t <= tau
    seg2 = ~seg1
    X = np.column_stack([
        seg1.astype(float),
        np.where(seg1, t, 0.0),
        seg2.astype(float),
        np.where(seg2, t, 0.0),
    ])
    beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
    rss = float(np.sum((y - X @ beta) ** 2))
    return rss


def delta_bic(y):
    """Delta-BIC (two-regime minus one-regime evidence) for trajectory y.

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
    rss1 = _fit_linear(t, y)
    rss1 = max(rss1, 1e-300)
    bic1 = n * np.log(rss1 / n) + 2 * np.log(n)
    best = (float("inf"), None)
    # Search tau in {1..n-2}: breaks near the edges are real (early solves).
    # Minimum 2 points per segment; BIC penalty absorbs the flexibility and
    # the null calibration sets the threshold empirically.
    for tau in range(1, n - 1):
        rss2 = max(_fit_piecewise(t, y, float(tau)), 1e-300)
        bic2 = n * np.log(rss2 / n) + 5 * np.log(n)
        if bic2 < best[0]:
            best = (bic2, tau)
    return float(bic1 - best[0]), best[1]


def classify(y, thr):
    """True -> two regimes."""
    d, tau = delta_bic(y)
    return bool(d > thr), d, tau


# ---------------------------------------------------------------------------
# Synthetic nulls (single-regime): linear decay, exponential decay, flat,
# all clipped to [0,1], Gaussian noise at pilot-plausible levels.
# ---------------------------------------------------------------------------

NOISE_LEVELS = [0.02, 0.05, 0.10]

def synth_null(n, rng, noise=None):
    kind = rng.integers(0, 3)
    t = np.arange(n, dtype=float)
    if noise is None:
        noise = NOISE_LEVELS[rng.integers(0, len(NOISE_LEVELS))]
    if kind == 0:      # linear decay to floor
        a = rng.uniform(0.5, 0.9)
        b = rng.uniform(0.03, 0.10)
        y = a - b * t
    elif kind == 1:    # exponential decay
        a = rng.uniform(0.5, 0.9)
        rho = rng.uniform(0.80, 0.95)
        y = a * rho ** t
    else:              # flat (stall-like, single regime)
        a = rng.uniform(0.1, 0.8)
        y = np.full(n, a)
    y = y + rng.normal(0, noise, n)
    return np.clip(y, 0.0, 1.0)


def synth_kink(n, kind, tau, rng, noise=None):
    """Two-regime synthetic trajectories. Realistic magnitudes: the regime
    changes Bar 0 must catch in the pilot are LARGE (breakthroughs, solves,
    give-ups, reversals), not subtle slope wiggles. 'weak_kink' is retained
    purely as a detection-limit probe (reported separately, not in the bar).
    kind in: breakthrough, give_up, rate_change, weak_kink, solve,
             solve_leave, stall_improve, reversal."""
    if noise is None:
        noise = NOISE_LEVELS[rng.integers(0, len(NOISE_LEVELS))]
    t = np.arange(n, dtype=float)
    if kind == "breakthrough":
        # Slow decay, then a sharp 0.35 drop (aha-moment without exact match).
        drop = 0.35
        y = np.where(t <= tau, 0.7 - 0.02 * t,
                     0.7 - 0.02 * tau - drop - 0.02 * (t - tau))
    elif kind == "give_up":
        # Decay, then flat stall (model stops revising).
        stall = 0.7 - 0.05 * tau
        y = np.where(t <= tau, 0.7 - 0.05 * t, stall)
    elif kind == "rate_change":
        y = np.where(t <= tau, 0.8 - 0.03 * t,
                     0.8 - 0.03 * tau - 0.12 * (t - tau))
    elif kind == "weak_kink":
        # Detection-limit probe only: subtle slope change.
        y = np.where(t <= tau, 0.8 - 0.05 * t,
                     0.8 - 0.05 * tau - 0.09 * (t - tau))
    elif kind == "solve":
        # Faithful: exact match forces e=0 EXACTLY (no noise on solved rounds).
        # Convention: regime 1 = t <= tau, regime 2 (solved) = t > tau.
        pre = 0.8 - 0.06 * t + rng.normal(0, noise, n)
        y = np.where(t <= tau, pre, 0.0)
    elif kind == "solve_leave":
        # Solved exactly for two rounds, then unsolves back to embedding error.
        pre = 0.8 - 0.06 * t + rng.normal(0, noise, n)
        post = 0.4 - 0.02 * (t - tau) + rng.normal(0, noise, n)
        y = np.where(t <= tau, pre, np.where(t <= tau + 2, 0.0, post))
    elif kind == "stall_improve":
        y = np.where(t <= tau, 0.6, 0.6 - 0.10 * (t - tau))
    elif kind == "reversal":
        y = np.where(t <= tau, 0.7 - 0.06 * t,
                     0.7 - 0.06 * tau + 0.05 * (t - tau))
    else:
        raise ValueError(kind)
    if kind in ("solve", "solve_leave"):
        # noise already applied faithfully above; just clip pre/post parts
        y = np.clip(y, 0.0, 1.0)
    else:
        y = y + rng.normal(0, noise, n)
        y = np.clip(y, 0.0, 1.0)
    return y


# ---------------------------------------------------------------------------
# Metric-layer synthetic pairs (frozen expectations).
# ---------------------------------------------------------------------------

REF = (
    "Natalia sold clips to 48 of her friends in April, and then she sold half as "
    "many clips in May. How many clips did Natalia sell altogether in April and May?\n\n"
    "Natalia sold 48 clips in April. In May she sold 48/2 = 24 clips. "
    "48 + 24 = 72.\n#### 72"
)

PAIR_A = ("April: 48 clips. May: half of 48 = 24. Total: 48 + 24 = 72.\n#### 72",
          "exact #### match -> e == 0.0")
PAIR_B = ("A different way: May is half of April, so total = 48 + 48/2 = 72 clips.\n#### 72",
          "correct number, different reasoning -> e == 0.0 (exact dominates)")
PAIR_C = ("Natalia sold 48 clips in April. In May she sold half as many, 24 clips. "
          "Adding them: 48 + 24 = 73.\n#### 73",
          "near-paraphrase, wrong number -> small d (expect < 0.4)")
PAIR_D = ("The Eiffel Tower is in Paris. It was completed in 1889 and is 330 metres tall.\n#### 1889",
          "unrelated -> large d (expect > 0.5)")
PAIR_E = ("48 plus 24 equals 72, so she sold 72 clips in total.",
          "no ####, last numeric token fallback -> e == 0.0")
PAIR_F_TRUNC = ("word " * 900 + "#### 72",
                "number beyond truncation -> exact False, e = embedding d")
PAIR_G_IDENT = ("identical text pair",)

METRIC_BARS = {
    "A_e_eq_0": ("PAIR_A e == 0.0 exactly",),
    "B_e_eq_0": ("PAIR_B e == 0.0 exactly",),
    "C_d_small": ("PAIR_C 0 < d < 0.4",),
    "D_d_large": ("PAIR_D d > 0.5",),
    "C_lt_D": ("d_C < d_D ordering",),
    "E_e_eq_0": ("PAIR_E e == 0.0 exactly",),
    "F_truncated": ("PAIR_F truncated to <=4000 and exact False",),
    "G_m_zero": ("m identical texts == 0.0",),
    "G_m_order": ("m_para < m_unrel",),
}


def run_metric_layer(emb):
    from revision_measure import error_trajectory, truncate, exact_match, extract_final_number
    out = {}
    # single-round trajectories: e(t) with n=1 -> use error_trajectory on [a]
    def e_of(a):
        return error_trajectory([a], REF, emb)

    ra = e_of(PAIR_A[0]); out["A"] = {"e": ra["e"][0], "exact": ra["exact"][0]}
    rb = e_of(PAIR_B[0]); out["B"] = {"e": rb["e"][0], "exact": rb["exact"][0]}
    rc = e_of(PAIR_C[0]); out["C"] = {"e": rc["e"][0], "d": rc["d"][0], "exact": rc["exact"][0]}
    rd = e_of(PAIR_D[0]); out["D"] = {"e": rd["e"][0], "d": rd["d"][0], "exact": rd["exact"][0]}
    re_ = e_of(PAIR_E[0]); out["E"] = {"e": re_["e"][0], "exact": re_["exact"][0]}
    rf = e_of(PAIR_F_TRUNC[0])
    out["F"] = {"e": rf["e"][0], "exact": rf["exact"][0],
                "truncated_len": len(truncate(PAIR_F_TRUNC[0]))}
    # revision magnitude checks
    E = emb.embed([PAIR_A[0], PAIR_C[0], PAIR_D[0]])
    m_ident = emb.cos_distance(E[0], E[0])
    m_para = emb.cos_distance(E[0], E[1])
    m_unrel = emb.cos_distance(E[0], E[2])
    out["G"] = {"m_ident": m_ident, "m_para": m_para, "m_unrel": m_unrel}
    # parser edge: "48.0" vs "48" must NOT exact-match (documented)
    out["parser_edge"] = {
        "48.0_vs_48": exact_match("#### 48.0", "#### 48"),
        "extract_48.0": extract_final_number("#### 48.0"),
    }

    checks = {
        "A_e_eq_0": out["A"]["e"] == 0.0,
        "B_e_eq_0": out["B"]["e"] == 0.0,
        "C_d_small": 0.0 < out["C"]["d"] < 0.4,
        "D_d_large": out["D"]["d"] > 0.5,
        "C_lt_D": out["C"]["d"] < out["D"]["d"],
        "E_e_eq_0": out["E"]["e"] == 0.0,
        "F_truncated": out["F"]["truncated_len"] <= 4000 and out["F"]["exact"] is False,
        # m_ident < 1e-6 (not == 0.0): embeddings vary by ~1e-7 across calls
        # (batch numerics; characterized, irrelevant at signal scales >= 0.02).
        "G_m_zero": out["G"]["m_ident"] < 1e-6,
        "G_m_order": out["G"]["m_para"] < out["G"]["m_unrel"],
    }
    out["checks"] = {k: bool(v) for k, v in checks.items()}
    out["pass"] = bool(all(checks.values()))
    return out
