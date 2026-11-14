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

    # Parámetros de regímenes cíclicos de Bitcoin con selección natural real:
    # 1. BULL_RUN: Tendencia alcista donde las mejores estrategias ganan capital y procrean (alcanzando 40 €).
    # 2. CHOPPY_RANGE: Rango lateral engañoso con falsas rupturas y fricción de comisiones.
    # 3. BEAR_SELLOFF: Corrección prolongada que castiga a estrategias sin disciplina y lleva a la quiebra técnica (muerte).
    regimes = ["BULL_RUN", "CHOPPY_RANGE", "BEAR_SELLOFF", "CHOPPY_RANGE", "BULL_RUN", "BEAR_SELLOFF"]
    current_regime = "CHOPPY_RANGE"
    regime_duration = 75
    regime_counter = 0

    for i in range(count):
        regime_counter += 1
        if regime_counter >= regime_duration:
            current_regime = random.choice(regimes)
            regime_duration = random.randint(55, 115)
            regime_counter = 0

        # Dinámica por régimen calibrada para estrés y rendimiento financiero real
        if current_regime == "BULL_RUN":
            drift = 0.0034 + random.gauss(0.0, 0.009)
            volatility = 0.013
        elif current_regime == "CHOPPY_RANGE":
            drift = -0.0006 + random.gauss(0.0, 0.013)
            volatility = 0.022
        elif current_regime == "BEAR_SELLOFF":
            drift = -0.0028 + random.gauss(0.0, 0.012)
            volatility = 0.019

        # Sacudidas repentinas (barridos institucionales de stops)
        if random.random() < 0.015:
            drift -= random.uniform(0.025, 0.045)

        open_p = price
        close_p = max(18000.0, open_p * (1.0 + drift))

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
