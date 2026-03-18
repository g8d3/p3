"""Strategy logic: composite scoring, ranking, and rebalance orders."""

from datetime import datetime, timezone
from subnet_trader.models import (
    SubnetData,
    SignalScores,
    CompositeScore,
    RebalanceOrder,
    AnalysisResult,
)
from subnet_trader.signals import compute_all_signals
from subnet_trader.config import Config, Weights


def compute_composite_score(signals: SignalScores, weights: dict[str, float]) -> float:
    """Compute weighted composite score from individual signals."""
    return (
        signals.yield_score * weights.get("yield", 0.30)
        + signals.momentum_score * weights.get("momentum", 0.25)
        + signals.price_trend_score * weights.get("price_trend", 0.20)
        + signals.volume_score * weights.get("volume", 0.15)
        + signals.age_score * weights.get("age", 0.10)
    )


def rank_subnets(
    subnets: list[SubnetData],
    signals_map: dict[int, SignalScores],
    weights: dict[str, float],
    top_n: int | None = None,
) -> list[CompositeScore]:
    """Rank subnets by composite score.

    Returns list of CompositeScore sorted by composite descending,
    with rank assigned (1 = best).
    """
    scores = []
    for subnet in subnets:
        signals = signals_map.get(subnet.netuid, SignalScores())
        composite = compute_composite_score(signals, weights)
        scores.append((subnet, signals, composite))

    # Sort by composite descending
    scores.sort(key=lambda x: x[2], reverse=True)

    # Apply top_n limit
    if top_n is not None:
        scores = scores[:top_n]

    # Build ranked results
    result = []
    for rank, (subnet, signals, composite) in enumerate(scores, 1):
        result.append(CompositeScore(
            netuid=subnet.netuid,
            name=subnet.name,
            composite=round(composite, 6),
            rank=rank,
            signals=signals,
            raw_data=subnet,
        ))

    return result


def generate_rebalance_orders(
    ranked: list[CompositeScore],
    current_holdings: dict[int, float],
    total_tao: float,
) -> list[RebalanceOrder]:
    """Generate stake/unstake orders to rebalance portfolio.

    Args:
        ranked: Subnets ranked by composite score (top N)
        current_holdings: Current TAO holdings per netuid
        total_tao: Total TAO to allocate across top subnets

    Returns:
        List of RebalanceOrder actions
    """
    orders = []

    # Calculate target allocation proportional to composite score
    target_netuids = {s.netuid for s in ranked}
    total_composite = sum(s.composite for s in ranked)

    if total_composite == 0:
        return orders

    target_allocation = {}
    for score in ranked:
        target_allocation[score.netuid] = (score.composite / total_composite) * total_tao

    # Generate unstake orders for subnets no longer in top
    for netuid, amount in current_holdings.items():
        if netuid not in target_netuids and amount > 0:
            orders.append(RebalanceOrder(
                action="unstake",
                netuid=netuid,
                amount_tao=round(amount, 4),
            ))

    # Generate stake orders for target subnets
    for netuid, target_amount in target_allocation.items():
        current_amount = current_holdings.get(netuid, 0.0)
        diff = target_amount - current_amount

        if abs(diff) < 1.0:  # Skip tiny adjustments (< 1 TAO)
            continue

        if diff > 0:
            orders.append(RebalanceOrder(
                action="stake",
                netuid=netuid,
                amount_tao=round(diff, 4),
            ))
        elif diff < 0:
            orders.append(RebalanceOrder(
                action="unstake",
                netuid=netuid,
                amount_tao=round(abs(diff), 4),
            ))

    return orders


class SubnetAnalyzer:
    """High-level analyzer interface for subnet trading strategy.

    Agent-friendly API:
        from subnet_trader import SubnetAnalyzer, load_config

        config = load_config()
        analyzer = SubnetAnalyzer(config)
        result = await analyzer.analyze()
        print(result.to_json())
    """

    def __init__(self, config: Config):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            from subnet_trader.chain import SubnetChainClient
            self._client = SubnetChainClient(network=self.config.network)
        return self._client

    def _fetch_subnets(self) -> list[SubnetData]:
        """Fetch all subnet data from chain."""
        client = self._get_client()
        return client.get_all_subnets()

    def _fetch_history(self) -> tuple[dict[int, float], dict[int, float]]:
        """Fetch historical data for momentum and price MA.

        Returns:
            (emission_history, price_ma) dicts mapping netuid → value
        """
        from subnet_trader.db import HistoryDB
        db = HistoryDB()
        emission_history = db.get_emission_history(days=7)
        price_ma = db.get_price_ma(days=30)
        return emission_history, price_ma

    def _fetch_current_block(self) -> int:
        """Get current block number."""
        # For now, estimate based on time
        import time
        return int(time.time() // 12)  # ~12 seconds per block

    def analyze(
        self,
        current_holdings: dict[int, float] | None = None,
        total_tao: float = 100.0,
    ) -> AnalysisResult:
        """Run full analysis pipeline.

        Args:
            current_holdings: Current TAO staked per netuid (default: empty)
            total_tao: Total TAO to allocate (default: 100)

        Returns:
            AnalysisResult with ranked subnets and rebalance orders
        """
        if current_holdings is None:
            current_holdings = {}

        # 1. Fetch data
        subnets = self._fetch_subnets()
        emission_history, price_ma = self._fetch_history()
        current_block = self._fetch_current_block()

        # 2. Compute signals
        signals_map = compute_all_signals(
            subnets, emission_history, price_ma, current_block
        )

        # 3. Rank subnets
        weights = self.config.weights.as_dict()
        ranked = rank_subnets(subnets, signals_map, weights, self.config.top_n)

        # 4. Generate orders
        orders = generate_rebalance_orders(ranked, current_holdings, total_tao)

        # 5. Snapshot to DB for future history
        from subnet_trader.db import HistoryDB
        db = HistoryDB()
        db.save_snapshot(subnets, current_block)

        return AnalysisResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            subnets=ranked,
            orders=orders,
        )

    def rank_subnets(self, top_n: int | None = None) -> list[CompositeScore]:
        """Synchronous convenience method for ranking subnets."""
        result = self.analyze()
        if top_n:
            return result.subnets[:top_n]
        return result.subnets

    def close(self):
        """Clean up resources."""
        if self._client:
            self._client.close()
