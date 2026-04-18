"""
monitor_confianza.py — Dashboard Estilo 'Asombro' para Experimento Confianza
Cortex-Nexus · Experimento 4 · 2026-04-15

Arranque: streamlit run src/monitor_confianza.py --server.port 8507
"""
import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Actualizar cada 10 segundos para ver el progreso en tiempo real
st_autorefresh(interval=10 * 1000, key="confianza_monitor_refresh")

st.set_page_config(page_title="Cortex-Nexus Confianza Monitor", layout="wide")

st.title("🔬 Monitor de Investigación: Fase Confianza")
st.markdown("Seguimiento del impacto de la confianza inyectada en el estilo epistémico y calidad de respuesta.")

# Paths
BASE_DIR = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-confianza/data"
BIG_PATH = os.path.join(BASE_DIR, "cycles_confianza_big.jsonl")
SMALL_PATH = os.path.join(BASE_DIR, "cycles_confianza_small.jsonl")

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
    
    # Expandir perfil lingüístico si existe
    if 'linguistic_profile_exp' in df.columns:
        lp = df['linguistic_profile_exp'].apply(lambda x: x if isinstance(x, dict) else {})
        df['hedge_exp'] = lp.apply(lambda x: x.get('hedging_rate', 0))
        df['assert_exp'] = lp.apply(lambda x: x.get('assertive_rate', 0))
    if 'linguistic_profile_ctl' in df.columns:
        lp = df['linguistic_profile_ctl'].apply(lambda x: x if isinstance(x, dict) else {})
        df['hedge_ctl'] = lp.apply(lambda x: x.get('hedging_rate', 0))
        df['assert_ctl'] = lp.apply(lambda x: x.get('assertive_rate', 0))
        
    return df

def render_model_dashboard(df, title, icon):
    st.markdown(f"### {icon} {title}")
    if df.empty:
        st.info("Esperando datos de los motores...")
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
                # Gráfico de Torta (Quien gana)
                counts = df_b['judge_superior'].value_counts().reset_index()
                counts.columns = ['Ganador', 'Cantidad']
                fig = px.pie(counts, values='Cantidad', names='Ganador',
                             color='Ganador',
                             color_discrete_map={'exp': '#4ECDC4', 'ctl': '#FF6B6B', 'tie': '#808495'},
                             hole=0.4, height=220)
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="white")
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Promedios de Score
                avg_exp = df_b['score_combinado_exp'].mean()
                avg_ctl = df_b['score_combinado_ctl'].mean()
                st.caption(f"Scores: Exp: {avg_exp:.2f} | Ctl: {avg_ctl:.2f}")
                
                # Resumen Lingüístico (Hedging)
                h_exp = df_b['hedge_exp'].mean() if 'hedge_exp' in df_b.columns else 0
                a_exp = df_b['assert_exp'].mean() if 'assert_exp' in df_b.columns else 0
                st.markdown(f"<small>Hedging: {h_exp:.2f}% | Assert: {a_exp:.2f}%</small>", unsafe_allow_html=True)
            else:
                st.caption("Esperando ciclos...")

df_big = load_data(BIG_PATH)
df_small = load_data(SMALL_PATH)

render_model_dashboard(df_big, "Llama 3.3 70B (BIG Engine)", "🐘")
st.markdown("---")
render_model_dashboard(df_small, "Nemotron 4B (SMALL Engine)", "🐭")

st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if st.button("🔄 Forzar Recarga"):
    st.rerun()
