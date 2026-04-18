"""
monitor_confirmacion_final.py — Dashboard Unificado para la Fase de Confirmación Final
Cortex-Nexus · 2026-04-16

Trackea:
- Asombro Confirmación
- Óptimo Confirmación
- Confianza en Domino Técnico

Uso:
  streamlit run src/monitor_confirmacion_final.py --server.port 8520
"""
import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Refresco cada 15 segundos
st_autorefresh(interval=15 * 1000, key="confirmacion_refresh")

st.set_page_config(page_title="Cortex-Nexus — Confirmación Final", layout="wide")
st.title("🚀 Monitor: Fase de Confirmación Final")
st.markdown("**Test 1**: Asombro &nbsp;|&nbsp; **Test 2**: Óptimo &nbsp;|&nbsp; **Test 3**: Técnico con Confianza")

BASE_ASOMBRO = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-asombro/data"
BASE_VALIDACION = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-validacion/data"
BASE_CONFIANZA = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-confianza/data"

PATHS = {
    "asombro": os.path.join(BASE_ASOMBRO, "cycles_asombro_confirmacion.jsonl"),
    "optimo": os.path.join(BASE_VALIDACION, "cycles_optimo_confirmacion.jsonl"),
    "tecnico": os.path.join(BASE_CONFIANZA, "cycles_tecnico_confianza.jsonl")
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
# TAB 1: ASOMBRO
# ─────────────────────────────────────────────────────────
def render_asombro():
    st.markdown("### 🌌 Confirmación 1 — Asombro (PRIORITARIA)")
    st.markdown("Busca cruzar p<0.05. Target: 100 ciclos en bloques.")
    
    df = load_jsonl(PATHS["asombro"])
    if df.empty:
        st.info("Esperando datos del motor de asombro...")
        return
        
    total = len(df)
    pct = min(100, round((total / 100) * 100, 1))
    
    m1, m2 = st.columns(2)
    with m1: st.metric("Ciclos completados", total, f"/ 100 total")
    with m2: st.metric("Progreso", f"{pct}%")

    if 'delta_score' in df.columns and 'asombro_fixed' in df.columns:
        # Renombramos asombro_fixed temporalmente si es wonder_fixed
        col_name = 'asombro_fixed' if 'asombro_fixed' in df.columns else 'wonder_fixed'
        
        agg = df.groupby(col_name).agg(
            n=('delta_score', 'count'),
            delta_media=('delta_score', 'mean')
        ).reset_index()

        fig = px.line(
            agg, x=col_name, y='delta_media', 
            markers=True, text='n',
            title='Δ Score por Nivel de Asombro'
        )
        fig.update_traces(textposition='top center')
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.03)')
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────
# TAB 2: ÓPTIMO
# ─────────────────────────────────────────────────────────
def render_optimo():
    st.markdown("### ⚖️ Confirmación 2 — Configuración Óptima")
    st.markdown("Curiosidad_sola vs Optimo_2d. Target: 120 ciclos.")

    df = load_jsonl(PATHS["optimo"])
    if df.empty:
        st.info("Esperando datos del motor de óptimo...")
        return

    total = len(df)
    pct = min(100, round((total / 120) * 100, 1))
    
    m1, m2 = st.columns(2)
    with m1: st.metric("Ciclos completados", total, f"/ 120 total")
    with m2: st.metric("Progreso", f"{pct}%")

    if 'delta_score' in df.columns and 'condicion' in df.columns:
        fig = px.box(
            df, x='condicion', y='delta_score', color='condicion',
            points='all', title="Distribución de Δ Score por Condición"
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.03)', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────
# TAB 3: TÉCNICO CON CONFIANZA
# ─────────────────────────────────────────────────────────
def render_tecnico():
    st.markdown("### ⚙️ Confirmación 3 — Dominio Técnico con Confianza")
    st.markdown("Prueba la alineación tarea-emoción. Target: 100 ciclos en bloques.")

    df = load_jsonl(PATHS["tecnico"])
    if df.empty:
        st.info("Esperando datos del motor técnico/confianza...")
        return

    total = len(df)
    pct = min(100, round((total / 100) * 100, 1))
    
    m1, m2 = st.columns(2)
    with m1: st.metric("Ciclos completados", total, f"/ 100 total")
    with m2: st.metric("Progreso", f"{pct}%")

    if 'delta_score' in df.columns and 'confidence_fixed' in df.columns:
        agg = df.groupby('confidence_fixed').agg(
            n=('delta_score', 'count'),
            delta_media=('delta_score', 'mean')
        ).reset_index()

        fig = px.bar(
            agg, x='confidence_fixed', y='delta_media', 
            text='n', title='Δ Score Promedio por Nivel de Confianza',
            color='delta_media', color_continuous_scale=px.colors.diverging.RdYlGn
        )
        fig.update_traces(textposition='auto')
        fig.add_hline(y=0, line_dash="dash", line_color="white")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.03)')
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────
tab_a, tab_b, tab_c = st.tabs([
    "🌌 Test 1: Asombro",
    "⚖️ Test 2: Óptimo",
    "⚙️ Test 3: Técnico+Confianza"
])

with tab_a: render_asombro()
with tab_b: render_optimo()
with tab_c: render_tecnico()

st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Puerto 8520")
if st.button("🔄 Forzar Recarga (Manual)"):
    st.rerun()
