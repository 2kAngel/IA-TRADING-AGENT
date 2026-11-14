import urllib.request
import json
import os
from typing import List, Dict, Any


def fetch_binance_btc_candles(symbol: str = "BTCEUR", interval: str = "1h", limit: int = 100) -> List[Dict[str, Any]]:
    """
    Obtiene velas OHLCV reales y gratuitas de Binance Spot vía REST público.
    No requiere API Key ni credenciales.
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        raw_data = json.loads(response.read().decode("utf-8"))

    candles = []
    for k in raw_data:
        candles.append({
            "timestamp": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return candles


def generate_synthetic_btc_candles(count: int = 150, start_price: float = 60000.0) -> List[Dict[str, Any]]:
    """
    Generador determinista de velas sintéticas para backtests locales offline y tests de integración.
    """
    import math
    candles = []
    price = start_price
    for i in range(count):
        # Onda con tendencia y oscilación controlada
        change_pct = 0.008 * math.sin(i / 8.0) + (0.002 if i > 30 else -0.001)
        open_p = price
        close_p = open_p * (1.0 + change_pct)
        high_p = max(open_p, close_p) * 1.003
        low_p = min(open_p, close_p) * 0.997
        candles.append({
            "timestamp": 1700000000000 + (i * 3600000),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": round(15.0 + abs(change_pct) * 1000, 2),
        })
        price = close_p
    return candles
