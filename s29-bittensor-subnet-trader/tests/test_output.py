"""Tests for CSV output."""

import pytest
import csv
import io
from datetime import datetime
from subnet_trader.models import (
    SubnetData,
    SignalScores,
    CompositeScore,
    RebalanceOrder,
    AnalysisResult,
)
from subnet_trader.output import write_csv, analysis_to_csv


class TestCsvOutput:
    """Test CSV output formatting."""

    def test_basic_csv_output(self):
        """Test basic CSV output with subnets."""
        now = datetime.now()
        
        subnets = [
            SubnetData(
                netuid=1,
                name="Apex",
                alpha_price=0.15,
                volume_24h=1_000_000,
                has_volume=True,
            ),
            SubnetData(
                netuid=8,
                name="Corcel",
                alpha_price=0.10,
                has_volume=False,
            ),
        ]
        
        scores = [
            CompositeScore(
                netuid=1,
                name="Apex",
                composite=0.85,
                rank=1,
                signals=SignalScores(
                    yield_score=1.0,
                    volume_score=1.0,
                    momentum_1h_score=None,
                    momentum_1d_score=0.8,
                    momentum_7d_score=None,
                    age_score=0.9,
                ),
                raw_data=subnets[0],
                signals_available=4,
            ),
            CompositeScore(
                netuid=8,
                name="Corcel",
                composite=0.65,
                rank=2,
                signals=SignalScores(
                    yield_score=0.5,
                    volume_score=None,  # No volume data
                    momentum_1h_score=None,
                    momentum_1d_score=None,
                    momentum_7d_score=None,
                    age_score=None,
                ),
                raw_data=subnets[1],
                signals_available=1,
            ),
        ]
        
        result = AnalysisResult(
            timestamp=now.isoformat(),
            subnets=scores,
            orders=[],
            signals_included=["yield", "volume", "momentum_1d", "age"],
        )
        
        csv_content = analysis_to_csv(result)
        
        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        assert len(rows) == 2
        # First row (rank 1)
        assert rows[0]["netuid"] == "1"
        assert rows[0]["name"] == "Apex"
        assert rows[0]["rank"] == "1"
        assert rows[0]["composite_score"] == "0.85"
        assert rows[0]["signals_available"] == "4"
        assert rows[0]["volume_score"] == "1.0"
        # None values should be empty in CSV
        assert rows[0]["momentum_1h_score"] == ""

    def test_csv_includes_signal_columns(self):
        """Verify all signal columns are present in CSV."""
        subnets = [
            SubnetData(netuid=1, name="Test"),
        ]
        
        scores = [
            CompositeScore(
                netuid=1,
                name="Test",
                composite=0.75,
                rank=1,
                signals=SignalScores(
                    yield_score=0.8,
                    volume_score=0.6,
                    momentum_1h_score=0.9,
                    momentum_1d_score=0.7,
                    momentum_7d_score=0.5,
                    age_score=0.4,
                ),
                raw_data=subnets[0],
                signals_available=6,
            ),
        ]
        
        result = AnalysisResult(
            timestamp=datetime.now().isoformat(),
            subnets=scores,
            orders=[],
            signals_included=["yield", "volume", "momentum_1h", "momentum_1d", "momentum_7d", "age"],
        )
        
        csv_content = analysis_to_csv(result)
        
        reader = csv.DictReader(io.StringIO(csv_content))
        headers = reader.fieldnames
        
        assert "netuid" in headers
        assert "name" in headers
        assert "composite_score" in headers
        assert "rank" in headers
        assert "yield_score" in headers
        assert "volume_score" in headers
        assert "momentum_1h_score" in headers
        assert "momentum_1d_score" in headers
        assert "momentum_7d_score" in headers
        assert "age_score" in headers
        assert "signals_available" in headers

    def test_csv_with_rebalance_orders(self):
        """Test CSV output includes rebalance orders."""
        orders = [
            RebalanceOrder(action="stake", netuid=1, amount_tao=100.0, reason="Top ranked"),
            RebalanceOrder(action="unstake", netuid=8, amount_tao=50.0, reason="Low score"),
        ]
        
        csv_content = write_csv(orders)
        
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]["action"] == "stake"
        assert rows[0]["netuid"] == "1"
        assert rows[0]["amount_tao"] == "100.0"
        assert rows[0]["reason"] == "Top ranked"
        assert rows[1]["action"] == "unstake"

    def test_csv_none_values_as_empty(self):
        """None signal scores should appear as empty in CSV, not 'None' or '0'."""
        subnets = [
            SubnetData(netuid=1, name="Test", alpha_price=0.1),
        ]
        
        scores = [
            CompositeScore(
                netuid=1,
                name="Test",
                composite=None,  # No composite because no signals
                rank=1,
                signals=SignalScores(
                    yield_score=None,  # No data
                    volume_score=None,
                    momentum_1h_score=None,
                    momentum_1d_score=None,
                    momentum_7d_score=None,
                    age_score=None,
                ),
                raw_data=subnets[0],
                signals_available=0,
            ),
        ]
        
        result = AnalysisResult(
            timestamp=datetime.now().isoformat(),
            subnets=scores,
            orders=[],
            signals_included=[],
        )
        
        csv_content = analysis_to_csv(result)
        
        reader = csv.DictReader(io.StringIO(csv_content))
        row = list(reader)[0]
        
        # None values should be empty string, not the literal "None"
        assert row["composite_score"] == ""
        assert row["yield_score"] == ""
        assert row["signals_available"] == "0"

    def test_csv_raw_data_columns(self):
        """Test that key raw data columns are included."""
        subnets = [
            SubnetData(
                netuid=1,
                name="Apex",
                alpha_price=0.15,
                volume_24h=1_500_000,
                has_volume=True,
                price_change_1d=-5.0,
                has_price_changes=True,
            ),
        ]
        
        scores = [
            CompositeScore(
                netuid=1,
                name="Apex",
                composite=0.8,
                rank=1,
                signals=SignalScores(
                    yield_score=1.0,
                    volume_score=1.0,
                    momentum_1d_score=0.3,
                ),
                raw_data=subnets[0],
                signals_available=3,
            ),
        ]
        
        result = AnalysisResult(
            timestamp=datetime.now().isoformat(),
            subnets=scores,
            orders=[],
            signals_included=["yield", "volume", "momentum_1d"],
        )
        
        csv_content = analysis_to_csv(result)
        
        reader = csv.DictReader(io.StringIO(csv_content))
        row = list(reader)[0]
        
        # Verify raw data is included
        assert row["alpha_price"] == "0.15"
        assert row["volume_24h"] == "1500000"
        assert row["price_change_1d"] == "-5.0"
