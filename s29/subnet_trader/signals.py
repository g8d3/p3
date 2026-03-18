"""Signal computation for subnet scoring.

CRITICAL: This module implements signals that ONLY compute from REAL available data.
When data is unavailable, signals return None - NO hardcoded fallback values like 0.5.

This is intentional design - we do not fake signals to make them appear functional
when they cannot be computed from real data.
"""

from datetime import datetime
from typing import Optional
from subnet_trader.models import SubnetData, SignalScores


# Signal weights (used when available signals are normalized)
WEIGHTS = {
    "yield": 0.30,
    "volume": 0.20,
    "momentum_1h": 0.15,
    "momentum_1d": 0.15,
    "momentum_7d": 0.10,
    "age": 0.10,
}


def normalize(values: list[float]) -> list[float]:
    """Normalize a list of values to [0, 1] using min-max scaling.
    
    Args:
        values: List of numeric values to normalize
        
    Returns:
        List of normalized values in [0, 1]
    """
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [1.0] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def compute_yield_signal(subnets: list[SubnetData]) -> list[SignalScores]:
    """Compute yield signal: based on alpha_price.
    
    Higher alpha price suggests higher value/demand for the subnet token.
    
    Args:
        subnets: List of subnets with alpha_price data
        
    Returns:
        List of SignalScores with yield_score populated (or None)
    """
    if not subnets:
        return []
    
    scores = []
    prices = [s.alpha_price for s in subnets]
    
    # We have prices (even if all zero), compute normalized scores
    # When all equal, normalize returns [1.0] * len(values)
    normalized_prices = normalize(prices)
    
    for i, subnet in enumerate(subnets):
        score = SignalScores(yield_score=normalized_prices[i])
        scores.append(score)
    
    return scores


def compute_volume_signal(subnets: list[SubnetData]) -> list[SignalScores]:
    """Compute volume signal: based on REAL 24h volume from taostats.io.
    
    CRITICAL: This signal only computes when has_volume=True.
    If volume data is unavailable, volume_score will be None.
    
    Args:
        subnets: List of subnets with volume data
        
    Returns:
        List of SignalScores with volume_score populated (or None)
    """
    if not subnets:
        return []
    
    # Find subnets with volume data available
    subnets_with_volume = [
        (i, s) for i, s in enumerate(subnets) if s.has_volume and s.volume_24h >= 0
    ]
    
    if not subnets_with_volume:
        # No volume data available - return None for all
        return [SignalScores(volume_score=None) for _ in subnets]
    
    # Normalize volumes for subnets that have data
    indices = [idx for idx, _ in subnets_with_volume]
    volumes = [s.volume_24h for _, s in subnets_with_volume]
    normalized_volumes = normalize(volumes)
    
    # Create volume_to_normalized lookup
    volume_map = {idx: norm for idx, norm in zip(indices, normalized_volumes)}
    
    scores = []
    for i, subnet in enumerate(subnets):
        if i in volume_map:
            score = SignalScores(volume_score=volume_map[i])
        else:
            # Subnet doesn't have volume data
            score = SignalScores(volume_score=None)
        scores.append(score)
    
    return scores


