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

# Inyección de estilos CSS para interfaz ultra-compacta y cabecera FIJA (sticky)
st.markdown("""
<style>
/* 1. Reducir padding excesivo de Streamlit en la parte superior y laterales */
.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 2rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
}

/* 2. Ocultar botones redundantes superiores (Deploy y menú) para ahorrar espacio */
.stAppDeployButton {
    display: none !important;
}
#MainMenu {
    visibility: hidden !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 1.2rem !important;
}

/* 3. Cabecera fija (Sticky) compacta para el resumen de métricas */
div[data-testid="stElementContainer"]:has(.sticky-summary-panel),
div.element-container:has(.sticky-summary-panel) {
    position: sticky !important;
    top: 0 !important;
    z-index: 990 !important;
    background-color: var(--background-color, #ffffff) !important;
    padding-top: 4px !important;
    padding-bottom: 8px !important;
    border-bottom: 1px solid rgba(128, 128, 128, 0.2) !important;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05) !important;
    margin-bottom: 8px !important;
}

.sticky-summary-panel {
    display: flex;
    flex-direction: column;
    gap: 6px;
    width: 100%;
}

.sticky-top-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0 2px;
}

.sticky-brand-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-color, #1f2937);
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.sticky-brand-subtitle {
    font-size: 0.78rem;
    color: #6b7280;
    font-weight: 400;
    margin-left: 8px;
}

.metrics-strip {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
    width: 100%;
}

.metric-pill {
    background: var(--secondary-background-color, #f8f9fa);
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 6px;
    padding: 4px 10px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.metric-pill-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    line-height: 1.1;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.metric-pill-value {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-color, #111827);
    line-height: 1.2;
    display: flex;
    align-items: baseline;
    gap: 6px;
    white-space: nowrap;
}

.metric-delta-tag {
    font-size: 0.75rem;
    font-weight: 600;
}

.c-green { color: #059669 !important; }
.c-red { color: #dc2626 !important; }
.c-gray { color: #6b7280 !important; }

/* 4. Pestañas más compactas */
button[data-baseweb="tab"] {
    padding-top: 6px !important;
    padding-bottom: 6px !important;
    font-size: 0.88rem !important;
}
</style>
""", unsafe_allow_html=True)

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

if "simulation_executed" not in st.session_state:
    st.session_state["simulation_executed"] = False

if st.sidebar.button("🚀 Ejecutar Nueva Simulación", type="primary", use_container_width=True):
    with st.spinner(f"Simulando {semillas_calculadas} semillas ({capital_input} €) a lo largo de {num_velas_input} velas..."):
        res = execute_custom_simulation(num_candles=num_velas_input, capital_inicial=float(capital_input))
        st.session_state["simulation_executed"] = True
        st.sidebar.success(f"¡Completado! {res['total_active']} bots vivos ({res['total_equity']:.2f} €).")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Con más de 1.000 velas verás nacer nietos (Gen 2) y bisnietos (Gen 3), y los bots de RSI y Bollinger empezarán a operar.")

