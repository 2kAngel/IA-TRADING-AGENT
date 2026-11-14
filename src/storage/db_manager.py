import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from src.core.models import BotStatus, StrategyGenome, LedgerEntry, TradeRecord, ReproductionRecord
from src.core.bot import Bot


class DatabaseManager:
    """
    Gestor de base de datos SQLite con soporte para persistencia ACID y WAL.
    Permite reconstruir el estado completo del ecosistema tras cualquier reinicio.
    """

    def __init__(self, db_path: str = "data/evolution.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self._init_schema()

    def clear_all_data(self):
        """Limpia todas las tablas de forma transaccional sin necesidad de borrar el archivo de disco."""
        with self.conn:
            self.conn.execute("DELETE FROM reproductions;")
            self.conn.execute("DELETE FROM trades;")
            self.conn.execute("DELETE FROM ledger_entries;")
            self.conn.execute("DELETE FROM bots;")

    def _init_schema(self):
        with self.conn:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS bots (
                bot_id TEXT PRIMARY KEY,
                parent_id TEXT,
                generation INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                death_at TEXT,
                genome_json TEXT NOT NULL,
                reproduction_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(parent_id) REFERENCES bots(bot_id)
            );

            CREATE TABLE IF NOT EXISTS ledger_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL NOT NULL,
                reference_id TEXT,
                FOREIGN KEY(bot_id) REFERENCES bots(bot_id)
            );

            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                bot_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                commission REAL NOT NULL,
                slippage REAL NOT NULL,
                net_pnl REAL,
                status TEXT NOT NULL,
                FOREIGN KEY(bot_id) REFERENCES bots(bot_id)
            );

            CREATE TABLE IF NOT EXISTS reproductions (
                reproduction_id TEXT PRIMARY KEY,
                parent_bot_id TEXT NOT NULL,
                child_bot_id TEXT NOT NULL,
                capital_transferred REAL NOT NULL,
                timestamp TEXT NOT NULL,
                mutation_type TEXT NOT NULL,
                mutation_summary TEXT NOT NULL,
                FOREIGN KEY(parent_bot_id) REFERENCES bots(bot_id),
                FOREIGN KEY(child_bot_id) REFERENCES bots(bot_id)
            );
            """)

    def save_bot(self, bot: Bot):
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO bots (
                    bot_id, parent_id, generation, status, created_at, death_at, genome_json, reproduction_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bot.bot_id,
                    bot.parent_id,
                    bot.generation,
                    bot.status.value,
                    bot.created_at,
                    bot.death_at,
                    json.dumps(bot.genome.to_dict()),
                    bot.reproduction_count,
                ),
            )

    def save_ledger_entry(self, entry: LedgerEntry):
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO ledger_entries (
                    bot_id, timestamp, entry_type, amount, balance_after, reference_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.bot_id,
                    entry.timestamp,
                    entry.entry_type.value,
                    entry.amount,
                    entry.balance_after,
                    entry.reference_id,
                ),
            )

    def save_trade(self, trade: TradeRecord):
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO trades (
                    trade_id, bot_id, symbol, side, entry_price, exit_price,
                    quantity, entry_time, exit_time, commission, slippage, net_pnl, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.trade_id,
                    trade.bot_id,
                    trade.symbol,
                    trade.side.value,
                    trade.entry_price,
                    trade.exit_price,
                    trade.quantity,
                    trade.entry_time,
                    trade.exit_time,
                    trade.commission,
                    trade.slippage,
                    trade.net_pnl,
                    trade.status.value,
                ),
            )

    def save_reproduction(self, rep: ReproductionRecord):
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO reproductions (
                    reproduction_id, parent_bot_id, child_bot_id, capital_transferred,
                    timestamp, mutation_type, mutation_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rep.reproduction_id,
                    rep.parent_bot_id,
                    rep.child_bot_id,
                    rep.capital_transferred,
                    rep.timestamp,
                    rep.mutation_type,
                    rep.mutation_summary,
                ),
            )

    def load_all_bots(self) -> List[Bot]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT bot_id, parent_id, generation, status, created_at, death_at, genome_json, reproduction_count FROM bots")
        rows = cursor.fetchall()

        bots = []
        for row in rows:
            bot_id, parent_id, generation, status_str, created_at, death_at, genome_json, rep_count = row
            genome_dict = json.loads(genome_json)
            genome = StrategyGenome.from_dict(genome_dict)

            # Reconstruir saldo del ledger
            cur_l = self.conn.cursor()
            cur_l.execute(
                "SELECT balance_after FROM ledger_entries WHERE bot_id = ? ORDER BY entry_id DESC LIMIT 1",
                (bot_id,),
            )
            bal_row = cur_l.fetchone()
            current_balance = bal_row[0] if bal_row else 20.0

            bot = Bot(
                bot_id=bot_id,
                parent_id=parent_id,
                generation=generation,
                genome=genome,
                initial_capital=current_balance,
                status=BotStatus(status_str),
                created_at=created_at,
            )
            bot.death_at = death_at
            bot.reproduction_count = rep_count
            bots.append(bot)

        return bots

    def close(self):
        self.conn.close()
