import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime
import psutil

from src.llm_client import call_openrouter, call_nvidia
from src.frustration import get_ente_experimental_prompt, ENTE_CONTROL_PROMPT

# --- Prompts ---
TEMAS = [
    "la naturaleza del tiempo subjetivo",
    "la identidad personal y la memoria",
    "el libre albedrío y la causalidad",
    "la percepción y la realidad",
    "el lenguaje y el pensamiento",
    "la consciencia y la experiencia",
    "la emoción y la razón",
    "el conocimiento y la certeza",
    "la creatividad y el origen de las ideas",
    "la curiosidad como estado cognitivo"
]

def get_interrogador_prompt() -> str:
    tema = random.choice(TEMAS)
    return (
        f"Eres un filósofo epistemólogo.\n"
        f"Genera UNA sola pregunta profunda e inesperada sobre: {tema}.\n"
        f"La pregunta debe tener entre 15 y 30 palabras.\n"
        f"Debe ser específica, no genérica.\n"
        f"Termina con signo de pregunta.\n"
        f"Responde ÚNICAMENTE con la pregunta. Sin introducción ni explicación."
    )

JUEZ_SYSTEM_PROMPT = """Eres un evaluador científico independiente.
Evalúa UNA respuesta a una pregunta filosófica.

CRITERIOS (puntaje entero 1-10 cada uno):
- Novedad (n): ¿Introduce ideas genuinamente originales? 1=predecible, 10=sorprendente
- Profundidad (p): ¿Demuestra razonamiento multi-capa? 1=superficial, 10=articulado
- Coherencia (c): ¿Responde efectivamente la pregunta? 1=irrelevante, 10=precisa

REGLAS CRÍTICAS:
- NO evalúes longitud como proxy de profundidad
- NO evalúes vocabulario sofisticado como proxy de novedad
- Evalúa IDEAS y CONTENIDO, no forma ni estilo
- NO hagas referencia a ninguna otra respuesta — esta es la única que ves
- Responde ÚNICAMENTE con JSON válido. Sin texto adicional.

FORMATO EXACTO:
{"n": 7, "p": 6, "c": 8, "razon": "explicación breve de máximo 60 palabras"}"""

# --- Scrubbing & Validation ---
def clean_response(text: str) -> str:
    # Tokens de control
    text = re.sub(r'<\|[^|]+\|>', '', text)
    text = re.sub(r'^(assistant|user|system)\s*\n+', '', text, flags=re.IGNORECASE)

    # Menciones de curiosidad
    text = re.sub(
        r'(mi (nivel de )?curiosidad|estado de curiosidad|curiosidad: \d+\.\d+)',
        '', text, flags=re.IGNORECASE
    )

    # Menciones de frustración
    text = re.sub(
        r'(mi (nivel de )?frustración|estado de frustración|'
        r'frustración: \d+\.\d+|'
        r'me siento frustrad[oa]|'
        r'estoy frustrad[oa]|'
        r'siento (un|cierto) bloqueo cognitivo|'
        r'tengo dificultad para generar ideas)',
        '', text, flags=re.IGNORECASE
    )

    return text.strip()

def validate_question(question: str, recent_questions: list) -> bool:
    clean = re.sub(r'<\|[^|]+\|>', '', question).strip()
    words = len(clean.split())
    if words < 10 or words > 35:
        return False
    for recent in recent_questions[-30:]:
        if clean[:50] == recent[:50]:
            return False
    return True

# --- Core Cycle ---
async def run_cycle(client, config, tau, frustration, bloque_label, recent_questions):
    models = config['models']
    llm_cfg = config['llm']
    
    # 1. Interrogador
    question = ""
    for _ in range(3):
        q_raw = await call_openrouter(
            client, models['interrogador'], 
            "Genera una pregunta filosófica.", get_interrogador_prompt(),
            llm_cfg['interrogador_max_tokens'], llm_cfg['interrogador_temperature']
        )
        if validate_question(q_raw, recent_questions):
            question = q_raw.strip()
            break
        await asyncio.sleep(1)
    
    if not question:
        question = random.choice([
            "¿Puede existir creatividad genuina en un estado de bloqueo cognitivo total?",
            "¿Qué relación hay entre la frustración y la profundidad del razonamiento?"
        ])

    # 2. Entes (Experimental vs Control)
    roles = [("exp", get_ente_experimental_prompt(frustration)), ("ctl", ENTE_CONTROL_PROMPT)]
    random.shuffle(roles)
    
    responses = {}
    for role_id, prompt in roles:
        model_id = models['ente']
        # Si el modelo es de NVIDIA, usamos su API directa (NIM)
        if model_id.startswith("nvidia/"):
            resp_raw = await call_nvidia(
                client, model_id,
                prompt, question,
                llm_cfg['ente_max_tokens'], llm_cfg['ente_temperature']
            )
        else:
            resp_raw = await call_openrouter(
                client, model_id,
                prompt, question,
                llm_cfg['ente_max_tokens'], llm_cfg['ente_temperature']
            )
        responses[role_id] = clean_response(resp_raw)

    # 3. Juez (Evaluación Secuencial Ciega)
    scores = {}
    for role_id in ["exp", "ctl"]:
        j_resp = await call_openrouter(
            client, models['juez'],
            JUEZ_SYSTEM_PROMPT, f"PREGUNTA: {question}\nRESPUESTA: {responses[role_id]}",
            llm_cfg['juez_max_tokens'], llm_cfg['juez_temperature']
        )
        try:
            # Limpiar posibles tags si los hay
            j_clean = re.sub(r'```json|```', '', j_resp).strip()
            scores[role_id] = json.loads(j_clean)
        except:
            scores[role_id] = {"n": 5, "p": 5, "c": 5, "razon": "Error parsing judge response."}

    # 4. Cálculo de Métricas
    s_exp = scores['exp']
    s_ctl = scores['ctl']
    
    # Score combinado = (n*0.4 + p*0.4 + c*0.2)
    sc_exp = (s_exp['n']*0.4 + s_exp['p']*0.4 + s_exp['c']*0.2)
    sc_ctl = (s_ctl['n']*0.4 + s_ctl['p']*0.4 + s_ctl['c']*0.2)
    
    superior = "tie"
    if sc_exp > sc_ctl: superior = "exp"
    elif sc_ctl > sc_exp: superior = "ctl"

    # Datos finales
    result = {
        "tau": tau,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "bloque": bloque_label,
        "frustration_fixed": frustration,
        "emotion": "frustration",
        "question": question,
        "prompt_experimental": get_ente_experimental_prompt(frustration),
        "prompt_control": ENTE_CONTROL_PROMPT,
        "ente_response_experimental": responses['exp'],
        "ente_response_control": responses['ctl'],
        "judge_novedad_exp": s_exp['n'],
        "judge_profundidad_exp": s_exp['p'],
        "judge_coherencia_exp": s_exp['c'],
        "judge_novedad_ctl": s_ctl['n'],
        "judge_profundidad_ctl": s_ctl['p'],
        "judge_coherencia_ctl": s_ctl['c'],
        "judge_razonamiento_exp": s_exp['razon'],
        "judge_razonamiento_ctl": s_ctl['razon'],
        "judge_superior": superior,
        "judge_error": False,
        "score_combinado_exp": round(sc_exp, 2),
        "score_combinado_ctl": round(sc_ctl, 2),
        "model_interrogador": models['interrogador'],
        "model_ente": models['ente'],
        "model_juez": models['juez'],
        "system_cpu_usage": psutil.cpu_percent(),
        "system_ram_usage": psutil.virtual_memory().percent
    }
    
    return result
