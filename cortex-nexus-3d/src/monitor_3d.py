"""
monitor_3d.py — Dashboard del Experimento 3D: Curiosidad × Frustración × Asombro
Cortex-Nexus · 2026-04-16 | Maximiliano Rodrigo Speranza

Arranque: streamlit run src/monitor_3d.py --server.port 8510
Celular:  http://192.168.0.88:8510
"""
import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=10 * 1000, key="3d_monitor_refresh")

st.set_page_config(page_title="Cortex-Nexus 3D Monitor", layout="wide")

st.title("🧊 Monitor de Investigación: Experimento 3D")
st.markdown("**Curiosidad × Frustración × Asombro** — Mapeando el cubo emocional 3D y sus efectos en el output cognitivo.")

BASE_DIR = "/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-3d/data"
BIG_PATH = os.path.join(BASE_DIR, "cycles_3d_big.jsonl")
SMALL_PATH = os.path.join(BASE_DIR, "cycles_3d_small.jsonl")

# Info de los 8 estados 3D (vértices del cubo)
ESTADOS_INFO = {
    "AAA_apatia":     {"C": 0.20, "F": 0.20, "W": 0.20, "label": "AAA: Apatía total",     "emoji": "😶"},
    "BBB_positivo":   {"C": 0.95, "F": 0.20, "W": 0.95, "label": "BBB: Todo positivo",     "emoji": "🚀"},
    "CCC_negativo":   {"C": 0.20, "F": 0.95, "W": 0.20, "label": "CCC: Todo negativo",     "emoji": "🧱"},
    "BXB_curAsom":    {"C": 0.95, "F": 0.20, "W": 0.95, "label": "BXB: Cur+Asom",          "emoji": "✨"},
    "BCX_curFrus":    {"C": 0.95, "F": 0.95, "W": 0.20, "label": "BCX: Cur+Frus",          "emoji": "⚡"},
    "XCB_fruAsom":    {"C": 0.20, "F": 0.95, "W": 0.95, "label": "XCB: Frus+Asom",         "emoji": "🌪️"},
    "MMM_equilibrio": {"C": 0.75, "F": 0.50, "W": 0.75, "label": "MMM: Equilibrio",        "emoji": "⚖️"},
    "BMB_maxima":     {"C": 0.95, "F": 0.95, "W": 0.95, "label": "BMB: Tensión máxima ★",  "emoji": "💥"},
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
    last_estado = df['estado_3d'].iloc[-1]

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


def render_3d_scatter(df, title):
    """Scatter 3D del cubo emocional — color = Δ Score."""
    st.markdown(f"#### 🧊 Cubo 3D de Estados Emocionales — Δ Score (Exp - Ctl)")

    if df.empty or 'delta_score' not in df.columns:
        st.info("Esperando datos para construir el cubo 3D...")
        return

    agg = df.groupby('estado_3d').agg(
        delta_mean=('delta_score', 'mean'),
        n=('delta_score', 'count')
    ).reset_index()

    rows = []
    for _, row in agg.iterrows():
        info = ESTADOS_INFO.get(row['estado_3d'], {})
        rows.append({
            'label': info.get('label', row['estado_3d']),
            'C': info.get('C', 0.5),
            'F': info.get('F', 0.5),
            'W': info.get('W', 0.5),
            'delta': round(row['delta_mean'], 3),
            'n': int(row['n'])
        })

    if not rows:
        st.info("Sin datos todavía.")
        return

    plot_df = pd.DataFrame(rows)

    # Scatter 3D
    fig = px.scatter_3d(
        plot_df,
        x='C', y='F', z='W',
        color='delta',
        size='n',
        text='label',
        size_max=40,
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0,
        labels={
            'C': 'Curiosidad →',
            'F': 'Frustración →',
            'W': 'Asombro →',
            'delta': 'Δ Score'
        },
        height=600
    )
    fig.update_traces(textposition='top center', textfont=dict(size=10))
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[0, 1.1], tickvals=[0.2, 0.5, 0.75, 0.95]),
            yaxis=dict(range=[0, 1.1], tickvals=[0.2, 0.5, 0.75, 0.95]),
            zaxis=dict(range=[0, 1.1], tickvals=[0.2, 0.5, 0.75, 0.95]),
        ),
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla resumen
    st.markdown("**Tabla de Δ Score por Estado:**")
    table_df = plot_df[['label', 'C', 'F', 'W', 'delta', 'n']].copy()
    table_df.columns = ['Estado', 'Curiosidad', 'Frustración', 'Asombro', 'Δ Score (media)', 'Ciclos']
    table_df = table_df.sort_values('Δ Score (media)', ascending=False)
    st.dataframe(table_df, use_container_width=True, hide_index=True)


