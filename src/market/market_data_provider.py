import os
import json
import time
from typing import List, Dict, Any, Optional
import pandas as pd

# Directorio de caché local
CACHE_DIR = os.path.join("data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

ASSET_CONFIGS = {
    "BTC": {
        "name": "Bitcoin (BTC)",
        "ticker": "BTC-USD",
        "symbol": "BTC/USD",
        "currency": "$",
        "icon": "🪙",
        "default_price": 63000.0,
    },
    "GOLD": {
        "name": "Oro (Gold)",
        "ticker": "GC=F",
        "symbol": "XAU/USD",
        "currency": "$",
        "icon": "🥇",
        "default_price": 2650.0,
    },
    "SP500": {
        "name": "S&P 500 (SPY)",
        "ticker": "SPY",
        "symbol": "SPY/USD",
        "currency": "$",
        "icon": "📈",
        "default_price": 580.0,
    },
    "IBERDROLA": {
        "name": "Iberdrola (IBE.MC)",
        "ticker": "IBE.MC",
        "symbol": "IBE/EUR",
        "currency": "€",
        "icon": "⚡",
        "default_price": 13.80,
    },
}

TIMEFRAME_CONFIGS = {
    "1m": {
        "name": "1 Minuto (1m)",
        "interval": "1m",
        "yf_period": "7d",
        "max_candles": 2000,
        "default_candles": 800,
        "slider_step": 100,
        "description": "Scalping rápido intradía (últimos 5-7 días)",
    },
    "1h": {
        "name": "1 Hora (1h)",
        "interval": "1h",
        "yf_period": "730d",
        "max_candles": 3000,
        "default_candles": 800,
        "slider_step": 100,
        "description": "Swing trading continuo (hasta 2 años)",
    },
    "1w": {
        "name": "1 Semana (1w)",
        "interval": "1wk",
        "yf_period": "max",
        "max_candles": 500,
        "default_candles": 150,
        "slider_step": 10,
        "description": "Posicional / Macro-tendencias (años de mercado)",
    },
}


def get_cache_file_path(asset_key: str, timeframe: str) -> str:
    return os.path.join(CACHE_DIR, f"{asset_key.lower()}_{timeframe}.json")


def fetch_and_cache_market_candles(asset_key: str = "BTC", timeframe: str = "1h") -> List[Dict[str, Any]]:
    """
    Descarga velas reales mediante yfinance y las persiste en data/cache.
    """
    if asset_key not in ASSET_CONFIGS:
        asset_key = "BTC"
    if timeframe not in TIMEFRAME_CONFIGS:
        timeframe = "1h"

    cfg_asset = ASSET_CONFIGS[asset_key]
    cfg_tf = TIMEFRAME_CONFIGS[timeframe]
    ticker = cfg_asset["ticker"]
    interval = cfg_tf["interval"]
    period = cfg_tf["yf_period"]

    try:
        import yfinance as yf
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            candles = []
            for ts, row in df.iterrows():
                try:
                    c_open = float(row["Open"])
                    c_high = float(row["High"])
                    c_low = float(row["Low"])
                    c_close = float(row["Close"])
                    c_vol = float(row["Volume"]) if "Volume" in row and not pd.isna(row["Volume"]) else 1000.0
                    
                    if c_high < c_low:
                        c_high, c_low = c_low, c_high

                    candles.append({
                        "timestamp": str(ts),
                        "open": round(c_open, 4),
                        "high": round(c_high, 4),
                        "low": round(c_low, 4),
                        "close": round(c_close, 4),
                        "volume": round(c_vol, 2),
                    })
                except Exception:
                    continue

            if candles:
                cache_path = get_cache_file_path(asset_key, timeframe)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(candles, f)
                return candles
    except Exception as e:
        print(f"[MarketDataProvider] Advertencia al descargar {ticker}: {e}")

    return []


def load_cached_market_candles(asset_key: str = "BTC", timeframe: str = "1h") -> List[Dict[str, Any]]:
    """
    Carga velas desde el archivo de caché en disco si existe.
    """
    cache_path = get_cache_file_path(asset_key, timeframe)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    return []


def get_market_candles(
    asset_key: str = "BTC",
    timeframe: str = "1h",
    num_candles: int = 800,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """
    Obtiene las últimas `num_candles` velas para el activo y temporalidad especificados.
    1. Consulta caché local.
    2. Si no hay suficientes o force_refresh=True, descarga de yfinance.
    3. Si falla la red, genera fallback estocástico calibrado a ese activo.
    """
    candles = []
    if not force_refresh:
        candles = load_cached_market_candles(asset_key, timeframe)

    if len(candles) < num_candles:
        fetched = fetch_and_cache_market_candles(asset_key, timeframe)
        if len(fetched) > len(candles):
            candles = fetched

    # Si tenemos suficientes velas reales, devolver las últimas num_candles
    if len(candles) >= num_candles:
        return candles[-num_candles:]
    elif len(candles) > 0:
        return candles

    # Fallback estocástico calibrado por activo si no hay internet ni caché
    from src.market.realistic_generator import generate_realistic_btc_market_cycles
    base_price = ASSET_CONFIGS.get(asset_key, {}).get("default_price", 60000.0)
    synthetic = generate_realistic_btc_market_cycles(num_candles=num_candles, initial_price=base_price)
    return synthetic
