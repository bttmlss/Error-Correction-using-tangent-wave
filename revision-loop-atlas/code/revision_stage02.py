"""Stage 0.2: Targeted Pattern Battery for the LLM Revision-Loop Atlas.

FROZEN DETECTOR DEFINITIONS — written before any synthetic validation ran.
Threshold VALUES marked [CALIBRATED] are set solely by empirical null calibration
(on null trajectories only, never on pattern synthetics, never by hand).

Each detector consumes an error trajectory e(t), t = 0..8 (n = 9 rounds), and for
Track A the exact-match flag sequence. Scope (hard limit): Stage 0.2 does NOT
discover states. It establishes only: "If a trajectory really contains pattern X,
can our frozen measurement pipeline reliably recognize X without calling ordinary
trajectories X?"

Detectors
---------
Track A — Solve (deterministic, no statistics):
    Fire iff exists t in 1..8 with exact[t-1] == False and exact[t] == True.
    (exact flags come from revision_measure.exact_match on answer text.)

Track B1 — Stall / high-error plateau:
    Let W = e[3:9] (rounds 3..8, six points).
    Fire iff mean(W) > 0.4  [0.4 definitional: what "high error" means]
            AND |OLS_slope(W)| < S_STALL   [S_STALL CALIBRATED on nulls]
    Rationale for slope (not max|dE|): slope aggregates window movement into one
    low-variance statistic; max|dE| is dominated by single noisy differences and
    cannot separate slow decay from stall at high noise.

Track B2 — Oscillation / instability:
    de[i] = e[i+1] - e[i], i = 0..7.
    A reversal at i in 0..6 iff de[i]*de[i+1] < 0
        AND |de[i]| > AMP AND |de[i+1]| > AMP   [AMP CALIBRATED on nulls]
    Fire iff reversal count >= 3.
    The amplitude gate exists so noise cannot manufacture oscillation.

Track B3 — Divergence / deterioration:
    Fire iff #{i : de[i] > 0} >= 5  AND  (e[8] - e[0]) > T_DIV   [T_DIV CALIBRATED]
    (de has 8 entries; ">=5 of 8 rounds" per spec.)

Track B4 — Residual kink (auxiliary only):
    Fire iff CPL dBIC(y) > 13.89   [Stage 0.1 n=9 recalibrated threshold, frozen]
            AND |Δslope| >= 3 * σ̂_resid,
    where Δslope is the CPL second-segment slope change and σ̂_resid is the residual
    std of the CPL fit. Strictly for transitions above the empirically established
    SNR boundary; not a primary instrument.

Null family (SAME for every detector — Adrian's tightening: thresholds set by
EMPIRICAL null calibration, never by theoretical premises):
    Single-regime exponential decay e(t) = a*exp(-λt) + ε
        and linear decay e(t) = a - b*t + ε,
    a ∈ {0.6, 0.9}, λ ∈ {0.25, 0.5}, b ∈ {0.06, 0.12},
    σ ∈ {0.02, 0.05, 0.10}, n = 9, clipped to [0, 1].
    ("Ordinary steady improvement"; very slow decays are an acknowledged gray zone,
    reported via a stress subset, not part of the gate.)

Deterministic: all randomness from numpy Generator(seed=1907) with spawned streams.
"""

import numpy as np

SEED = 1907
N = 9  # rounds t = 0..8

# ---------------- Frozen form constants ----------------
B1_E_FLOOR = 0.4
B1_W0, B1_W1 = 3, 9          # window e[3:9]
B2_MIN_REVERSALS = 3
B3_MIN_POSITIVE = 5
CPL_THR_N9 = 13.89           # Stage 0.1 recalibrated n=9 threshold (frozen)

NULL_SIGMAS = [0.02, 0.05, 0.10]
NULL_A = [0.6, 0.9]
NULL_LAM = [0.25, 0.5]
NULL_B = [0.06, 0.12]


# ---------------- Detectors ----------------

