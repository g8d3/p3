"""Strategy: ranking subnets and generating rebalance orders."""

from typing import Optional
from subnet_trader.models import (
    SubnetData,
    SignalScores,
    CompositeScore,
    RebalanceOrder,
)


# Signal weights for composite score calculation
SIGNAL_WEIGHTS = {
    "yield": 0.30,
    "volume": 0.20,
    "momentum_1h": 0.15,
    "momentum_1d": 0.15,
    "momentum_7d": 0.10,
    "age": 0.10,
}


def compute_composite_score(signals: SignalScores) -> Optional[float]:
    """Compute weighted composite score from available signals.
    
    Only uses signals that are not None. Weight is redistributed to
    available signals to ensure fair comparison.
    
    Args:
        signals: SignalScores with some or all signals populated
        
    Returns:
        Composite score in [0, 1], or None if no signals available
    """
    # Collect available signals with weights
    available = []
    if signals.yield_score is not None:
        available.append(("yield", signals.yield_score))
    if signals.volume_score is not None:
        available.append(("volume", signals.volume_score))
    if signals.momentum_1h_score is not None:
        available.append(("momentum_1h", signals.momentum_1h_score))
    if signals.momentum_1d_score is not None:
        available.append(("momentum_1d", signals.momentum_1d_score))
    if signals.momentum_7d_score is not None:
        available.append(("momentum_7d", signals.momentum_7d_score))
    if signals.age_score is not None:
        available.append(("age", signals.age_score))
    
    if not available:
        return None
    
    # Calculate total weight of available signals
    total_weight = sum(SIGNAL_WEIGHTS.get(name, 0) for name, _ in available)
    
    if total_weight == 0:
        return None
    
    # Compute weighted average with normalized weights
    composite = sum(
        score * (SIGNAL_WEIGHTS.get(name, 0) / total_weight)
        for name, score in available
    )
    
    return composite


def rank_subnets(
    subnets: list[SubnetData],
    signals: dict[int, SignalScores],
) -> list[CompositeScore]:
    """Rank subnets by composite score.
    
    Args:
        subnets: List of subnets
        signals: Dict mapping netuid → SignalScores
        
    Returns:
        List of CompositeScore sorted by composite (descending)
    """
    results = []
    
    for subnet in subnets:
        sig = signals.get(subnet.netuid, SignalScores())
        composite = compute_composite_score(sig)
        
        # Count available signals
        signals_available = sum(1 for v in [
            sig.yield_score,
            sig.volume_score,
            sig.momentum_1h_score,
            sig.momentum_1d_score,
            sig.momentum_7d_score,
            sig.age_score,
        ] if v is not None)
        
        results.append(CompositeScore(
            netuid=subnet.netuid,
            name=subnet.name,
            composite=composite,
            rank=0,  # Will be set after sorting
            signals=sig,
            raw_data=subnet,
            signals_available=signals_available,
        ))
    
    # Sort by composite score (descending), None scores at the end
    results.sort(
        key=lambda x: (x.composite is None, -(x.composite or 0))
    )
    
    # Assign ranks
    for i, result in enumerate(results):
        result.rank = i + 1
    
    return results


def generate_orders(
    ranked: list[CompositeScore],
    total_stake_tao: float,
    top_n: int = 5,
    bottom_n: int = 0,
) -> list[RebalanceOrder]:
    """Generate rebalance orders based on rankings.
    
    Args:
        ranked: List of subnets ranked by composite score
        total_stake_tao: Total TAO available for staking
        top_n: Number of top-ranked subnets to stake in (0 to skip staking)
        bottom_n: Number of bottom-ranked subnets to unstake from
        
    Returns:
        List of RebalanceOrder
    """
    orders = []
    
    # Filter to subnets with valid composite scores
    valid_ranked = [r for r in ranked if r.composite is not None]
    
    if not valid_ranked:
        return orders
    
    # Stake in top N (if top_n > 0)
    if top_n > 0:
        # Calculate total score for proportional allocation
        total_score = sum(r.composite for r in valid_ranked)
        
        for subnet in valid_ranked[:top_n]:
            # Proportional allocation based on score
            proportion = subnet.composite / total_score if total_score > 0 else 0
            amount = total_stake_tao * proportion * (top_n / len(valid_ranked))  # Boost for top
            
            orders.append(RebalanceOrder(
                action="stake",
                netuid=subnet.netuid,
                amount_tao=round(amount, 6),
                reason=f"Top rank {subnet.rank} (score: {subnet.composite:.3f})",
            ))
    
    # Unstake from bottom N (if bottom_n > 0)
    if bottom_n > 0:
        for subnet in valid_ranked[-bottom_n:]:
            if subnet.composite < 0.3:  # Only unstake from low scorers
                orders.append(RebalanceOrder(
                    action="unstake",
                    netuid=subnet.netuid,
                    amount_tao=round(total_stake_tao * 0.1, 6),  # Unstake 10% of stake
                    reason=f"Low score {subnet.composite:.3f}",
                ))
    
    return orders
