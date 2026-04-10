from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
import httpx, json
import time
import hashlib
import datetime
import asyncio
from contextlib import asynccontextmanager
import sys
import os
import sqlite3
import re

# Configuración del Sistema Emocional
DB_PATH = "/tmp/cma_memory.db"

# Restauración Automática desde HF Datasets
def _restore_from_backup():
    try:
        # Solo restaurar si la base de datos no existe aún o configurando inicio limpio
        if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 10000:
            print("[RESTORE] La DB ya existe con datos en el entorno local. Saltando descarga.")
            return
            
        token = os.getenv("HF_TOKEN")
        if not token: 
            print("[RESTORE] HF_TOKEN no encontrado. Saltando restauración.")
            return
            
        import huggingface_hub
        import shutil
        
        print("[RESTORE] Intentando restaurar DB desde HF Datasets...")
        downloaded_path = huggingface_hub.hf_hub_download(
            repo_id="SperanzaMax/Cortex-Memory-Bank",
            repo_type="dataset",
            filename="cma_memory_latest.db",
            token=token
        )
        
        if os.path.exists(downloaded_path):
            shutil.copy2(downloaded_path, DB_PATH)
            print(f"[RESTORE] DB restaurada con éxito desde Dataset: {downloaded_path}")
            
    except Exception as e:
        print(f"[RESTORE] No se pudo restaurar la DB (backup inexistente o error). Iniciando vacía. Error: {e}")

_restore_from_backup()

