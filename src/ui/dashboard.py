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
st.sidebar.markdown("Selecciona el tamaño del histórico para someter a los bots a pruebas de corto, medio o largo plazo:")

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
    with st.spinner(f"Simulando competencia evolutiva a lo largo de {num_velas_input} velas..."):
        res = execute_custom_simulation(num_candles=num_velas_input)
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
    st.subheader("Clasificación de Bots por Capital y Rentabilidad")
    st.caption("🎭 **Regla 'Bufón o Leyenda' activa:** Si un bot cae a <= 4.50 €, entra en modo desesperado arriesgando el 100% restante para intentar resurgir o morir en el intento.")
    if not df_bots.empty:
        display_df = df_bots[[
            "bot_id", "generation", "status", "capital", "reproductions",
            "trades", "win_rate", "profit_factor", "realized_pnl", "parent_id"
        ]].copy()
        
        display_df.rename(columns={
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

        def highlight_bot_status(row):
            status = row["Estado"]
            children = row["Hijos"]
            # Rojo: Muertos
            if status == "DEAD":
                return ["background-color: #4a1515; color: #ff9999; font-weight: bold;"] * len(row)
            # Verde: Vivos con hijos
            elif status == "ACTIVE" and children > 0:
                return ["background-color: #12381f; color: #99ffbb; font-weight: bold;"] * len(row)
            # Azul: Vivos sin hijos
            elif status == "ACTIVE" and children == 0:
                return ["background-color: #122538; color: #99ccff;"] * len(row)
            return [""] * len(row)

        st.dataframe(
            display_df.style.apply(highlight_bot_status, axis=1),
            use_container_width=True,
            height=380,
        )
        st.markdown(
            "🔴 **Rojo:** Muertos (quiebra técnica) | "
            "🟢 **Verde:** Vivos con hijos (progenitores exitosos) | "
            "🔵 **Azul:** Vivos sin hijos (jóvenes o en camino)"
        )
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
