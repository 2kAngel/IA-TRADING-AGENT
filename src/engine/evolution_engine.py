import copy
import random
import uuid
from typing import Dict, Any, Tuple, List
from src.core.bot import Bot
from src.core.models import StrategyGenome, ReproductionRecord
from src.core.naming import NamingConvention

ARCHETYPE_PARAM_TEMPLATES = {
    "donchian_breakout": {
        "donchian_entry": (10, 50),
        "donchian_exit": (5, 25),
    },
    "trend_pullback_rsi": {
        "ema_trend": (20, 100),
        "rsi_period": (8, 24),
        "rsi_oversold": (20, 38),
        "rsi_overbought": (65, 80),
    },
    "bollinger_mean_reversion": {
        "bb_period": (14, 35),
        "bb_mult": (1.6, 2.6),
    },
    "macd_momentum": {
        "macd_fast": (8, 16),
        "macd_slow": (20, 34),
        "macd_signal": (7, 12),
    },
    "unger_session_breakout": {
        "lookback": (6, 24),
        "exit_lookback": (3, 12),
    },
    "williams_r_momentum": {
        "wr_period": (10, 21),
        "wr_oversold": (-85.0, -75.0),
    },
    "hughes_keltner_trend": {
        "k_period": (14, 30),
        "k_mult": (1.2, 2.2),
    },
    "hoffman_irb_bounce": {
        "ema_trend": (14, 30),
    },
}


class EvolutionEngine:
    """
    Motor evolutivo avanzado:
    - Mutación Tipo A: Parámetros numéricos continuos/discretos.
    - Mutación Tipo B: Ratio Riesgo / Beneficio y Stop Loss.
    - Mutación Tipo C (Especiación): Salto de arqueotipo / recombinación de estrategia.
    """

    def __init__(
        self,
        reproduction_threshold: float = 40.0,
        reproduction_cost: float = 20.0,
        mutation_rate: float = 0.35,
        param_mutation_std: float = 0.15,
        speciation_rate: float = 0.10,  # 10% probabilidad de explorar otro arqueotipo
    ):
        self.reproduction_threshold = reproduction_threshold
        self.reproduction_cost = reproduction_cost
        self.mutation_rate = mutation_rate
        self.param_mutation_std = param_mutation_std
        self.speciation_rate = speciation_rate

    def mutate_genome(self, genome: StrategyGenome) -> Tuple[StrategyGenome, str, str]:
        child_params = copy.deepcopy(genome.parameters)
        current_arch = genome.archetype
        mutation_type = "PARAMETER_ADJUSTMENT"
        changes = []

        # 1. Posible Especiación (Salto a otra familia técnica)
        if random.random() < self.speciation_rate:
            other_arches = [a for a in ARCHETYPE_PARAM_TEMPLATES.keys() if a != current_arch]
            current_arch = random.choice(other_arches)
            mutation_type = "SPECIATION_ARCHETYPE_JUMP"
            # Cargar parámetros predeterminados con ligera variación
            child_params = {}
            for param_name, (min_v, max_v) in ARCHETYPE_PARAM_TEMPLATES[current_arch].items():
                if isinstance(min_v, int):
                    child_params[param_name] = random.randint(min_v, max_v)
                else:
                    child_params[param_name] = round(random.uniform(min_v, max_v), 2)
            changes.append(f"Nueva Familia Arquetípica: {current_arch}")

        else:
            # 2. Mutación fina de parámetros existentes
            for key, value in child_params.items():
                if isinstance(value, (int, float)) and random.random() < self.mutation_rate:
                    delta_factor = random.gauss(1.0, self.param_mutation_std)
                    new_val = max(2, int(round(value * delta_factor))) if isinstance(value, int) else round(value * delta_factor, 2)
                    if new_val != value:
                        child_params[key] = new_val
                        changes.append(f"{key}: {value} -> {new_val}")

        # 3. Mutación de Stop Loss y Gestión de Riesgo
        new_sl = genome.stop_loss_pct
        if random.random() < self.mutation_rate:
            delta_sl = random.choice([-0.005, 0.005])
            new_sl = max(0.005, min(0.05, round(new_sl + delta_sl, 4)))
            if new_sl != genome.stop_loss_pct:
                changes.append(f"SL: {genome.stop_loss_pct} -> {new_sl}")

        new_rr = genome.risk_reward_ratio
        if random.random() < self.mutation_rate:
            new_rr = max(1.2, round(new_rr + random.choice([-0.3, 0.3]), 2))
            if new_rr != genome.risk_reward_ratio:
                changes.append(f"RR: {genome.risk_reward_ratio} -> {new_rr}")

        if not changes:
            # Si no hubo mutación al azar, forzar variación mínima
            changes.append("Ajuste menor determinista")

        summary = ", ".join(changes)
        child_genome = StrategyGenome(
            archetype=current_arch,
            parameters=child_params,
            risk_reward_ratio=new_rr,
            stop_loss_pct=new_sl,
            trailing_stop=genome.trailing_stop,
        )
        return child_genome, mutation_type, summary

    def reproduce(self, parent: Bot) -> Tuple[Bot, ReproductionRecord]:
        if not parent.can_reproduce(self.reproduction_threshold):
            raise ValueError(
                f"El bot {parent.bot_id} no cumple las condiciones de reproducción (Efectivo: {parent.portfolio.cash_balance:.2f}€)."
            )

        reproduction_id = str(uuid.uuid4())
        child_id = str(uuid.uuid4())

        parent.portfolio.debit_for_reproduction(
            reproduction_cost=self.reproduction_cost,
            reference_id=reproduction_id,
        )
        parent.reproduction_count += 1
        child_mutation_index = getattr(parent, "mutation_index", 0) + 1
        unique_tag = uuid.uuid4().hex[:4].upper()

        child_genome, mut_type, summary = self.mutate_genome(parent.genome)
        child_id = NamingConvention.generate_name(
            archetype=child_genome.archetype,
            generation=parent.generation + 1,
            mutation_index=child_mutation_index,
            parent_id=parent.bot_id,
            unique_suffix=unique_tag,
        )

        child = Bot(
            bot_id=child_id,
            parent_id=parent.bot_id,
            generation=parent.generation + 1,
            genome=child_genome,
            initial_capital=self.reproduction_cost,
            mutation_index=child_mutation_index,
        )

        record = ReproductionRecord(
            reproduction_id=reproduction_id,
            parent_bot_id=parent.bot_id,
            child_bot_id=child_id,
            capital_transferred=self.reproduction_cost,
            mutation_type=mut_type,
            mutation_summary=summary,
        )

        return child, record