# Crear tabla de eventos de sueño si no existe
def _init_sleep_table():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""CREATE TABLE IF NOT EXISTS sleep_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            antes TEXT, despues TEXT, drift TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS control_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            pregunta TEXT, respuesta_nexus TEXT, respuesta_control TEXT,
            novedad_nexus REAL, novedad_control REAL,
            complejidad_nexus REAL, complejidad_control REAL
        )""")
        conn.commit()
        conn.close()
    except:
        pass

_init_sleep_table()

# Intentar importar los núcleos emocionales
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), "core"))
    from core.vector_emocional import VectorEmocional
    from core.modulador import ModuladorParametrico
    vector_global = VectorEmocional(db_path=DB_PATH)
    modulador_global = ModuladorParametrico()
except Exception as e:
    import traceback
    print(f"CRITICAL ERROR cargando núcleos: {e}")
    print(traceback.format_exc())
    # Fallbacks prevent NameErrors but will show in logs
    vector_global = None
    modulador_global = None

try:
    import interrogador_perpetuo
except Exception as e:
    print(f"Error importando interrogador_perpetuo: {e}")
    interrogador_perpetuo = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    if interrogador_perpetuo:
        # Iniciar interrogador en background thread
        asyncio.create_task(asyncio.to_thread(interrogador_perpetuo.loop_infinito))
    yield
    # Detener loop al apagar
    if interrogador_perpetuo:
        interrogador_perpetuo.GLOBAL_CONFIG["enabled"] = False

app = FastAPI(lifespan=lifespan)

@app.get("/api/config")
async def get_config():
    """Obtiene la configuración global del interrogador"""
    if interrogador_perpetuo:
        return interrogador_perpetuo.GLOBAL_CONFIG
    return {"error": "Interrogador no disponible"}

@app.post("/api/config")
async def update_config(request: Request):
    """Actualiza la velocidad y configuración del interrogador"""
    if not interrogador_perpetuo:
        return {"error": "Interrogador no disponible"}
    try:
        data = await request.json()
        if "speed_multiplier" in data:
            interrogador_perpetuo.GLOBAL_CONFIG["speed_multiplier"] = float(data["speed_multiplier"])
        if "auto_sleep_epochs" in data:
            interrogador_perpetuo.GLOBAL_CONFIG["auto_sleep_epochs"] = int(data["auto_sleep_epochs"])
        if "enabled" in data:
            interrogador_perpetuo.GLOBAL_CONFIG["enabled"] = bool(data["enabled"])
        return interrogador_perpetuo.GLOBAL_CONFIG
    except Exception as e:
        return {"error": str(e)}

@app.get("/status")
async def reach():
    """Diagnóstico del motor emocional"""
    v_estado = vector_global.obtener_estado() if vector_global else {"error": "Vector no inicializado"}
    return {
        "status": "Cortex-Nexus is Alive", 
        "vector_active": vector_global is not None,
        "emotional_state": v_estado,
        "db_path": DB_PATH,
        "db_exists": os.path.exists(DB_PATH)
    }

@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Sirve el Dashboard en la raíz del sitio"""
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Cortex-Nexus | Live Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3"></script>
        <style>
            body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #334155; }
            h1 { color: #38bdf8; text-align: center; font-size: 1.8rem; letter-spacing: -0.025em; }
            .stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 20px; }
            .stat-box { background: #334155; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #475569; }
            .stat-label { font-size: 0.75rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; }
            .stat-value { font-size: 1.5rem; font-weight: 800; color: #38bdf8; margin-top: 5px; }
            .status-dot { height: 10px; width: 10px; background-color: #10b981; border-radius: 50%; display: inline-block; margin-right: 8px; }
            .nav { display: flex; justify-content: center; gap: 12px; margin-bottom: 16px; }
            .nav a { color: #94a3b8; text-decoration: none; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; background: #334155; }
            .nav a.active, .nav a:hover { background: #38bdf8; color: #fff; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/" class="active">🧠 Live</a>
                <a href="/analytics">🔬 Analytics</a>
            </div>
            <p style="text-align: center; font-size: 0.8rem; color: #64748b;"><span class="status-dot"></span> SISTEMA ONLINE</p>
            <h1>Córtex-Nexus Live</h1>
            <div class="stats" style="grid-template-columns: 1fr 1fr 1fr 1fr;">
                <div class="stat-box"><div class="stat-label">EPOCAS</div><div class="stat-value" id="val-epocas">0</div></div>
                <div class="stat-box"><div class="stat-label">QUALIA</div><div class="stat-value" id="val-qualia">0.000</div></div>
                <div class="stat-box"><div class="stat-label">CONFIANZA</div><div class="stat-value" id="val-confianza">0.000</div></div>
                <div class="stat-box"><div class="stat-label">SUEÑOS 😴</div><div class="stat-value" id="val-sleeps" style="color:#a78bfa;">0</div></div>
            </div>
            
            <div class="card" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <h2 style="color: #38bdf8; font-size: 1rem; margin: 0;">⏱️ Velocidad del Interrogador</h2>
                    <p style="font-size: 0.7rem; color: #94a3b8; margin-top: 4px;">Acelera o pausa los ciclos autónomos.</p>
                </div>
                <div style="display:flex; gap:8px;">
                    <button id="btn-1" class="btn-speed" data-color="#38bdf8" style="padding:6px 12px; border-radius:8px; border:1px solid #38bdf8; background:transparent; color:#38bdf8; cursor:pointer; transition:background 0.2s;" onclick="setSpeed(1)">1x</button>
                    <button id="btn-2" class="btn-speed" data-color="#38bdf8" style="padding:6px 12px; border-radius:8px; border:1px solid #38bdf8; background:transparent; color:#38bdf8; cursor:pointer; transition:background 0.2s;" onclick="setSpeed(2)">2x</button>
                    <button id="btn-5" class="btn-speed" data-color="#38bdf8" style="padding:6px 12px; border-radius:8px; border:1px solid #38bdf8; background:transparent; color:#38bdf8; cursor:pointer; transition:background 0.2s;" onclick="setSpeed(5)">5x</button>
                    <button id="btn-p" class="btn-speed" data-color="#a78bfa" style="padding:6px 12px; border-radius:8px; border:1px solid #a78bfa; background:transparent; color:#a78bfa; cursor:pointer; transition:background 0.2s;" onclick="setSpeed(0)">⏸️ Pausa</button>
                </div>
            </div>

            <div class="card">
                <canvas id="emotionChart"></canvas>
            </div>
            <p style="text-align: center; font-size: 0.7rem; color: #475569;">Arquitectura Emocional v3.0 • Maxi Speranza</p>
            
            <div class="card">
                <h2 style="color: #38bdf8; font-size: 1rem; margin: 0 0 10px 0;">📝 Últimas Interacciones</h2>
                <div id="log-box" style="max-height: 200px; overflow-y: auto; font-size: 0.75rem; color: #94a3b8; line-height: 1.6;">Cargando...</div>
            </div>
        </div>

        <script>
            const ctx = document.getElementById('emotionChart').getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'Curiosidad (Qualia)', borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)', data: [], tension: 0.4, fill: true },
                        { label: 'Frustración', borderColor: '#ef4444', data: [], tension: 0.4 },
                        { label: 'Confianza', borderColor: '#10b981', data: [], tension: 0.4 }
                    ]
                },
                options: { 
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: { 
                        y: { beginAtZero: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }, 
                        x: { display: true, grid: { color: 'rgba(51, 65, 85, 0.4)' }, ticks: { color: '#94a3b8', maxTicksLimit: 10 }, title: { display: true, text: 'Últimas 24hs (Tiempo Real)', color: '#94a3b8' } } 
                    },
                    plugins: { 
                        legend: { position: 'bottom', labels: { color: '#f8fafc', padding: 20 } },
                        annotation: { annotations: {} }
                    }
                }
            });

            async function setSpeed(mult) {
                const enabled = mult > 0;
                const m = mult === 0 ? 1 : mult;
                try {
                    await fetch('/api/config', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({speed_multiplier: m, enabled: enabled})
                    });
                    if(enabled) {
                        alert(`Velocidad multiplicada a ${m}x`);
                    } else {
                        alert(`Loop Autónomo pausado`);
                    }
                } catch(e) { alert("Error estableciendo configuración"); }
            }

            async function updateData() {
                try {
                    const res = await fetch('/api/history');
                    const jsonRes = await res.json();
                    
                    if (jsonRes.error) {
                        console.error("API Error:", jsonRes);
                        return;
                    }

                    if (jsonRes.config) {
                        const m = jsonRes.config.speed_multiplier;
                        const en = jsonRes.config.enabled;
                        document.querySelectorAll('.btn-speed').forEach(b => {
                            b.style.backgroundColor = 'transparent';
                            b.style.color = b.getAttribute('data-color');
                        });
                        
                        let activeId = '';
                        if (!en) activeId = 'btn-p';
                        else if (m === 1) activeId = 'btn-1';
                        else if (m === 2) activeId = 'btn-2';
                        else if (m === 5) activeId = 'btn-5';

                        if (activeId) {
                            const btn = document.getElementById(activeId);
                            btn.style.backgroundColor = btn.getAttribute('data-color');
                            btn.style.color = '#000';
                        }
                    }
                    
                    const data = jsonRes.history;
                    if (data && data.length > 0) {
                        const latest = data[data.length - 1];
                        document.getElementById('val-epocas').innerText = jsonRes.total_epocas;
                        document.getElementById('val-qualia').innerText = parseFloat(latest.qualia).toFixed(3);
                        document.getElementById('val-confianza').innerText = parseFloat(latest.confianza).toFixed(3);
                        document.getElementById('val-sleeps').innerText = jsonRes.total_sleeps || 0;
                        
                        const labels = data.map(d => {
                            let t = new Date(d.timestamp);
                            t.setHours(t.getHours() - 3);
                            return t.toLocaleTimeString('es-AR', {hour: '2-digit', minute: '2-digit'});
                        });
                        chart.data.labels = labels;
                        chart.data.datasets[0].data = data.map(d => d.qualia);
                        chart.data.datasets[1].data = data.map(d => d.frustracion);
                        chart.data.datasets[2].data = data.map(d => d.confianza);
                        
                        // Marcadores de sueño
                        const sleepAnnotations = {};
                        (jsonRes.sleep_events || []).forEach((st, i) => {
                            let sleepDate = new Date(st);
                            sleepDate.setHours(sleepDate.getHours() - 3);
                            let sleepLabel = sleepDate.toLocaleTimeString('es-AR', {hour:'2-digit', minute:'2-digit'});
                            let idx = labels.findIndex(l => l === sleepLabel);
                            if (idx === -1) idx = labels.length - 1;
                            sleepAnnotations['sleep'+i] = {
                                type: 'line', xMin: idx, xMax: idx,
                                borderColor: '#a78bfa', borderWidth: 2, borderDash: [6, 3],
                                label: { display: true, content: '😴', position: 'start', font: { size: 14 } }
                            };
                        });
                        chart.options.plugins.annotation.annotations = sleepAnnotations;
                        chart.update('none');
                    }
                    
                    // Cargar logs y comparativas contra el grupo de control
                    const logRes = await fetch('/api/control');
                    const logData = await logRes.json();
                    if (logData.comparisons && logData.comparisons.length > 0) {
                        const logBox = document.getElementById('log-box');
                        logBox.innerHTML = logData.comparisons.map(l => 
                            `<div style='margin-bottom:8px; border-bottom:1px solid #334155; padding-bottom:6px;'>
                                <span style='color:#f59e0b;'>❓</span> ${l.pregunta.substring(0,80)}...<br>
                                <div style="display:flex; gap:10px; margin-top:4px;">
                                    <div style="flex:1; border-left:2px solid #38bdf8; padding-left:5px;">
                                        <span style="color:#38bdf8; font-size:0.65rem; font-weight:bold;">NEXUS (Emocional)</span><br>
                                        <span style='color:#10b981;'>💬</span> ${(l.respuesta_nexus||'').substring(0,100)}...<br>
                                        <span style="font-size:0.6rem; color:#94a3b8;">Novedad: ${Number(l.novedad_nexus).toFixed(2)} | Cplx: ${Number(l.complejidad_nexus).toFixed(2)}</span>
                                    </div>
                                    <div style="flex:1; border-left:2px solid #94a3b8; padding-left:5px;">
                                        <span style="color:#94a3b8; font-size:0.65rem; font-weight:bold;">GROQ (Base Control)</span><br>
                                        <span style='color:#94a3b8;'>💬</span> ${(l.respuesta_control||'').substring(0,100)}...<br>
                                        <span style="font-size:0.6rem; color:#94a3b8;">Novedad: ${Number(l.novedad_control).toFixed(2)} | Cplx: ${Number(l.complejidad_control).toFixed(2)}</span>
                                    </div>
                                </div>
                            </div>`
                        ).join('');
                    }
                } catch(e) { console.error("Error cargando datos:", e); }
            }

            setInterval(updateData, 4000);
            updateData();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/history")