def render_bar_chart(df, title):
    """Barras horizontales comparativas por estado."""
    st.markdown(f"#### 📊 Δ Score Comparativo por Estado")

    if df.empty or 'delta_score' not in df.columns:
        st.info("Esperando datos...")
        return

    agg = df.groupby('estado_3d').agg(
        delta_mean=('delta_score', 'mean'),
        n=('delta_score', 'count')
    ).reset_index()

    rows = []
    for _, row in agg.iterrows():
        info = ESTADOS_INFO.get(row['estado_3d'], {})
        rows.append({
            'label': info.get('label', row['estado_3d']),
            'delta': round(row['delta_mean'], 3),
            'n': int(row['n']),
            'color': '#4ECDC4' if row['delta_mean'] >= 0 else '#FF6B6B'
        })

    plot_df = pd.DataFrame(rows).sort_values('delta', ascending=True)

    fig = go.Figure(go.Bar(
        x=plot_df['delta'],
        y=plot_df['label'],
        orientation='h',
        marker_color=['#4ECDC4' if d >= 0 else '#FF6B6B' for d in plot_df['delta']],
        text=[f"Δ={d:+.3f} (n={n})" for d, n in zip(plot_df['delta'], plot_df['n'])],
        textposition='outside'
    ))
    fig.update_layout(
        height=400,
        xaxis_title="Δ Score (Exp - Ctl)",
        yaxis_title="",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.03)',
    )
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)


def render_pie_charts(df, title):
    """Gráficos de torta por estado — mismo estilo que 2D."""
    st.markdown(f"#### 🥧 Distribución de Resultados por Estado")

    if df.empty:
        st.info("Sin datos aún...")
        return

    estados_orden = list(ESTADOS_INFO.keys())
    cols1 = st.columns(4)
    cols2 = st.columns(4)

    for i, estado in enumerate(estados_orden):
        col = cols1[i] if i < 4 else cols2[i - 4]
        with col:
            info = ESTADOS_INFO[estado]
            st.markdown(f"**{info['emoji']} {info['label']}**")
            st.markdown(f"<small>C={info['C']} F={info['F']} W={info['W']}</small>", unsafe_allow_html=True)
            df_e = df[df['estado_3d'] == estado]
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
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{title}_{estado}")

                avg_d = df_e['delta_score'].mean() if 'delta_score' in df_e.columns else 0
                st.caption(f"Δ={avg_d:+.3f} | n={len(df_e)}")
            else:
                st.caption(f"Esperando ciclos...")


def render_timeline(df, title):
    """Timeline de Δ Score a lo largo del tiempo."""
    st.markdown(f"#### 📈 Timeline — Δ Score por Ciclo")

    if df.empty or 'delta_score' not in df.columns:
        st.info("Esperando datos...")
        return

    fig = px.scatter(
        df, x='tau', y='delta_score',
        color='estado_3d',
        labels={'tau': 'TAU (ciclo)', 'delta_score': 'Δ Score', 'estado_3d': 'Estado'},
        height=350,
        opacity=0.7
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.03)',
    )
    st.plotly_chart(fig, use_container_width=True)


# === RENDER PRINCIPAL ===
df_big = load_data(BIG_PATH)
df_small = load_data(SMALL_PATH)

tab_big, tab_small = st.tabs(["🐘 BIG Engine (Llama 3.3 70B)", "🐭 SMALL Engine (Nemotron 4B)"])

with tab_big:
    df_big = render_progress_bar(df_big, "Llama 3.3 70B (BIG)", "🐘")
    if not df_big.empty:
        render_3d_scatter(df_big, "BIG")
        st.markdown("---")
        render_bar_chart(df_big, "BIG")
        st.markdown("---")
        render_pie_charts(df_big, "BIG")
        st.markdown("---")
        render_timeline(df_big, "BIG")

with tab_small:
    df_small = render_progress_bar(df_small, "Nemotron 4B (SMALL)", "🐭")
    if not df_small.empty:
        render_3d_scatter(df_small, "SMALL")
        st.markdown("---")
        render_bar_chart(df_small, "SMALL")
        st.markdown("---")
        render_pie_charts(df_small, "SMALL")
        st.markdown("---")
        render_timeline(df_small, "SMALL")

st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Puerto 8510 | IP: 192.168.0.88")
if st.button("🔄 Forzar Recarga"):
    st.rerun()