def _ols_slope(y_2d, t0=0):
    """OLS slope per row. y_2d: (M, K); t = t0..t0+K-1."""
    K = y_2d.shape[1]
    t = np.arange(t0, t0 + K, dtype=float)
    tc = t - t.mean()
    yc = y_2d - y_2d.mean(axis=1, keepdims=True)
    return (yc @ tc) / (tc @ tc)


def b1_stat(Y):
    """Return (mean_e_window, abs_slope) per trajectory. Y: (M, 9)."""
    W = Y[:, B1_W0:B1_W1]
    return W.mean(axis=1), np.abs(_ols_slope(W, t0=B1_W0))


def b1_fire(Y, S):
    m, s = b1_stat(Y)
    return (m > B1_E_FLOOR) & (s < S)


def b2_count(Y, AMP):
    """Reversal count per trajectory. Y: (M, 9)."""
    de = np.diff(Y, axis=1)  # (M, 8)
    opp = de[:, :-1] * de[:, 1:] < 0
    big = (np.abs(de[:, :-1]) > AMP) & (np.abs(de[:, 1:]) > AMP)
    return np.sum(opp & big, axis=1)


def b2_fire(Y, AMP):
    return b2_count(Y, AMP) >= B2_MIN_REVERSALS


def b3_fire(Y, T):
    de = np.diff(Y, axis=1)
    return (np.sum(de > 0, axis=1) >= B3_MIN_POSITIVE) & ((Y[:, 8] - Y[:, 0]) > T)