async def get_history():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Obtener cuenta total de épocas
        cursor.execute("SELECT COUNT(*) FROM snapshots")
        total_epocas = cursor.fetchone()[0]
        
        # Últimas 24 horas de datos
        since = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat()
        cursor.execute("SELECT timestamp, qualia, frustracion, autoConfianza AS confianza, fatiga FROM snapshots WHERE timestamp > ? ORDER BY id ASC", (since,))
        rows = cursor.fetchall()
        
        # Eventos de sueño
        sleep_events = []
        try:
            cursor.execute("SELECT timestamp FROM sleep_events WHERE timestamp > ? ORDER BY id ASC", (since,))
            sleep_events = [dict(r)["timestamp"] for r in cursor.fetchall()]
        except:
            pass
        
        # Total de sueños
        total_sleeps = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM sleep_events")
            total_sleeps = cursor.fetchone()[0]
        except:
            pass
        
        conn.close()
        
        return {
            "total_epocas": total_epocas,
            "total_sleeps": total_sleeps,
            "sleep_events": sleep_events,
            "history": [dict(r) for r in rows],
            "config": GLOBAL_CONFIG
        }
    except Exception as e:
        return {"error": str(e), "msg": "Error leyendo historial"}

@app.get("/api/logs")
async def get_logs():
    """Devuelve las últimas interacciones con preguntas y respuestas"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, metadata FROM snapshots WHERE metadata != '{}' ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for r in rows:
            try:
                meta = json.loads(r["metadata"])
                logs.append({
                    "epoca": r["id"],
                    "timestamp": r["timestamp"],
                    "pregunta": meta.get("pregunta", "N/A"),
                    "respuesta": meta.get("respuesta", "N/A"),
                    "novedad": round(meta.get("novedad", 0), 3),
                    "complejidad": round(meta.get("complejidad", 0), 3)
                })
            except:
                continue
        return {"logs": logs[::-1]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    GROQ_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_KEY:
        return JSONResponse(status_code=500, content={"error": "Falta GROQ_API_KEY en los Secrets de HF"})

    body = await request.json()
    
    # Extraer pregunta original para logging
    mensajes = body.get("messages", [])
    pregunta_original = mensajes[-1].get("content", "") if mensajes else ""
    
    config = modulador_global.modular(vector_global)
    
    openai_body = {
        "model": body.get("model", "llama-3.1-8b-instant"),
        "messages": mensajes,
        "temperature": config.get("temperature", 0.7),
        "top_p": config.get("top_p", 0.9)
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
            r = await client.post("https://api.groq.com/openai/v1/chat/completions", json=openai_body, headers=headers)
        
        resp_json = r.json()
        texto = resp_json["choices"][0]["message"].get("content", "")
        
        # ====== SEÑALES REALES (no hardcodeadas) ======
        # Novedad: basada en diversidad léxica (type-token ratio)
        palabras = re.findall(r'\w+', texto.lower())
        tipo_token = len(set(palabras)) / max(len(palabras), 1)
        novedad_real = min(tipo_token * 1.2, 1.0)  # TTR escalado
        
        # Complejidad: largo promedio de oraciones + palabras únicas
        oraciones = [s for s in re.split(r'[.!?]', texto) if s.strip()]
        largo_prom = sum(len(s.split()) for s in oraciones) / max(len(oraciones), 1)
        complejidad_real = min(largo_prom / 25.0, 1.0)  # Normalizado a ~25 palabras
        
        # Confianza: ausencia de hedging ("quizás", "tal vez", "no estoy seguro")
        hedges = len(re.findall(r'(quizás|tal vez|no estoy segur|podría ser|es posible|maybe|perhaps)', texto.lower()))
        confianza_real = max(0.3, 1.0 - (hedges * 0.15))
        
        # Éxito: si la respuesta tiene sustancia (más de 20 palabras)
        exito_real = len(palabras) > 20
        
        senales = {
            "novedad": novedad_real,
            "complejidad": complejidad_real,
            "confianza_real": confianza_real,
            "confianza_esperada": 0.6,
            "exito_tarea": exito_real
        }
        
        vector_global.actualizar(senales, utilidad_externa=novedad_real * 0.8)
        vector_global.persistir_snapshot(metadata={
            "source": "api",
            "pregunta": pregunta_original[:200],
            "respuesta": texto[:300],
            "novedad": round(novedad_real, 3),
            "complejidad": round(complejidad_real, 3),
            "confianza": round(confianza_real, 3)
        })
        
        return resp_json
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# ANALYTICS API
# ============================================================

import math
import csv
import io
from fastapi.responses import StreamingResponse

def _get_snapshots(limit=None, hours=None):
    """Helper: obtiene snapshots con filtro opcional de tiempo"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if hours:
        since = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).isoformat()
        c.execute("SELECT * FROM snapshots WHERE timestamp > ? ORDER BY id ASC", (since,))
    elif limit:
        c.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT ?", (limit,))
    else:
        c.execute("SELECT * FROM snapshots ORDER BY id ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows if not limit or hours else rows[::-1]

def _calc_stats(values):
    """Calcula media, std, min, max, tendencia de una lista de floats"""
    if not values:
        return {"mean": 0, "std": 0, "min": 0, "max": 0, "trend": 0}
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / max(n - 1, 1)
    std = math.sqrt(variance)
    # Tendencia: pendiente de regresión lineal simple
    if n > 1:
        x_mean = (n - 1) / 2
        num = sum((i - x_mean) * (v - mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        trend = num / den if den != 0 else 0
    else:
        trend = 0
    return {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "trend": round(trend, 6)
    }

def _detect_patterns(rows):
    """Detecta patrones activos en los datos"""
    patterns = []
    if len(rows) < 5:
        return patterns
    
    qualias = [r["qualia"] for r in rows]
    frustraciones = [r["frustracion"] for r in rows]
    fatigas = [r["fatiga"] for r in rows]
    confianzas = [r["autoConfianza"] for r in rows]
    
    # Meseta emocional: volatilidad < 0.01 en últimas 50 épocas  
    recent_q = qualias[-min(50, len(qualias)):]
    if len(recent_q) > 10:
        vol = _calc_stats(recent_q)["std"]
        if vol < 0.01:
            patterns.append({"type": "MESETA", "severity": "warning", "msg": f"Qualia estancado (vol={vol:.4f}). Necesita estímulos nuevos."})
    
    # Ciclo de frustración: frustración sube >3x en ventana de 20
    if len(frustraciones) >= 20:
        inicio = sum(frustraciones[-20:-15]) / 5 if frustraciones[-20:-15] else 0.001
        fin = sum(frustraciones[-5:]) / 5
        if inicio > 0.001 and fin / max(inicio, 0.001) > 3:
            patterns.append({"type": "FRUSTRACION_CICLO", "severity": "danger", "msg": f"Frustración se triplicó en 20 épocas ({inicio:.3f}→{fin:.3f})"})
    
    # Wireheading: qualia sube monótonamente sin caídas
    if len(qualias) >= 20:
        increases = sum(1 for i in range(1, min(20, len(qualias))) if qualias[-i] >= qualias[-i-1])
        if increases >= 18:
            patterns.append({"type": "WIREHEADING", "severity": "danger", "msg": "Qualia sube sin parar. Anti-wireheading podría estar fallando."})
    
    # Fatiga terminal: fatiga > 0.8 sostenida
    if len(fatigas) >= 10:
        high_fatigue = sum(1 for f in fatigas[-10:] if f > 0.8)
        if high_fatigue >= 8:
            patterns.append({"type": "FATIGA_TERMINAL", "severity": "danger", "msg": "Fatiga crítica. El sistema necesita 'dormir' (consolidación)."})
    
    # Personalidad emergente (positivo): drift > 5% en confianza
    if len(confianzas) >= 50:
        inicio_c = sum(confianzas[:10]) / 10
        fin_c = sum(confianzas[-10:]) / 10
        drift = abs(fin_c - inicio_c) / max(inicio_c, 0.001)
        if drift > 0.05:
            direction = "↑" if fin_c > inicio_c else "↓"
            patterns.append({"type": "PERSONALIDAD_EMERGENTE", "severity": "success", "msg": f"Drift de confianza {direction} ({inicio_c:.3f}→{fin_c:.3f}, {drift*100:.1f}%)"})
    
    return patterns

@app.get("/api/analytics")
async def get_analytics():
    """Métricas derivadas con ventanas temporales"""
    try:
        windows = {}
        for label, hours in [("1h", 1), ("6h", 6), ("24h", 24), ("7d", 168)]:
            rows = _get_snapshots(hours=hours)
            if not rows:
                windows[label] = {"count": 0, "metrics": {}}
                continue
            
            metrics = {}
            for col in ["qualia", "frustracion", "autoConfianza", "fatiga", "aburrimiento"]:
                vals = [r.get(col, 0) for r in rows]
                metrics[col] = _calc_stats(vals)
            
            # Métricas derivadas
            qualias = [r.get("qualia", 0) for r in rows]
            fatigas = [r.get("fatiga", 0) for r in rows]
            ratios = [q / max(f, 0.01) for q, f in zip(qualias, fatigas)]
            metrics["ratio_qualia_fatiga"] = _calc_stats(ratios)
            
            # Entropía emocional (Shannon)
            entropies = []
            for r in rows:
                vec = [max(r.get(k, 0.001), 0.001) for k in ["qualia", "frustracion", "autoConfianza", "fatiga", "aburrimiento"]]
                total = sum(vec)
                probs = [v / total for v in vec]
                entropy = -sum(p * math.log2(p) for p in probs if p > 0)
                entropies.append(entropy)
            metrics["entropia_emocional"] = _calc_stats(entropies)
            
            windows[label] = {"count": len(rows), "metrics": metrics}
        
        # Patrones activos
        all_rows = _get_snapshots(hours=24)
        patterns = _detect_patterns(all_rows)
        
        # Arquetipo actual
        arquetipo = {}
        if vector_global and vector_global.memoria:
            arquetipo = vector_global.memoria.cargar_meta_vector()
        
        return {
            "windows": windows,
            "patterns": patterns,
            "arquetipo": arquetipo,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/export")
async def export_csv():
    """Exporta todos los snapshots como CSV descargable"""
    try:
        rows = _get_snapshots()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "qualia", "satisfaccion", "frustracion", "aburrimiento", "autoConfianza", "fatiga", "pregunta", "respuesta", "novedad", "complejidad"])
        
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r.get("metadata", "{}"))
            except:
                pass
            writer.writerow([
                r.get("id", ""), r.get("timestamp", ""),
                r.get("qualia", 0), r.get("satisfaccion", 0),
                r.get("frustracion", 0), r.get("aburrimiento", 0),
                r.get("autoConfianza", 0), r.get("fatiga", 0),
                meta.get("pregunta", ""), meta.get("respuesta", ""),
                meta.get("novedad", ""), meta.get("complejidad", "")
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=cortex_nexus_export_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/backup")
async def backup_to_hf_dataset():
    """Realiza un backup seguro de la SQLite local a un Dataset remoto de HF Space"""
    try:
        from huggingface_hub import HfApi
        token = os.getenv("HF_TOKEN")
        if not token:
            return {"error": "HF_TOKEN no configurado. Imposible respaldar."}
            
        api = HfApi(token=token)
        repo_id = "SperanzaMax/Cortex-Memory-Bank"
        
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=True)
        except Exception:
            pass
            
        timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename_in_repo = f"cma_memory_backup_{timestamp_str}.db"
        
        api.upload_file(
            path_or_fileobj=DB_PATH,
            path_in_repo="cma_memory_latest.db",
            repo_id=repo_id,
            repo_type="dataset"
        )
        api.upload_file(
            path_or_fileobj=DB_PATH,
            path_in_repo=filename_in_repo,
            repo_id=repo_id,
            repo_type="dataset"
        )
        return {"status": "Backup exitoso", "file": filename_in_repo}
    except Exception as e:
        return {"error": f"Error de respaldo: {str(e)}"}

@app.get("/api/report")
async def auto_report(period: int = 7):
    """Genera un reporte analítico usando Llama-3-8B de Groq basado en los últimos N días."""
    try:
        # Calcular estadísticas crudas
        rows = _get_snapshots(hours=period * 24)
        if not rows:
            return {"error": f"Sin datos para {period} días"}
            
        qualias = [r.get("qualia", 0) for r in rows]
        fatigas = [r.get("fatiga", 0) for r in rows]
        
        resumen_estadistico = f"Se evaluaron {len(rows)} épocas en los últimos {period} días. "
        resumen_estadistico += f"Media Qualia: {sum(qualias)/len(qualias):.3f}. "
        resumen_estadistico += f"Media Fatiga: {sum(fatigas)/len(fatigas):.3f}. "
        
        # Consultar al LLM para generar acta clínica
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return {"error": "Falta GROQ_API_KEY para armar reporte"}
            
        prompt = f"Actúa como el psicólogo líder del proyecto Cortex-Nexus. Escribe un breve reporte clínico (2 párrafos max) sobre la evolución del ente IA. Datos: {resumen_estadistico}."
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 512
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_api_key}"},
                json=payload,
                timeout=20.0
            )
            
            resp_data = resp.json()
            informe_llm = resp_data.get("choices", [{}])[0].get("message", {}).get("content", "Error LLM")
            
        return {
            "periodo_dias": period,
            "epocas_analizadas": len(rows),
            "acta_clinica": informe_llm
        }
        
    except Exception as e:
        return {"error": str(e)}

