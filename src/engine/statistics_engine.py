import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional


class StatisticsEngine:
    """
    Calcula métricas estadísticas cuantitativas institucionales para bots individuales
    y para el ecosistema global (Win Rate, Profit Factor, Drawdown, Sharpe Ratio, Sortino).
    """

    def __init__(self, db_path: str = "data/evolution.db"):
        self.db_path = db_path

    def get_ecosystem_overview(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Conteo de bots
        cur.execute("SELECT status, COUNT(*) FROM bots GROUP BY status")
        status_counts = dict(cur.fetchall())
        active_count = status_counts.get("ACTIVE", 0)
        dead_count = status_counts.get("DEAD", 0)
        total_bots = active_count + dead_count

        # Total generaciones
        cur.execute("SELECT MAX(generation) FROM bots")
        max_gen_row = cur.fetchone()
        max_gen = max_gen_row[0] if max_gen_row and max_gen_row[0] is not None else 0

        # Total reproducciones
        cur.execute("SELECT COUNT(*) FROM reproductions")
        total_reps = cur.fetchone()[0]

        # Capital total actual de los bots vivos
        cur.execute("""
            SELECT SUM(balance_after) 
            FROM ledger_entries le
            JOIN (
                SELECT bot_id, MAX(entry_id) as last_entry 
                FROM ledger_entries 
                GROUP BY bot_id
            ) latest ON le.entry_id = latest.last_entry
            JOIN bots b ON b.bot_id = le.bot_id
            WHERE b.status = 'ACTIVE'
        """)
        capital_row = cur.fetchone()
        current_capital = round(capital_row[0] or 0.0, 2)

        # Capital inicial inyectado por bot genesis (Gen 0)
        cur.execute("SELECT COUNT(*) FROM bots WHERE generation = 0")
        genesis_count = cur.fetchone()[0]
        initial_invested = genesis_count * 20.0

        net_profit = round(current_capital - initial_invested, 2)
        roi_pct = round((net_profit / initial_invested * 100.0), 2) if initial_invested > 0 else 0.0

        conn.close()
        return {
            "total_bots": total_bots,
            "active_bots": active_count,
            "dead_bots": dead_count,
            "max_generation": max_gen,
            "total_reproductions": total_reps,
            "current_capital": current_capital,
            "initial_invested": initial_invested,
            "net_profit": net_profit,
            "roi_pct": roi_pct,
        }

    def get_bot_leaderboard(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT 
                b.bot_id,
                b.parent_id,
                b.generation,
                b.status,
                b.reproduction_count,
                b.created_at,
                b.genome_json,
                COALESCE(latest_bal.balance_after, 20.0) as current_balance,
                COUNT(t.trade_id) as total_trades,
                SUM(CASE WHEN t.net_pnl > 0 THEN 1 ELSE 0 END) as win_trades,
                COALESCE(SUM(t.net_pnl), 0.0) as realized_pnl,
                COALESCE(SUM(CASE WHEN t.net_pnl > 0 THEN t.net_pnl ELSE 0 END), 0.0) as gross_profit,
                COALESCE(ABS(SUM(CASE WHEN t.net_pnl < 0 THEN t.net_pnl ELSE 0 END)), 0.0) as gross_loss
            FROM bots b
            LEFT JOIN (
                SELECT le.bot_id, le.balance_after
                FROM ledger_entries le
                INNER JOIN (
                    SELECT bot_id, MAX(entry_id) as max_id 
                    FROM ledger_entries 
                    GROUP BY bot_id
                ) m ON le.entry_id = m.max_id
            ) latest_bal ON b.bot_id = latest_bal.bot_id
            LEFT JOIN trades t ON b.bot_id = t.bot_id AND t.status = 'CLOSED'
            GROUP BY b.bot_id
            ORDER BY current_balance DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        records = []
        for _, row in df.iterrows():
            total_t = int(row["total_trades"])
            wins = int(row["win_trades"])
            win_rate = round((wins / total_t * 100.0), 1) if total_t > 0 else 0.0
            gross_prof = float(row["gross_profit"])
            gross_loss = float(row["gross_loss"])
            profit_factor = round(gross_prof / gross_loss, 2) if gross_loss > 0 else (round(gross_prof, 2) if gross_prof > 0 else 0.0)

            records.append({
                "bot_id": row["bot_id"],
                "parent_id": row["parent_id"] or "RAÍZ (Génesis)",
                "generation": int(row["generation"]),
                "status": row["status"],
                "capital": round(float(row["current_balance"]), 2),
                "reproductions": int(row["reproduction_count"]),
                "trades": total_t,
                "win_rate": win_rate,
                "realized_pnl": round(float(row["realized_pnl"]), 2),
                "profit_factor": profit_factor,
                "genome_json": row["genome_json"],
            })
        return records

    def get_genealogy_tree_data(self) -> Dict[str, Any]:
        """Extrae nodos y aristas para graficar el árbol evolutivo completo."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT bot_id, parent_id, generation, status FROM bots")
        rows = cur.fetchall()
        conn.close()

        nodes = []
        edges = []
        for bot_id, parent_id, gen, status in rows:
            nodes.append({
                "id": bot_id,
                "label": f"{bot_id[:8]}.. (G{gen})",
                "generation": gen,
                "status": status,
            })
            if parent_id:
                edges.append({"from": parent_id, "to": bot_id})

        return {"nodes": nodes, "edges": edges}
