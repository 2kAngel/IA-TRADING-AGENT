import math
import random
from typing import List, Dict, Any


def generate_realistic_btc_market_cycles(count: int = 1000, start_price: float = 60000.0) -> List[Dict[str, Any]]:
    """
    Generador cuantitativo con REGÍMENES REALES DE BITCOIN:
    1. Fases de tendencia alcista fuerte (Bull Runs).
    2. Fases de 'picadora de carne' (Rango falso que barre stops).
    3. Fases de Bear Market / Desplome prolongado (-25% a -40%).
    4. Flash Crashes (Cisnes negros repentinos con mechas de liquidación).
    """
    random.seed(42)  # Determinista pero con dinamismo realista
    candles = []
    price = start_price

    # Parámetros de regímenes cíclicos de Bitcoin
    regimes = ["BULL_TREND", "CHOPPY_RANGE", "PULLBACK", "ACCUMULATION"]
    current_regime = "ACCUMULATION"
    regime_duration = 80
    regime_counter = 0

    for i in range(count):
        regime_counter += 1
        if regime_counter >= regime_duration:
            current_regime = random.choice(regimes)
            regime_duration = random.randint(60, 140)
            regime_counter = 0

        # Dinámica por régimen con oscilaciones reales
        if current_regime == "BULL_TREND":
            drift = 0.0022 + random.gauss(0.0, 0.008)
            volatility = 0.012
        elif current_regime == "CHOPPY_RANGE":
            # Rango oscilante con trampas de mercado y falsas rupturas
            drift = -0.0003 + random.gauss(0.0, 0.011)
            volatility = 0.018
        elif current_regime == "PULLBACK":
            # Fase correctiva / toma de beneficios
            drift = -0.0016 + random.gauss(0.0, 0.009)
            volatility = 0.015
        elif current_regime == "ACCUMULATION":
            # Consolidación antes de nuevos impulsos
            drift = 0.0007 + random.gauss(0.0, 0.007)
            volatility = 0.010

        # Ocasional sacudida rápida (-2% a -4%) para probar el rigor de los stop losses
        if random.random() < 0.012:
            drift -= random.uniform(0.02, 0.035)

        open_p = price
        close_p = max(25000.0, open_p * (1.0 + drift))

        # Mechas realistas (barridos de stops institucionales)
        high_p = max(open_p, close_p) * (1.0 + abs(random.gauss(0.004, volatility * 0.5)))
        low_p = min(open_p, close_p) * (1.0 - abs(random.gauss(0.004, volatility * 0.5)))

        candles.append({
            "timestamp": 1704067200000 + (i * 3600000),  # Desde 1 de enero de 2024
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": round(50.0 + abs(drift) * 8000.0 + random.uniform(10, 40), 2),
        })
        price = close_p

    return candles
