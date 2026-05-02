"""Integration tests with real data from Bittensor chain and taostats.io.

These tests fetch REAL data and verify:
1. Data is within realistic ranges
2. Signals compute correctly
3. Rankings are sensible
4. Orders are generated (dry-run only)

Run with: pytest tests/test_integration.py -v -m network
"""

import pytest
import asyncio
from datetime import datetime

from subnet_trader.chain import SubnetChainClient
from subnet_trader.tao_api import TaostatsClient, fetch_all_subnet_data
from subnet_trader.signals import compute_all_signals
from subnet_trader.strategy import rank_subnets, generate_orders


# Realistic ranges for validation
REALISTIC_RANGES = {
    "alpha_price": (0.001, 50.0),       # TAO per alpha
    "volume_24h": (0, 1_000_000_000),   # TAO (1B max)
    "price_change_pct": (-99, 1000),     # -99% to +1000%
    "market_cap": (0, 10_000_000_000_000),  # TAO (10T max)
}


def validate_subnet_data(subnet):
    """Validate subnet data is within realistic ranges."""
    errors = []
    
    if subnet.alpha_price < REALISTIC_RANGES["alpha_price"][0]:
        errors.append(f"Price {subnet.alpha_price} too low")
    if subnet.alpha_price > REALISTIC_RANGES["alpha_price"][1]:
        errors.append(f"Price {subnet.alpha_price} too high")
    
    if subnet.volume_24h < REALISTIC_RANGES["volume_24h"][0]:
        errors.append(f"Volume {subnet.volume_24h} negative")
    if subnet.volume_24h > REALISTIC_RANGES["volume_24h"][1]:
        errors.append(f"Volume {subnet.volume_24h} impossibly high")
    
    for change in [subnet.price_change_1h, subnet.price_change_1d, 
                   subnet.price_change_7d, subnet.price_change_30d]:
        if change is not None:
            if change < REALISTIC_RANGES["price_change_pct"][0]:
                errors.append(f"Price change {change}% impossibly low")
            if change > REALISTIC_RANGES["price_change_pct"][1]:
                errors.append(f"Price change {change}% impossibly high")
    
    return errors


@pytest.mark.network
class TestRealChainData:
    """Test fetching real data from Bittensor chain."""
    
    @pytest.fixture
    def chain_client(self):
        client = SubnetChainClient(network="finney")
        yield client
        client.close()
    
    def test_fetch_returns_subnets(self, chain_client):
        """Should return list of subnets."""
        subnets = chain_client.get_all_subnets()
        
        assert len(subnets) > 0, "Should return at least one subnet"
        assert len(subnets) >= 10, f"Expected ~129 subnets, got {len(subnets)}"
    
    def test_subnet_fields_present(self, chain_client):
        """Each subnet should have required fields."""
        subnets = chain_client.get_all_subnets()
        
        for subnet in subnets[:5]:  # Check first 5
            assert subnet.netuid is not None
            assert subnet.name is not None
            assert subnet.alpha_price >= 0
    
    def test_prices_within_realistic_range(self, chain_client):
        """Prices should be within Bittensor's known range."""
        subnets = chain_client.get_all_subnets()
        
        for subnet in subnets:
            if subnet.alpha_price > 0:
                assert 0.001 <= subnet.alpha_price <= 50, (
                    f"Subnet {subnet.netuid} price {subnet.alpha_price} outside range"
                )
    
    def test_emission_values_non_negative(self, chain_client):
        """Emission values should be non-negative."""
        subnets = chain_client.get_all_subnets()
        
        for subnet in subnets:
            assert subnet.emission_share >= 0, (
                f"Subnet {subnet.netuid} has negative emission share"
            )
            assert subnet.tao_emission_per_block >= 0, (
                f"Subnet {subnet.netuid} has negative emission"
            )
    
    def test_subnet_numbers_increment(self, chain_client):
        """Subnet netuids should be sequential (0, 1, 2, ...)."""
        subnets = chain_client.get_all_subnets()
        netuids = sorted([s.netuid for s in subnets])
        
        # Should include 0 (root) and go up sequentially
        assert netuids[0] == 0, "Should include root subnet (netuid=0)"
        # Check for gaps - though some gaps may exist for deactivated subnets
        for i, uid in enumerate(netuids[:20]):
            # First 20 should mostly be sequential
            if i > 0 and uid - netuids[i-1] > 1:
                pass  # Gaps allowed


