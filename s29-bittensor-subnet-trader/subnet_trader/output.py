"""Output formatting for analysis results."""

import csv
import io
from typing import List
from subnet_trader.models import (
    AnalysisResult,
    CompositeScore,
    RebalanceOrder,
)


def analysis_to_csv(result: AnalysisResult) -> str:
    """Convert AnalysisResult to CSV format.
    
    Args:
        result: AnalysisResult with subnets and orders
        
    Returns:
        CSV string
    """
    if not result.subnets:
        return ""
    
    # Define columns
    fieldnames = [
        "rank",
        "netuid",
        "name",
        "composite_score",
        "signals_available",
        # Signal scores
        "yield_score",
        "volume_score",
        "momentum_1h_score",
        "momentum_1d_score",
        "momentum_7d_score",
        "age_score",
        # Raw data
        "alpha_price",
        "volume_24h",
        "price_change_1h",
        "price_change_1d",
        "price_change_7d",
        "price_change_30d",
        "registration_timestamp",
    ]
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for score in result.subnets:
        row = {
            "rank": score.rank,
            "netuid": score.netuid,
            "name": score.name,
            "composite_score": _format_float(score.composite),
            "signals_available": score.signals_available,
            # Signal scores (None becomes empty string)
            "yield_score": _format_float(score.signals.yield_score),
            "volume_score": _format_float(score.signals.volume_score),
            "momentum_1h_score": _format_float(score.signals.momentum_1h_score),
            "momentum_1d_score": _format_float(score.signals.momentum_1d_score),
            "momentum_7d_score": _format_float(score.signals.momentum_7d_score),
            "age_score": _format_float(score.signals.age_score),
            # Raw data
            "alpha_price": _format_float(score.raw_data.alpha_price),
            "volume_24h": _format_float(score.raw_data.volume_24h),
            "price_change_1h": _format_float(score.raw_data.price_change_1h),
            "price_change_1d": _format_float(score.raw_data.price_change_1d),
            "price_change_7d": _format_float(score.raw_data.price_change_7d),
            "price_change_30d": _format_float(score.raw_data.price_change_30d),
            "registration_timestamp": _format_timestamp(score.raw_data.registration_timestamp),
        }
        writer.writerow(row)
    
    return output.getvalue()


def write_csv(orders: List[RebalanceOrder]) -> str:
    """Convert rebalance orders to CSV format.
    
    Args:
        orders: List of RebalanceOrder
        
    Returns:
        CSV string
    """
    if not orders:
        return ""
    
    fieldnames = ["action", "netuid", "amount_tao", "reason"]
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for order in orders:
        writer.writerow({
            "action": order.action,
            "netuid": order.netuid,
            "amount_tao": order.amount_tao,
            "reason": order.reason,
        })
    
    return output.getvalue()


def _format_float(value) -> str:
    """Format a float value for CSV output.
    
    None values become empty strings.
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        # Always show as decimal with 6 decimal places, strip trailing zeros
        result = f"{float(value):.6f}".rstrip("0").rstrip(".")
        # Ensure at least one decimal place for floats
        if "." not in result and isinstance(value, float):
            result += ".0"
        return result
    return str(value)


def _format_timestamp(value) -> str:
    """Format a datetime for CSV output."""
    if value is None:
        return ""
    return value.isoformat()
