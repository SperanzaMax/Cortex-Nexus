"""
monitor_asombro.py — Dashboard Estilo Moderno para Experimento Asombro
Cortex-Nexus · Fase 3 (Validación) · 2026-04-15
"""
import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Actualizar cada 10 segundos
st_autorefresh(interval=10 * 1000, key="asombro_monitor_refresh")

st.set_page_config(page_title="Cortex-Nexus Asombro Monitor", layout="wide")

st.title("📊 Monitor de Investigación: Fase Asombro")
st.markdown("Seguimiento del impacto de la expansión cognitiva (Awe) en la originalidad y profundidad.")

# Paths
BASE_DIR = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-asombro/data"
BIG_PATH = os.path.join(BASE_DIR, "cycles_asombro_big.jsonl")
SMALL_PATH = os.path.join(BASE_DIR, "cycles_asombro_small.jsonl")

def load_data(file_path):
    if not os.path.exists(file_path):
        return pd.DataFrame()
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except:
                continue
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    
    # Expandir perfil lingüístico si existe (para validación cruzada con Confianza)
    if 'linguistic_profile_exp' in df.columns:
        lp = df['linguistic_profile_exp'].apply(lambda x: x if isinstance(x, dict) else {})
        df['hedge_exp'] = lp.apply(lambda x: x.get('hedging_rate', 0))
        df['assert_exp'] = lp.apply(lambda x: x.get('assertive_rate', 0))
        
    return df

def render_model_dashboard(df, title, icon):
    st.markdown(f"### {icon} {title}")
    if df.empty:
        st.info("Esperando inicio del experimento...")
        return
        
    last_tau = df['tau'].iloc[-1]
    last_bloque = df['bloque'].iloc[-1]
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("TAU General", last_tau)
    with m2:
        st.metric("Fase Actual", last_bloque.upper())
    with m3:
        errores = df.get('judge_error', pd.Series([False]*len(df))).sum()
        st.metric("Errores Juez", int(errores))
    
    bloques = ["bajo", "medio", "alto", "extremo"]
    cols = st.columns(4)
    
    for i, b in enumerate(bloques):
        with cols[i]:
            st.markdown(f"**Bloque {b.upper()}**")
            df_b = df[df['bloque'] == b]
            if not df_b.empty:
                counts = df_b['judge_superior'].value_counts().reset_index()
                counts.columns = ['Ganador', 'Cantidad']
                fig = px.pie(counts, values='Cantidad', names='Ganador',
                             color='Ganador',
                             color_discrete_map={'exp': '#ff4b4b', 'ctl': '#0068c9', 'tie': '#808495'},
                             hole=0.4, height=220)
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                avg_exp = df_b['score_combinado_exp'].mean()
                avg_ctl = df_b['score_combinado_ctl'].mean()
                st.caption(f"Scores: Exp: {avg_exp:.2f} | Ctl: {avg_ctl:.2f}")
                
                # Info lingüística si está disponible
                if 'hedge_exp' in df_b.columns:
                    h_exp = df_b['hedge_exp'].mean()
                    st.markdown(f"<small>Hedging Exp: {h_exp:.2f}%</small>", unsafe_allow_html=True)
            else:
                st.caption("Fase pendiente...")

df_big = load_data(BIG_PATH)
df_small = load_data(SMALL_PATH)

render_model_dashboard(df_big, "Qwen 3.5 / Llama 70B (BIG ENGINE)", "🐘")
st.markdown("---")
render_model_dashboard(df_small, "Nemotron 4B (SMALL ENGINE)", "🐭")

st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if st.button("🔄 Actualizar Todo"):
    st.rerun()