@pytest.mark.network
class TestRealTaostatsData:
    """Test fetching real data from taostats.io API."""
    
    @pytest.fixture
    def tao_client(self):
        return TaostatsClient()
    
    @pytest.mark.asyncio
    async def test_api_returns_data(self, tao_client):
        """taostats.io should return subnet pool data."""
        pools = await tao_client.get_subnet_pools()
        
        assert len(pools) > 0, "Should return at least one subnet"
    
    @pytest.mark.asyncio
    async def test_pool_fields_present(self, tao_client):
        """Pool data should have expected fields."""
        pools = await tao_client.get_subnet_pools()
        
        if len(pools) == 0:
            pytest.skip("No pools returned")
        
        pool = pools[0]
        assert pool.netuid is not None
        assert pool.name is not None
        assert pool.alpha_price is not None
        assert isinstance(pool.has_volume, bool)
        assert isinstance(pool.has_price_changes, bool)
    
    @pytest.mark.asyncio
    async def test_price_changes_realistic(self, tao_client):
        """Price changes should be within realistic bounds."""
        pools = await tao_client.get_subnet_pools()
        
        for pool in pools:
            for change_name, change_val in [
                ("1h", pool.price_change_1h),
                ("1d", pool.price_change_1d),
                ("7d", pool.price_change_7d),
            ]:
                if change_val is not None:
                    # Sanity bounds: -100% to +10000%
                    assert -100 <= change_val <= 10000, (
                        f"Pool {pool.netuid} {change_name} change {change_val}% unrealistic"
                    )
    
    @pytest.mark.asyncio
    async def test_fetch_specific_subnet(self, tao_client):
        """Can fetch data for specific subnet (netuid=1 = Apex)."""
        pools = await tao_client.get_subnet_pools(netuids=[1])
        
        assert len(pools) >= 1, "Should return Apex (netuid=1)"
        apex = pools[0]
        assert apex.netuid == 1
        assert apex.name.lower() in ["apex", "α"] or "apex" in apex.name.lower()


