# utils.py
"""
Utility functions for the funding rate CLI
"""

from datetime import datetime
from typing import Optional


def format_timestamp(timestamp) -> str:
    """Convert timestamp to human readable format"""
    if not timestamp:
        return "N/A"

    try:
        # Handle different timestamp formats
        if isinstance(timestamp, str):
            # Try to parse as ISO format or unix timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                # Assume unix timestamp in seconds
                dt = datetime.fromtimestamp(float(timestamp))
        elif isinstance(timestamp, (int, float)):
            # Unix timestamp
            if timestamp > 1e10:  # milliseconds
                dt = datetime.fromtimestamp(timestamp / 1000)
            else:  # seconds
                dt = datetime.fromtimestamp(timestamp)
        else:
            return str(timestamp)

        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return str(timestamp)