import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Actualizar cada 10 segundos
st_autorefresh(interval=10 * 1000, key="frustration_monitor_refresh")

st.set_page_config(page_title="Cortex-Nexus Frustración Monitor", layout="wide")

st.title("📊 Monitor de Investigación: Fase Frustración")
st.markdown("Seguimiento en tiempo real de los experimentos BIG (405B) y SMALL (4B)")

# Paths
BASE_DIR = "/home/maxi/Disco_de_Guardado/cortex-nexus-frustracion/data"
BIG_PATH = os.path.join(BASE_DIR, "cycles_frustracion_big.jsonl")
SMALL_PATH = os.path.join(BASE_DIR, "cycles_frustracion_small.jsonl")

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
    return pd.DataFrame(data)

# Layout
col1, col2 = st.columns(2)

# --- Experiment BIG ---
with col1:
    st.markdown("### 🐘 Qwen 3.5 Flash 405B")
    df_big = load_data(BIG_PATH)
    if not df_big.empty:
        last_tau = df_big['tau'].max()
        last_bloque = df_big['bloque'].iloc[-1]
        
        st.metric(f"TAU: {last_tau}", f"Bloque: {last_bloque}")
        
        counts = df_big['judge_superior'].value_counts().reset_index()
        counts.columns = ['Ganador', 'Cantidad']
        fig = px.pie(counts, values='Cantidad', names='Ganador', 
                     color='Ganador',
                     color_discrete_map={'exp': '#ff4b4b', 'ctl': '#0068c9', 'tie': '#808495'},
                     hole=0.4, height=250)
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
        
        avg_exp = df_big['score_combinado_exp'].mean()
        avg_ctl = df_big['score_combinado_ctl'].mean()
        st.caption(f"**Promedio:** Exp: {avg_exp:.2f} | Ctl: {avg_ctl:.2f}")
    else:
        st.info("Esperando datos de BIG...")

# --- Experiment SMALL ---
with col2:
    st.markdown("### 🐭 Nemotron 4B")
    df_small = load_data(SMALL_PATH)
    if not df_small.empty:
        last_tau = df_small['tau'].max()
        last_bloque = df_small['bloque'].iloc[-1]
        
        st.metric(f"TAU: {last_tau}", f"Bloque: {last_bloque}")
        
        counts = df_small['judge_superior'].value_counts().reset_index()
        counts.columns = ['Ganador', 'Cantidad']
        fig = px.pie(counts, values='Cantidad', names='Ganador',
                     color='Ganador',
                     color_discrete_map={'exp': '#ff4b4b', 'ctl': '#0068c9', 'tie': '#808495'},
                     hole=0.4, height=250)
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

        avg_exp = df_small['score_combinado_exp'].mean()
        avg_ctl = df_small['score_combinado_ctl'].mean()
        st.caption(f"**Promedio:** Exp: {avg_exp:.2f} | Ctl: {avg_ctl:.2f}")
    else:
        st.info("Esperando datos de SMALL...")

# Auto-refresh
st.empty()
if st.button("🔄 Actualizar"):
    st.rerun()

st.markdown("---")
st.caption(f"Última actualización local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
