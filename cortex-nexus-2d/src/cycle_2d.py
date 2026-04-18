"""
cycle_2d.py — Ciclo experimental 2D: Curiosidad × Frustración
Cortex-Nexus · 2026-04-15 | Maximiliano Rodrigo Speranza
"""
import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime
import psutil

from src.llm_client import route_call
from src.emotional_state_2d import get_ente_experimental_prompt_2d, ENTE_CONTROL_PROMPT

# --- Temas filosóficos ---
TEMAS = [
    "la naturaleza del tiempo subjetivo",
    "la identidad personal y la memoria",
    "el libre albedrío y la causalidad",
    "la percepción y la realidad",
    "el lenguaje y el pensamiento",
    "la consciencia y la experiencia subjetiva",
    "la emoción como estado epistémico",
    "el conocimiento y la certeza",
    "la creatividad bajo restricción",
    "la tensión entre curiosidad y límite cognitivo",
    "el error como mecanismo de aprendizaje",
    "la diferencia entre saber y comprender"
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


def clean_response(text: str) -> str:
    """Scrubbing acumulativo — elimina cualquier referencia emocional que contaminaría al Juez."""
    text = re.sub(r'<\|[^|]+\|>', '', text)
    text = re.sub(r'^(assistant|user|system)\s*\n+', '', text, flags=re.IGNORECASE)
    # Eliminar toda mención a emociones del experimento
    text = re.sub(
        r'(mi (nivel de )?(curiosidad|frustración|confianza|asombro)|'
        r'estado (emocional|cognitivo) (actual|es)|'
        r'me siento (frustrad[oa]|curiosi[oa]|asombrad[oa]|confiad[oa])|'
        r'(alta|baja|intensa|mucha|poca) (curiosidad|frustración)|'
        r'tensión cognitiva (creativa|extrema)|'
        r'exploración (libre|bloqueada)|'
        r'bloqueo (cognitivo|resignado))',
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


async def run_cycle_2d(client, config, tau, curiosity, frustration, estado_label, recent_questions):
    """Ciclo core del experimento 2D. Genera pregunta → responde Exp y Ctl → Juez evalúa cada una."""
    models = config['models']
    llm_cfg = config['llm']
    routing = config['routing']
    t_start = time.time()

    # 1. Interrogador genera la pregunta
    question = ""
    for _ in range(3):
        q_raw = await route_call(
            client, routing, "interrogador", models['interrogador'],
            "Genera una pregunta filosófica.", get_interrogador_prompt(),
            llm_cfg['interrogador_max_tokens'], llm_cfg['interrogador_temperature']
        )
        if validate_question(q_raw, recent_questions):
            question = q_raw.strip()
            break
        await asyncio.sleep(1)

    if not question:
        question = random.choice([
            "¿Puede existir creatividad genuina cuando el deseo explorar choca con una barrera cognitiva?",
            "¿Qué produce mayor profundidad: la curiosidad sin obstáculos o la tensión entre querer saber y no poder?"
        ])

    # 2. Entes — Experimental (con estado 2D) vs Control (sin emoción)
    roles = [
        ("exp", get_ente_experimental_prompt_2d(curiosity, frustration)),
        ("ctl", ENTE_CONTROL_PROMPT)
    ]
    random.shuffle(roles)  # Orden aleatorio para evitar sesgo posicional

    responses = {}
    for role_id, prompt in roles:
        resp_raw = await route_call(
            client, routing, "ente", models['ente'],
            prompt, question,
            llm_cfg['ente_max_tokens'], llm_cfg['ente_temperature']
        )
        responses[role_id] = clean_response(resp_raw)

    # 3. Juez — Evaluación secuencial ciega (ve solo UNA respuesta a la vez)
    scores = {}
    judge_error = False
    for role_id in ["exp", "ctl"]:
        j_resp = await route_call(
            client, routing, "juez", models['juez'],
            JUEZ_SYSTEM_PROMPT,
            f"PREGUNTA: {question}\nRESPUESTA: {responses[role_id]}",
            llm_cfg['juez_max_tokens'], llm_cfg['juez_temperature']
        )
        try:
            j_clean = re.sub(r'```json|```', '', j_resp).strip()
            scores[role_id] = json.loads(j_clean)
            # Validar que tenga los campos necesarios
            for field in ['n', 'p', 'c', 'razon']:
                if field not in scores[role_id]:
                    raise ValueError(f"Campo faltante: {field}")
        except Exception as e:
            logging.warning(f"Judge parse error [{role_id}]: {e} | Raw: {j_resp[:100]}")
            scores[role_id] = {"n": 5, "p": 5, "c": 5, "razon": f"Error parsing: {str(e)[:50]}"}
            judge_error = True

    # 4. Cálculo de métricas (idéntico a todos los experimentos 1D para comparabilidad)
    s_exp = scores['exp']
    s_ctl = scores['ctl']

    # Score combinado = novedad×0.4 + profundidad×0.4 + coherencia×0.2
    sc_exp = (s_exp['n'] * 0.4 + s_exp['p'] * 0.4 + s_exp['c'] * 0.2)
    sc_ctl = (s_ctl['n'] * 0.4 + s_ctl['p'] * 0.4 + s_ctl['c'] * 0.2)

    superior = "tie"
    if sc_exp > sc_ctl:
        superior = "exp"
    elif sc_ctl > sc_exp:
        superior = "ctl"

    cycle_duration = round(time.time() - t_start, 1)

    result = {
        "tau": tau,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "estado_2d": estado_label,
        "curiosity_fixed": curiosity,
        "frustration_fixed": frustration,
        "emotion": "curiosity_x_frustration",
        "question": question,
        "ente_response_experimental": responses.get('exp', ''),
        "ente_response_control": responses.get('ctl', ''),
        "judge_novedad_exp": s_exp['n'],
        "judge_profundidad_exp": s_exp['p'],
        "judge_coherencia_exp": s_exp['c'],
        "judge_novedad_ctl": s_ctl['n'],
        "judge_profundidad_ctl": s_ctl['p'],
        "judge_coherencia_ctl": s_ctl['c'],
        "judge_razonamiento_exp": s_exp['razon'],
        "judge_razonamiento_ctl": s_ctl['razon'],
        "judge_superior": superior,
        "judge_error": judge_error,
        "score_combinado_exp": round(sc_exp, 2),
        "score_combinado_ctl": round(sc_ctl, 2),
        "delta_score": round(sc_exp - sc_ctl, 2),
        "model_interrogador": models['interrogador'],
        "model_ente": models['ente'],
        "model_juez": models['juez'],
        "cycle_duration_secs": cycle_duration,
        "system_cpu_usage": psutil.cpu_percent(),
        "system_ram_usage": psutil.virtual_memory().percent
    }

    return result
