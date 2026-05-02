"""11-Step Signal Combination Engine.

Implements the institutional-grade signal combination procedure from the
Fundamental Law of Active Management:

    IR = IC × √N

The 11 steps:
1-2.  Collect and demean historical returns per signal.
3-4.  Normalize everything to the same volatility scale.
5-7.  Cross-sectionally demean to kill shared market effects.
8-9.  Estimate forward-looking independent edge via regression on recent performance.
10-11. Weight = (independent edge) / volatility, then normalize so total allocation = 1.
"""

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from scipy import stats as scipy_stats

from signals.base import Signal, SignalOutput


@dataclass
class CombinationResult:
    """Output of the combination engine."""

    combined_value: float  # The mega-alpha signal value [-1, 1]
    weights: dict[str, float]  # Per-signal weights
    independent_edges: dict[str, float]  # Per-signal independent edge estimates
    information_ratio: float  # Combined IR estimate
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


class CombinationEngine:
    """11-step signal combination engine.

    Takes multiple signals with their historical returns and produces
    a single weighted mega-alpha signal with optimal weights.
    """

    def __init__(
        self,
        min_history: int = 20,
        regression_lookback: int = 20,
        vol_lookback: int = 60,
    ):
        """
        Args:
            min_history: Minimum number of return observations required.
            regression_lookback: Periods to use for edge estimation regression.
            vol_lookback: Periods to use for volatility estimation.
        """
        self.min_history = min_history
        self.regression_lookback = regression_lookback
        self.vol_lookback = vol_lookback

    def combine(self, signals: list[Signal], current_outputs: list[SignalOutput]) -> CombinationResult:
        """Run the 11-step combination procedure.

        Args:
            signals: List of signal instances with historical returns.
            current_outputs: Current signal outputs (parallel list to signals).

        Returns:
            CombinationResult with the mega-alpha signal and weights.
        """
        if len(signals) != len(current_outputs):
            raise ValueError("signals and current_outputs must have the same length")

        if len(signals) == 0:
            return CombinationResult(
                combined_value=0.0,
                weights={},
                independent_edges={},
                information_ratio=0.0,
                timestamp=datetime.utcnow(),
            )

        # Filter to signals with sufficient history
        eligible = []
        eligible_outputs = []
        for sig, out in zip(signals, current_outputs):
            if len(sig.returns_history) >= self.min_history:
                eligible.append(sig)
                eligible_outputs.append(out)

        if len(eligible) == 0:
            # Not enough history — use equal weights as fallback
            return self._equal_weight_fallback(signals, current_outputs)

        # ─── Steps 1-2: Collect and demean historical returns ───
        returns_matrix = self._build_returns_matrix(eligible)
        demeaned = self._demean_returns(returns_matrix)

        # ─── Steps 3-4: Normalize to same volatility scale ───
        normalized = self._normalize_volatility(demeaned, returns_matrix)

        # ─── Steps 5-7: Cross-sectionally demean (remove market beta) ───
        orthogonalized = self._cross_sectional_demean(normalized)

        # ─── Steps 8-9: Estimate independent edge via regression ───
        raw_edges = self._estimate_independent_edges(
            orthogonalized, returns_matrix
        )

        # Map signal indices to names
        independent_edges = {}
        for i, out in enumerate(eligible_outputs):
            key = f"signal_{i}"
            independent_edges[out.name] = raw_edges.get(key, 0.0)

        # ─── Steps 10-11: Compute weights and normalize ───
        raw_weights = self._compute_weights(raw_edges, returns_matrix)

        # Map weights to signal names
        weights = {}
        for i, out in enumerate(eligible_outputs):
            key = f"signal_{i}"
            weights[out.name] = raw_weights.get(key, 0.0)

        # Compute combined signal
        combined_value = 0.0
        for out in eligible_outputs:
            combined_value += weights.get(out.name, 0.0) * out.value

        combined_value = np.clip(combined_value, -1, 1)

        # Estimate information ratio
        ic_avg = np.mean([abs(e) for e in independent_edges.values()]) if independent_edges else 0
        n_independent = len(eligible)
        ir = ic_avg * np.sqrt(n_independent)

        return CombinationResult(
            combined_value=float(combined_value),
            weights=weights,
            independent_edges={k: float(v) for k, v in independent_edges.items()},
            information_ratio=float(ir),
            timestamp=datetime.utcnow(),
            metadata={
                "n_eligible": len(eligible),
                "n_total": len(signals),
                "method": "11_step" if len(eligible) >= self.min_history else "equal_weight",
            },
        )

    def _build_returns_matrix(self, signals: list[Signal]) -> np.ndarray:
        """Step 1: Build a T×N matrix of historical returns.

        Aligns all signals to the same time index (using the shortest history).
        Each column is a signal, each row is a time period.
        """
        min_len = min(len(s.returns_history) for s in signals)
        max_len = max(len(s.returns_history) for s in signals)

        # Use the most recent min_len observations for all signals
        # Pad shorter histories with zeros if needed, but prefer truncation
        use_len = min(min_len, self.vol_lookback)

        matrix = np.zeros((use_len, len(signals)))
        for i, sig in enumerate(signals):
            hist = sig.returns_history[-use_len:]
            matrix[: len(hist), i] = hist

        return matrix

    def _demean_returns(self, returns_matrix: np.ndarray) -> np.ndarray:
        """Step 2: Subtract the mean return from each signal's history.

        This removes drift and focuses on the signal's edge relative to its average.
        """
        means = returns_matrix.mean(axis=0)
        return returns_matrix - means

    def _normalize_volatility(
        self, demeaned: np.ndarray, original: np.ndarray
    ) -> np.ndarray:
        """Steps 3-4: Normalize all signals to the same volatility scale.

        Divides each signal's returns by its volatility, then rescales to
        a target volatility (the median volatility across all signals).
        This ensures no signal dominates simply because it's noisier.
        """
        vols = np.std(original, axis=0, ddof=1)
        vols = np.where(vols < 1e-10, 1e-10, vols)  # Prevent division by zero

        # Normalize to unit volatility
        unit_vol = demeaned / vols

        # Rescale to median volatility
        target_vol = np.median(vols)
        return unit_vol * target_vol

    def _cross_sectional_demean(self, normalized: np.ndarray) -> np.ndarray:
        """Steps 5-7: Cross-sectionally demean to remove shared market effects.

        At each point in time, subtract the cross-sectional mean across all signals.
        This removes the "market beta" — the component that all signals share
        due to common market exposure — leaving only the truly independent alpha.

        This is the key step that prevents over-sizing correlated signals.
        """
        cross_sectional_mean = normalized.mean(axis=1, keepdims=True)
        return normalized - cross_sectional_mean

    def _estimate_independent_edges(
        self, orthogonalized: np.ndarray, original: np.ndarray
    ) -> dict[str, float]:
        """Steps 8-9: Estimate forward-looking independent edge via regression.

        For each signal, we estimate its independent edge as the mean of its
        recent orthogonalized returns, weighted by statistical significance
        (t-statistic). This is equivalent to regressing on a constant but
        avoids the degenerate case of constant-x regression.

        The t-statistic measures how confidently the edge is different from zero.
        We use it to shrink noisy edge estimates toward zero.
        """
        n_signals = orthogonalized.shape[1]
        edges = {}

        lookback = min(self.regression_lookback, orthogonalized.shape[0])

        for i in range(n_signals):
            recent = orthogonalized[-lookback:, i]

            if len(recent) < 5:
                edges[f"signal_{i}"] = 0.0
                continue

            # Estimate edge as mean of orthogonalized returns
            mean_edge = np.mean(recent)
            std_edge = np.std(recent, ddof=1)

            if std_edge < 1e-10:
                edges[f"signal_{i}"] = 0.0
                continue

            # t-statistic: measures significance of the edge
            t_stat = mean_edge / (std_edge / np.sqrt(len(recent)))

            # Significance weighting: shrink edge by (1 - p_value)
            # For large |t|, p_value → 0, so weight → 1
            # For small |t|, p_value → 1, so weight → 0
            p_value = 2 * (1 - scipy_stats.t.cdf(abs(t_stat), df=len(recent) - 1))
            significance = 1.0 - p_value

            edge = mean_edge * significance
            edges[f"signal_{i}"] = float(edge)

        return edges

    def _compute_weights(
        self,
        independent_edges: dict[str, float],
        returns_matrix: np.ndarray,
    ) -> dict[str, float]:
        """Steps 10-11: Compute optimal weights.

        Weight = independent_edge / volatility
        Then normalize so weights sum to 1 (for allocation).

        This is the core of the Fundamental Law: each signal gets weight
        proportional to its unique edge, penalized by its noise.
        """
        vols = np.std(returns_matrix, axis=0, ddof=1)
        vols = np.where(vols < 1e-10, 1e-10, vols)

        raw_weights = {}
        for i, (name, edge) in enumerate(independent_edges.items()):
            # Weight = edge / vol (risk-adjusted edge)
            w = edge / vols[i]
            # Only keep positive weights (signals with actual edge)
            raw_weights[name] = max(float(w), 0.0)

        # Normalize to sum to 1
        total = sum(raw_weights.values())
        if total < 1e-10:
            # No edge detected — equal weight
            n = len(raw_weights)
            return {k: 1.0 / n for k in raw_weights}

        return {k: v / total for k, v in raw_weights.items()}

    def _equal_weight_fallback(
        self, signals: list[Signal], outputs: list[SignalOutput]
    ) -> CombinationResult:
        """Fallback: equal-weight combination when insufficient history."""
        n = len(signals)
        if n == 0:
            return CombinationResult(
                combined_value=0.0,
                weights={},
                independent_edges={},
                information_ratio=0.0,
                timestamp=datetime.utcnow(),
            )

        weight = 1.0 / n
        weights = {out.name: weight for out in outputs}
        combined = sum(out.value * weight for out in outputs)

        return CombinationResult(
            combined_value=float(np.clip(combined, -1, 1)),
            weights=weights,
            independent_edges={out.name: 0.0 for out in outputs},
            information_ratio=0.0,
            timestamp=datetime.utcnow(),
            metadata={"method": "equal_weight_fallback"},
        )
