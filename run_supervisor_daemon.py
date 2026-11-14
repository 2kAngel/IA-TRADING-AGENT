import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine.continuous_supervisor import ContinuousSupervisor


def main():
    """
    Punto de entrada para el servicio supervisor desatendido.
    Por defecto revisa el mercado cada 60 segundos (configurable).
    """
    supervisor = ContinuousSupervisor(
        db_path="data/evolution.db",
        poll_interval_seconds=60,
        symbol="BTCEUR",
        candle_interval="1h",
    )
    supervisor.start_loop()


if __name__ == "__main__":
    main()
