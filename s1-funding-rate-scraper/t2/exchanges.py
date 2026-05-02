# exchanges.py
"""
Exchange API clients for funding rate data
"""

import requests
import time
from typing import Dict, List, Optional, Any


class ExchangeAPIClient:
    """Base class for exchange API clients"""

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        """Get all funding rates from this exchange"""
        raise NotImplementedError


class LighterClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Lighter", "https://mainnet.zklighter.elliot.ai")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/api/v1/funding-rates", timeout=5)
            response.raise_for_status()
            data = response.json()

            rates = []
            funding_rates = data.get("funding_rates", [])
            for rate_data in funding_rates:
                rates.append({
                    "exchange": self.name,
                    "symbol": rate_data.get("symbol"),
                    "funding_rate": float(rate_data.get("rate", 0)),
                    "funding_period": "8h",  # Lighter uses 8h funding periods
                    "source_exchange": rate_data.get("exchange", "unknown"),
                    "market_id": rate_data.get("market_id")
                })
            return rates

        except Exception as e:
            print(f"Error fetching {self.name} funding rates: {e}")
            return []


class AsterClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Aster", "https://fapi.asterdex.com")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Aster API requires symbol parameter, so we'll fetch common pairs
        common_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "MATICUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT", "UNIUSDT"]
        rates = []

        for symbol in common_symbols:
            try:
                response = self.session.get(f"{self.base_url}/fapi/v1/fundingRate", params={"symbol": symbol}, timeout=5)
                response.raise_for_status()
                data = response.json()

                # Aster returns an array of historical funding rates
                if isinstance(data, list) and len(data) > 0:
                    # Get the most recent funding rate
                    latest = data[-1]
                    rates.append({
                        "exchange": self.name,
                        "symbol": latest.get("symbol", symbol),
                        "funding_rate": float(latest.get("fundingRate", 0)),
                        "funding_period": latest.get("funding_interval", "8h"),  # Use API response if available
                        "funding_time": latest.get("fundingTime"),
                        "historical_count": len(data)
                    })
                elif isinstance(data, dict):
                    # Handle potential dict response
                    if data.get("code") == 200:
                        funding_data = data.get("data", {})
                        rates.append({
                            "exchange": self.name,
                            "symbol": funding_data.get("symbol", symbol),
                            "funding_rate": float(funding_data.get("fundingRate", 0)),
                            "funding_period": funding_data.get("fundingInterval", "8h"),
                            "funding_interval": funding_data.get("fundingInterval"),
                            "next_funding_rate": float(funding_data.get("nextFundingRate", 0))
                        })
                    else:
                        # Try direct dict format
                        rates.append({
                            "exchange": self.name,
                            "symbol": data.get("symbol", symbol),
                            "funding_rate": float(data.get("fundingRate", 0)),
                            "funding_period": data.get("fundingInterval", "8h"),
                            "funding_interval": data.get("fundingInterval"),
                            "next_funding_rate": float(data.get("nextFundingRate", 0))
                        })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class HyperliquidClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Hyperliquid", "https://api.hyperliquid.xyz")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Hyperliquid requires coin parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        current_time = int(time.time() * 1000)  # Current time in milliseconds
        start_time = current_time - (24 * 60 * 60 * 1000)  # 24 hours ago

        for symbol in common_symbols:
            try:
                response = self.session.post(f"{self.base_url}/info",
                                            json={
                                                "type": "fundingHistory",
                                                "coin": symbol,
                                                "startTime": start_time
                                            },
                                            headers={"Content-Type": "application/json"},
                                             timeout=5)
                response.raise_for_status()
                data = response.json()

                # Get most recent funding rate
                if data and len(data) > 0:
                    latest = data[-1]  # Most recent entry
                    rates.append({
                        "exchange": self.name,
                        "symbol": symbol,
                        "funding_rate": float(latest.get("fundingRate", 0)),
                        "funding_period": "1h",  # Hyperliquid uses 1h funding periods
                        "premium": float(latest.get("premium", 0)),
                        "timestamp": latest.get("time")
                    })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class EdgeXClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("edgeX", "https://api.starknet.extended.exchange")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # EdgeX requires market parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        for symbol in common_symbols:
            try:
                # Convert symbol to Extended format (BTC -> BTC-USD)
                market_symbol = f"{symbol}-USD"
                response = self.session.get(f"{self.base_url}/api/v1/info/markets/{market_symbol}/stats", timeout=5)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "OK":
                    market_data = data.get("data", {})
                    rates.append({
                        "exchange": self.name,
                        "symbol": market_symbol,
                        "funding_rate": float(market_data.get("fundingRate", 0)),
                        "funding_period": "8h",  # EdgeX uses 8h funding periods
                        "funding_time": market_data.get("nextFundingRate"),
                        "mark_price": float(market_data.get("markPrice", 0))
                    })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class ApexClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("ApeX Protocol", "https://api.pro.apex.exchange")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Apex requires symbol parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        for symbol in common_symbols:
            try:
                # Use public endpoint for funding rates
                response = self.session.get(f"{self.base_url}/v3/funding",
                                            params={"symbol": f"{symbol}-USDT"},
                                            timeout=5)
                response.raise_for_status()
                data = response.json()

                # Get the most recent funding rate
                if data and len(data) > 0:
                    latest = data[-1]  # Most recent entry
                    rates.append({
                        "exchange": self.name,
                        "symbol": latest.get("symbol", f"{symbol}-USDT"),
                        "funding_rate": float(latest.get("rate", 0)),
                        "funding_period": "8h",  # Apex uses 8h funding periods
                        "funding_time": latest.get("time"),
                        "mark_price": float(latest.get("price", 0))
                    })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class GrvtClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Grvt", "https://api-docs.grvt.io")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Grvt requires instrument parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        for symbol in common_symbols:
            try:
                response = self.session.get(f"{self.base_url}/funding-rate", params={"instrument": symbol}, timeout=5)
                response.raise_for_status()
                data = response.json()
                rates.append({
                    "exchange": self.name,
                    "symbol": data.get("instrument", symbol),
                    "funding_rate": float(data.get("funding_rate", 0)),
                    "funding_period": "8h",  # Grvt uses 8h funding periods
                    "funding_time": data.get("funding_time"),
                    "mark_price": float(data.get("mark_price", 0))
                })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class ExtendedClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Extended", "https://api.docs.extended.exchange")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Extended requires market parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        for symbol in common_symbols:
            try:
                response = self.session.get(f"{self.base_url}/funding-rate", params={"market": symbol}, timeout=5)
                response.raise_for_status()
                data = response.json()
                rates.append({
                    "exchange": self.name,
                    "symbol": data.get("market", symbol),
                    "funding_rate": float(data.get("funding_rate", 0)),
                    "funding_period": "8h",  # Extended uses 8h funding periods
                    "timestamp": data.get("timestamp")
                })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class ParadexClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Paradex", "https://api.prod.paradex.trade")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Paradex requires market parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        for symbol in common_symbols:
            try:
                response = self.session.get(f"{self.base_url}/v1/funding-data", params={"market": symbol}, timeout=5)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                if results:
                    latest = results[0]
                    rates.append({
                        "exchange": self.name,
                        "symbol": symbol,
                        "funding_rate": float(latest.get("funding_rate", 0)),
                        "funding_period": "1h",  # Paradex uses 1h funding periods
                        "funding_time": latest.get("funding_time"),
                        "oracle_price": float(latest.get("oracle_price", 0))
                    })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class PacificaClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Pacifica", "https://api.pacifica.fi")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Pacifica requires symbol parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        for symbol in common_symbols:
            try:
                response = self.session.get(f"{self.base_url}/api/v1/funding_rate/history", params={"symbol": symbol}, timeout=5)
                response.raise_for_status()
                data = response.json()
                if data.get("success") and data.get("data"):
                    latest = data["data"][0]
                    rates.append({
                        "exchange": self.name,
                        "symbol": symbol,
                        "funding_rate": float(latest.get("funding_rate", 0)),
                        "funding_period": "8h",  # Pacifica uses 8h funding periods
                        "created_at": latest.get("created_at"),
                        "oracle_price": float(latest.get("oracle_price", 0))
                    })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates


class ReyaClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Reya", "https://api.reya.xyz")

    def get_funding_rates(self) -> List[Dict[str, Any]]:
        # Reya requires market parameter, so we'll fetch common pairs
        common_symbols = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
        rates = []

        for symbol in common_symbols:
            try:
                response = self.session.get(f"{self.base_url}/v2/funding", params={"market": symbol}, timeout=5)
                response.raise_for_status()
                data = response.json()
                rates.append({
                    "exchange": self.name,
                    "symbol": data.get("market", symbol),
                    "funding_rate": float(data.get("current_funding_rate", 0)),
                    "funding_period": "1h",  # Reya uses 1h funding periods
                    "next_funding_time": data.get("next_funding_time"),
                    "mark_price": float(data.get("mark_price", 0))
                })
            except Exception as e:
                print(f"Error fetching {self.name} {symbol}: {e}")
                continue

        return rates