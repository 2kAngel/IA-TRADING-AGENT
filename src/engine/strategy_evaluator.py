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

        if arch == "inverted_range_breakout":
            # Estrategia INVERTIDA (Breakout de Rango + Volumen POC)
            periodo = params.get("periodo_rango", 15)
            pct_zona = params.get("pct_zona", 0.15)
            vol_mult = params.get("vol_mult", 1.1)

            if candle_idx < periodo + 1:
                return False

            window = candles[candle_idx - periodo : candle_idx + 1]
            resistencia = max(c["high"] for c in window)
            soporte = min(c["low"] for c in window)
            alto_canal = resistencia - soporte
            if alto_canal <= 0:
                return False

            # POC (Point of Control ponderado por volumen)
            vol_total = sum(c.get("volume", 0) for c in window)
            if vol_total > 0:
                poc = sum(((c["high"] + c["low"]) / 2.0) * c.get("volume", 0) for c in window) / vol_total
            else:
                poc = sum((c["high"] + c["low"]) / 2.0 for c in window) / len(window)

            zona_venta_suelo = resistencia - (alto_canal * pct_zona)
            vol_medio = vol_total / len(window)
            c = candles[candle_idx]
            volumen_valido = c.get("volume", 0) >= (vol_medio * vol_mult)

            # Ruptura alcista con fuerza y volumen sobre el POC
            return (c["close"] >= zona_venta_suelo) and (c["close"] > c["open"]) and (c["close"] > poc) and volumen_valido

        elif arch == "donchian_breakout":
            entry_p = params.get("donchian_entry", 20)
            if candle_idx < entry_p:
                return False
            window = candles[candle_idx - entry_p : candle_idx]
            entry_high = max(c["high"] for c in window)
            return closes[candle_idx] > entry_high

        elif arch == "trend_pullback_rsi":
            rsi_period = params.get("rsi_period", 14)
            rsi_oversold = params.get("rsi_oversold", 35)

            if candle_idx < rsi_period + 2:
                return False

            rsi_vals = TechnicalIndicators.rsi(closes[: candle_idx + 1], rsi_period)
            current_rsi = rsi_vals[-1]
            prev_rsi = rsi_vals[-2]

            # Salida o rebote desde sobreventa RSI cruzando hacia arriba
            return (prev_rsi <= rsi_oversold) and (current_rsi > rsi_oversold)

        elif arch == "bollinger_mean_reversion":
            bb_period = params.get("bb_period", 20)
            bb_mult = params.get("bb_mult", 2.0)

            if candle_idx < bb_period + 1:
                return False

            _, _, lower_val = TechnicalIndicators.bollinger_bands_point(closes[: candle_idx + 1], bb_period, bb_mult)
            # Rebote: el mínimo perforó la banda inferior pero el cierre recuperó
            return candles[candle_idx]["low"] <= lower_val and closes[candle_idx] > lower_val and closes[candle_idx] > candles[candle_idx]["open"]

        elif arch == "scherman_volatility_divergence":
            # Ivan Scherman (Campeón Mundial 2023 - +491.4%): Agotamiento institucional con bandas y volumen
            bb_period = params.get("bb_period", 20)
            bb_mult = params.get("bb_mult", 2.0)
            if candle_idx < bb_period + 12:
                return False
            _, _, lower_val = TechnicalIndicators.bollinger_bands_point(closes[: candle_idx + 1], bb_period, bb_mult)
            c = candles[candle_idx]
            prev_window = candles[candle_idx - 10 : candle_idx]
            prev_min_low = min(x["low"] for x in prev_window)
            # Divergencia: nuevo mínimo en precio pero rechaza fuera de bandas con absorción institucional
            return c["low"] <= prev_min_low and c["close"] > lower_val and c["volume"] < candles[candle_idx - 1]["volume"] and c["close"] > c["open"]

        elif arch == "seibert_zeno_price_action":
            # Stefan Seibert (Campeón Mundial 2022 y 2020 - +342.3%): Sistema Zeno de Ruptura de Rango y Expansión ATR
            period = params.get("period", 20)
            if candle_idx < period + 5:
                return False
            sma_mid, _, _ = TechnicalIndicators.bollinger_bands_point(closes[: candle_idx + 1], period, 2.0)
            c = candles[candle_idx]
            prev_atr = sum(candles[i]["high"] - candles[i]["low"] for i in range(candle_idx - 10, candle_idx)) / 10.0
            c_range = c["high"] - c["low"]
            # Tendencia por encima de la media + vela expansiva superando el máximo anterior
            return c["close"] > sma_mid and c["close"] > c["open"] and c_range > prev_atr and c["close"] > candles[candle_idx - 1]["high"]

        elif arch == "mccormick_td_exhaustion":
            # Kevin McCormick (Campeón Mundial 2021 - +253.8%): Setup DeMARK TD Sequential 9 Reversal
            if candle_idx < 13:
                return False
            # Conteo de 9 cierres consecutivos inferiores a close[4]
            is_td9 = True
            for k in range(9):
                curr_i = candle_idx - k
                if not (closes[curr_i] < closes[curr_i - 4]):
                    is_td9 = False
                    break
            # Señal de compra tras completar el conteo 9 cuando la vela actual rebota
            return is_td9 and closes[candle_idx] > candles[candle_idx]["open"]

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

        elif arch == "unger_session_breakout":
            # Andrea Unger (Campeón 2008-2010, 2012): Ruptura de rango previo con filtro de volatilidad
            lookback = params.get("lookback", 12)
            if candle_idx < lookback + 1:
                return False
            window = candles[candle_idx - lookback : candle_idx]
            ref_high = max(c["high"] for c in window)
            current_close = closes[candle_idx]
            # Filtro de expansión: el rango del cuerpo actual debe ser positivo y superar el techo
            return current_close > ref_high and current_close > candles[candle_idx]["open"]

        elif arch == "williams_r_momentum":
            # Larry Williams (1987) / Michelle Williams (1997): Rebote desde zona extrema Williams %R (< -80 saliendo arriba)
            wr_period = params.get("wr_period", 14)
            wr_oversold = params.get("wr_oversold", -80.0)
            if candle_idx < wr_period + 2:
                return False
            highs = [c["high"] for c in candles[: candle_idx + 1]]
            lows = [c["low"] for c in candles[: candle_idx + 1]]
            wr_vals = TechnicalIndicators.williams_r(highs, lows, closes[: candle_idx + 1], wr_period)
            if math.isnan(wr_vals[-1]) or math.isnan(wr_vals[-2]):
                return False
            return wr_vals[-2] <= wr_oversold and wr_vals[-1] > wr_oversold

        elif arch == "hughes_keltner_trend":
            # Chuck Hughes (Campeón multi-año, ej. 2015, 1999): Reversión en Keltner Channel a favor de tendencia
            k_period = params.get("k_period", 20)
            k_mult = params.get("k_mult", 1.5)
            if candle_idx < k_period + 2:
                return False
            mid_k, _, lower_k = TechnicalIndicators.keltner_channels_point(
                candles[: candle_idx + 1], closes[: candle_idx + 1], ema_period=k_period, mult=k_mult
            )
            current_c = closes[candle_idx]
            current_low = candles[candle_idx]["low"]
            # Rebote en banda inferior de Keltner dentro de tendencia
            return current_low <= lower_k and current_c > lower_k and current_c > candles[candle_idx]["open"]

        elif arch == "hoffman_irb_bounce":
            # Rob Hoffman (Campeón Internacional): Inventory Retracement Bar
            # Vela de rechazo bajista: mecha pronunciada en pullback y cierre recuperando en tercio superior
            ema_p = params.get("ema_trend", 20)
            if candle_idx < ema_p + 2:
                return False
            c_candle = candles[candle_idx]
            c_open = c_candle["open"]
            c_close = c_candle["close"]
            c_high = c_candle["high"]
            c_low = c_candle["low"]
            c_range = c_high - c_low
            if c_range <= 0:
                return False
            # Mecha inferior de al menos 40% del rango total (rechazo de venta institucional)
            lower_wick = min(c_open, c_close) - c_low
            wick_ratio = lower_wick / c_range
            return wick_ratio >= 0.40 and c_close > c_open

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

        if arch == "inverted_range_breakout":
            periodo = params.get("periodo_rango", 15)
            if candle_idx < periodo + 1:
                return False
            window = candles[candle_idx - periodo : candle_idx + 1]
            resistencia = max(c["high"] for c in window)
            soporte = min(c["low"] for c in window)
            alto_canal = resistencia - soporte
            tp_price = entry_price + (alto_canal * 1.5)
            return current_close >= tp_price or current_close < soporte

        elif arch == "donchian_breakout":
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
            sma_mid, _, _ = TechnicalIndicators.bollinger_bands_point(closes[: candle_idx + 1], bb_period)
            # Salida en la media central de Bollinger (Take Profit natural)
            return current_close >= sma_mid

        elif arch == "scherman_volatility_divergence":
            # Salida Ivan Scherman: cruce por encima de la media de 20 periodos (cierre de divergencia)
            bb_period = params.get("bb_period", 20)
            if candle_idx < bb_period:
                return False
            sma_mid, _, _ = TechnicalIndicators.bollinger_bands_point(closes[: candle_idx + 1], bb_period)
            return current_close >= sma_mid

        elif arch == "seibert_zeno_price_action":
            # Salida Stefan Seibert: cierre por debajo de la media móvil rápida o trailing 1.8x
            period = params.get("period", 20)
            if candle_idx < period:
                return False
            sma_mid, _, _ = TechnicalIndicators.bollinger_bands_point(closes[: candle_idx + 1], period)
            return current_close < sma_mid or current_close >= entry_price * 1.035

        elif arch == "mccormick_td_exhaustion":
            # Salida Kevin McCormick: Take profit a 4 velas o 2.5% de rebote
            return current_close >= entry_price * 1.025 or current_close <= entry_price * (1.0 - sl_pct)

        elif arch == "macd_momentum":
            fast = params.get("macd_fast", 12)
            slow = params.get("macd_slow", 26)
            signal = params.get("macd_signal", 9)
            if candle_idx < slow + signal:
                return False
            macd_line, sig_line, _ = TechnicalIndicators.macd(closes[: candle_idx + 1], fast, slow, signal)
            # Cruce bajista
            return macd_line[-1] < sig_line[-1]

        elif arch == "unger_session_breakout":
            # Salida de Andrea Unger: cierre por debajo del mínimo de la ventana o tras N velas
            exit_p = params.get("exit_lookback", 6)
            if candle_idx < exit_p:
                return False
            ref_low = min(c["low"] for c in candles[candle_idx - exit_p : candle_idx])
            return current_close < ref_low

        elif arch == "williams_r_momentum":
            # Salida Larry Williams: %R entra en sobrecompra (> -20) y cruza hacia abajo
            wr_period = params.get("wr_period", 14)
            if candle_idx < wr_period:
                return False
            highs = [c["high"] for c in candles[: candle_idx + 1]]
            lows = [c["low"] for c in candles[: candle_idx + 1]]
            wr_vals = TechnicalIndicators.williams_r(highs, lows, closes[: candle_idx + 1], wr_period)
            return wr_vals[-1] >= -20.0

        elif arch == "hughes_keltner_trend":
            # Salida Chuck Hughes: precio alcanza o supera la banda superior de Keltner
            k_period = params.get("k_period", 20)
            k_mult = params.get("k_mult", 1.5)
            if candle_idx < k_period:
                return False
            _, upper_k, _ = TechnicalIndicators.keltner_channels_point(
                candles[: candle_idx + 1], closes[: candle_idx + 1], ema_period=k_period, mult=k_mult
            )
            return current_close >= upper_k

        elif arch == "hoffman_irb_bounce":
            # Salida Rob Hoffman: objetivo 1.8x de riesgo o cierre bajo mínimo previo
            target_tp = entry_price * (1.0 + (sl_pct * 1.8))
            return current_close >= target_tp

        return False
