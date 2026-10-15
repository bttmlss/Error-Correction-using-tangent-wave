"""Pre-data analysis helpers for Stage 2 Step 1.

Implements protocol-v11 calibration summaries and the residual-variability
comparison. This module never silently takes abs() of a negative gain.

Input conventions:
- command calibration rows: source_id, u (signed integer command), delta_words
- jitter rows: source_id, interface ('command' or 'reading'), stated_value,
  delta_words, sigma

The protocol does not fully operationalize a numeric saturation threshold.
Accordingly, saturation is reported descriptively (large-command achieved
response plateaus across increasing command magnitudes); it is not used to
silently alter alpha. The 15% small-vs-large slope rule is separately used
for the pre-registered piecewise-alpha decision.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, Sequence, Any
import math
import random

import numpy as np


class CalibrationFailure(ValueError):
    """A pre-registered calibration stop condition was met."""


@dataclass(frozen=True)
class SlopeEstimate:
    slope: float
    intercept: float
    n: int
    ci_low: float | None = None
    ci_high: float | None = None


@dataclass(frozen=True)
class CalibrationSummary:
    small_slope: float
    large_slope: float
    positive_small_slope: float | None
    negative_small_slope: float | None
    sign_gain_relative_difference: float | None
    selected_small_gain: float
    saturation_flag: bool
    saturation_details: str
    piecewise_alpha: bool
    alpha_small: float | None
    alpha_large: float | None
    alpha_rule: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = [dict(r) for r in rows]
    if not out:
        raise ValueError("No rows supplied")
    return out


def _ols(x: Sequence[float], y: Sequence[float]) -> SlopeEstimate:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if len(x_arr) != len(y_arr) or len(x_arr) < 3:
        raise ValueError("OLS requires at least 3 paired observations")
    if not np.isfinite(x_arr).all() or not np.isfinite(y_arr).all():
        raise ValueError("OLS input contains non-finite values")
    design = np.column_stack([np.ones(len(x_arr)), x_arr])
    beta, _, rank, _ = np.linalg.lstsq(design, y_arr, rcond=None)
    if rank < 2:
        raise ValueError("Slope is not identifiable: predictor has no variation")
    resid = y_arr - design @ beta
    dof = len(y_arr) - 2
    se2 = float(resid @ resid) / dof
    cov = se2 * np.linalg.inv(design.T @ design)
    se_slope = math.sqrt(max(0.0, float(cov[1, 1])))
    # 95% normal approximation; report is diagnostic, not a small-sample t CI.
    return SlopeEstimate(float(beta[1]), float(beta[0]), len(x_arr),
                         float(beta[1] - 1.96 * se_slope),
                         float(beta[1] + 1.96 * se_slope))


def _slope(rows: Sequence[Mapping[str, Any]]) -> SlopeEstimate:
    return _ols([float(r["u"]) for r in rows],
                [float(r["delta_words"]) for r in rows])


def _saturation_check(rows: Sequence[Mapping[str, Any]], min_drop: float = 0.20) -> tuple[bool, str]:
    """Flag a descriptive response plateau in large-command bins.

    For each absolute command magnitude, compute median absolute response.
    A plateau is flagged if the highest-magnitude bin's median response is
    at least `min_drop` below the preceding bin, or fails to exceed it by 5%.
    This is a transparent diagnostic convention, not a protocol-specified gate.
    """
    by_mag: dict[float, list[float]] = {}
    for r in rows:
        mag = abs(float(r["u"]))
        by_mag.setdefault(mag, []).append(abs(float(r["delta_words"])))
    mags = sorted(by_mag)
    if len(mags) < 2:
        return False, "not assessed: fewer than two large-command magnitudes"
    medians = [float(np.median(by_mag[m])) for m in mags]
    prev, last = medians[-2], medians[-1]
    if prev > 0 and last < prev * (1.0 - min_drop):
        return True, f"possible reversal/compression: median |Δwords| fell {((prev-last)/prev):.1%} from |u|={mags[-2]:g} to {mags[-1]:g}"
    if last <= prev * 1.05:
        return True, f"possible plateau: median |Δwords| rose ≤5% from |u|={mags[-2]:g} to {mags[-1]:g}"
    return False, f"no plateau flag: median |Δwords| rose from {prev:g} to {last:g} at largest command magnitudes"


def summarize_calibration(
    rows: Iterable[Mapping[str, Any]],
    *,
    g_target: float | None,
    small_max: float = 8,
    large_min: float = 16,
    piecewise_threshold: float = 0.15,
    sign_asymmetry_threshold: float = 0.20,
    allow_ambiguous_sign_rerun: bool = False,
) -> CalibrationSummary:
    """Summarize open-loop command calibration rows under protocol v13.

    Negative slope raises CalibrationFailure unless caller explicitly marks that
    the command wording was ambiguous and is being handled as the one permitted
    phrasing correction/rerun. Do not pass True merely to suppress a failure.
    """
    data = _rows(rows)
    required = {"source_id", "u", "delta_words"}
    if any(not required.issubset(r) for r in data):
        raise ValueError(f"Each row must contain {sorted(required)}")
    small = [r for r in data if 0 < abs(float(r["u"])) <= small_max]
    large = [r for r in data if abs(float(r["u"])) >= large_min]
    if len(small) < 3 or len(large) < 3:
        raise ValueError("Need at least 3 small-command and 3 large-command observations")
    sm = _slope(small)
    lg = _slope(large)
    warnings: list[str] = []
    if sm.slope < 0 or lg.slope < 0:
        msg = (f"wrong-sign gain detected (small={sm.slope:.6g}, large={lg.slope:.6g}); "
               "check wording/sign convention; if wording is clear, calibration fails")
        if not allow_ambiguous_sign_rerun:
            raise CalibrationFailure(msg)
        warnings.append(msg + "; caller marked phrasing ambiguity for the single permitted rerun")
    pos = [r for r in small if float(r["u"]) > 0]
    neg = [r for r in small if float(r["u"]) < 0]
    pos_slope = _slope(pos).slope if len(pos) >= 3 and len({float(r['u']) for r in pos}) > 1 else None
    neg_slope = _slope(neg).slope if len(neg) >= 3 and len({float(r['u']) for r in neg}) > 1 else None
    asym = None
    if pos_slope is not None and neg_slope is not None:
        denom = (abs(pos_slope) + abs(neg_slope)) / 2
        asym = abs(abs(pos_slope) - abs(neg_slope)) / denom if denom else math.inf
    if asym is not None and asym > sign_asymmetry_threshold:
        warnings.append("positive/negative command gains differ by >20%; report both and use the smaller absolute gain conservatively")
        selected = min(abs(pos_slope), abs(neg_slope))
    else:
        selected = (pos_slope + neg_slope) / 2 if pos_slope is not None and neg_slope is not None else sm.slope
    relative_change = abs(lg.slope - sm.slope) / abs(sm.slope) if sm.slope else math.inf
    piecewise = relative_change > piecewise_threshold
    sat, sat_details = _saturation_check(large)
    alpha_small = alpha_large = None
    alpha_rule = "not calculated: g_target not supplied"
    if g_target is not None:
        if selected <= 0 or lg.slope <= 0:
            alpha_rule = "not calculated: non-positive gain; calibration failure/debug required"
        elif asym is not None and asym > sign_asymmetry_threshold:
            # Conservative selected gain governs small regime; large uses the
            # large pooled slope unless a sign asymmetry is explicitly flagged.
            alpha_small = float(g_target) / selected
            alpha_large = float(g_target) / lg.slope
            alpha_rule = "piecewise or single alpha per 15% rule; sign asymmetry reported"
        else:
            alpha_small = float(g_target) / selected
            alpha_large = float(g_target) / lg.slope
            alpha_rule = "piecewise alpha if relative slope change >15%; otherwise use small-regime alpha"
    if piecewise and sm.ci_low is not None and sm.ci_low <= 0 <= sm.ci_high:
        warnings.append("small-slope 95% CI includes zero: protocol says fall back to single alpha from small gain and report uncertainty")
        piecewise = False
    if lg.ci_low is not None and lg.ci_low <= 0 <= lg.ci_high:
        warnings.append("large-slope 95% CI includes zero: protocol says fall back to single alpha from small gain and report uncertainty")
        piecewise = False
    if g_target is not None and not piecewise:
        alpha_large = alpha_small
    return CalibrationSummary(
        small_slope=sm.slope, large_slope=lg.slope,
        positive_small_slope=pos_slope, negative_small_slope=neg_slope,
        sign_gain_relative_difference=asym, selected_small_gain=selected,
        saturation_flag=sat, saturation_details=sat_details,
        piecewise_alpha=piecewise, alpha_small=alpha_small,
        alpha_large=alpha_large, alpha_rule=alpha_rule,
        warnings=tuple(warnings),
    )


def _fixed_effect_residual_variance(rows: Sequence[Mapping[str, Any]]) -> tuple[float, int]:
    """OLS Δwords ~ source fixed effects + stated_value + sigma; residual variance."""
    source_ids = [str(r["source_id"]) for r in rows]
    levels = sorted(set(source_ids))
    if len(rows) <= len(levels) + 2:
        raise ValueError("Not enough rows for source fixed effects, stated value, and sigma")
    # Drop one source dummy to avoid collinearity with intercept.
    source_cols = [[1.0 if sid == level else 0.0 for sid in source_ids] for level in levels[1:]]
    cols = [[1.0] * len(rows), *source_cols,
            [float(r["stated_value"]) for r in rows],
            [float(r["sigma"]) for r in rows]]
    X = np.asarray(cols, dtype=float).T
    y = np.asarray([float(r["delta_words"]) for r in rows], dtype=float)
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    if rank < X.shape[1]:
        raise ValueError("Jitter design matrix is rank-deficient")
    residuals = y - X @ beta
    dof = len(y) - rank
    return float(residuals @ residuals / dof), dof


def jitter_variance_ratio(
    rows: Iterable[Mapping[str, Any]], *, overlap_limit: float = 8.0,
) -> dict[str, Any]:
    """Compute command/reading residual-variance ratio on overlapping range.

    Filters |stated_value| <= overlap_limit, fits the same fixed-effect model
    to both interfaces, and reports residual variance and residual df.
    """
    data = _rows(rows)
    required = {"source_id", "interface", "stated_value", "delta_words", "sigma"}
    if any(not required.issubset(r) for r in data):
        raise ValueError(f"Each row must contain {sorted(required)}")
    data = [r for r in data if abs(float(r["stated_value"])) <= overlap_limit]
    cmd = [r for r in data if r["interface"] == "command"]
    reading = [r for r in data if r["interface"] == "reading"]
    if not cmd or not reading:
        raise ValueError("Need both command and reading interface rows in overlapping range")
    v_cmd, df_cmd = _fixed_effect_residual_variance(cmd)
    v_read, df_read = _fixed_effect_residual_variance(reading)
    if v_read <= 0:
        raise ValueError("Reading-interface residual variance must be positive")
    return {"command_variance": v_cmd, "reading_variance": v_read,
            "ratio": v_cmd / v_read, "command_df": df_cmd,
            "reading_df": df_read, "overlap_limit": overlap_limit,
            "n_command": len(cmd), "n_reading": len(reading)}


def paired_cluster_bootstrap_ratio(
    rows: Iterable[Mapping[str, Any]], *, n_boot: int = 2000,
    seed: int = 20261014, overlap_limit: float = 8.0,
) -> dict[str, Any]:
    """Paired source-cluster bootstrap CI for command/reading jitter ratio."""
    data = [dict(r) for r in _rows(rows)
            if abs(float(r["stated_value"])) <= overlap_limit]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for r in data:
        by_source.setdefault(str(r["source_id"]), []).append(r)
    # Pairing requires each resampled source to contribute both interfaces.
    eligible = sorted(s for s, rs in by_source.items()
                      if {r["interface"] for r in rs} >= {"command", "reading"})
    if len(eligible) < 2:
        raise ValueError("Need at least two paired source clusters with both interfaces")
    base = jitter_variance_ratio(data, overlap_limit=overlap_limit)
    rng = random.Random(seed)
    ratios: list[float] = []
    for _ in range(n_boot):
        sampled = [rng.choice(eligible) for _ in eligible]
        boot_rows: list[dict[str, Any]] = []
        # Duplicate sampled clusters receive distinct bootstrap IDs so their
        # fixed-effect intercepts remain separate, as in a cluster bootstrap.
        for draw_i, source in enumerate(sampled):
            for r in by_source[source]:
                rr = dict(r)
                rr["source_id"] = f"boot{draw_i}:{source}"
                boot_rows.append(rr)
        try:
            ratios.append(jitter_variance_ratio(boot_rows, overlap_limit=overlap_limit)["ratio"])
        except ValueError:
            continue
    if len(ratios) < max(100, int(0.8 * n_boot)):
        raise ValueError(f"Too few valid bootstrap replicates: {len(ratios)}/{n_boot}")
    return {**base, "ci_low_95": float(np.quantile(ratios, 0.025)),
            "ci_high_95": float(np.quantile(ratios, 0.975)),
            "n_boot_requested": n_boot, "n_boot_valid": len(ratios),
            "bootstrap_seed": seed, "cluster_count": len(eligible),
            "gate_stop_if_upper_ge": 0.90,
            "gate_strong_if_upper_lt": 0.80}


def evaluate_jitter_gate(bootstrap_result: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the protocol's pre-registered Gate 1 threshold."""
    upper = float(bootstrap_result["ci_high_95"])
    return {"decision": "STOP" if upper >= 0.90 else "PASS_GATE_1",
            "ci_upper": upper,
            "reason": "95% CI upper bound >= 0.90" if upper >= 0.90 else "95% CI upper bound < 0.90"}
