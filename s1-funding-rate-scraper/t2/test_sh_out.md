Fetching funding rates for 1 pairs from 10 exchanges...

Fetching from Lighter...

Fetching from Aster...

Fetching from Hyperliquid...

Fetching from edgeX...

Fetching from ApeX Protocol...
Error fetching ApeX Protocol BTC: HTTPSConnectionPool(host='api.pro.apex.exchange', port=443): Max retries exceeded with url: /v3/funding?symbol=BTC-USDT (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x7521007f5590>, 'Connection to api.pro.apex.exchange timed out. (connect timeout=5)'))

Fetching from Grvt...
Error fetching Grvt BTC: 403 Client Error: Forbidden for url: https://api-docs.grvt.io/funding-rate?instrument=BTC

Fetching from Extended...
Error fetching Extended BTC: 404 Client Error: Not Found for url: https://api.docs.extended.exchange/funding-rate?market=BTC

Fetching from Paradex...
Error fetching Paradex BTC: 401 Client Error: Unauthorized for url: https://api.prod.paradex.trade/v1/funding-data?market=BTC

Fetching from Pacifica...

Fetching from Reya...
Error fetching Reya BTC: 404 Client Error: Not Found for url: https://api.reya.xyz/v2/funding?market=BTC

+-------------+----------+----------------+----------------+---------------------+
| Exchange    | Symbol   |   Funding Rate | Funding Time   | Next Funding Time   |
+=============+==========+================+================+=====================+
| Lighter     | BTC      |        6.6e-05 | N/A            | N/A                 |
+-------------+----------+----------------+----------------+---------------------+
| Aster       | BTCUSDT  |       -4e-06   | 1764777600000  | N/A                 |
+-------------+----------+----------------+----------------+---------------------+
| Hyperliquid | BTC      |        1.3e-05 | N/A            | N/A                 |
+-------------+----------+----------------+----------------+---------------------+
| edgeX       | BTC-USD  |       -2e-06   | 1764792000000  | N/A                 |
+-------------+----------+----------------+----------------+---------------------+
| Pacifica    | BTC      |        1.3e-05 | N/A            | N/A                 |
+-------------+----------+----------------+----------------+---------------------+