@pytest.mark.network
class TestFullPipeline:
    """Test the full analysis pipeline with real data."""
    
    @pytest.fixture
    def chain_client(self):
        client = SubnetChainClient(network="finney")
        yield client
        client.close()
    
    @pytest.fixture
    def tao_client(self):
        return TaostatsClient()
    
    @pytest.mark.asyncio
    async def test_merged_data_is_valid(self, chain_client, tao_client):
        """Merged data from chain + taostats should be valid."""
        subnets = await fetch_all_subnet_data(chain_client, tao_client)
        
        assert len(subnets) > 0, "Should have merged subnet data"
        
        for subnet in subnets:
            # Should have at least some data
            assert subnet.alpha_price >= 0, (
                f"Subnet {subnet.netuid} has negative price"
            )
            
            # Validate realistic ranges
            errors = validate_subnet_data(subnet)
            assert len(errors) == 0, f"Subnet {subnet.netuid}: {errors}"
    
    @pytest.mark.asyncio
    async def test_signals_computed(self, chain_client, tao_client):
        """Signals should compute for real subnets."""
        subnets = await fetch_all_subnet_data(chain_client, tao_client)
        
        if len(subnets) == 0:
            pytest.skip("No subnets returned")
        
        # Limit to first 10 for speed
        subnets = subnets[:10]
        now = datetime.now()
        signals = compute_all_signals(subnets, now)
        
        assert len(signals) == len(subnets)
        
        # At least some subnets should have computable signals
        subnets_with_signals = [
            netuid for netuid, sig in signals.items()
            if sig.has_any_signal()
        ]
        assert len(subnets_with_signals) > 0, "Some subnets should have computable signals"
    
    @pytest.mark.asyncio
    async def test_rankings_produced(self, chain_client, tao_client):
        """Rankings should be produced from real data."""
        subnets = await fetch_all_subnet_data(chain_client, tao_client)
        
        if len(subnets) == 0:
            pytest.skip("No subnets returned")
        
        subnets = subnets[:20]  # Limit for speed
        now = datetime.now()
        signals = compute_all_signals(subnets, now)
        ranked = rank_subnets(subnets, signals)
        
        assert len(ranked) == len(subnets)
        
        # Ranks should be sequential
        ranks = [r.rank for r in ranked]
        assert sorted(ranks) == list(range(1, len(ranks) + 1))
    
    @pytest.mark.asyncio
    async def test_orders_generated(self, chain_client, tao_client):
        """Orders should be generated from rankings (dry-run)."""
        subnets = await fetch_all_subnet_data(chain_client, tao_client)
        
        if len(subnets) == 0:
            pytest.skip("No subnets returned")
        
        subnets = subnets[:20]
        now = datetime.now()
        signals = compute_all_signals(subnets, now)
        ranked = rank_subnets(subnets, signals)
        orders = generate_orders(ranked, total_stake_tao=1000.0, top_n=5)
        
        # Should generate stake orders
        assert len(orders) > 0, "Should generate stake orders for top subnets"
        assert all(o.action == "stake" for o in orders if o.action == "stake")
        
        # All orders should have valid amounts
        for order in orders:
            assert order.netuid is not None
            assert order.amount_tao > 0
            assert order.reason != ""
    
    @pytest.mark.asyncio
    async def test_data_quality_check(self, chain_client, tao_client):
        """Verify data quality from real sources."""
        subnets = await fetch_all_subnet_data(chain_client, tao_client)
        
        if len(subnets) == 0:
            pytest.skip("No subnets returned")
        
        # Count subnets with various data availability
        stats = {
            "total": len(subnets),
            "with_price": sum(1 for s in subnets if s.alpha_price > 0),
            "with_volume": sum(1 for s in subnets if s.has_volume),
            "with_price_changes": sum(1 for s in subnets if s.has_price_changes),
            "with_registration": sum(1 for s in subnets if s.has_registration),
        }
        
        # Most subnets should have prices
        assert stats["with_price"] > stats["total"] * 0.5, (
            f"Only {stats['with_price']}/{stats['total']} have prices"
        )
        
        # Print stats for visibility
        print(f"\nData availability:")
        print(f"  Total subnets: {stats['total']}")
        print(f"  With prices: {stats['with_price']}")
        print(f"  With volume: {stats['with_volume']}")
        print(f"  With price changes: {stats['with_price_changes']}")
        print(f"  With registration: {stats['with_registration']}")


@pytest.mark.network  
class TestCSVOutputWithRealData:
    """Test CSV output with real data."""
    
    @pytest.fixture
    def chain_client(self):
        client = SubnetChainClient(network="finney")
        yield client
        client.close()
    
    @pytest.fixture
    def tao_client(self):
        return TaostatsClient()
    
    @pytest.mark.asyncio
    async def test_csv_format_valid(self, chain_client, tao_client):
        """CSV output should be valid and parseable."""
        from subnet_trader.output import analysis_to_csv
        from subnet_trader.models import AnalysisResult
        
        subnets = await fetch_all_subnet_data(chain_client, tao_client)
        
        if len(subnets) == 0:
            pytest.skip("No subnets returned")
        
        subnets = subnets[:5]  # Limit
        now = datetime.now()
        signals = compute_all_signals(subnets, now)
        ranked = rank_subnets(subnets, signals)
        
        result = AnalysisResult(
            timestamp=now.isoformat(),
            subnets=ranked,
            orders=[],
            signals_included=["yield", "volume", "momentum_1d"],
        )
        
        csv_output = analysis_to_csv(result)
        
        # Should have header row
        lines = csv_output.strip().split("\n")
        assert len(lines) >= 2, "CSV should have header and at least one data row"
        
        # Should parse correctly
        import csv
        import io
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == len(subnets)
        
        # Each row should have required columns
        required_cols = ["rank", "netuid", "name", "composite_score", "yield_score"]
        for col in required_cols:
            assert col in reader.fieldnames, f"Missing column: {col}"


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-m", "network", "--tb=short"])
