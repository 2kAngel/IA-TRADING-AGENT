import os
import sys
import json
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Evolution Trading System - Multi-Asset Lab",
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
from src.market.market_data_provider import ASSET_CONFIGS, TIMEFRAME_CONFIGS
from src.core.models import StrategyGenome

DB_PATH = os.path.join("data", "evolution.db")
stats_engine = StatisticsEngine(db_path=DB_PATH)

# ==========================================
# BARRA LATERAL: CONTROL DE SIMULACIÓN Y MERCADO
# ==========================================
st.sidebar.header("⚙️ Control de Simulación")

# 1. Selector de Activo
asset_options = {
    "BTC": "🪙 Bitcoin (BTC)",
    "GOLD": "🥇 Oro / Gold (GC=F)",
    "SP500": "📈 S&P 500 (SPY)",
    "IBERDROLA": "⚡ Iberdrola (IBE.MC)",
}
selected_asset = st.sidebar.selectbox(
    "Activo Financiero",
    options=list(asset_options.keys()),
    format_func=lambda x: asset_options[x],
    index=0,
    help="Datos de mercado reales descargados y cacheados localmente.",
)

# 2. Selector de Temporalidad
tf_options = {
    "1m": "⚡ 1 Minuto (1m)",
    "1h": "⏳ 1 Hora (1h)",
    "1w": "📅 1 Semana (1w)",
}
selected_tf = st.sidebar.selectbox(
    "Temporalidad de Velas",
    options=list(tf_options.keys()),
    format_func=lambda x: tf_options[x],
    index=1,
    help="1m: Scalping intradía | 1h: Swing trading | 1w: Macro-tendencias",
)

st.sidebar.markdown("---")

# 3. Capital Inicial
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

# 4. Número de Velas (adaptado según temporalidad)
if selected_tf == "1m":
    slider_min, slider_max, slider_default, slider_step = 100, 2000, 800, 100
    tf_unit = "minutos"
    caption_txt = "⏱️ Scalping de alta frecuencia (últimos días de mercado)."
elif selected_tf == "1h":
    slider_min, slider_max, slider_default, slider_step = 100, 3000, 800, 100
    tf_unit = "horas"
    caption_txt = "📅 Swing trading horario continuo."
else:
    slider_min, slider_max, slider_default, slider_step = 20, 500, 100, 10
    tf_unit = "semanas"
    caption_txt = "📅 Macro-tendencias históricas de largo plazo."

num_velas_input = st.sidebar.slider(
    f"Número de Velas ({tf_unit.capitalize()})",
    min_value=slider_min,
    max_value=slider_max,
    value=slider_default,
    step=slider_step,
)
st.sidebar.caption(caption_txt)

# 5. Selector de Apalancamiento
leverage_options = {
    1.0: "1x (Sin apalancamiento / Spot)",
    2.0: "2x (Apalancamiento x2)",
    5.0: "5x (Apalancamiento x5)",
}
selected_leverage = st.sidebar.selectbox(
    "Apalancamiento (CFD Capital.com)",
    options=list(leverage_options.keys()),
    format_func=lambda x: leverage_options[x],
    index=0,
    help="Multiplica los beneficios y pérdidas en cada trade. Modelo Capital.com (0% comisión fija + spread).",
)

if "simulation_executed" not in st.session_state:
    st.session_state["simulation_executed"] = False

if st.sidebar.button("🚀 Ejecutar Nueva Simulación", type="primary", use_container_width=True):
    lev_str = f"{int(selected_leverage)}x" if selected_leverage > 1.0 else "1x"
    with st.spinner(f"Simulando {semillas_calculadas} semillas ({capital_input} €) en {asset_options[selected_asset]} [{tf_options[selected_tf]}] {lev_str} ({num_velas_input} velas)..."):
        res = execute_custom_simulation(
            num_candles=num_velas_input,
            capital_inicial=float(capital_input),
            asset=selected_asset,
            timeframe=selected_tf,
            leverage=float(selected_leverage),
        )
        st.session_state["simulation_executed"] = True
        st.session_state["active_asset"] = selected_asset
        st.session_state["active_tf"] = selected_tf
        st.session_state["active_leverage"] = selected_leverage
        st.sidebar.success(f"¡Completado! {res['total_active']} bots vivos ({res['total_equity']:.2f} €).")
        st.rerun()


active_asset_code = st.session_state.get("active_asset", selected_asset)
active_tf_code = st.session_state.get("active_tf", selected_tf)
active_leverage_val = st.session_state.get("active_leverage", selected_leverage)
active_asset_name = asset_options.get(active_asset_code, active_asset_code)
active_tf_name = tf_options.get(active_tf_code, active_tf_code)
active_lev_badge = f"{int(active_leverage_val)}x" if active_leverage_val > 1.0 else "1x (Spot)"

