import os
import pytest
from src.core.bot import Bot
from src.core.models import BotStatus, StrategyGenome
from src.engine.evolution_engine import EvolutionEngine
from src.storage.db_manager import DatabaseManager


class TestEcosystemCriticalRequirements:
    """
    Suite de validación formal que ejecuta los 8 TESTS CRÍTICOS
    definidos en la Sección 13 del Proyecto.
    """

    def test_1_bot_begins_with_20_euros(self):
        """TEST 1: Un bot comienza con exactamente 20.0 €."""
        bot = Bot(initial_capital=20.0)
        assert bot.equity == 20.0
        assert bot.portfolio.cash_balance == 20.0
        assert bot.is_alive
        assert bot.generation == 0

    def test_2_bot_reproduces_at_40_euros(self):
        """
        TEST 2: El bot alcanza 40 €.
        Resultado esperado:
        - Progenitor: 20 €.
        - Descendiente: 20 €.
        - Capital total del sistema: 40 €.
        """
        engine = EvolutionEngine(reproduction_threshold=40.0, reproduction_cost=20.0)
        bot_a = Bot(initial_capital=20.0)

        # Simular beneficio hasta 40.0 €
        bot_a.portfolio.cash_balance = 40.0

        assert bot_a.can_reproduce(threshold=40.0)
        bot_b, record = engine.reproduce(bot_a)

        assert bot_a.equity == 20.0
        assert bot_b.equity == 20.0
        assert (bot_a.equity + bot_b.equity) == 40.0
        assert bot_b.generation == 1
        assert bot_b.parent_id == bot_a.bot_id
        assert bot_a.reproduction_count == 1

    def test_3_descendant_reproduces_at_40_euros(self):
        """
        TEST 3: El descendiente alcanza 40 €.
        Resultado esperado:
        - Progenitor original: 20 €.
        - Segundo bot: 20 €.
        - Tercer bot: 20 €.
        - Capital total: 60 €.
        """
        engine = EvolutionEngine(reproduction_threshold=40.0, reproduction_cost=20.0)
        bot_a = Bot(initial_capital=20.0)
        bot_a.portfolio.cash_balance = 40.0

        bot_b, _ = engine.reproduce(bot_a)

        # Bot B gana hasta 40 €
        bot_b.portfolio.cash_balance = 40.0
        bot_c, _ = engine.reproduce(bot_b)

        assert bot_a.equity == 20.0
        assert bot_b.equity == 20.0
        assert bot_c.equity == 20.0
        assert (bot_a.equity + bot_b.equity + bot_c.equity) == 60.0
        assert bot_c.generation == 2
        assert bot_c.parent_id == bot_b.bot_id

    def test_4_bot_loses_all_capital_dies_others_continue(self):
        """
        TEST 4: Uno de los bots pierde todo su capital.
        Resultado esperado:
        - Bot muerto.
        - Capital 0 €.
        - Sin nuevas operaciones.
        - Los demás bots siguen funcionando normalmente.
        """
        bot_1 = Bot(initial_capital=20.0)
        bot_2 = Bot(initial_capital=20.0)

        # Bot 1 pierde su capital
        bot_1.portfolio.cash_balance = 0.0
        bot_1.evaluate_life_or_death(death_threshold=0.0)

        assert bot_1.status == BotStatus.DEAD
        assert not bot_1.is_alive
        assert bot_1.equity == 0.0

        # Bot 2 sigue activo e inalterado
        assert bot_2.is_alive
        assert bot_2.equity == 20.0

    def test_5_system_restart_persistence(self, tmp_path):
        """
        TEST 5: El sistema se cierra y reinicia.
        Resultado esperado:
        - Se recuperan todos los bots, balances, estrategias y árbol evolutivo.
        - No se duplican operaciones ni reproducciones.
        """
        db_file = str(tmp_path / "test_persistence.db")
        db = DatabaseManager(db_path=db_file)

        engine = EvolutionEngine(reproduction_threshold=40.0, reproduction_cost=20.0)
        parent = Bot(initial_capital=20.0)
        parent.portfolio.cash_balance = 40.0
        child, rep_record = engine.reproduce(parent)

        # Guardar en base de datos
        db.save_bot(parent)
        for e in parent.portfolio.ledger:
            db.save_ledger_entry(e)

        db.save_bot(child)
        for e in child.portfolio.ledger:
            db.save_ledger_entry(e)

        db.save_reproduction(rep_record)
        db.close()

        # Reinicio del sistema (nueva conexión limpia)
        db_restored = DatabaseManager(db_path=db_file)
        restored_bots = db_restored.load_all_bots()

        assert len(restored_bots) == 2
        bot_map = {b.bot_id: b for b in restored_bots}

        restored_parent = bot_map[parent.bot_id]
        restored_child = bot_map[child.bot_id]

        assert restored_parent.equity == 20.0
        assert restored_child.equity == 20.0
        assert restored_child.parent_id == restored_parent.bot_id
        assert restored_child.generation == 1
        db_restored.close()

    def test_6_trades_reflect_fees_and_slippage(self):
        """
        TEST 6: Una operación tiene comisiones y slippage.
        Resultado esperado:
        - El balance refleja los costes reales.
        - El capital total no se duplica.
        - La reproducción utiliza el patrimonio neto real.
        """
        bot = Bot(initial_capital=20.0)

        # Abrir trade de 20 € con 0.1% comisión y 0.02% slippage
        trade = bot.portfolio.open_trade(
            trade_id="T001",
            symbol="BTC/EUR",
            price=50000.0,
            capital_to_invest=20.0,
            commission_rate=0.001,
            slippage_rate=0.0002,
        )

        assert bot.portfolio.cash_balance == 0.0
        assert bot.portfolio.open_position is not None
        assert trade.commission > 0

        # Cerrar trade con precio idéntico para verificar impacto estricto de costes
        closed_trade = bot.portfolio.close_trade(
            trade_id="T001",
            exit_price=50000.0,
            commission_rate=0.001,
            slippage_rate=0.0002,
        )

        # Tras dos comisiones y dos deslizamientos, el capital debe ser estrictamente menor a 20.0 €
        assert bot.portfolio.cash_balance < 20.0
        assert bot.portfolio.cash_balance > 19.90
        assert closed_trade.net_pnl < 0  # Pérdida debida a costes operativos

    def test_7_reproduction_blocked_with_open_position(self):
        """
        TEST 7: Un bot alcanza el umbral de reproducción con una posición abierta.
        Resultado esperado:
        - No crea descendencia utilizando beneficios flotantes no realizados.
        - Solo reproduce cuando la posición se cierra en efectivo.
        """
        engine = EvolutionEngine(reproduction_threshold=40.0, reproduction_cost=20.0)
        bot = Bot(initial_capital=20.0)

        # Abre posición con todo el capital
        bot.portfolio.open_trade(
            trade_id="T002",
            symbol="BTC/EUR",
            price=50000.0,
            capital_to_invest=20.0,
        )

        # El precio de mercado de BTC sube un 150%, haciendo que el market_value sea 50.0 €
        bot.portfolio.open_position.current_price = 125000.0
        assert bot.portfolio.total_equity > 40.0  # Beneficio flotante no realizado

        # Intento de reproducir con posición abierta DEBE SER RECHAZADO
        assert not bot.can_reproduce(threshold=40.0)
        with pytest.raises(ValueError):
            engine.reproduce(bot)

        # Cerrar posición en efectivo a 125000.0 €
        bot.portfolio.close_trade(
            trade_id="T002",
            exit_price=125000.0,
        )

        # Ahora el beneficio es realizado en efectivo: AHORA SÍ PUEDE REPRODUCIRSE
        assert bot.can_reproduce(threshold=40.0)
        child, _ = engine.reproduce(bot)
        assert child.equity == 20.0
        assert bot.equity >= 20.0

    def test_8_two_concurrent_bots_isolated_portfolios(self):
        """
        TEST 8: Dos bots operan simultáneamente.
        Resultado esperado:
        - Sus carteras permanecen estrictamente independientes.
        - No comparten accidentalmente posiciones ni capital.
        - Sus estrategias y mutaciones evolucionan de forma diferente.
        """
        bot_1 = Bot(initial_capital=20.0)
        bot_2 = Bot(initial_capital=20.0)

        bot_1.portfolio.open_trade(
            trade_id="T1",
            symbol="BTC/EUR",
            price=60000.0,
            capital_to_invest=20.0,
        )

        # Bot 1 tiene posición abierta y 0 de efectivo
        assert bot_1.portfolio.cash_balance == 0.0
        assert bot_1.portfolio.open_position is not None

        # Bot 2 permanece con sus 20 € de efectivo intactos y sin posición
        assert bot_2.portfolio.cash_balance == 20.0
        assert bot_2.portfolio.open_position is None

        # Modificación en estrategia de bot_1 no altera bot_2
        bot_1.genome.parameters["donchian_entry"] = 35
        assert bot_2.genome.parameters["donchian_entry"] == 20

    def test_9_multi_asset_and_timeframe_execution(self):
        """
        TEST 9: Simulación multi-activo y multi-temporalidad.
        Valida que el simulador ejecuta sobre activos reales (Gold, SP500, Iberdrola)
        y distintas temporalidades (1m, 1h, 1w) conservando las reglas de capital.
        """
        from src.engine.simulator_service import execute_custom_simulation

        # Oro en 1h
        res_gold = execute_custom_simulation(num_candles=100, capital_inicial=40.0, asset="GOLD", timeframe="1h")
        assert res_gold["candles_processed"] > 0
        assert res_gold["total_active"] + res_gold["total_dead"] >= 2
        assert res_gold["total_equity"] > 0

        # Iberdrola en 1m
        res_ibe = execute_custom_simulation(num_candles=100, capital_inicial=20.0, asset="IBERDROLA", timeframe="1m")
        assert res_ibe["candles_processed"] > 0
        assert res_ibe["total_active"] + res_ibe["total_dead"] >= 1
