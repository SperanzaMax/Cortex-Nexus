"""
monitor_2d.py — Dashboard del Experimento 2D: Curiosidad × Frustración
Cortex-Nexus · 2026-04-15 | Maximiliano Rodrigo Speranza

Arranque: streamlit run src/monitor_2d.py --server.port 8509
Celular:  http://192.168.0.88:8509
"""
import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=10 * 1000, key="2d_monitor_refresh")

st.set_page_config(page_title="Cortex-Nexus 2D Monitor", layout="wide")

st.title("🗺️ Monitor de Investigación: Experimento 2D")
st.markdown("**Curiosidad × Frustración** — Mapeando el espacio emocional 2D y sus efectos en el output cognitivo.")

BASE_DIR = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-2d/data"
BIG_PATH = os.path.join(BASE_DIR, "cycles_2d_big.jsonl")
SMALL_PATH = os.path.join(BASE_DIR, "cycles_2d_small.jsonl")

# Orden canónico de los 8 estados 2D
ESTADOS_INFO = {
    "A_apatia":      {"C": 0.20, "F": 0.20, "label": "A: Apatía"},
    "B_exploracion": {"C": 0.95, "F": 0.20, "label": "B: Exploración"},
    "C_bloqueo":     {"C": 0.20, "F": 0.95, "label": "C: Bloqueo"},
    "D_tension":     {"C": 0.95, "F": 0.95, "label": "D: Tensión ★"},
    "E_neutro":      {"C": 0.50, "F": 0.50, "label": "E: Neutro"},
    "F_cur_alta":    {"C": 0.75, "F": 0.35, "label": "F: Cur. alta"},
    "G_frus_alta":   {"C": 0.35, "F": 0.75, "label": "G: Frus. alta"},
    "H_equilibrio":  {"C": 0.75, "F": 0.75, "label": "H: Equilibrio"},
}

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
    return pd.DataFrame(data)


def render_progress_bar(df, title, icon):
    """Barra de progreso global y métricas clave."""
    st.markdown(f"### {icon} {title}")
    if df.empty:
        st.info("Esperando datos del motor...")
        return df

    total = len(df)
    errors = df.get('judge_error', pd.Series([False] * total)).sum()
    last_tau = df['tau'].iloc[-1]
    last_estado = df['estado_2d'].iloc[-1]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("TAU Actual", last_tau, f"/ 240 total")
    with m2:
        st.metric("Estado Actual", last_estado.replace("_", " "))
    with m3:
        pct = round((total / 240) * 100, 1)
        st.metric("Progreso", f"{pct}%", f"{total}/240 ciclos")
    with m4:
        st.metric("Errores Juez", int(errors), f"{round(errors/total*100,1)}%" if total > 0 else "0%")

    return df


def render_2d_heatmap(df, title):
    """El gráfico estrella: heatmap 2D del Δ Score en el espacio Curiosidad × Frustración."""
    st.markdown(f"#### 🗺️ Mapa 2D de Efectos — Δ Score (Exp - Ctl)")

    if df.empty or 'delta_score' not in df.columns:
        st.info("Esperando datos para construir el mapa 2D...")
        return

    # Agregar por estado
    agg = df.groupby('estado_2d').agg(
        delta_mean=('delta_score', 'mean'),
        n=('delta_score', 'count')
    ).reset_index()

    # Enriquecer con coordenadas 2D
    rows = []
    for _, row in agg.iterrows():
        info = ESTADOS_INFO.get(row['estado_2d'], {})
        rows.append({
            'label': info.get('label', row['estado_2d']),
            'C': info.get('C', 0.5),
            'F': info.get('F', 0.5),
            'delta': round(row['delta_mean'], 3),
            'n': int(row['n'])
        })

    if not rows:
        st.info("Sin datos todavía.")
        return

    plot_df = pd.DataFrame(rows)

    # Scatter plot 2D con tamaño = n ciclos, color = delta
    fig = px.scatter(
        plot_df,
        x='C', y='F',
        color='delta',
        size='n',
        text='label',
        size_max=60,
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0,
        labels={'C': 'Curiosidad →', 'F': '← Frustración', 'delta': 'Δ Score'},
        range_x=[-0.05, 1.1],
        range_y=[-0.05, 1.1],
        height=500
    )
    fig.update_traces(
        textposition='top center',
        textfont=dict(size=11)
    )
    fig.update_layout(
        xaxis=dict(tickvals=[0, 0.2, 0.5, 0.75, 0.95], gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(tickvals=[0, 0.2, 0.5, 0.75, 0.95], gridcolor='rgba(128,128,128,0.2)'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.03)',
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla resumen
    st.markdown("**Tabla de Δ Score por Estado:**")
    table_df = plot_df[['label', 'C', 'F', 'delta', 'n']].copy()
    table_df.columns = ['Estado', 'Curiosidad', 'Frustración', 'Δ Score (media)', 'Ciclos']
    table_df = table_df.sort_values('Δ Score (media)', ascending=False)
    st.dataframe(table_df, use_container_width=True, hide_index=True)


def render_pie_charts(df, title):
    """Gráficos de torta por estado — mismo estilo que Asombro y Confianza."""
    st.markdown(f"#### 🥧 Distribución de Resultados por Estado")

    if df.empty:
        st.info("Sin datos aún...")
        return

    # Mostrar en orden canónico, 4 por fila
    estados_orden = list(ESTADOS_INFO.keys())
    cols1 = st.columns(4)
    cols2 = st.columns(4)

    for i, estado in enumerate(estados_orden):
        col = cols1[i] if i < 4 else cols2[i - 4]
        with col:
            info = ESTADOS_INFO[estado]
            st.markdown(f"**{info['label']}**")
            st.markdown(f"<small>C={info['C']} / F={info['F']}</small>", unsafe_allow_html=True)
            df_e = df[df['estado_2d'] == estado]
            if not df_e.empty:
                counts = df_e['judge_superior'].value_counts().reset_index()
                counts.columns = ['Ganador', 'Cantidad']
                fig = px.pie(
                    counts, values='Cantidad', names='Ganador',
                    color='Ganador',
                    color_discrete_map={'exp': '#4ECDC4', 'ctl': '#FF6B6B', 'tie': '#808495'},
                    hole=0.4, height=200
                )
                fig.update_layout(
                    margin=dict(t=5, b=5, l=5, r=5),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="white")
                )
                st.plotly_chart(fig, use_container_width=True)

                avg_d = df_e['delta_score'].mean() if 'delta_score' in df_e.columns else 0
                st.caption(f"Δ={avg_d:+.3f} | n={len(df_e)}")
            else:
                st.caption(f"Esperando ciclos...")


# === RENDER PRINCIPAL ===
df_big = load_data(BIG_PATH)
df_small = load_data(SMALL_PATH)

tab_big, tab_small = st.tabs(["🐘 BIG Engine (Llama 3.3 70B)", "🐭 SMALL Engine (Nemotron 4B)"])

with tab_big:
    df_big = render_progress_bar(df_big, "Llama 3.3 70B (BIG)", "🐘")
    if not df_big.empty:
        render_2d_heatmap(df_big, "BIG")
        st.markdown("---")
        render_pie_charts(df_big, "BIG")

with tab_small:
    df_small = render_progress_bar(df_small, "Nemotron 4B (SMALL)", "🐭")
    if not df_small.empty:
        render_2d_heatmap(df_small, "SMALL")
        st.markdown("---")
        render_pie_charts(df_small, "SMALL")

st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Puerto 8509 | IP: 192.168.0.88")
if st.button("🔄 Forzar Recarga"):
    st.rerun()
