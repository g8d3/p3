"""Empirical Kelly position sizing.

Implements the empirical Kelly criterion with uncertainty adjustment:

    f_empirical = f_kelly × (1 - CV_edge)

where CV_edge (coefficient of variation of edge) comes from Monte Carlo
simulations of the edge estimate. This accounts for estimation uncertainty
and prevents over-betting on noisy edge estimates.
"""

from dataclasses import dataclass

import numpy as np
from scipy import stats as scipy_stats

from engine.combination import CombinationResult


@dataclass
class PositionSize:
    """Position sizing result."""

    fraction: float  # Fraction of capital to risk (0 to 1)
    size_usd: float  # Position size in USD
    direction: int  # 1 = long, -1 = short, 0 = neutral
    kelly_fraction: float  # Raw Kelly fraction
    cv_edge: float  # Coefficient of variation of edge
    confidence: float  # Confidence level (0 to 1)


class KellySizer:
    """Empirical Kelly position sizer with uncertainty adjustment."""

    def __init__(
        self,
        capital: float = 10000.0,
        max_fraction: float = 0.25,  # Never risk more than 25% of capital
        min_edge: float = 0.02,  # Minimum edge to trade
        n_simulations: int = 1000,  # Monte Carlo simulations for CV
        kelly_fraction: float = 0.5,  # Half-Kelly by default (more conservative)
    ):
        self.capital = capital
        self.max_fraction = max_fraction
        self.min_edge = min_edge
        self.n_simulations = n_simulations
        self.kelly_fraction = kelly_fraction

    def size(
        self,
        combination: CombinationResult,
        signal_returns_history: dict[str, np.ndarray] | None = None,
    ) -> PositionSize:
        """Compute position size from the combination result.

        Args:
            combination: The combination engine output.
            signal_returns_history: Optional dict of signal_name -> returns array
                for Monte Carlo simulation.

        Returns:
            PositionSize with the computed position.
        """
        edge = abs(combination.combined_value)
        direction = 1 if combination.combined_value > 0 else -1

        if edge < self.min_edge:
            return PositionSize(
                fraction=0.0,
                size_usd=0.0,
                direction=0,
                kelly_fraction=0.0,
                cv_edge=1.0,
                confidence=0.0,
            )

        # ─── Compute raw Kelly fraction ───
        # Two approaches depending on data maturity:
        # 1. When we have a meaningful IR: use IR-based Kelly (f = IR²/2)
        # 2. When IR is near zero (early stages): use signal strength directly
        ir = combination.information_ratio
        if ir > 0.1:
            # Kelly fraction = IR² / 2 (for Gaussian returns)
            kelly_f = min(ir ** 2 / 2, self.max_fraction)
        elif ir > 0:
            # Low but positive IR: blend IR-based with signal-strength-based
            ir_based = ir ** 2 / 2
            signal_based = edge * 0.1  # Conservative: 10% of signal strength
            kelly_f = min(max(ir_based, signal_based), self.max_fraction)
        else:
            # Zero or negative IR: still trade if signal is strong enough,
            # but with very small size (exploration mode)
            kelly_f = min(edge * 0.05, self.max_fraction * 0.25)

        # ─── Estimate CV_edge via Monte Carlo ───
        cv_edge = self._estimate_cv_edge(edge, combination, signal_returns_history)

        # ─── Apply empirical Kelly adjustment ───
        # f_empirical = f_kelly × (1 - CV_edge)
        # CV_edge close to 1 means very uncertain edge → reduce size
        # CV_edge close to 0 means very certain edge → full Kelly
        adjustment = max(1.0 - cv_edge, 0.0)
        empirical_f = kelly_f * adjustment * self.kelly_fraction

        # Apply max fraction cap
        empirical_f = min(empirical_f, self.max_fraction)

        # Compute USD size
        size_usd = empirical_f * self.capital

        # Confidence metric
        confidence = 1.0 - cv_edge

        return PositionSize(
            fraction=float(empirical_f),
            size_usd=float(size_usd),
            direction=direction,
            kelly_fraction=float(kelly_f),
            cv_edge=float(cv_edge),
            confidence=float(confidence),
        )

    def _estimate_cv_edge(
        self,
        edge: float,
        combination: CombinationResult,
        signal_returns_history: dict[str, np.ndarray] | None = None,
    ) -> float:
        """Estimate the coefficient of variation of the edge.

        CV_edge = std(edge_estimates) / |mean(edge_estimates)|

        We use a parametric approach based on the number of observations
        and the information ratio. The key insight: CV should decrease
        as we accumulate more data (more confident in our edge estimate).

        With N observations and true IC, the standard error of the mean
        return is σ/√N, so CV ≈ (σ/√N) / |μ| = 1/(IC × √N).

        We cap CV at 0.9 (not 1.0) to always allow some trading.
        """
        ir = combination.information_ratio

        # Count total observations across all signals
        n_obs = 0
        if signal_returns_history:
            for arr in signal_returns_history.values():
                n_obs += len(arr)

        if n_obs < 10:
            # Very little data: high uncertainty but don't zero out
            return 0.9

        # Parametric CV: 1 / (IR × √N_effective)
        # With more data, CV decreases (more confident)
        n_effective = max(n_obs, 1)

        if ir > 0.01:
            cv = 1.0 / (ir * np.sqrt(n_effective / 100))
        else:
            # Very low IR: use data quantity as proxy for confidence
            # After 100 observations, CV ≈ 0.7; after 1000, CV ≈ 0.3
            cv = 1.0 / (1.0 + np.sqrt(n_effective / 100))

        # Always allow some trading: cap at 0.9
        return float(min(cv, 0.9))

    def update_capital(self, new_capital: float) -> None:
        """Update the capital base (e.g., after PnL realization)."""
        self.capital = new_capital
