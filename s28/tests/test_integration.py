"""End-to-end integration tests."""

import pytest
import json
from unittest.mock import patch
from subnet_trader.models import SubnetData, AnalysisResult
from subnet_trader.strategy import SubnetAnalyzer
from subnet_trader.config import load_config


class TestEndToEnd:
    """Full pipeline: fetch → signals → score → orders → JSON output."""

    @pytest.fixture
    def mock_subnets(self):
        return [
            SubnetData(
                netuid=1, name="Apex", symbol="α",
                tao_staked=500_000, alpha_price=0.15,
                tao_reserve=75_000, alpha_reserve=500_000,
                alpha_staked=1_000_000, emission_share=0.12,
                tao_emission_per_block=0.12, registration_block=100_000,
                market_cap=150_000, volume_24h=10_000,
                price_change_1d=-2.5, price_change_7d=-8.0,
            ),
            SubnetData(
                netuid=19, name="τ", symbol="t",
                tao_staked=800_000, alpha_price=0.069,
                tao_reserve=22_500, alpha_reserve=324_000,
                alpha_staked=532_000, emission_share=0.08,
                tao_emission_per_block=0.08, registration_block=200_000,
                market_cap=60_000, volume_24h=5_600,
                price_change_1d=-5.0, price_change_7d=-29.0,
            ),
            SubnetData(
                netuid=8, name="Stable", symbol="S",
                tao_staked=1_000_000, alpha_price=0.10,
                tao_reserve=100_000, alpha_reserve=1_000_000,
                alpha_staked=2_000_000, emission_share=0.15,
                tao_emission_per_block=0.15, registration_block=300_000,
                market_cap=100_000, volume_24h=3_000,
                price_change_1d=0.5, price_change_7d=2.0,
            ),
        ]

    def test_full_pipeline_produces_valid_result(self, mock_subnets):
        """End-to-end: analyzer should produce valid AnalysisResult."""
        config = load_config()
        analyzer = SubnetAnalyzer(config)

        with patch.object(analyzer, "_fetch_subnets") as mock_fetch:
            with patch.object(analyzer, "_fetch_history") as mock_hist:
                mock_fetch.return_value = mock_subnets
                mock_hist.return_value = ({}, {})

                result = analyzer.analyze()

        assert isinstance(result, AnalysisResult)
        assert result.timestamp != ""
        assert len(result.subnets) > 0

    def test_output_is_valid_json(self, mock_subnets):
        """Output should serialize to valid JSON."""
        config = load_config()
        analyzer = SubnetAnalyzer(config)

        with patch.object(analyzer, "_fetch_subnets") as mock_fetch:
            with patch.object(analyzer, "_fetch_history") as mock_hist:
                mock_fetch.return_value = mock_subnets
                mock_hist.return_value = ({}, {})

                result = analyzer.analyze()

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert "timestamp" in parsed
        assert "subnets" in parsed
        assert "orders" in parsed
        assert isinstance(parsed["subnets"], list)
        assert isinstance(parsed["orders"], list)

    def test_output_schema_matches_contract(self, mock_subnets):
        """Output should match the agent-friendly schema."""
        config = load_config()
        analyzer = SubnetAnalyzer(config)

        with patch.object(analyzer, "_fetch_subnets") as mock_fetch:
            with patch.object(analyzer, "_fetch_history") as mock_hist:
                mock_fetch.return_value = mock_subnets
                mock_hist.return_value = ({}, {})

                result = analyzer.analyze()

        for subnet in result.subnets:
            d = subnet.to_dict()
            assert "netuid" in d
            assert "name" in d
            assert "composite_score" in d
            assert "rank" in d
            assert "signals" in d
            assert "raw_data" in d

            signals = d["signals"]
            assert "yield_score" in signals
            assert "momentum_score" in signals
            assert "price_trend_score" in signals
            assert "volume_score" in signals
            assert "age_score" in signals

    def test_ranks_are_sequential(self, mock_subnets):
        """Ranks should be sequential starting from 1."""
        config = load_config()
        analyzer = SubnetAnalyzer(config)

        with patch.object(analyzer, "_fetch_subnets") as mock_fetch:
            with patch.object(analyzer, "_fetch_history") as mock_hist:
                mock_fetch.return_value = mock_subnets
                mock_hist.return_value = ({}, {})

                result = analyzer.analyze()

        ranks = [s.rank for s in result.subnets]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_composite_scores_descending(self, mock_subnets):
        """Composite scores should be in descending order."""
        config = load_config()
        analyzer = SubnetAnalyzer(config)

        with patch.object(analyzer, "_fetch_subnets") as mock_fetch:
            with patch.object(analyzer, "_fetch_history") as mock_hist:
                mock_fetch.return_value = mock_subnets
                mock_hist.return_value = ({}, {})

                result = analyzer.analyze()

        scores = [s.composite for s in result.subnets]
        assert scores == sorted(scores, reverse=True)


class TestCLIOutput:
    """Test CLI produces expected output format."""

    def test_json_flag_output(self):
        """CLI with --json should produce parseable JSON."""
        from subnet_trader.models import CompositeScore, SignalScores, SubnetData, RebalanceOrder
        from datetime import datetime, timezone

        result = AnalysisResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            subnets=[
                CompositeScore(
                    netuid=1, name="Apex", composite=0.85, rank=1,
                    signals=SignalScores(0.9, 0.8, 0.7, 0.6, 1.0),
                    raw_data=SubnetData(netuid=1, name="Apex"),
                ),
            ],
            orders=[
                RebalanceOrder(action="stake", netuid=1, amount_tao=100.0),
            ],
        )

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert parsed["subnets"][0]["netuid"] == 1
        assert parsed["subnets"][0]["composite_score"] == 0.85
        assert parsed["orders"][0]["action"] == "stake"
