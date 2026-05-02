"""Signal computation for subnet scoring."""

from subnet_trader.models import SubnetData, SignalScores


def normalize(values: list[float]) -> list[float]:
    """Normalize a list of values to [0, 1] using min-max scaling."""
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [1.0] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def compute_yield_signal(subnets: list[SubnetData]) -> list[float]:
    """Compute yield signal: higher alpha price = higher yield potential.
    
    Since emission data isn't available via SDK, use alpha price as proxy.
    Higher price suggests higher demand for the subnet's token.
    """
    if not subnets:
        return []
    
    prices = [s.alpha_price for s in subnets]
    if not any(p > 0 for p in prices):
        return [0.5] * len(subnets)
    
    return normalize(prices)


def compute_momentum_signal(
    subnets: list[SubnetData],
    emission_history: dict[int, float],
) -> list[float]:
    """Compute momentum signal: change in emission share over time.
    
    Without historical emission data, return neutral (0.5).
    """
    if not emission_history:
        return [0.5] * len(subnets)

    deltas = []
    for s in subnets:
        prev_share = emission_history.get(s.netuid, s.emission_share)
        if prev_share > 0:
            delta = (s.emission_share - prev_share) / prev_share
        else:
            delta = 0.0
        deltas.append(delta)

    normalized = normalize(deltas)
    return normalized


def compute_price_trend_signal(
    subnets: list[SubnetData],
    price_ma: dict[int, float],
) -> list[float]:
    """Compute price trend signal: current price vs moving average.
    
    Without historical price data, return neutral (0.5).
    """
    if not price_ma:
        return [0.5] * len(subnets)

    ratios = []
    for s in subnets:
        ma = price_ma.get(s.netuid, s.alpha_price)
        if ma > 0:
            ratio = s.alpha_price / ma
            score = max(0.0, min(1.0, 2.0 - ratio))
            ratios.append(score)
        else:
            ratios.append(0.5)
    return ratios


def compute_volume_signal(subnets: list[SubnetData]) -> list[float]:
    """Compute volume signal: based on alpha price as proxy.
    
    Without volume data, use alpha price as proxy for activity/demand.
    """
    prices = [s.alpha_price for s in subnets]
    if not any(p > 0 for p in prices):
        return [0.5] * len(subnets)
    return normalize(prices)


def compute_age_signal(
    subnets: list[SubnetData],
    current_block: int,
) -> list[float]:
    """Compute age signal: how long the subnet has existed.
    
    Without registration block data, return neutral (0.5).
    """
    maturity_blocks = 50400  # ~7 days

    ages = []
    for s in subnets:
        if s.registration_block is not None and s.registration_block > 0:
            blocks_old = current_block - s.registration_block
            age = min(blocks_old / maturity_blocks, 1.0)
            ages.append(max(0.0, age))
        else:
            ages.append(0.5)
    return ages


def compute_all_signals(
    subnets: list[SubnetData],
    emission_history: dict[int, float],
    price_ma: dict[int, float],
    current_block: int,
) -> dict[int, SignalScores]:
    """Compute all signals for all subnets.

    Returns dict mapping netuid → SignalScores.
    """
    yield_scores = compute_yield_signal(subnets)
    momentum_scores = compute_momentum_signal(subnets, emission_history)
    price_trend_scores = compute_price_trend_signal(subnets, price_ma)
    volume_scores = compute_volume_signal(subnets)
    age_scores = compute_age_signal(subnets, current_block)

    result = {}
    for i, subnet in enumerate(subnets):
        result[subnet.netuid] = SignalScores(
            yield_score=yield_scores[i],
            momentum_score=momentum_scores[i],
            price_trend_score=price_trend_scores[i],
            volume_score=volume_scores[i],
            age_score=age_scores[i],
        )

    return result
