from typing import Optional


class NamingConvention:
    """
    Genera identificadores estructurados, legibles y taxonómicos para los bots:
    Formato: FAMILIA-LINEA_G[Generacion]_M[NumeroMutacion]_[HashCorto]
    Ejemplos:
      - DONCHIAN-A_G0_M0_ROOT (Semilla Génesis)
      - DONCHIAN-A_G1_M1_4F9B (Hijo de generación 1, mutación 1)
      - MACD-B_G2_M3_A81C     (Nieto de generación 2, mutación 3 acumulada)
    """

    ARCHETYPE_PREFIXES = {
        "donchian_breakout": "DONCHIAN",
        "macd_momentum": "MACD",
        "trend_pullback_rsi": "RSI",
        "bollinger_mean_reversion": "BOLL",
    }

    @staticmethod
    def get_family_code(archetype: str) -> str:
        return NamingConvention.ARCHETYPE_PREFIXES.get(archetype, "HYBRID")

    @staticmethod
    def generate_name(
        archetype: str,
        generation: int,
        mutation_index: int,
        parent_id: Optional[str] = None,
        lineage_letter: str = "A",
        unique_suffix: Optional[str] = None,
    ) -> str:
        fam = NamingConvention.get_family_code(archetype)

        if generation == 0:
            suffix = unique_suffix or "ROOT"
            return f"{fam}-{lineage_letter}_G0_M0_{suffix}"

        # Heredar o extraer prefijo de linaje del progenitor si existe
        if parent_id and "_" in parent_id:
            parent_base = parent_id.split("_")[0]
            # Si el hijo mutó de familia técnica (especiación), se actualiza la familia
            if "-" in parent_base:
                _, lin = parent_base.split("-", 1)
                lineage_letter = lin

        suffix = unique_suffix or "N"
        return f"{fam}-{lineage_letter}_G{generation}_M{mutation_index}_{suffix}"
