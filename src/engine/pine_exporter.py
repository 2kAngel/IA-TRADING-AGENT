from typing import Dict, Any
from src.core.models import StrategyGenome


class PineScriptExporter:
    """
    Genera scripts nativos en Pine Script v6 perfectamente válidos para TradingView.
    Permite exportar el genoma exacto del bot ganador para validarlo en el Strategy Tester.
    """

    @staticmethod
    def export_bot_to_pine_v6(bot_id: str, generation: int, genome: StrategyGenome) -> str:
        arch = genome.archetype
        params = genome.parameters
        sl_pct = genome.stop_loss_pct * 100.0

        header = f"""//@version=6
strategy("Bitcoin Evolution - {bot_id} (G{generation})", 
         overlay=true, 
         initial_capital=20, 
         currency=currency.EUR, 
         default_qty_type=strategy.percent_of_equity, 
         default_qty_value=100,
         commission_type=strategy.commission.percent,
         commission_value=0.075)

// ==========================================
// 1. FILTRO DE FECHAS (ERA MODERNA DE BITCOIN)
// ==========================================
anoInicio    = input.int(2024, "Ano de Inicio Backtest", group="Rango Temporal")
mesInicio    = input.int(1, "Mes de Inicio", minval=1, maxval=12, group="Rango Temporal")
diaInicio    = input.int(1, "Dia de Inicio", minval=1, maxval=31, group="Rango Temporal")
dentroFecha  = time >= timestamp(syminfo.timezone, anoInicio, mesInicio, diaInicio, 0, 0)

// ==========================================
// 2. IDENTIDAD GENETICA DEL BOT
// ==========================================
botId        = input.string("{bot_id}", "Bot ID", group="Identidad")
generation   = input.int({generation}, "Generacion", group="Identidad")
slInputPct   = input.float({sl_pct:.2f}, "Stop Loss (%)", minval=0.1, step=0.1, group="Riesgo") / 100.0
"""

        # Lógica específica por arquetipo técnico
        if arch == "donchian_breakout":
            entry_p = params.get("donchian_entry", 20)
            exit_p = params.get("donchian_exit", 10)
            body = f"""
// ==========================================
// 3. INDICADORES: DONCHIAN BREAKOUT
// ==========================================
donchianEntry = input.int({entry_p}, "Periodo Donchian Entrada", group="Parametros")
donchianExit  = input.int({exit_p}, "Periodo Donchian Salida", group="Parametros")

canalAlto = ta.highest(high[1], donchianEntry)
canalBajo = ta.lowest(low[1], donchianExit)

condicionLong = dentroFecha and ta.crossover(close, canalAlto) and (strategy.position_size == 0)
condicionExit = (close < canalBajo)

plot(canalAlto, "Donchian Techo", color=color.blue, linewidth=2)
plot(canalBajo, "Donchian Suelo", color=color.orange, linewidth=1)
"""

        elif arch == "macd_momentum":
            fast = params.get("macd_fast", 12)
            slow = params.get("macd_slow", 26)
            signal = params.get("macd_signal", 9)
            body = f"""
// ==========================================
// 3. INDICADORES: MACD MOMENTUM
// ==========================================
macdFast   = input.int({fast}, "MACD Fast", group="Parametros")
macdSlow   = input.int({slow}, "MACD Slow", group="Parametros")
macdSignal = input.int({signal}, "MACD Signal", group="Parametros")

[macdLine, signalLine, hist] = ta.macd(close, macdFast, macdSlow, macdSignal)

condicionLong = dentroFecha and ta.crossover(macdLine, signalLine) and (strategy.position_size == 0)
condicionExit = ta.crossunder(macdLine, signalLine)

plot(close, "Precio BTC", color=color.gray)
"""

        elif arch == "trend_pullback_rsi":
            ema_p = params.get("ema_trend", 50)
            rsi_p = params.get("rsi_period", 14)
            rsi_os = params.get("rsi_oversold", 30)
            rsi_ob = params.get("rsi_overbought", 70)
            body = f"""
// ==========================================
// 3. INDICADORES: TREND PULLBACK RSI
// ==========================================
emaPeriod   = input.int({ema_p}, "EMA Tendencia", group="Parametros")
rsiPeriod   = input.int({rsi_p}, "RSI Periodo", group="Parametros")
rsiOversold = input.float({rsi_os}, "RSI Sobreventa", group="Parametros")
rsiOverbought = input.float({rsi_ob}, "RSI Sobrecompra", group="Parametros")

emaVal = ta.ema(close, emaPeriod)
rsiVal = ta.rsi(close, rsiPeriod)

condicionLong = dentroFecha and (close > emaVal) and ta.crossover(rsiVal, rsiOversold) and (strategy.position_size == 0)
condicionExit = (rsiVal >= rsiOverbought)

plot(emaVal, "EMA Tendencia", color=color.orange, linewidth=2)
"""

        elif arch == "bollinger_mean_reversion":
            bb_p = params.get("bb_period", 20)
            bb_m = params.get("bb_mult", 2.0)
            body = f"""
// ==========================================
// 3. INDICADORES: BOLLINGER MEAN REVERSION
// ==========================================
bbPeriod = input.int({bb_p}, "Bollinger Periodo", group="Parametros")
bbMult   = input.float({bb_m}, "Bollinger Desviacion", group="Parametros")

[midBB, upperBB, lowerBB] = ta.bb(close, bbPeriod, bbMult)

condicionLong = dentroFecha and (low <= lowerBB) and (close > lowerBB) and (close > open) and (strategy.position_size == 0)
condicionExit = (close >= midBB)

plot(upperBB, "BB Upper", color=color.red)
plot(midBB, "BB Mid", color=color.gray, style=plot.style_dotted)
plot(lowerBB, "BB Lower", color=color.green)
"""

        elif arch == "unger_session_breakout":
            lookback = params.get("lookback", 12)
            exit_p = params.get("exit_lookback", 6)
            body = f"""
// ==========================================
// 3. INDICADORES: ANDREA UNGER SESSION BREAKOUT
// ==========================================
lookbackVal = input.int({lookback}, "Lookback Entrada", group="Parametros")
exitVal     = input.int({exit_p}, "Lookback Salida", group="Parametros")

techoUnger = ta.highest(high[1], lookbackVal)
sueloUnger = ta.lowest(low[1], exitVal)

condicionLong = dentroFecha and (close > techoUnger) and (close > open) and (strategy.position_size == 0)
condicionExit = (close < sueloUnger)

plot(techoUnger, "Techo Unger", color=color.teal, linewidth=2)
plot(sueloUnger, "Suelo Unger", color=color.maroon, linewidth=1)
"""

        elif arch == "williams_r_momentum":
            wr_p = params.get("wr_period", 14)
            wr_os = params.get("wr_oversold", -80.0)
            body = f"""
// ==========================================
// 3. INDICADORES: LARRY WILLIAMS %R MOMENTUM
// ==========================================
wrPeriod   = input.int({wr_p}, "Williams %R Periodo", group="Parametros")
wrOversold = input.float({wr_os}, "Nivel Sobreventa", group="Parametros")

wpr = ta.wpr(wrPeriod)

condicionLong = dentroFecha and ta.crossover(wpr, wrOversold) and (strategy.position_size == 0)
condicionExit = ta.crossunder(wpr, -20.0)

plot(close, "Precio BTC", color=color.gray)
"""

        elif arch == "hughes_keltner_trend":
            k_p = params.get("k_period", 20)
            k_m = params.get("k_mult", 1.5)
            body = f"""
// ==========================================
// 3. INDICADORES: CHUCK HUGHES KELTNER CHANNEL
// ==========================================
kPeriod = input.int({k_p}, "Keltner Periodo", group="Parametros")
kMult   = input.float({k_m}, "Keltner Multiplicador", group="Parametros")

[midK, upperK, lowerK] = ta.kc(close, kPeriod, kMult)

condicionLong = dentroFecha and (low <= lowerK) and (close > lowerK) and (close > open) and (strategy.position_size == 0)
condicionExit = (close >= upperK)

plot(upperK, "Keltner Upper", color=color.purple)
plot(midK, "Keltner Mid", color=color.blue)
plot(lowerK, "Keltner Lower", color=color.fuchsia)
"""

        elif arch == "hoffman_irb_bounce":
            body = f"""
// ==========================================
// 3. INDICADORES: ROB HOFFMAN INVENTORY RETRACEMENT BAR
// ==========================================
cRange     = high - low
lowerWick  = math.min(open, close) - low
wickRatio  = cRange > 0 ? (lowerWick / cRange) : 0.0

condicionLong = dentroFecha and (wickRatio >= 0.40) and (close > open) and (strategy.position_size == 0)
condicionExit = (close >= strategy.position_avg_price * 1.035)

plot(close, "Precio BTC", color=color.yellow)
"""

        execution = f"""
// ==========================================
// 4. EJECUCION DE ORDENES Y ALERTAS WEBHOOK
// ==========================================
var float stopLossLevel = na

msgBuy  = '{{"bot_id": "' + botId + '", "action": "BUY", "symbol": "' + syminfo.ticker + '", "price": ' + str.tostring(close) + ', "equity": ' + str.tostring(strategy.equity) + '}}'
msgSell = '{{"bot_id": "' + botId + '", "action": "CLOSE", "symbol": "' + syminfo.ticker + '", "price": ' + str.tostring(close) + ', "equity": ' + str.tostring(strategy.equity) + '}}'

if condicionLong
    stopLossLevel := close * (1.0 - slInputPct)
    strategy.entry("Long Entry", strategy.long, alert_message=msgBuy)

if strategy.position_size > 0
    if condicionExit or (close <= stopLossLevel)
        strategy.close("Long Entry", comment="Exit Signal / SL", alert_message=msgSell)
else
    stopLossLevel := na

plot(stopLossLevel, "Stop Loss Nivel", color=color.maroon, style=plot.style_linebr, linewidth=2)
"""

        return header + body + execution
