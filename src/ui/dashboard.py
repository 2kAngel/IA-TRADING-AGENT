import os
import sys
import json
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Bitcoin Evolution - Trading Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.engine.statistics_engine import StatisticsEngine
from src.engine.pine_exporter import PineScriptExporter
from src.engine.simulator_service import execute_custom_simulation
from src.core.models import StrategyGenome

DB_PATH = os.path.join("data", "evolution.db")
stats_engine = StatisticsEngine(db_path=DB_PATH)

# ==========================================
# BARRA LATERAL: CONTROL DE SIMULACIÓN Y VELAS
# ==========================================
st.sidebar.header("⚙️ Control de Simulación")

capital_input = st.sidebar.number_input(
    "Capital Inicial Total (€)",
    min_value=20,
    max_value=1000,
    value=80,
    step=20,
    help="Cada 20 € se engendra 1 bot semilla Génesis independiente (ej. 20€ = 1 semilla, 80€ = 4 semillas, 100€ = 5 semillas).",
)

semillas_calculadas = max(1, int(capital_input // 20))
st.sidebar.caption(f"🌱 Población Inicial: **{semillas_calculadas} bot(s) semilla** (20 € c/u).")

num_velas_input = st.sidebar.slider(
    "Número de Velas (Horas)",
    min_value=100,
    max_value=3000,
    value=800,
    step=100,
    help="100 velas ≈ 4 días | 720 velas ≈ 1 mes | 2.160 velas ≈ 3 meses",
)

dias_aprox = round(num_velas_input / 24.0, 1)
st.sidebar.caption(f"📅 Equivalente aproximado: **{dias_aprox} días** de mercado (velas 1H).")

if st.sidebar.button("🚀 Ejecutar Nueva Simulación", type="primary", use_container_width=True):
    with st.spinner(f"Simulando {semillas_calculadas} semillas ({capital_input} €) a lo largo de {num_velas_input} velas..."):
        res = execute_custom_simulation(num_candles=num_velas_input, capital_inicial=float(capital_input))
        st.sidebar.success(f"¡Completado! {res['total_active']} bots vivos ({res['total_equity']:.2f} €).")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Con más de 1.000 velas verás nacer nietos (Gen 2) y bisnietos (Gen 3), y los bots de RSI y Bollinger empezarán a operar.")

st.title("🧬 Bitcoin Evolution Trading System")
st.caption("Laboratorio Cuantitativo de Selección Natural, Herencia Genética y Supervivencia para Bitcoin")

if not os.path.exists(DB_PATH):
    st.warning("⚠️ No se ha encontrado la base de datos en `data/evolution.db`.")
    st.stop()

# ==========================================
# 1. PANEL GENERAL
# ==========================================
overview = stats_engine.get_ecosystem_overview()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Capital Ecosistema", f"{overview['current_capital']:.2f} €", delta=f"{overview['net_profit']:.2f} €")
with col2:
    st.metric("Bots Activos", f"{overview['active_bots']}", delta=f"-{overview['dead_bots']} muertos" if overview['dead_bots'] > 0 else "0 muertos")
with col3:
    st.metric("Máxima Generación", f"Gen {overview['max_generation']}")
with col4:
    st.metric("Total Reproducciones", f"{overview['total_reproductions']}")
with col5:
    st.metric("ROI Global Ecosistema", f"{overview['roi_pct']:.2f} %")

st.markdown("---")

# ==========================================
# 2. PESTAÑAS PRINCIPALES
# ==========================================
tab_leaderboard, tab_genealogy, tab_equity, tab_inspector, tab_pine = st.tabs([
    "🏆 Ranking de Bots",
    "🌳 Árbol Evolutivo",
    "📈 Curva de Capital (Ledger)",
    "🔬 Inspector Genético",
    "📊 Exportar a TradingView (Pine v6)",
])

leaderboard_data = stats_engine.get_bot_leaderboard()
df_bots = pd.DataFrame(leaderboard_data)

with tab_leaderboard:
    st.subheader("Clasificación de Bots por Familias y Linajes Genéticos")
    st.caption("🎭 Cada sección representa una **Semilla Génesis** y su descendencia directa en orden cronológico de nacimiento. Puedes scrollear para analizar cada estrategia y sus mutaciones.")

    if not df_bots.empty:
        st.markdown(
            "🔴 **Rojo:** Muertos (quiebra técnica) | "
            "🟢 **Verde:** Vivos con hijos (progenitores exitosos) | "
            "🔵 **Azul:** Vivos sin hijos (jóvenes o en camino)"
        )

        def highlight_bot_status(row):
            status = row["Estado"]
            children = row["Hijos"]
            if status == "DEAD":
                return ["background-color: #4a1515; color: #ff9999; font-weight: bold;"] * len(row)
            elif status == "ACTIVE" and children > 0:
                return ["background-color: #12381f; color: #99ffbb; font-weight: bold;"] * len(row)
            elif status == "ACTIVE" and children == 0:
                return ["background-color: #122538; color: #99ccff;"] * len(row)
            return [""] * len(row)

        bots_by_id = {b["bot_id"]: b for b in leaderboard_data}
        children_map = {}
        for b in leaderboard_data:
            pid = b["parent_id"]
            if pid and pid != "RAÍZ (Génesis)":
                children_map.setdefault(pid, []).append(b["bot_id"])

        roots = [b for b in leaderboard_data if b["generation"] == 0]

        def get_seed_num(b_id):
            if "SEED" in b_id:
                try:
                    return int(b_id.split("SEED")[1].split("_")[0])
                except Exception:
                    return 999
            return 0

        roots.sort(key=lambda x: get_seed_num(x["bot_id"]))

        # Mapeo de nombres descriptivos de campeones por arquetipo o código
        name_map = {
            "DONCHIAN": "Richard Dennis (Turtles 1983 - Breakout Donchian)",
            "MACD": "Gerald Appel (1979 - Momentum Clásico)",
            "RSI": "J. Welles Wilder (1978 - RSI Pullback)",
            "BOLL": "John Bollinger (1983 - Mean Reversion)",
            "UNGER": "Andrea Unger (4x Campeón Mundial - Session Breakout)",
            "HOFFMAN": "Rob Hoffman (2015 - Inventory Retracement Bar)",
            "HUGHES": "Chuck Hughes (10x Campeón Mundial - Keltner Trend)",
            "WILLIAMS": "Larry & Michelle Williams (Récord Histórico 11,376% - Williams %R)",
            "DAVEY": "Kevin Davey (Campeón Mundial 2006 - Algo Volatility)",
            "DENNIS": "Richard Dennis (Turtle System 2)",
        }

        for r in roots:
            family_members = [r]

            def collect_descendants(parent_id):
                desc = []
                for cid in children_map.get(parent_id, []):
                    if cid in bots_by_id:
                        child = bots_by_id[cid]
                        desc.append(child)
                        desc.extend(collect_descendants(cid))
                return desc

            family_members.extend(collect_descendants(r["bot_id"]))

            # Parsear datos de la semilla
            root_code = r["bot_id"].split("-")[0]
            display_title = name_map.get(root_code, root_code)
            total_children = sum(m["reproductions"] for m in family_members)
            alive_count = sum(1 for m in family_members if m["status"] == "ACTIVE")
            dead_count = sum(1 for m in family_members if m["status"] == "DEAD")

            st.markdown(f"### 🛡️ Linaje: `{r['bot_id']}` — {display_title}")
            st.caption(
                f"📊 **Población del Linaje:** {len(family_members)} bots ({alive_count} vivos, {dead_count} muertos) | "
                f"**Reproducciones totales:** {total_children} | **Capital Semilla:** {r['capital']:.2f} €"
            )

            df_family = pd.DataFrame(family_members)
            display_family_df = df_family[[
                "bot_id", "generation", "status", "capital", "reproductions",
                "trades", "win_rate", "profit_factor", "realized_pnl", "parent_id"
            ]].copy()

            display_family_df.rename(columns={
                "bot_id": "ID Bot",
                "generation": "Gen",
                "status": "Estado",
                "capital": "Capital (€)",
                "reproductions": "Hijos",
                "trades": "Trades",
                "win_rate": "Win Rate (%)",
                "profit_factor": "Profit Factor",
                "realized_pnl": "PnL (€)",
                "parent_id": "Progenitor",
            }, inplace=True)

            tbl_height = min(320, 40 + len(display_family_df) * 36)
            st.dataframe(
                display_family_df.style.apply(highlight_bot_status, axis=1),
                use_container_width=True,
                height=tbl_height,
            )
            st.markdown("---")
    else:
        st.info("No hay bots registrados aún.")

with tab_genealogy:
    st.subheader("Árbol Genealógico del Ecosistema")
    genealogy = stats_engine.get_genealogy_tree_data()
    nodes = genealogy["nodes"]
    edges = genealogy["edges"]

    if nodes:
        df_nodes = pd.DataFrame(nodes)
        
        # Cruzar con número de hijos para colorear el árbol
        children_map = dict(zip(df_bots["bot_id"], df_bots["reproductions"]))
        def get_category(row):
            if row["status"] == "DEAD":
                return "Muerto (Quiebra)"
            elif children_map.get(row["id"], 0) > 0:
                return "Vivo con Hijos"
            else:
                return "Vivo sin Hijos"

        df_nodes["Categoria"] = df_nodes.apply(get_category, axis=1)

        fig_tree = px.scatter(
            df_nodes,
            x="generation",
            y="id",
            color="Categoria",
            size=[16] * len(df_nodes),
            hover_name="label",
            title="Distribución de Linajes por Generación",
            color_discrete_map={
                "Muerto (Quiebra)": "#ef553b",
                "Vivo con Hijos": "#00cc96",
                "Vivo sin Hijos": "#1f77b4",
            },
            labels={"generation": "Generación Evolutiva", "id": "Bot ID", "Categoria": "Estado"},
        )
        fig_tree.update_layout(height=400)
        st.plotly_chart(fig_tree, use_container_width=True)
        st.write(f"Total de ramificaciones registradas: **{len(edges)} enlaces parentales**.")
    else:
        st.info("Árbol vacío.")

with tab_equity:
    st.subheader("Evolución del Libro Mayor (Ledger) Contable")
    conn = sqlite3.connect(DB_PATH)
    ledger_df = pd.read_sql_query("SELECT bot_id, timestamp, balance_after, entry_type FROM ledger_entries ORDER BY entry_id ASC", conn)
    conn.close()

    if not ledger_df.empty:
        fig_equity = px.line(
            ledger_df,
            x="timestamp",
            y="balance_after",
            color="bot_id",
            title="Curvas de Capital Individuales (Regla Inquebrantable de Conservación)",
            labels={"balance_after": "Saldo en Cartera (€)", "timestamp": "Tiempo"},
        )
        fig_equity.add_hline(y=40.0, line_dash="dash", line_color="green", annotation_text="Umbral de Reproducción (40€)")
        fig_equity.add_hline(y=0.0, line_dash="dash", line_color="red", annotation_text="Umbral de Muerte (0€)")
        fig_equity.update_layout(height=450)
        st.plotly_chart(fig_equity, use_container_width=True)
    else:
        st.info("No hay movimientos en el ledger.")

with tab_inspector:
    st.subheader("Inspección de Genoma y Reglas de Trading")
    if not df_bots.empty:
        selected_bot_id = st.selectbox("Selecciona un bot para inspeccionar:", df_bots["bot_id"].unique(), key="inspector_select")
        selected_row = df_bots[df_bots["bot_id"] == selected_bot_id].iloc[0]
        
        col_meta, col_genome = st.columns([1, 2])
        with col_meta:
            st.markdown(f"**Identificador:** `{selected_row['bot_id']}`")
            st.markdown(f"**Generación:** `{selected_row['generation']}`")
            st.markdown(f"**Progenitor:** `{selected_row['parent_id']}`")
            st.markdown(f"**Estado:** `{selected_row['status']}`")
            st.markdown(f"**Capital Actual:** `{selected_row['capital']} €`")
            st.markdown(f"**Hijos engendrados:** `{selected_row['reproductions']}`")
        
        with col_genome:
            st.markdown("#### Genoma Técnico (Estrategia)")
            genome_dict = json.loads(selected_row["genome_json"])
            st.json(genome_dict)

with tab_pine:
    st.subheader("📊 Exportador Oficial a Pine Script v6 (TradingView)")
    st.markdown("Selecciona cualquier bot del ecosistema evolutivo para generar su código **Pine Script v6** listo para copiar y validar en el **Strategy Tester** de TradingView.")
    
    if not df_bots.empty:
        bot_to_export = st.selectbox("Bot a exportar a Pine v6:", df_bots["bot_id"].unique(), key="pine_select")
        target_row = df_bots[df_bots["bot_id"] == bot_to_export].iloc[0]
        genome_obj = StrategyGenome.from_dict(json.loads(target_row["genome_json"]))
        
        pine_code = PineScriptExporter.export_bot_to_pine_v6(
            bot_id=target_row["bot_id"],
            generation=target_row["generation"],
            genome=genome_obj,
        )

        st.code(pine_code, language="pinescript")
        st.download_button(
            label="💾 Descargar archivo .pine",
            data=pine_code,
            file_name=f"{target_row['bot_id']}_v6.pine",
            mime="text/plain",
        )
