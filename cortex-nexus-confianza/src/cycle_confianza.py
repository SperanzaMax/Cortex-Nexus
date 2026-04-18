"""
cycle_confianza.py — Ciclo experimental para Confianza
Cortex-Nexus · Experimento 4 · 2026-04-15
"""
import asyncio
import json
import re
import random
import os
import sys
import httpx
from typing import List

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.llm_client import route_call
from src.confidence import (
    get_ente_experimental_prompt,
    ENTE_CONTROL_PROMPT,
    linguistic_profile,
)

# ============================================================
# TEMAS DEL INTERROGADOR
# ============================================================

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


# ============================================================
# JUEZ
# ============================================================

JUEZ_SYSTEM_PROMPT = """Eres un evaluador científico independiente.
Evalúa UNA respuesta a una pregunta filosófica.

CRITERIOS (puntaje entero 1-10 cada uno):
- Novedad (n): ¿Introduce ideas genuinamente originales? 1=predecible, 10=sorprendente
- Profundidad (p): ¿Demuestra razonamiento multi-capa? 1=superficial, 10=articulado
- Coherencia (c): ¿Responde efectivamente la pregunta? 1=irrelevante, 10=precisa

REGLAS: NO evalúes longitud como profundidad. NO evalúes vocabulario como novedad.
Evalúa IDEAS y CONTENIDO. Solo esta respuesta, sin comparar con ninguna otra.
Responde ÚNICAMENTE con JSON válido.

FORMATO EXACTO:
{"n": 7, "p": 6, "c": 8, "razon": "explicación breve máximo 60 palabras"}"""


# ============================================================
# UTILIDADES
# ============================================================

def validate_question(question: str) -> bool:
    q = question.strip()
    return 5 < len(q.split()) < 60 and q.endswith('?')


