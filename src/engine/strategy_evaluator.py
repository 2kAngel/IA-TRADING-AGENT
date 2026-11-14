import math
from typing import List, Dict, Any, Optional
from src.core.models import StrategyGenome
from src.engine.indicators import TechnicalIndicators


class StrategyEvaluator:
    """
    Evalúa condiciones de entrada y salida para múltiples familias técnicas:
    1. donchian_breakout (Canales Donchian + ATR)
    2. trend_pullback_rsi (Tendencia EMA + Rebote Sobreventa RSI)
    3. bollinger_mean_reversion (Reversión a la Media en Bandas de Bollinger)
    4. macd_momentum (Cruces de MACD en dirección de Momentum)
    """

    @staticmethod
    def evaluate_entry(
        genome: StrategyGenome,
        candle_idx: int,
        candles: List[Dict[str, Any]],
        closes: List[float],
    ) -> bool:
        arch = genome.archetype
        params = genome.parameters

        if arch == "donchian_breakout":
            entry_p = params.get("donchian_entry", 20)
            if candle_idx < entry_p:
                return False
            window = candles[candle_idx - entry_p : candle_idx]
            entry_high = max(c["high"] for c in window)
            return closes[candle_idx] > entry_high

        elif arch == "trend_pullback_rsi":
            ema_period = params.get("ema_trend", 50)
            rsi_period = params.get("rsi_period", 14)
            rsi_oversold = params.get("rsi_oversold", 30)

            if candle_idx < max(ema_period, rsi_period) + 2:
                return False

            ema_vals = TechnicalIndicators.ema(closes[: candle_idx + 1], ema_period)
            rsi_vals = TechnicalIndicators.rsi(closes[: candle_idx + 1], rsi_period)

            current_close = closes[candle_idx]
            current_ema = ema_vals[-1]
            current_rsi = rsi_vals[-1]
            prev_rsi = rsi_vals[-2]

            # Tendencia alcista (precio > EMA) + Salida de sobreventa RSI cruzando hacia arriba
            return (current_close > current_ema) and (prev_rsi <= rsi_oversold) and (current_rsi > rsi_oversold)

        elif arch == "bollinger_mean_reversion":
            bb_period = params.get("bb_period", 20)
            bb_mult = params.get("bb_mult", 2.0)

            if candle_idx < bb_period + 1:
                return False

            _, _, lower = TechnicalIndicators.bollinger_bands(closes[: candle_idx + 1], bb_period, bb_mult)
            # Rebote: el mínimo perforó la banda inferior pero el cierre recuperó
            return candles[candle_idx]["low"] <= lower[-1] and closes[candle_idx] > lower[-1] and closes[candle_idx] > candles[candle_idx]["open"]

        elif arch == "macd_momentum":
            fast = params.get("macd_fast", 12)
            slow = params.get("macd_slow", 26)
            signal = params.get("macd_signal", 9)

            if candle_idx < slow + signal + 2:
                return False

            macd_line, sig_line, _ = TechnicalIndicators.macd(closes[: candle_idx + 1], fast, slow, signal)
            if math.isnan(macd_line[-1]) or math.isnan(sig_line[-1]) or math.isnan(macd_line[-2]) or math.isnan(sig_line[-2]):
                return False

            # Cruce alcista de MACD sobre la línea de señal
            return macd_line[-2] <= sig_line[-2] and macd_line[-1] > sig_line[-1]

        return False

    @staticmethod
    def evaluate_exit(
        genome: StrategyGenome,
        candle_idx: int,
        candles: List[Dict[str, Any]],
        closes: List[float],
        entry_price: float,
    ) -> bool:
        arch = genome.archetype
        params = genome.parameters
        current_close = closes[candle_idx]

        # Stop Loss fijo o dinámico universal
        sl_pct = genome.stop_loss_pct
        if current_close <= entry_price * (1.0 - sl_pct):
            return True

        if arch == "donchian_breakout":
            exit_p = params.get("donchian_exit", 10)
            if candle_idx < exit_p:
                return False
            window = candles[candle_idx - exit_p : candle_idx]
            exit_low = min(c["low"] for c in window)
            return current_close < exit_low

        elif arch == "trend_pullback_rsi":
            rsi_period = params.get("rsi_period", 14)
            rsi_overbought = params.get("rsi_overbought", 70)
            if candle_idx < rsi_period:
                return False
            rsi_vals = TechnicalIndicators.rsi(closes[: candle_idx + 1], rsi_period)
            return rsi_vals[-1] >= rsi_overbought

        elif arch == "bollinger_mean_reversion":
            bb_period = params.get("bb_period", 20)
            if candle_idx < bb_period:
                return False
            sma_mid, _, _ = TechnicalIndicators.bollinger_bands(closes[: candle_idx + 1], bb_period)
            # Salida en la media central de Bollinger (Take Profit natural)
            return current_close >= sma_mid[-1]

        elif arch == "macd_momentum":
            fast = params.get("macd_fast", 12)
            slow = params.get("macd_slow", 26)
            signal = params.get("macd_signal", 9)
            if candle_idx < slow + signal:
                return False
            macd_line, sig_line, _ = TechnicalIndicators.macd(closes[: candle_idx + 1], fast, slow, signal)
            # Cruce bajista
            return macd_line[-1] < sig_line[-1]

        return False
