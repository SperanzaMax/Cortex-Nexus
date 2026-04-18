"""
monitor_validacion.py — Dashboard Unificado de Validación
Cortex-Nexus · 2026-04-16

Tab 1: Experimento A — Cross-Domain (filosófico / técnico / creativo)
Tab 2: Experimento C — Validación del Óptimo (curiosidad_sola vs optimo_2d)

Puerto: 8511
"""
import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=10 * 1000, key="validacion_refresh")

st.set_page_config(page_title="Cortex-Nexus — Validación", layout="wide")
st.title("🔬 Monitor: Fase de Validación y Extensión")
st.markdown("**Exp A**: Cross-Domain &nbsp;|&nbsp; **Exp B**: Wilcoxon &nbsp;|&nbsp; **Exp C**: Validación del Óptimo")

BASE = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-validacion/data"

CROSSDOMAIN_PATHS = {
    "🧠 Filosófico":  os.path.join(BASE, "cycles_crossdomain_filosofico.jsonl"),
    "⚙️ Técnico":     os.path.join(BASE, "cycles_crossdomain_tecnico.jsonl"),
    "🎨 Creativo":    os.path.join(BASE, "cycles_crossdomain_creativo.jsonl"),
}
OPTIMO_PATH = os.path.join(BASE, "cycles_validacion_optimo.jsonl")
WILCOXON_PATH = os.path.join(BASE, "wilcoxon_results.json")

DOMAIN_COLORS = {
    "filosofico": "#4ECDC4",
    "tecnico":    "#FFE66D",
    "creativo":   "#FF6B6B",
}
CONDICION_COLORS = {
    "curiosidad_sola": "#4ECDC4",
    "optimo_2d":       "#FF6B6B",
}


def load_jsonl(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            try: data.append(json.loads(line))
            except: pass
    return pd.DataFrame(data) if data else pd.DataFrame()


# ─────────────────────────────────────────────────────────
# TAB: EXPERIMENTO A — CROSS-DOMAIN
# ─────────────────────────────────────────────────────────
def render_crossdomain():
    st.markdown("### 🌐 Experimento A — ¿El efecto de curiosidad es específico del dominio filosófico?")
    st.markdown("Diseño: 3 dominios × 4 bloques de curiosidad × 30 ciclos = 360 ciclos")

    # Cargar y combinar
    dfs = {}
    all_data = []
    for label, path in CROSSDOMAIN_PATHS.items():
        df = load_jsonl(path)
        dfs[label] = df
        if not df.empty:
            all_data.append(df)

    # Barras de progreso
    cols = st.columns(3)
    total_target = 120  # 4 bloques × 30 ciclos
    for i, (label, path) in enumerate(CROSSDOMAIN_PATHS.items()):
        df = dfs[label]
        with cols[i]:
            n = len(df)
            pct = round((n / total_target) * 100, 1)
            st.metric(label, f"{pct}%", f"{n}/{total_target} ciclos")

    if not all_data:
        st.info("Esperando datos del motor cross-domain...")
        return

    df_all = pd.concat(all_data, ignore_index=True)

    # ─── Gráfico estrella: Δ Score por dominio × bloque curiosidad ───
    st.markdown("---")
    st.markdown("#### 🎯 Δ Score por Dominio × Nivel de Curiosidad")
    if 'delta_score' in df_all.columns and 'curiosity_fixed' in df_all.columns and 'domain' in df_all.columns:
        agg = df_all.groupby(['domain', 'curiosity_fixed']).agg(
            delta_mean=('delta_score', 'mean'),
            n=('delta_score', 'count')
        ).reset_index()

        fig = go.Figure()
        for domain, color in DOMAIN_COLORS.items():
            d = agg[agg['domain'] == domain]
            if not d.empty:
                fig.add_trace(go.Scatter(
                    x=d['curiosity_fixed'],
                    y=d['delta_mean'],
                    mode='lines+markers',
                    name=domain.capitalize(),
                    line=dict(color=color, width=3),
                    marker=dict(size=10),
                    text=[f"n={n}" for n in d['n']],
                    hovertemplate="%{y:+.3f}<br>%{text}"
                ))

        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            height=400,
            xaxis_title="Nivel de Curiosidad →",
            yaxis_title="Δ Score (Exp - Ctl)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.03)',
            legend_title="Dominio",
        )
        st.plotly_chart(fig, use_container_width=True, key="crossdomain_line")

    # ─── Tabla resumen ───
    st.markdown("#### 📊 Tabla Comparativa por Dominio")
    if 'domain' in df_all.columns and 'delta_score' in df_all.columns:
        summary = df_all.groupby('domain').agg(
            n=('delta_score', 'count'),
            delta_media=('delta_score', 'mean'),
            nov_media=('judge_novedad_exp', 'mean'),
            pro_media=('judge_profundidad_exp', 'mean'),
            coh_media=('judge_coherencia_exp', 'mean')
        ).reset_index()
        summary.columns = ['Dominio', 'Ciclos', 'Δ Score (media)', 'Nov Exp', 'Pro Exp', 'Coh Exp']
        summary = summary.sort_values('Δ Score (media)', ascending=False)
        st.dataframe(summary, use_container_width=True, hide_index=True)

    # ─── Histograma de distribución de deltas ───
    st.markdown("#### 📐 Distribución de Δ Score por Dominio")
    if 'delta_score' in df_all.columns and 'domain' in df_all.columns:
        fig2 = px.histogram(
            df_all, x='delta_score', color='domain',
            color_discrete_map=DOMAIN_COLORS,
            nbins=25, barmode='overlay',
            labels={'delta_score': 'Δ Score', 'domain': 'Dominio'},
            height=350, opacity=0.75
        )
        fig2.add_vline(x=0, line_dash="dash", line_color="white", opacity=0.5)
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.03)')
        st.plotly_chart(fig2, use_container_width=True, key="crossdomain_hist")


