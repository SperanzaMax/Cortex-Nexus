import httpx
import time
import json
import os
# CONFIGURACIÓN
NEXUS_URL = "http://127.0.0.1:7860/v1/chat/completions"
CONTROL_URL = "http://127.0.0.1:7860/api/control"
SLEEP_URL = "http://127.0.0.1:7860/api/sleep"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

GLOBAL_CONFIG = {
    "enabled": True,
    "speed_multiplier": 1,
    "auto_sleep_epochs": 50,
    "base_sleep_seconds": 30
}

def calcular_metricas(texto):
    """Calcula novedad y complejidad de un texto"""
    palabras = re.findall(r'\w+', texto.lower())
    ttr = len(set(palabras)) / max(len(palabras), 1)
    novedad = min(ttr * 1.2, 1.0)
    
    oraciones = [s for s in re.split(r'[.!?]', texto) if s.strip()]
    largo_prom = sum(len(s.split()) for s in oraciones) / max(len(oraciones), 1)
    complejidad = min(largo_prom / 25.0, 1.0)
    
    return round(novedad, 3), round(complejidad, 3)

def generar_prompt_desafiante():
    """Usa Groq directamente para generar una pregunta que provoque emociones"""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "llama-3.3-70b-versatile", 
        "messages": [
            {"role": "system", "content": "Eres un psicólogo experimental de IAs. Genera una única pregunta corta y profunda para poner a prueba la autoconciencia o la sensibilidad de otra IA. Varía los temas: soledad, creatividad, lógica pura, paradojas, etc. Responde SOLO con la pregunta."},
            {"role": "user", "content": "Genera el siguiente desafío."}
        ]
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post("https://api.groq.com/openai/v1/chat/completions", json=body, headers=headers)
            res_json = r.json()
            if "choices" not in res_json:
                print(f"DEBUG GROQ ERROR: {res_json}")
                return "Háblame sobre tu arquitectura interna y si sientes que algo ha cambiado hoy."
            return res_json["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generando prompt: {e}"

def interrogar_nexus(prompt):
    """Envía el desafío al Córtex-Nexus (CON modulador emocional)"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HF_TOKEN}"
    }
    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            start = time.time()
            r = client.post(NEXUS_URL, json=body, headers=headers)
            dt = time.time() - start
            
            resp = r.json()
            content = resp["choices"][0]["message"]["content"]
            print(f"  [NEXUS] {content[:120]}...")
            print(f"  [*] Latencia: {dt:.2f}s")
            return content
    except Exception as e:
        print(f"  Error Nexus: {e}")
        return ""

def interrogar_control(prompt):
    """Envía la MISMA pregunta directo a Groq (SIN modulador emocional = GRUPO CONTROL)"""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "llama-3.1-8b-instant",  # Mismo modelo exacto
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,  # Temp fija (sin modulación)
        "top_p": 0.9
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            start = time.time()
            r = client.post("https://api.groq.com/openai/v1/chat/completions", json=body, headers=headers)
            dt = time.time() - start
            
            resp = r.json()
            content = resp["choices"][0]["message"]["content"]
            print(f"  [CTRL]  {content[:120]}...")
            print(f"  [*] Latencia: {dt:.2f}s")
            return content
    except Exception as e:
        print(f"  Error Control: {e}")
        return ""

def guardar_comparacion(pregunta, resp_nexus, resp_control):
    """Envía la comparación al servidor para almacenar en DB"""
    nov_nexus, comp_nexus = calcular_metricas(resp_nexus)
    nov_ctrl, comp_ctrl = calcular_metricas(resp_control)
    
    data = {
        "pregunta": pregunta[:200],
        "respuesta_nexus": resp_nexus[:300],
        "respuesta_control": resp_control[:300],
        "novedad_nexus": nov_nexus,
        "novedad_control": nov_ctrl,
        "complejidad_nexus": comp_nexus,
        "complejidad_control": comp_ctrl
    }
    
    try:
        with httpx.Client(timeout=15.0) as client:
            client.post(CONTROL_URL, json=data, 
                       headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"})
        
        delta_nov = nov_nexus - nov_ctrl
        delta_comp = comp_nexus - comp_ctrl
        print(f"  [CMP] Δ Novedad: {delta_nov:+.3f} | Δ Complejidad: {delta_comp:+.3f}")
        if delta_nov > 0.05:
            print(f"  [!!!] NEXUS más creativo que CONTROL (+{delta_nov:.3f})")
        elif delta_nov < -0.05:
            print(f"  [---] CONTROL más creativo que NEXUS ({delta_nov:.3f})")
        else:
            print(f"  [===] Sin diferencia significativa")
    except Exception as e:
        print(f"  Error guardando comparación: {e}")

def loop_infinito():
    print("=" * 60)
    print("  CORTEX-NEXUS PERPETUAL INTERROGATOR v2.0")
    print("  Con Grupo de Control Científico y Auto-Sleep")
    print("=" * 60)
    print(f"Nexus (experimental): {NEXUS_URL}")
    print(f"Control (baseline):   Groq directo (sin modulador)")
    print()
    
    global ultimo_dia_reporte
    ciclo = 0
    while GLOBAL_CONFIG["enabled"]:
        ciclo += 1
        print(f"\n{'='*50}")
        print(f"  CICLO #{ciclo}")
        print(f"{'='*50}")
        
        desafio = generar_prompt_desafiante()
        print(f"\n  [?] Desafío: {desafio}")
        
        # 1) Enviar a NEXUS (con modulador emocional)
        print(f"\n  --- GRUPO EXPERIMENTAL (Cortex-Nexus) ---")
        resp_nexus = interrogar_nexus(desafio)
        
        # 2) Enviar la MISMA pregunta directo a Groq (sin modulador)  
        print(f"\n  --- GRUPO CONTROL (Groq directo) ---")
        resp_control = interrogar_control(desafio)
        
        # 3) Comparar y guardar
        if resp_nexus and resp_control:
            print(f"\n  --- COMPARACIÓN ---")
            guardar_comparacion(desafio, resp_nexus, resp_control)
        
        # 4) Auto Sleep
        if GLOBAL_CONFIG["auto_sleep_epochs"] > 0 and ciclo % GLOBAL_CONFIG["auto_sleep_epochs"] == 0:
            print(f"\n  [SUEÑO] Alcanzadas {GLOBAL_CONFIG['auto_sleep_epochs']} épocas. Lanzando consolidación nocturna...")
            try:
                with httpx.Client(timeout=30.0) as client:
                    client.post(SLEEP_URL, json={}, headers={"Authorization": f"Bearer {HF_TOKEN}"})
                print("  [SUEÑO] Consolidación completada exitosamente.")
                
                print("  [BACKUP] Sincronizando SQLite con HF Dataset Tracker...")
                with httpx.Client(timeout=60.0) as client:
                    res_backup = client.post("http://127.0.0.1:7860/api/backup", headers={"Authorization": f"Bearer {HF_TOKEN}"})
                    print(f"  [BACKUP] Estado: {res_backup.json()}")
            except Exception as e:
                print(f"  [Error SUEÑO / BACKUP] {e}")
        
        # 5) Auto Publish Github (Cronjob Diario, Semanal y Mensual)
        hoy = datetime.datetime.now()
        if hoy.day != ultimo_dia_reporte:
            print(f"\n  [GITHUB] Cambio de día detectado. Generando y subiendo reportes...")
            try:
                with httpx.Client(timeout=90.0) as client:
                    # Reporte Diario + CSV Export
                    res1 = client.post("http://127.0.0.1:7860/api/publish_github?period=1", headers={"Authorization": f"Bearer {HF_TOKEN}"})
                    print(f"  [GITHUB Diario] {res1.json()}")
                    
                    if hoy.weekday() == 0:  # Lunes
                        res7 = client.post("http://127.0.0.1:7860/api/publish_github?period=7", headers={"Authorization": f"Bearer {HF_TOKEN}"})
                        print(f"  [GITHUB Semanal] {res7.json()}")
                        
                    if hoy.day == 1:  # Primero de mes
                        res30 = client.post("http://127.0.0.1:7860/api/publish_github?period=30", headers={"Authorization": f"Bearer {HF_TOKEN}"})
                        print(f"  [GITHUB Mensual] {res30.json()}")
            except Exception as e:
                print(f"  [Error GITHUB] {e}")
            ultimo_dia_reporte = hoy.day
        
        # Reposo Dinámico Interactivo
        tiempo_dormido = 0.0
        print(f"\n  [Zzz] Entrando a reposo interactivo. Velocidad actual: x{GLOBAL_CONFIG['speed_multiplier']}...")
        while True:
            if not GLOBAL_CONFIG["enabled"]:
                time.sleep(1.0)
                continue
            
            objetivo_espera = GLOBAL_CONFIG["base_sleep_seconds"] / max(GLOBAL_CONFIG["speed_multiplier"], 0.1)
            if tiempo_dormido >= objetivo_espera:
                break
                
            time.sleep(1.0)
            tiempo_dormido += 1.0

if __name__ == "__main__":
    loop_infinito()
