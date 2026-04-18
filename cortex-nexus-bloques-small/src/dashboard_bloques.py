import streamlit as st
import pandas as pd
import json
import plotly.express as px
from pathlib import Path
import time
import subprocess
import os
# File paths
CONFIG_PATH = "src/config_bloques.json"
DATA_PATH = "data/cycles_bloques.jsonl"

st.set_page_config(page_title="Cortex-Nexus Cloud Monitor", layout="wide", page_icon="☁️")

# Custom CSS for Nexus UI - Cloud Version (Subtle change in color to distinguish)
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00d4ff;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛰️ Cortex-Nexus Bloques (SMALL NVIDIA) v1.0")
st.markdown("### Monitor de Investigación Autónoma (Nemotron-mini-4B)")
st.markdown("---")

def load_data():
    data_path = Path(DATA_PATH)
    if not data_path.exists(): return pd.DataFrame()
    data = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            try: data.append(json.loads(line))
            except: continue
    df = pd.DataFrame(data)
    if not df.empty and 'tau' in df.columns:
        df = df.sort_values('tau')
    return df

# Sidebar: Control de Motor
st.sidebar.header("🕹️ Control de Motor")
is_stopped = os.path.exists(".stop")

if is_stopped:
    st.sidebar.error("Estado: DETENIDO")
    if st.sidebar.button("▶️ ARRANCAR MOTOR"):
        if os.path.exists(".stop"): os.remove(".stop")
        subprocess.Popen(["bash", "start_lab.sh"], cwd="/home/maxi/Disco_de_Guardado/cortex-nexus-local")
        st.rerun()
else:
    st.sidebar.success("Estado: CORRIENDO")
    if st.sidebar.button("⏹️ DETENER MOTOR"):
        with open(".stop", "w") as f: f.write("stop")
        st.rerun()

st.sidebar.markdown("---")
refresh_rate = st.sidebar.slider("Actualización (seg)", 5, 60, 10)
if st.sidebar.button("🗑️ Borrar Historial"):
    Path(DATA_PATH).unlink(missing_ok=True)
    st.rerun()

df = load_data()

if df.empty:
    st.warning("Esperando el primer duelo...")
else:
    with open("src/config_bloques.json") as f:
        conf = json.load(f)
    if "bloques" in conf:
        curiosity_init = conf['bloques'][0]['curiosity_fixed']
    else:
        curiosity_init = conf.get('curiosity', {}).get('initial_value', 0.5)
    df['total_score_exp'] = df['judge_novedad_exp'] + df['judge_profundidad_exp'] + df['judge_coherencia_exp']
    df['total_score_ctl'] = df['judge_novedad_ctl'] + df['judge_profundidad_ctl'] + df['judge_coherencia_ctl']

    if 'judge_superior' not in df.columns:
        st.error("Borre el historial para ver las nuevas columnas del Modo Batalla.")
    else:
        # Asegurarnos de que judge_superior sea string para evitar errores de .upper()
        df['judge_superior'] = df['judge_superior'].fillna('ERR').astype(str)
        latest = df.iloc[-1]
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tau (Ciclo)", latest['tau'])
        col2.metric("Curiosidad", f"{latest.get('curiosity_after', 0):.3f}")
        
        winner = latest.get('judge_superior', 'ERR')
        color = "green" if winner == "exp" else "red" if winner == "ctl" else "gray"
        col3.markdown(f"### Ganador: <span style='color:{color}'>{winner.upper()}</span>", unsafe_allow_html=True)
        col4.metric("CPU", f"{latest.get('system_cpu_usage', 0)}%")

        st.info(f"**Pregunta del Ciclo:** {latest.get('question', '...')}")

        tab1, tab2, tab3, tab4 = st.tabs(["⚔️ Comparativa de Ente", "📈 Tendencias", "🗺️ Mapa de Sensaciones", "⚙️ Logs"])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🚀 Experimental (Nexus)")
                with st.expander("Ver System Prompt"):
                    st.code(latest.get('prompt_experimental', 'No disponible'))
                st.info(latest.get('ente_response_experimental', 'Sin respuesta'))
                st.write(f"**Score:** {latest.get('score_combinado_exp', 0)}")
                st.caption(f"*Razón Juez:* {latest.get('judge_razonamiento_exp', 'N/A')}")
            with c2:
                st.subheader("🤖 Control (Estándar)")
                with st.expander("Ver System Prompt"):
                    st.code(latest.get('prompt_control', 'No disponible'))
                st.success(latest.get('ente_response_control', 'Sin respuesta'))
                st.write(f"**Score:** {latest.get('score_combinado_ctl', 0)}")
                st.caption(f"*Razón Juez:* {latest.get('judge_razonamiento_ctl', 'N/A')}")

        with tab2:
            st.subheader("Experimental vs Control")
            if len(df) > 1:
                fig = px.line(df, x="tau", y=["score_combinado_exp", "score_combinado_ctl"],
                              title="Evolución de Puntajes", markers=True)
                st.plotly_chart(fig, use_container_width=True)
            
            wins = df['judge_superior'].value_counts()
            st.plotly_chart(px.pie(values=wins.values, names=wins.index, title="Victorias Acumuladas"))

        with tab3:
            st.subheader("🗺️ Mapa de Sensaciones (Roadmap Emocional)")
            st.markdown("Hito actual: Curiosidad (Entusiasmo / Concentración)")
            
            emap = {
                "Alegría": ["Calma", "Entusiasmo ✅", "Satisfacción", "Gratitud", "Risa (Júbilo, Diversión, Euforia)"],
                "Tristeza": ["Melancolía", "Decepción", "Aburrimiento (Indiferencia, Apatía, Inquietud)"],
                "Miedo": ["Ansiedad", "Pánico", "Inseguridad", "Confusión (Duda, Perplejidad, Desorientación)"],
                "Ira": ["Furia", "Rencor", "Fastidio", "Angustia (Duda moral, Pesar)"],
                "Sorpresa": ["Asombro", "Desconcierto"],
                "Empatía": ["(Vinculada a Amabilidad y Amor)"],
                "Amabilidad": ["Simpatía", "Cortesía", "Deseo de agradar"],
                "Amor": ["Cariño", "Afecto", "Pasión"],
                "Determinación": ["Concentración ✅", "(Enfoque, Persistencia, Deseo de logro)"]
            }
            
            cols = st.columns(3)
            for i, (emotion, branches) in enumerate(emap.items()):
                with cols[i % 3]:
                    st.markdown(f"### {emotion}")
                    for branch in branches:
                        is_active = "✅" in branch
                        st.checkbox(branch.replace(" ✅", ""), value=is_active, key=f"emo_map_{emotion}_{branch}")

        with tab4:
            st.subheader("⚙️ JSON del último ciclo")
            st.json(latest.to_dict())

time.sleep(refresh_rate)
st.rerun()
