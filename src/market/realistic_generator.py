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
    random.seed(42)  # Determinista pero con caos realista
    candles = []
    price = start_price

    # Parámetros de regímenes (ciclos de 80 a 180 velas)
    regimes = ["BULL_TREND", "CHOPPY_RANGE", "FLASH_CRASH", "BEAR_GRIND"]
    current_regime = "CHOPPY_RANGE"
    regime_duration = 100
    regime_counter = 0

    for i in range(count):
        regime_counter += 1
        if regime_counter >= regime_duration:
            current_regime = random.choice(regimes)
            regime_duration = random.randint(70, 160)
            regime_counter = 0

        # Dinámica por régimen con estrés financiero real
        if current_regime == "BULL_TREND":
            drift = 0.0018 + random.gauss(0.0, 0.007)
            volatility = 0.012
        elif current_regime == "CHOPPY_RANGE":
            # Picadora de carne: Mercado oscilante que sangra las cuentas por comisiones y stops
            drift = -0.0012 + random.gauss(0.0, 0.015)
            volatility = 0.024  # Falsas rupturas violentas
        elif current_regime == "BEAR_GRIND":
            # Tendencia bajista severa y prolongada
            drift = -0.0045 + random.gauss(0.0, 0.012)
            volatility = 0.018
        elif current_regime == "FLASH_CRASH":
            # Desplome de cisne negro (barridos de stops y caídas en picado)
            drift = -0.045 + random.gauss(0.0, 0.025)
            volatility = 0.055

        open_p = price
        close_p = max(5000.0, open_p * (1.0 + drift))

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