# Comprobar si se ha ejecutado la simulación en esta sesión
if not st.session_state.get("simulation_executed", False) or not os.path.exists(DB_PATH):
    st.markdown("""
    <div style="margin-bottom: 0.6rem;">
        <h2 style="margin: 0; font-size: 1.35rem; font-weight: 700; color: var(--text-color, #1f2937);">🧬 Bitcoin Evolution Trading System</h2>
        <p style="margin: 0; color: #6b7280; font-size: 0.82rem;">Laboratorio Cuantitativo de Selección Natural, Herencia Genética y Supervivencia para Bitcoin</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("👈 **Esperando primera ejecución:** El sistema comienza vacío. Configura el **Capital Inicial Total** y el **Número de Velas** en el panel lateral y pulsa **'🚀 Ejecutar Nueva Simulación'** para comenzar.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"#### 💰 Capital Inicial Preparado\n**{capital_input} €**  \n({semillas_calculadas} bot(s) semilla Génesis de 20 € c/u)")
    with col_b:
        st.markdown(f"#### ⏳ Horizonte Temporal\n**{num_velas_input} Velas Horarias**  \n(~{dias_aprox} días de mercado continuo)")
    with col_c:
        st.markdown("#### 🧬 Reglas Biológicas Estrictas\n- 🐣 **Reproducción:** Al alcanzar **40.00 €** (transfiere 20 € a su hijo)\n- 💀 **Muerte técnica:** Si su capital cae a **≤ 4.50 €**")

    st.markdown("---")
    st.markdown("""
    ### 🏆 Catálogo de Estrategias Iniciales (Orden Riguroso)
    Al pulsar **'🚀 Ejecutar Nueva Simulación'**, los bots semilla se asignarán en estricto orden histórico:
    1. **Richard Dennis (1983)**: Breakout de Canales Donchian (Turtles)
    2. **Gerald Appel (1979)**: Momentum y Cruce de Medias MACD Clásico
    3. **J. Welles Wilder (1978)**: Pullback en Sobreventa RSI
    4. **John Bollinger (1983)**: Reversión a la Media en Bandas de Bollinger
    5. **Ivan Scherman (2023)**: Volatility Divergence & Bollinger Exhaustion *(Campeón Mundial 491%)*
    6. **Stefan Seibert (2022/2020)**: Zeno Price Action Breakout *(Bicampeón Mundial)*
    7. **Kevin McCormick (2021)**: DeMark TD9 Sequential Exhaustion *(Campeón Mundial 383%)*
    8. **Rob Hoffman (2015)**: Inventory Retracement Bar Reversal
    9. **Chuck Hughes (2015/1999)**: Trend Momentum en Canales de Keltner *(10x Campeón Mundial)*
    10. *...y demás campeones de la World Cup Trading Championship.*
    """)
    st.stop()

# ==========================================
# 1. PANEL GENERAL FIJO Y COMPACTO (STICKY HEADER)
# ==========================================
overview = stats_engine.get_ecosystem_overview()

delta_sign = "+" if overview['net_profit'] > 0 else ""
profit_cls = "c-green" if overview['net_profit'] > 0 else ("c-red" if overview['net_profit'] < 0 else "c-gray")
roi_cls = "c-green" if overview['roi_pct'] > 0 else ("c-red" if overview['roi_pct'] < 0 else "c-gray")
roi_sign = "+" if overview['roi_pct'] > 0 else ""

dead_count = overview['dead_bots']
dead_tag = f"<span class='metric-delta-tag c-red'>(-{dead_count} muertos)</span>" if dead_count > 0 else "<span class='metric-delta-tag c-gray'>(0 muertos)</span>"

st.markdown(f"""
<div class="sticky-summary-panel">
    <div class="sticky-top-row">
        <div class="sticky-brand-title">
            🧬 Bitcoin Evolution Trading System
            <span class="sticky-brand-subtitle">Laboratorio Cuantitativo de Selección Natural para Bitcoin</span>
        </div>
    </div>
    <div class="metrics-strip">
        <div class="metric-pill">
            <span class="metric-pill-label">Capital Ecosistema</span>
            <div class="metric-pill-value">
                {overview['current_capital']:.2f} €
                <span class="metric-delta-tag {profit_cls}">({delta_sign}{overview['net_profit']:.2f} €)</span>
            </div>
        </div>
        <div class="metric-pill">
            <span class="metric-pill-label">Bots Activos</span>
            <div class="metric-pill-value">
                {overview['active_bots']}
                {dead_tag}
            </div>
        </div>
        <div class="metric-pill">
            <span class="metric-pill-label">Máxima Generación</span>
            <div class="metric-pill-value">Gen {overview['max_generation']}</div>
        </div>
        <div class="metric-pill">
            <span class="metric-pill-label">Total Reproducciones</span>
            <div class="metric-pill-value">{overview['total_reproductions']} 🐣</div>
        </div>
        <div class="metric-pill">
            <span class="metric-pill-label">ROI Global Ecosistema</span>
            <div class="metric-pill-value {roi_cls}">{roi_sign}{overview['roi_pct']:.2f} %</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

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
    st.markdown(
        "<div style='margin: 4px 0 8px 0; display: flex; justify-content: space-between; align-items: center;'>"
        "<span style='font-size: 0.95rem; font-weight: 600; color: var(--text-color);'>Clasificación por Familias y Linajes Genéticos</span>"
        "<span style='font-size: 0.8rem;'>"
        "🔴 <b style='color:#dc2626;'>Muertos</b> &nbsp;|&nbsp; "
        "🟢 <b style='color:#059669;'>Vivos con hijos</b> &nbsp;|&nbsp; "
        "🔵 <b style='color:#2563eb;'>Vivos sin hijos</b>"
        "</span>"
        "</div>",
        unsafe_allow_html=True
    )

    if not df_bots.empty:

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
            "SCHERMAN": "Ivan Scherman (Campeón Mundial 2023 - Agotamiento Volatilidad)",
            "SEIBERT": "Stefan Seibert (Campeón Mundial 2022/2020 - Zeno Price Action)",
            "MCCORMICK": "Kevin McCormick (Campeón Mundial 2021 - DeMARK TD9 Reversal)",
            "HOFFMAN": "Rob Hoffman (Campeón 2015 - Inventory Retracement Bar)",
            "HUGHES": "Chuck Hughes (10x Campeón Mundial - Keltner Trend)",
            "UNGER": "Andrea Unger (4x Campeón Mundial - Session Breakout)",
            "DAVEY": "Kevin Davey (Campeón Mundial 2006 - Algo Volatility)",
            "WILLIAMS": "Larry & Michelle Williams (Récord Histórico 11,376% - Williams %R)",
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

            st.markdown(
                f"<div style='margin-top: 10px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: baseline;'>"
                f"<span style='font-size: 1.02rem; font-weight: 700; color: var(--text-color);'>🛡️ Linaje: <code>{r['bot_id']}</code> — {display_title}</span>"
                f"<span style='font-size: 0.8rem; color: #6b7280;'>"
                f"Población: <b>{len(family_members)}</b> ({alive_count} vivos, {dead_count} muertos) | Hijos: <b>{total_children}</b> | Semilla: <b>{r['capital']:.2f} €</b>"
                f"</span>"
                f"</div>",
                unsafe_allow_html=True
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
            st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)
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