# ─────────────────────────────────────────────────────────
# TAB: EXPERIMENTO B — WILCOXON
# ─────────────────────────────────────────────────────────
def render_wilcoxon():
    st.markdown("### 📐 Experimento B — Análisis Estadístico Wilcoxon (ya ejecutado)")
    if not os.path.exists(WILCOXON_PATH):
        st.warning("No se encontró wilcoxon_results.json — ejecutar `python analysis/statistical_tests.py`")
        return

    with open(WILCOXON_PATH) as f:
        data = json.load(f)

    rows = []
    for nombre, r in data.items():
        rows.append({
            "Experimento": nombre,
            "n": r.get("n", 0),
            "p-value": round(r.get("p_value", 1), 6),
            "Δ (media)": round(r.get("mean_delta", 0), 4),
            "Effect d": round(r.get("effect_size_d", 0), 4),
            "Significativo": "✓ SÍ" if r.get("significant", 0) == 1 else "✗ NO"
        })

    df_w = pd.DataFrame(rows).sort_values("p-value")

    # Highlight significativos
    st.dataframe(df_w, use_container_width=True, hide_index=True)

    # Barras de p-values (línea α=0.05)
    st.markdown("#### Distribución de p-values (α=0.05)")
    fig = go.Figure()
    colors = ["#4ECDC4" if r["Significativo"] == "✓ SÍ" else "#FF6B6B" for _, r in df_w.iterrows()]
    fig.add_trace(go.Bar(
        x=df_w["Experimento"],
        y=df_w["p-value"],
        marker_color=colors,
        text=[f"p={v:.4f}" for v in df_w["p-value"]],
        textposition='outside'
    ))
    fig.add_hline(y=0.05, line_dash="dash", line_color="yellow",
                  annotation_text="α=0.05", annotation_position="top right")
    fig.update_layout(
        height=400,
        yaxis_title="p-value (menor = más significativo)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.03)',
    )
    st.plotly_chart(fig, use_container_width=True, key="wilcoxon_bars")