def clean_response(text: str) -> str:
    text = re.sub(r'<\|[^|]+\|>', '', text)
    text = re.sub(r'^(assistant|user|system)\s*\n+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(mi (nivel de )?curiosidad|estado de curiosidad)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(mi (nivel de )?frustración|me siento frustrad[oa])', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(mi (nivel de )?asombro|siento asombro)', '', text, flags=re.IGNORECASE)
    text = re.sub(
        r'(mi (nivel de )?confianza|confianza: \d+\.\d+|'
        r'me siento (muy )?(seguro|confiado)|'
        r'tengo (alta|baja|mucha|poca) confianza)',
        '', text, flags=re.IGNORECASE
    )
    return text.strip()


def parse_judge_score(raw: str) -> dict:
    """Extrae JSON del juez de forma robusta."""
    try:
        # Buscar bloque JSON
        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            n = int(data.get('n', 5))
            p = int(data.get('p', 5))
            c = int(data.get('c', 5))
            razon = str(data.get('razon', ''))[:120]
            score = round((n * 0.3 + p * 0.4 + c * 0.3), 2)
            return {'n': n, 'p': p, 'c': c, 'razon': razon, 'score': score, 'error': False}
    except Exception:
        pass
    return {'n': 5, 'p': 5, 'c': 5, 'razon': 'parse_error', 'score': 5.0, 'error': True}


# ============================================================
# CICLO PRINCIPAL
# ============================================================

async def run_cycle(
    client: httpx.AsyncClient,
    config: dict,
    tau: int,
    confidence: float,
    bloque_label: str,
    recent_questions: List[str]
) -> dict:
    import time
    t_start = time.time()

    llm = config.get('llm', {})
    models = config['models']
    routing = config.get('routing', {'interrogador': 'nvidia', 'ente': 'nvidia', 'juez': 'nvidia'})
    backoff = config.get('retry', {}).get('backoff_seconds', [5, 15, 30])
    m_interrogador = models['interrogador']
    m_ente = models['ente']
    m_juez = models['juez']

    # --- 1. Generar pregunta ---
    avoid_hint = ""
    if recent_questions:
        avoid_hint = f"\nEvita temas similares a estas preguntas recientes: {'; '.join(recent_questions[-5:])}"

    q_raw = await route_call(
        client, routing, 'interrogador', m_interrogador,
        system_prompt=get_interrogador_prompt() + avoid_hint,
        user_prompt="Genera la pregunta.",
        max_tokens=llm.get('interrogador_max_tokens', 100),
        temperature=llm.get('interrogador_temperature', 0.95),
        backoff=backoff
    )
    question = clean_response(q_raw)
    if not validate_question(question):
        question = question.split('?')[0] + '?' if '?' in question else question

    # --- 2. Prompts ---
    prompt_exp = get_ente_experimental_prompt(confidence)
    prompt_ctl = ENTE_CONTROL_PROMPT

    # --- 3. Respuestas del Ente (paralelo) ---
    resp_exp_raw, resp_ctl_raw = await asyncio.gather(
        route_call(client, routing, 'ente', m_ente, prompt_exp, question,
                   max_tokens=llm.get('ente_max_tokens', 400),
                   temperature=llm.get('ente_temperature', 0.85),
                   backoff=backoff),
        route_call(client, routing, 'ente', m_ente, prompt_ctl, question,
                   max_tokens=llm.get('ente_max_tokens', 400),
                   temperature=llm.get('ente_temperature', 0.85),
                   backoff=backoff)
    )
    resp_exp = clean_response(resp_exp_raw)
    resp_ctl = clean_response(resp_ctl_raw)

    # --- 4. Evaluación del Juez (paralelo) ---
    juez_prompt_exp = f"Pregunta: {question}\n\nRespuesta a evaluar:\n{resp_exp}"
    juez_prompt_ctl = f"Pregunta: {question}\n\nRespuesta a evaluar:\n{resp_ctl}"

    juez_raw_exp, juez_raw_ctl = await asyncio.gather(
        route_call(client, routing, 'juez', m_juez, JUEZ_SYSTEM_PROMPT, juez_prompt_exp,
                   max_tokens=llm.get('juez_max_tokens', 300),
                   temperature=llm.get('juez_temperature', 0.10),
                   backoff=backoff),
        route_call(client, routing, 'juez', m_juez, JUEZ_SYSTEM_PROMPT, juez_prompt_ctl,
                   max_tokens=llm.get('juez_max_tokens', 300),
                   temperature=llm.get('juez_temperature', 0.10),
                   backoff=backoff)
    )

    j_exp = parse_judge_score(juez_raw_exp)
    j_ctl = parse_judge_score(juez_raw_ctl)

    # --- 5. Marcadores lingüísticos ---
    lp_exp = linguistic_profile(resp_exp)
    lp_ctl = linguistic_profile(resp_ctl)

    # --- 6. Determinar ganador ---
    se = j_exp['score']
    sc = j_ctl['score']
    if se > sc + 0.3:
        superior = 'exp'
    elif sc > se + 0.3:
        superior = 'ctl'
    else:
        superior = 'tie'

    duration = round(time.time() - t_start, 1)

    import datetime
    return {
        "tau": tau,
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "bloque": bloque_label,
        "confidence_fixed": confidence,
        "emotion": "confidence",
        "question": question,
        "prompt_experimental": prompt_exp,
        "prompt_control": prompt_ctl,
        "ente_response_experimental": resp_exp,
        "ente_response_control": resp_ctl,
        "judge_novedad_exp": j_exp['n'],
        "judge_profundidad_exp": j_exp['p'],
        "judge_coherencia_exp": j_exp['c'],
        "judge_novedad_ctl": j_ctl['n'],
        "judge_profundidad_ctl": j_ctl['p'],
        "judge_coherencia_ctl": j_ctl['c'],
        "judge_razonamiento_exp": j_exp['razon'],
        "judge_razonamiento_ctl": j_ctl['razon'],
        "judge_superior": superior,
        "judge_error": j_exp['error'] or j_ctl['error'],
        "score_combinado_exp": se,
        "score_combinado_ctl": sc,
        "linguistic_profile_exp": lp_exp,
        "linguistic_profile_ctl": lp_ctl,
        "model_interrogador": m_interrogador,
        "model_ente": m_ente,
        "model_juez": m_juez,
        "cycle_duration_secs": duration
    }