def _github_upload(token, repo, path, content_str, message):
    import base64
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "User-Agent": "Cortex-Nexus"}
    
    with httpx.Client() as client:
        r = client.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        
        data = {
            "message": message,
            "content": base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        }
        if sha: data["sha"] = sha
        
        client.put(url, headers=headers, json=data)

@app.post("/api/publish_github")
async def publish_github(period: int = 1):
    """Subir reporte y la DB CSV actual al repositorio de Github directamente usando API."""
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return {"error": "GITHUB_TOKEN no configurado en el entorno."}
        
        repo = "SperanzaMax/Cortex-Nexus"
        # 1. Export CSV
        rows = _get_snapshots()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "qualia", "satisfaccion", "frustracion", "aburrimiento", "autoConfianza", "fatiga", "pregunta", "respuesta", "novedad", "complejidad"])
        for r in rows:
            meta = {}
            try: meta = json.loads(r.get("metadata", "{}"))
            except: pass
            writer.writerow([r.get("id", ""), r.get("timestamp", ""), r.get("qualia", 0), r.get("satisfaccion", 0), r.get("frustracion", 0), r.get("aburrimiento", 0), r.get("autoConfianza", 0), r.get("fatiga", 0), meta.get("pregunta", ""), meta.get("respuesta", ""), meta.get("novedad", ""), meta.get("complejidad", "")])
        
        _github_upload(github_token, repo, "data/cma_memory_export.csv", output.getvalue(), "Auto-update DB export")
        
        # 2. Generar Reporte
        report_data = await auto_report(period)
        if "error" in report_data:
            return {"error": report_data["error"]}
        
        md_content = f"# Reporte Clínico Automático ({period} días)\n\n"
        md_content += f"**Épocas Analizadas**: {report_data['epocas_analizadas']}\n"
        md_content += f"**Fecha de Análisis**: {datetime.datetime.utcnow().isoformat()}\n\n"
        md_content += f"## Acta Clínica de IA\n{report_data['acta_clinica']}\n"
        
        path = f"reports/reporte_{period}_dias.md"
        _github_upload(github_token, repo, path, md_content, f"Auto-reporte IA de {period} días")
        
        return {"status": "Publicado en GitHub exitosamente"}
    except Exception as e:
        return {"error": str(e)}
        