def compute_momentum_signal(subnets: list[SubnetData]) -> list[SignalScores]:
    """Compute momentum signals: based on REAL price changes from taostats.io.
    
    CRITICAL: These signals only compute when has_price_changes=True.
    If price change data is unavailable, momentum scores will be None.
    
    Uses multiple timeframes:
    - 1h: Short-term momentum
    - 1d: Medium-term momentum
    - 7d: Long-term momentum
    
    Args:
        subnets: List of subnets with price change data
        
    Returns:
        List of SignalScores with momentum scores populated (or None)
    """
    if not subnets:
        return []
    
    scores = []
    
    # Separate subnets into those with/without price change data
    with_data = [(i, s) for i, s in enumerate(subnets) if s.has_price_changes]
    
    # For momentum, we rank by percentage change (higher change = higher score)
    # Positive changes indicate upward momentum
    
    # 1h momentum
    indices_1h = [i for i, s in with_data if s.price_change_1h is not None]
    changes_1h = [s.price_change_1h for _, s in with_data if s.price_change_1h is not None]
    normalized_1h = normalize(changes_1h) if changes_1h else []
    map_1h = {idx: norm for idx, norm in zip(indices_1h, normalized_1h)}
    
    # 1d momentum
    indices_1d = [i for i, s in with_data if s.price_change_1d is not None]
    changes_1d = [s.price_change_1d for _, s in with_data if s.price_change_1d is not None]
    normalized_1d = normalize(changes_1d) if changes_1d else []
    map_1d = {idx: norm for idx, norm in zip(indices_1d, normalized_1d)}
    
    # 7d momentum
    indices_7d = [i for i, s in with_data if s.price_change_7d is not None]
    changes_7d = [s.price_change_7d for _, s in with_data if s.price_change_7d is not None]
    normalized_7d = normalize(changes_7d) if changes_7d else []
    map_7d = {idx: norm for idx, norm in zip(indices_7d, normalized_7d)}
    
    for i, subnet in enumerate(subnets):
        score = SignalScores(
            momentum_1h_score=map_1h.get(i),
            momentum_1d_score=map_1d.get(i),
            momentum_7d_score=map_7d.get(i),
        )
        scores.append(score)
    
    return scores


def compute_age_signal(
    subnets: list[SubnetData],
    current_time: datetime,
) -> list[SignalScores]:
    """Compute age signal: based on registration_timestamp.
    
    CRITICAL: This signal only computes when has_registration=True.
    If registration data is unavailable, age_score will be None.
    
    Older subnets (registered earlier) score higher, as they're more established.
    Score is normalized to [0, 1] where 1 = most mature.
    
    Args:
        subnets: List of subnets with registration data
        current_time: Current timestamp for age calculation
        
    Returns:
        List of SignalScores with age_score populated (or None)
    """
    if not subnets:
        return []
    
    # Find subnets with registration data
    with_data = [
        (i, s) for i, s in enumerate(subnets)
        if s.has_registration and s.registration_timestamp is not None
    ]
    
    if not with_data:
        return [SignalScores(age_score=None) for _ in subnets]
    
    # Calculate ages in days
    ages_days = []
    for _, subnet in with_data:
        age_delta = current_time - subnet.registration_timestamp
        ages_days.append(age_delta.total_seconds() / (24 * 3600))
    
    # Normalize ages
    normalized_ages = normalize(ages_days)
    
    # Create lookup
    age_map = {idx: age for idx, age in zip([i for i, _ in with_data], normalized_ages)}
    
    scores = []
    for i, subnet in enumerate(subnets):
        score = SignalScores(age_score=age_map.get(i))
        scores.append(score)
    
    return scores


def compute_all_signals(
    subnets: list[SubnetData],
    current_time: datetime,
) -> dict[int, SignalScores]:
    """Compute all signals for all subnets.
    
    This function merges individual signal computations into a single
    SignalScores object per subnet.
    
    Args:
        subnets: List of subnets with available data
        current_time: Current timestamp for age calculation
        
    Returns:
        Dict mapping netuid → SignalScores
    """
    if not subnets:
        return {}
    
    # Compute each signal type
    yield_scores = compute_yield_signal(subnets)
    volume_scores = compute_volume_signal(subnets)
    momentum_scores = compute_momentum_signal(subnets)
    age_scores = compute_age_signal(subnets, current_time)
    
    # Merge into final scores
    result = {}
    for i, subnet in enumerate(subnets):
        y = yield_scores[i]
        v = volume_scores[i]
        m = momentum_scores[i]
        a = age_scores[i]
        
        result[subnet.netuid] = SignalScores(
            yield_score=y.yield_score if y else None,
            volume_score=v.volume_score if v else None,
            momentum_1h_score=m.momentum_1h_score if m else None,
            momentum_1d_score=m.momentum_1d_score if m else None,
            momentum_7d_score=m.momentum_7d_score if m else None,
            age_score=a.age_score if a else None,
        )
    
    return result
