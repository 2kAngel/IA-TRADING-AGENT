import math
from typing import List, Dict, Any, Tuple


class TechnicalIndicators:
    """
    Biblioteca técnica optimizada para cálculo vectorizado e incremental
    de indicadores para Bitcoin: EMA, SMA, RSI, MACD, Bollinger Bands, ATR y ADX.
    """

    @staticmethod
    def sma(values: List[float], period: int) -> List[float]:
        if len(values) < period:
            return [float("nan")] * len(values)
        res = [float("nan")] * (period - 1)
        current_sum = sum(values[:period])
        res.append(current_sum / period)
        for i in range(period, len(values)):
            current_sum += values[i] - values[i - period]
            res.append(current_sum / period)
        return res

    @staticmethod
    def ema(values: List[float], period: int) -> List[float]:
        if len(values) < period:
            return [float("nan")] * len(values)
        multiplier = 2.0 / (period + 1)
        res = [float("nan")] * (period - 1)
        # Primer valor es el SMA inicial
        sma_init = sum(values[:period]) / period
        res.append(sma_init)
        prev_ema = sma_init
        for i in range(period, len(values)):
            new_ema = (values[i] - prev_ema) * multiplier + prev_ema
            res.append(new_ema)
            prev_ema = new_ema
        return res

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> List[float]:
        if len(closes) <= period:
            return [float("nan")] * len(closes)
        gains = []
        losses = []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(0.0, change))
            losses.append(max(0.0, -change))

        res = [float("nan")] * period
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            res.append(100.0)
        else:
            rs = avg_gain / avg_loss
            res.append(100.0 - (100.0 / (1.0 + rs)))

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                res.append(100.0)
            else:
                rs = avg_gain / avg_loss
                res.append(100.0 - (100.0 / (1.0 + rs)))
        return res

    @staticmethod
    def bollinger_bands(closes: List[float], period: int = 20, mult: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
        sma_vals = TechnicalIndicators.sma(closes, period)
        upper = []
        lower = []
        for i in range(len(closes)):
            if math.isnan(sma_vals[i]) or i < period - 1:
                upper.append(float("nan"))
                lower.append(float("nan"))
            else:
                window = closes[i - period + 1 : i + 1]
                mean = sma_vals[i]
                variance = sum((x - mean) ** 2 for x in window) / period
                std_dev = math.sqrt(variance)
                upper.append(mean + (mult * std_dev))
                lower.append(mean - (mult * std_dev))
        return sma_vals, upper, lower

    @staticmethod
    def bollinger_bands_point(closes: List[float], period: int = 20, mult: float = 2.0) -> Tuple[float, float, float]:
        """Calcula de forma O(period) únicamente el último punto de Bollinger sin vectorizar el histórico completo."""
        if len(closes) < period:
            return float("nan"), float("nan"), float("nan")
        window = closes[-period:]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std_dev = math.sqrt(variance)
        return mean, mean + (mult * std_dev), mean - (mult * std_dev)

    @staticmethod
    def williams_r(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """Calcula Williams %R (-100 a 0) de Larry Williams."""
        if len(closes) < period:
            return [float("nan")] * len(closes)
        res = [float("nan")] * (period - 1)
        for i in range(period - 1, len(closes)):
            h_max = max(highs[i - period + 1 : i + 1])
            l_min = min(lows[i - period + 1 : i + 1])
            if h_max == l_min:
                res.append(-50.0)
            else:
                wr = ((h_max - closes[i]) / (h_max - l_min)) * -100.0
                res.append(wr)
        return res

    @staticmethod
    def keltner_channels_point(
        candles: List[Dict[str, Any]],
        closes: List[float],
        ema_period: int = 20,
        mult: float = 1.5,
        atr_period: int = 10,
    ) -> Tuple[float, float, float]:
        """Calcula el canal de Keltner (Chuck Hughes) en el punto actual."""
        if len(closes) < max(ema_period, atr_period):
            return float("nan"), float("nan"), float("nan")
        multiplier = 2.0 / (ema_period + 1)
        ema = sum(closes[:ema_period]) / ema_period
        for c in closes[ema_period:]:
            ema = (c - ema) * multiplier + ema

        tr_sum = 0.0
        n_candles = len(candles)
        for i in range(n_candles - atr_period, n_candles):
            h = candles[i]["high"]
            l = candles[i]["low"]
            pc = candles[i - 1]["close"] if i > 0 else (h + l) / 2.0
            tr_sum += max(h - l, abs(h - pc), abs(l - pc))
        atr = tr_sum / atr_period
        return ema, ema + (mult * atr), ema - (mult * atr)

    @staticmethod
    def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
        ema_fast = TechnicalIndicators.ema(closes, fast)
        ema_slow = TechnicalIndicators.ema(closes, slow)
        macd_line = []
        for f, s in zip(ema_fast, ema_slow):
            if math.isnan(f) or math.isnan(s):
                macd_line.append(float("nan"))
            else:
                macd_line.append(f - s)

        # Signal line es EMA del MACD
        valid_macd = [x for x in macd_line if not math.isnan(x)]
        if len(valid_macd) >= signal:
            signal_partial = TechnicalIndicators.ema(valid_macd, signal)
            nan_prefix = [float("nan")] * (len(macd_line) - len(valid_macd))
            signal_line = nan_prefix + signal_partial
        else:
            signal_line = [float("nan")] * len(macd_line)

        hist = []
        for m, sig in zip(macd_line, signal_line):
            if math.isnan(m) or math.isnan(sig):
                hist.append(float("nan"))
            else:
                hist.append(m - sig)
        return macd_line, signal_line, hist

    @staticmethod
    def atr(candles: List[Dict[str, Any]], period: int = 14) -> List[float]:
        if len(candles) < 2:
            return [float("nan")] * len(candles)
        tr_list = [candles[0]["high"] - candles[0]["low"]]
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
        return TechnicalIndicators.sma(tr_list, period)