def _cpl_full(y):
    """CPL fit returning (dBIC, tau, b2=Δslope, resid_std).

    Same math as revision_stage0_cpl.delta_bic_cpl (a + b1*t + b2*max(0,t-tau));
    additionally returns the slope change and residual std for the B4 gate.
    dBIC uses the identical BIC bookkeeping (k=2 vs k=4) so the Stage 0.1
    threshold 13.89 applies unchanged.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    t = np.arange(n, dtype=float)
    if float(np.var(y)) < 1e-12:
        return float("-inf"), None, 0.0, 0.0
    X1 = np.column_stack([np.ones_like(t), t])
    beta1, *_ = np.linalg.lstsq(X1, y, rcond=None)
    rss1 = max(float(np.sum((y - X1 @ beta1) ** 2)), 1e-300)
    bic1 = n * np.log(rss1 / n) + 2 * np.log(n)
    best = (float("inf"), None, None)
    for tau in range(1, n - 1):
        X2 = np.column_stack([np.ones_like(t), t, np.maximum(0.0, t - tau)])
        beta2, *_ = np.linalg.lstsq(X2, y, rcond=None)
        rss2 = max(float(np.sum((y - X2 @ beta2) ** 2)), 1e-300)
        bic2 = n * np.log(rss2 / n) + 4 * np.log(n)
        if bic2 < best[0]:
            resid = y - X2 @ beta2
            best = (bic2, tau, float(beta2[2]),
                    max(float(np.std(resid)), 1e-12))
    dBIC = float(bic1 - best[0])
    return dBIC, best[1], best[2], best[3]


def b4_fire_one(y, thr=CPL_THR_N9):
    d, tau, b2, sig = _cpl_full(y)
    return bool(d > thr and abs(b2) >= 3.0 * sig)


def b4_fire(Y, thr=CPL_THR_N9):
    return np.array([b4_fire_one(y, thr) for y in Y])


def trackA_fire(exact_flags):
    """Deterministic solve-onset detection on exact-match flag sequences.

    exact_flags: (M, 9) bool array. Fires iff a False->True transition occurs.
    """
    F = np.asarray(exact_flags, dtype=bool)
    return np.any(~F[:, :-1] & F[:, 1:], axis=1)


# ---------------- Synthetic generators ----------------

def _rng(seed):
    return np.random.default_rng(seed)


def gen_nulls(seed, n_per_cell=1500):
    """Null family: single-regime exponential/linear decay. Returns (M, 9)."""
    rng = _rng(seed)
    t = np.arange(N, dtype=float)
    blocks = []
    for a in NULL_A:
        for lam in NULL_LAM:
            base = a * np.exp(-lam * t)
            for sig in NULL_SIGMAS:
                blocks.append(np.clip(
                    base + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
        for b in NULL_B:
            base = a - b * t
            for sig in NULL_SIGMAS:
                blocks.append(np.clip(
                    base + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
    return np.vstack(blocks)


def gen_stress_nulls(seed, n_per_cell=1500):
    """Gray-zone nulls: very slow decays (documented, NOT part of the gate)."""
    rng = _rng(seed)
    t = np.arange(N, dtype=float)
    blocks = []
    for a in [0.7, 0.9]:
        for lam, b in [(0.12, None), (None, 0.03)]:
            base = a * np.exp(-lam * t) if lam else a - b * t
            for sig in NULL_SIGMAS:
                blocks.append(np.clip(
                    base + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
    return np.vstack(blocks)


def gen_patterns(seed, n_per_cell=400):
    """Gross behavioral patterns. Returns dict name -> (M, 9) e-trajectories."""
    rng = _rng(seed)
    t = np.arange(N, dtype=float)
    P = {}
    # Stall: flat at high error
    blocks = []
    for L in [0.55, 0.70]:
        for sig in NULL_SIGMAS:
            blocks.append(np.clip(L + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
    P["stall_flat"] = np.vstack(blocks)
    # Stall after improvement: decay then flat at ~0.5
    blocks = []
    for sig in NULL_SIGMAS:
        base = np.where(t < 3, 0.85 - 0.12 * t, 0.49)
        blocks.append(np.clip(base + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
    P["stall_improve"] = np.vstack(blocks)
    # Divergence: rising error
    blocks = []
    for s in [0.07, 0.10]:
        for sig in NULL_SIGMAS:
            blocks.append(np.clip(0.30 + s * t + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
    P["divergence"] = np.vstack(blocks)
    # Oscillation: alternating direction, gross amplitude
    blocks = []
    for A in [0.12, 0.18]:
        for sig in NULL_SIGMAS:
            blocks.append(np.clip(0.55 + A * ((-1.0) ** t) + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
    P["oscillation"] = np.vstack(blocks)
    # Large kink (for B4 auxiliary): big slope change, above SNR boundary
    blocks = []
    for dsl, sig in [(0.18, 0.02), (0.18, 0.05), (0.30, 0.02), (0.30, 0.05), (0.30, 0.10)]:
        base = np.where(t <= 4, 0.80 - 0.02 * t, 0.72 - dsl * (t - 4))
        blocks.append(np.clip(base + rng.normal(0, sig, (n_per_cell, N)), 0, 1))
    P["large_kink"] = (np.vstack(blocks),
                       [(0.18, 0.02)] * n_per_cell + [(0.18, 0.05)] * n_per_cell +
                       [(0.30, 0.02)] * n_per_cell + [(0.30, 0.05)] * n_per_cell +
                       [(0.30, 0.10)] * n_per_cell)
    return P


def gen_solve_patterns(seed, n_per_cell=400):
    """Solve-flag sequences + matching e trajectories. Returns (flags, e)."""
    rng = _rng(seed)
    flags, es = [], []
    # solve at t=3
    for _ in range(n_per_cell):
        f = np.array([False] * 3 + [True] * 6)
        e = np.array([0.65, 0.55, 0.45, 0, 0, 0, 0, 0, 0])
        flags.append(f); es.append(e)
    # solve at t=1 (immediate)
    for _ in range(n_per_cell):
        f = np.array([False] + [True] * 8)
        e = np.array([0.5, 0, 0, 0, 0, 0, 0, 0, 0])
        flags.append(f); es.append(e)
    # never solves (negative control)
    for _ in range(n_per_cell):
        f = np.array([False] * 9)
        e = np.clip(0.7 - 0.05 * np.arange(9) + rng.normal(0, 0.02, 9), 0, 1)
        flags.append(f); es.append(e)
    return np.array(flags), np.array(es)