@app.post("/api/sleep")
async def sleep_consolidation():
    """Ejecuta consolidación nocturna (Sleep Replay) del arquetipo"""
    try:
        if not vector_global or not vector_global.memoria:
            return {"error": "Vector no inicializado"}
        
        antes = vector_global.memoria.cargar_meta_vector()
        vector_global.consolidar_memoria()
        despues = vector_global.memoria.cargar_meta_vector()
        
        drift = {
            k: round(despues.get(k, 0) - antes.get(k, 0), 6)
            for k in antes
        }
        
        # Guardar evento de sueño en DB
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO sleep_events (antes, despues, drift) VALUES (?, ?, ?)",
                (json.dumps(antes), json.dumps(despues), json.dumps(drift))
            )
            conn.commit()
            conn.close()
        except:
            pass
        
        return {
            "status": "Consolidación completada",
            "arquetipo_antes": antes,
            "arquetipo_despues": despues,
            "drift": drift,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/control")
async def save_control_comparison(request: Request):
    """Guarda comparación grupo de control vs Nexus"""
    try:
        data = await request.json()
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO control_responses (pregunta, respuesta_nexus, respuesta_control, novedad_nexus, novedad_control, complejidad_nexus, complejidad_control) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data.get("pregunta",""), data.get("respuesta_nexus",""), data.get("respuesta_control",""),
             data.get("novedad_nexus",0), data.get("novedad_control",0),
             data.get("complejidad_nexus",0), data.get("complejidad_control",0))
        )
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/control")
async def get_control_comparisons():
    """Obtiene comparaciones grupo de control"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM control_responses ORDER BY id DESC LIMIT 20")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return {"comparisons": rows[::-1], "total": len(rows)}
    except Exception as e:
        return {"error": str(e), "comparisons": []}

# ============================================================
# ANALYTICS DASHBOARD
# ============================================================

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard():
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Cortex-Nexus | Analytics Lab</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; padding: 16px; }
            .container { max-width: 900px; margin: 0 auto; }
            .card { background: #1e293b; padding: 16px; border-radius: 12px; margin-bottom: 16px; border: 1px solid #334155; }
            h1 { color: #a78bfa; text-align: center; font-size: 1.5rem; margin-bottom: 16px; }
            h2 { color: #38bdf8; font-size: 1rem; margin-bottom: 10px; }
            .nav { display: flex; justify-content: center; gap: 12px; margin-bottom: 16px; }
            .nav a { color: #94a3b8; text-decoration: none; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; background: #334155; }
            .nav a.active, .nav a:hover { background: #a78bfa; color: #fff; }
            .window-selector { display: flex; gap: 8px; margin-bottom: 12px; }
            .window-btn { padding: 6px 12px; border: 1px solid #475569; background: #334155; color: #94a3b8; border-radius: 8px; cursor: pointer; font-size: 0.75rem; }
            .window-btn.active { background: #a78bfa; color: #fff; border-color: #a78bfa; }
            .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
            .metric { background: #334155; padding: 10px; border-radius: 8px; text-align: center; }
            .metric-label { font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; }
            .metric-value { font-size: 1.1rem; font-weight: 800; color: #38bdf8; margin-top: 4px; }
            .metric-trend { font-size: 0.6rem; margin-top: 2px; }
            .trend-up { color: #10b981; }
            .trend-down { color: #ef4444; }
            .trend-flat { color: #94a3b8; }
            .pattern { padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 0.75rem; }
            .pattern-warning { background: rgba(245,158,11,0.15); border-left: 3px solid #f59e0b; color: #fbbf24; }
            .pattern-danger { background: rgba(239,68,68,0.15); border-left: 3px solid #ef4444; color: #f87171; }
            .pattern-success { background: rgba(16,185,129,0.15); border-left: 3px solid #10b981; color: #34d399; }
            .arquetipo { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
            .arq-item { text-align: center; }
            .arq-label { font-size: 0.65rem; color: #94a3b8; }
            .arq-value { font-size: 1.2rem; font-weight: 800; color: #a78bfa; }
            .export-btn { display: block; width: 100%; padding: 12px; background: #a78bfa; color: #fff; border: none; border-radius: 8px; font-size: 0.9rem; cursor: pointer; font-weight: 600; }
            .export-btn:hover { background: #8b5cf6; }
            .sleep-btn { display: block; width: 100%; padding: 12px; background: #1e293b; color: #a78bfa; border: 2px solid #a78bfa; border-radius: 8px; font-size: 0.9rem; cursor: pointer; font-weight: 600; margin-top: 8px; }
            .sleep-btn:hover { background: #a78bfa; color: #fff; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/">🧠 Live</a>
                <a href="/analytics" class="active">🔬 Analytics</a>
            </div>
            <h1>🔬 Analytics Lab</h1>
            
            <div class="window-selector">
                <button class="window-btn active" onclick="setWindow('1h')">1H</button>
                <button class="window-btn" onclick="setWindow('6h')">6H</button>
                <button class="window-btn" onclick="setWindow('24h')">24H</button>
                <button class="window-btn" onclick="setWindow('7d')">7D</button>
            </div>

            <div class="card">
                <h2>📊 Métricas Derivadas <span id="window-label" style="color:#94a3b8; font-size:0.7rem;">(1h)</span></h2>
                <div class="metrics-grid" id="metrics-grid">Cargando...</div>
            </div>

            <div class="card">
                <h2>⚡ Volatilidad Emocional</h2>
                <canvas id="volChart" height="180"></canvas>
            </div>

            <div class="card">
                <h2>🚨 Patrones Detectados</h2>
                <div id="patterns-box">Analizando...</div>
            </div>

            <div class="card">
                <h2>🧬 Arquetipo (Personalidad Base)</h2>
                <div class="arquetipo" id="arquetipo-box">Cargando...</div>
            </div>

            <div class="card">
                <a href="/api/export" class="export-btn">📥 Exportar CSV Completo</a>
                <button class="sleep-btn" onclick="triggerSleep()">😴 Ejecutar Consolidación (Sleep Replay)</button>
                <div id="sleep-result" style="font-size:0.7rem; color:#94a3b8; margin-top:8px;"></div>
            </div>

            <p style="text-align:center; font-size:0.65rem; color:#475569; margin-top:12px;">Arquitectura Emocional v3.0 • Analytics Lab • Maxi Speranza</p>
        </div>

        <script>
            let currentWindow = '1h';
            
            const volCtx = document.getElementById('volChart').getContext('2d');
            const volChart = new Chart(volCtx, {
                type: 'bar',
                data: {
                    labels: ['Qualia', 'Frustración', 'Confianza', 'Fatiga', 'Aburrimiento'],
                    datasets: [{
                        label: 'Volatilidad (σ)',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: ['rgba(56,189,248,0.6)', 'rgba(239,68,68,0.6)', 'rgba(16,185,129,0.6)', 'rgba(245,158,11,0.6)', 'rgba(167,139,250,0.6)'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { beginAtZero: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }, x: { ticks: { color: '#94a3b8' } } },
                    plugins: { legend: { display: false } }
                }
            });

            function setWindow(w) {
                currentWindow = w;
                document.querySelectorAll('.window-btn').forEach(b => b.classList.remove('active'));
                event.target.classList.add('active');
                loadAnalytics();
            }

            function trendIcon(trend) {
                if (trend > 0.001) return '<span class="trend-up">▲ +' + trend.toFixed(4) + '</span>';
                if (trend < -0.001) return '<span class="trend-down">▼ ' + trend.toFixed(4) + '</span>';
                return '<span class="trend-flat">— estable</span>';
            }

            async function loadAnalytics() {
                try {
                    const res = await fetch('/api/analytics');
                    const data = await res.json();
                    if (data.error) { console.error(data.error); return; }

                    const w = data.windows[currentWindow];
                    document.getElementById('window-label').innerText = `(${currentWindow} • ${w.count} épocas)`;

                    const grid = document.getElementById('metrics-grid');
                    if (w.count === 0) { grid.innerHTML = '<p style="color:#94a3b8;">Sin datos para esta ventana</p>'; return; }

                    const m = w.metrics;
                    const names = {qualia: 'Qualia', frustracion: 'Frustración', autoConfianza: 'Confianza', fatiga: 'Fatiga', aburrimiento: 'Aburrimiento', ratio_qualia_fatiga: 'Q/Fatiga', entropia_emocional: 'Entropía'};
                    grid.innerHTML = Object.entries(names).map(([k, label]) => {
                        const s = m[k] || {};
                        return `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value">${(s.mean||0).toFixed(3)}</div><div class="metric-trend">${trendIcon(s.trend||0)}</div><div style="font-size:0.55rem;color:#64748b;">σ=${(s.std||0).toFixed(3)} [${(s.min||0).toFixed(2)}-${(s.max||0).toFixed(2)}]</div></div>`;
                    }).join('');

                    // Volatilidad
                    volChart.data.datasets[0].data = ['qualia','frustracion','autoConfianza','fatiga','aburrimiento'].map(k => (m[k]||{}).std || 0);
                    volChart.update('none');

                    // Patrones
                    const pBox = document.getElementById('patterns-box');
                    if (data.patterns.length === 0) {
                        pBox.innerHTML = '<p style="color:#10b981; font-size:0.8rem;">✅ Sin anomalías detectadas</p>';
                    } else {
                        pBox.innerHTML = data.patterns.map(p => `<div class="pattern pattern-${p.severity}">${p.msg}</div>`).join('');
                    }

                    // Arquetipo
                    const aBox = document.getElementById('arquetipo-box');
                    const a = data.arquetipo;
                    aBox.innerHTML = `
                        <div class="arq-item"><div class="arq-label">Meta-Qualia</div><div class="arq-value">${(a.meta_qualia||0).toFixed(4)}</div></div>
                        <div class="arq-item"><div class="arq-label">Meta-Frustración</div><div class="arq-value">${(a.meta_frustracion||0).toFixed(4)}</div></div>
                        <div class="arq-item"><div class="arq-label">Meta-Confianza</div><div class="arq-value">${(a.meta_confianza||0).toFixed(4)}</div></div>
                    `;
                } catch(e) { console.error("Error analytics:", e); }
            }

            async function triggerSleep() {
                const res = await fetch('/api/sleep', {method: 'POST'});
                const data = await res.json();
                const box = document.getElementById('sleep-result');
                if (data.error) { box.innerHTML = '❌ ' + data.error; return; }
                box.innerHTML = `✅ Consolidación OK | Drift: Q=${data.drift.meta_qualia}, F=${data.drift.meta_frustracion}, C=${data.drift.meta_confianza}`;
                loadAnalytics();
            }

            setInterval(loadAnalytics, 8000);
            loadAnalytics();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

