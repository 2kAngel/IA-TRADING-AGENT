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