# Comprobar si se ha ejecutado la simulación en esta sesión
if not st.session_state.get("simulation_executed", False) or not os.path.exists(DB_PATH):
    st.markdown(f"""
    <div style="margin-bottom: 0.6rem;">
        <h2 style="margin: 0; font-size: 1.35rem; font-weight: 700; color: var(--text-color, #1f2937);">🧬 Evolution Trading System — {asset_options[selected_asset]}</h2>
        <p style="margin: 0; color: #6b7280; font-size: 0.82rem;">Laboratorio Cuantitativo de Selección Natural, Herencia Genética y Supervivencia Multi-Activo (Oro, S&P 500, Iberdrola, Cripto)</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("👈 **Esperando primera ejecución:** El sistema comienza vacío. Selecciona el **Activo**, la **Temporalidad**, el **Capital** y pulsa **'🚀 Ejecutar Nueva Simulación'** para comenzar.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"#### 💰 Cartera y Margen\n- **Activo:** {asset_options[selected_asset]}\n- **Capital:** **{capital_input} €** ({semillas_calculadas} semillas)\n- **Apalancamiento:** **{leverage_options[selected_leverage]}**")
    with col_b:
        st.markdown(f"#### ⏳ Horizonte Temporal\n- **Temporalidad:** {tf_options[selected_tf]}\n- **Velas:** **{num_velas_input} velas** ({tf_unit})")
    with col_c:
        st.markdown("#### 🧬 Reglas Biológicas Estrictas\n- 🐣 **Reproducción:** Al alcanzar **40.00 €** (+20 € al hijo)\n- 💀 **Muerte técnica:** Si su patrimonio cae a **≤ 4.50 €** (margen mínimo de broker)")

    st.markdown("---")
    st.markdown("""
    ### 🏆 Catálogo de Estrategias Iniciales (Orden Riguroso)
    Al pulsar **'🚀 Ejecutar Nueva Simulación'**, los bots semilla se asignarán en estricto orden histórico:
    1. **Estrategia Invertida (Breakout Rango + POC Volumen)**: Ruptura alcista institucional sobre POC y zona alta
    2. **Richard Dennis (1983)**: Breakout de Canales Donchian (Turtles)
    3. **Gerald Appel (1979)**: Momentum y Cruce de Medias MACD Clásico
    4. **J. Welles Wilder (1978)**: Pullback en Sobreventa RSI
    5. **John Bollinger (1983)**: Reversión a la Media en Bandas de Bollinger
    6. **Ivan Scherman (2023)**: Volatility Divergence & Bollinger Exhaustion *(Campeón Mundial 491%)*
    7. **Stefan Seibert (2022/2020)**: Zeno Price Action Breakout *(Bicampeón Mundial)*
    8. **Kevin McCormick (2021)**: DeMark TD9 Sequential Exhaustion *(Campeón Mundial 383%)*
    9. **Rob Hoffman (2015)**: Inventory Retracement Bar Reversal
    10. **Chuck Hughes (2015/1999)**: Trend Momentum en Canales de Keltner *(10x Campeón Mundial)*
    11. *...y demás campeones de la World Cup Trading Championship.*
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
            🧬 Evolution Trading System — {active_asset_name}
            <span style="font-size:0.75rem; color:#2563eb; background:rgba(37,99,235,0.12); padding:2px 7px; border-radius:8px; font-weight:600; margin-left:6px;">{active_tf_name}</span>
            <span style="font-size:0.75rem; color:#d97706; background:rgba(217,119,6,0.12); padding:2px 7px; border-radius:8px; font-weight:600; margin-left:4px;">{active_lev_badge}</span>
            <span class="sticky-brand-subtitle">Laboratorio Cuantitativo de Selección Natural</span>
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
            "INVERTIDA": "Estrategia Invertida (Breakout Rango + POC Volumen)",
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
    # Filtrar solo estados consolidados de capital (evita mostrar el efectivo en 0 mientras el dinero está invertido en mercado)
    ledger_df = pd.read_sql_query(
        "SELECT bot_id, timestamp, balance_after, entry_type FROM ledger_entries "
        "WHERE entry_type IN ('INITIAL_CAPITAL', 'TRADE_RETURN', 'REPRODUCTION_DEBIT', 'REPRODUCTION_CREDIT') "
        "ORDER BY entry_id ASC", 
        conn
    )
    conn.close()

    if not ledger_df.empty:
        fig_equity = px.line(
            ledger_df,
            x="timestamp",
            y="balance_after",
            color="bot_id",
            title="Curvas de Capital Real (Patrimonio Liquidable por Bot)",
            labels={"balance_after": "Capital Real (€)", "timestamp": "Tiempo"},
        )
        fig_equity.add_hline(y=40.0, line_dash="dash", line_color="green", annotation_text="Umbral de Reproducción (40€)")
        fig_equity.add_hline(y=4.5, line_dash="dash", line_color="red", annotation_text="Umbral de Muerte (4.50€)")
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
        
        try:
            pine_code = PineScriptExporter.export_bot_to_pine_v6(
                bot_id=target_row["bot_id"],
                generation=target_row["generation"],
                genome=genome_obj,
                leverage=float(active_leverage_val),
            )
            st.code(pine_code, language="pinescript")
            st.download_button(
                label="💾 Descargar archivo .pine",
                data=pine_code,
                file_name=f"{target_row['bot_id']}_v6.pine",
                mime="text/plain",
            )
        except Exception as e:
            st.error(f"Error al generar Pine Script: {e}")