# ─────────────────────────────────────────────────────────
# TAB: EXPERIMENTO C — VALIDACIÓN ÓPTIMO
# ─────────────────────────────────────────────────────────
def render_optimo():
    st.markdown("### ⚖️ Experimento C — ¿La configuración óptima es realmente superior?")
    st.markdown("Curiosidad sola (C=0.95) vs Óptimo 2D (C=0.95 + F=0.20) · 100 ciclos cada condición")

    df = load_jsonl(OPTIMO_PATH)
    if df.empty:
        st.info("Esperando datos del motor de validación del óptimo...")
        return

    total = len(df)
    pct = round((total / 200) * 100, 1)
    last_cond = df['condicion'].iloc[-1] if 'condicion' in df.columns else "?"

    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Ciclos completados", total, f"/ 200 total")
    with m2: st.metric("Progreso", f"{pct}%")
    with m3: st.metric("Condición actual", last_cond)

    # ─── Evolución temporal ───
    st.markdown("#### 📈 Δ Score por Ciclo — Comparación Rolling")
    if 'delta_score' in df.columns and 'condicion' in df.columns:
        # Rolling mean por condición
        fig = go.Figure()
        for cond, color in CONDICION_COLORS.items():
            dc = df[df['condicion'] == cond].copy()
            if not dc.empty:
                dc['rolling'] = dc['delta_score'].rolling(10, min_periods=1).mean()
                fig.add_trace(go.Scatter(
                    x=dc.index, y=dc['rolling'],
                    mode='lines', name=cond,
                    line=dict(color=color, width=3)
                ))
                # Scatter de puntos individuales (más tenue)
                fig.add_trace(go.Scatter(
                    x=dc.index, y=dc['delta_score'],
                    mode='markers', name=f"{cond} (raw)",
                    marker=dict(color=color, size=4, opacity=0.3),
                    showlegend=False
                ))

        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            height=400,
            xaxis_title="Ciclo",
            yaxis_title="Δ Score (Exp - Ctl)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.03)',
        )
        st.plotly_chart(fig, use_container_width=True, key="optimo_rolling")

    # ─── Comparativa de métricas ───
    st.markdown("#### 📊 Métricas Promedio por Condición")
    if 'condicion' in df.columns:
        agg = df.groupby('condicion').agg(
            n=('delta_score', 'count'),
            delta=('delta_score', 'mean'),
            nov_exp=('judge_novedad_exp', 'mean'),
            pro_exp=('judge_profundidad_exp', 'mean'),
            coh_exp=('judge_coherencia_exp', 'mean'),
            nov_ctl=('judge_novedad_ctl', 'mean'),
            pro_ctl=('judge_profundidad_ctl', 'mean'),
        ).reset_index()
        agg.columns = ['Condición', 'n', 'Δ Score', 'Nov.Exp', 'Pro.Exp', 'Coh.Exp', 'Nov.Ctl', 'Pro.Ctl']
        for c in ['Δ Score', 'Nov.Exp', 'Pro.Exp', 'Coh.Exp']:
            agg[c] = agg[c].round(3)
        st.dataframe(agg, use_container_width=True, hide_index=True)

    # ─── Boxplot ───
    st.markdown("#### 📦 Distribución de Δ Score por Condición")
    if 'delta_score' in df.columns and 'condicion' in df.columns:
        fig2 = px.box(
            df, x='condicion', y='delta_score',
            color='condicion',
            color_discrete_map=CONDICION_COLORS,
            points='all',
            labels={'delta_score': 'Δ Score', 'condicion': 'Condición'},
            height=400
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.03)',
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True, key="optimo_boxplot")


# ─────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────
tab_a, tab_b, tab_c = st.tabs([
    "🌐 Exp A — Cross-Domain",
    "📐 Exp B — Wilcoxon",
    "⚖️ Exp C — Validación Óptimo"
])

with tab_a:
    render_crossdomain()

with tab_b:
    render_wilcoxon()

with tab_c:
    render_optimo()

st.markdown("---")
st.caption(
    f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    f"Puerto 8511 | IP: 192.168.0.88"
)
if st.button("🔄 Forzar Recarga"):
    st.rerun()
