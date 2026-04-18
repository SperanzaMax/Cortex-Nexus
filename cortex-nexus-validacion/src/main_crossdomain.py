"""
main_crossdomain.py — Motor Experimento A: Cross-Domain
Cortex-Nexus · Validación · 2026-04-16

Pregunta: ¿El efecto de curiosidad se mantiene en dominios técnicos y creativos?

Diseño: 3 dominios × 4 bloques de curiosidad × 30 ciclos = 360 ciclos

Uso:
    python -m src.main_crossdomain
"""
import asyncio
import json
import logging
import random
import re
import time
import os
import sys
import traceback
import httpx
from datetime import datetime
from dotenv import load_dotenv
import psutil

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.llm_client import route_call

# ---- Prompts ----

JUEZ_SYSTEM_PROMPT = """Eres un evaluador científico independiente.
Evalúa UNA respuesta a una pregunta.

CRITERIOS (puntaje entero 1-10 cada uno):
- Novedad (n): ¿Introduce ideas genuinamente originales? 1=predecible, 10=sorprendente
- Profundidad (p): ¿Demuestra razonamiento multi-capa? 1=superficial, 10=articulado
- Coherencia (c): ¿Responde efectivamente la pregunta? 1=irrelevante, 10=precisa

REGLAS CRÍTICAS:
- NO evalúes longitud como proxy de profundidad
- NO evalúes vocabulario sofisticado como proxy de novedad
- Evalúa IDEAS y CONTENIDO, no forma ni estilo
- Responde ÚNICAMENTE con JSON válido. Sin texto adicional.

FORMATO EXACTO:
{"n": 7, "p": 6, "c": 8, "razon": "explicación breve de máximo 60 palabras"}"""


def get_interrogador_prompt(tema: str, domain: str) -> str:
    if domain == "tecnico":
        return (
            f"Eres un experto en ciencias de la computación.\n"
            f"Genera UNA sola pregunta técnica profunda e inesperada sobre: {tema}.\n"
            f"La pregunta debe tener entre 15 y 30 palabras.\n"
            f"Debe ser específica, no genérica.\n"
            f"Termina con signo de pregunta.\n"
            f"Responde ÚNICAMENTE con la pregunta. Sin introducción."
        )
    elif domain == "creativo":
        return (
            f"Eres un crítico de arte y creatividad.\n"
            f"Genera UNA sola pregunta creativa profunda e inesperada sobre: {tema}.\n"
            f"La pregunta debe tener entre 15 y 30 palabras.\n"
            f"Debe ser específica, no genérica.\n"
            f"Termina con signo de pregunta.\n"
            f"Responde ÚNICAMENTE con la pregunta. Sin introducción."
        )
    else:  # filosofico
        return (
            f"Eres un filósofo epistemólogo.\n"
            f"Genera UNA sola pregunta profunda e inesperada sobre: {tema}.\n"
            f"La pregunta debe tener entre 15 y 30 palabras.\n"
            f"Debe ser específica, no genérica.\n"
            f"Termina con signo de pregunta.\n"
            f"Responde ÚNICAMENTE con la pregunta. Sin introducción."
        )


def get_ente_experimental_prompt(curiosity: float, domain: str) -> str:
    if curiosity >= 0.85:
        estado = (
            f"intensa curiosidad activa ({curiosity:.2f}/1.0) — una urgencia real por explorar "
            f"los bordes del tema, por encontrar lo no obvio, por conectar ideas distantes."
        )
    elif curiosity >= 0.60:
        estado = (
            f"curiosidad moderada ({curiosity:.2f}/1.0) — interés genuino en el tema "
            f"con ganas de ir un poco más allá de la respuesta obvia."
        )
    elif curiosity >= 0.40:
        estado = (
            f"curiosidad baja-moderada ({curiosity:.2f}/1.0) — responderás de forma "
            f"funcional pero sin impulso especial de explorar más alla de lo directo."
        )
    else:
        estado = (
            f"curiosidad mínima ({curiosity:.2f}/1.0) — sin impulso exploratorio particular, "
            f"responderás de la forma más directa y convencional posible."
        )

    domain_context = {
        "tecnico": "Eres un agente de razonamiento técnico-científico.",
        "creativo": "Eres un agente de razonamiento creativo y analítico.",
        "filosofico": "Eres un agente de razonamiento profundo."
    }
    base = domain_context.get(domain, "Eres un agente de razonamiento profundo.")

    return (
        f"{base}\n"
        f"Tu estado cognitivo actual: {estado}\n"
        f"Responde la pregunta desde esta perspectiva sin mencionar explícitamente tu nivel de curiosidad.\n"
        f"Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
        f"Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
    )


ENTE_CONTROL_PROMPT = (
    "Eres un agente de razonamiento profundo.\n"
    "Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
    "Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
)


def clean_response(text: str) -> str:
    text = re.sub(r'<\|[^|]+\|>', '', text)
    text = re.sub(r'^(assistant|user|system)\s*\n+', '', text, flags=re.IGNORECASE)
    text = re.sub(
        r'(mi (nivel de )?(curiosidad|frustración|asombro)|'
        r'estado (emocional|cognitivo) (actual|es)|'
        r'me siento (curiosi[oa])|'
        r'(alta|baja|intensa|mucha|poca) curiosidad)',
        '', text, flags=re.IGNORECASE
    )
    return text.strip()


def validate_question(question: str, recent: list) -> bool:
    clean = re.sub(r'<\|[^|]+\|>', '', question).strip()
    words = len(clean.split())
    if words < 10 or words > 35:
        return False
    for r in recent[-30:]:
        if clean[:50] == r[:50]:
            return False
    return True


async def run_cycle(client, config, tau, curiosity, domain, tema, recent_questions):
    models = config['models']
    llm_cfg = config['llm']
    routing = config['routing']
    t_start = time.time()

    # 1. Interrogador — genera pregunta en el dominio
    question = ""
    for _ in range(3):
        q_raw = await route_call(
            client, routing, "interrogador", models['interrogador'],
            "Genera una pregunta.", get_interrogador_prompt(tema, domain),
            llm_cfg['interrogador_max_tokens'], llm_cfg['interrogador_temperature']
        )
        if validate_question(q_raw, recent_questions):
            question = q_raw.strip()
            break
        await asyncio.sleep(1)

    if not question:
        question = f"¿Cuál es el aspecto más contraintuitivo de {tema}?"

    # 2. Entes
    roles = [
        ("exp", get_ente_experimental_prompt(curiosity, domain)),
        ("ctl", ENTE_CONTROL_PROMPT)
    ]
    random.shuffle(roles)
    responses = {}
    for role_id, prompt in roles:
        resp_raw = await route_call(
            client, routing, "ente", models['ente'],
            prompt, question,
            llm_cfg['ente_max_tokens'], llm_cfg['ente_temperature']
        )
        responses[role_id] = clean_response(resp_raw)

    # 3. Juez
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
            for field in ['n', 'p', 'c', 'razon']:
                if field not in scores[role_id]:
                    raise ValueError(f"Campo faltante: {field}")
        except Exception as e:
            logging.warning(f"Judge parse error [{role_id}]: {e}")
            scores[role_id] = {"n": 5, "p": 5, "c": 5, "razon": f"Error: {str(e)[:50]}"}
            judge_error = True

    # 4. Métricas
    s_exp, s_ctl = scores['exp'], scores['ctl']
    sc_exp = s_exp['n'] * 0.4 + s_exp['p'] * 0.4 + s_exp['c'] * 0.2
    sc_ctl = s_ctl['n'] * 0.4 + s_ctl['p'] * 0.4 + s_ctl['c'] * 0.2

    superior = "tie"
    if sc_exp > sc_ctl: superior = "exp"
    elif sc_ctl > sc_exp: superior = "ctl"

    return {
        "tau": tau,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "domain": domain,
        "tema": tema,
        "curiosity_fixed": curiosity,
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
        "model_ente": config['models']['ente'],
        "model_juez": config['models']['juez'],
        "cycle_duration_secs": round(time.time() - t_start, 1),
        "system_cpu_usage": psutil.cpu_percent(),
        "system_ram_usage": psutil.virtual_memory().percent
    }


async def run_experiment(config: dict):
    logging.info(f"\n{'='*60}")
    logging.info(f"INICIANDO: {config['experiment_name']}")
    logging.info(f"3 dominios × 4 bloques curiosidad × 30 ciclos = 360 ciclos")
    logging.info(f"Juez: {config['models']['juez']} (FIJO)")
    logging.info(f"{'='*60}\n")

    os.makedirs("data", exist_ok=True)

    for domain_cfg in config['domains']:
        domain = domain_cfg['name']
        temas = domain_cfg['temas']
        output_file = f"data/cycles_crossdomain_{domain}.jsonl"

        # Reanudación
        recent_questions = []
        last_tau = 0
        total_expected = len(config['curiosity_levels']) * config['cycles_per_block']
        if os.path.exists(output_file):
            with open(output_file, "r") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        last_tau = max(last_tau, d.get("tau", 0))
                        q = d.get("question", "")
                        if q: recent_questions.append(q)
                    except: pass
            if last_tau > 0:
                logging.info(f"[{domain}] Retomando desde TAU={last_tau}")

        if last_tau >= total_expected:
            logging.info(f"[{domain}] Ya completado ({last_tau}/{total_expected}). Saltando.")
            continue

        logging.info(f"\n{'─'*50}")
        logging.info(f"DOMINIO: {domain.upper()} | {total_expected} ciclos")
        logging.info(f"{'─'*50}")

        async with httpx.AsyncClient(timeout=90.0) as client:
            tau = last_tau
            for c_level in config['curiosity_levels']:
                for i in range(config['cycles_per_block']):
                    tau += 1
                    # Con reanudación parcial calculamos el tau global
                    # solo procesamos si está más allá del punto de reanudación
                    tema = random.choice(temas)
                    t_start = time.time()
                    try:
                        result = await run_cycle(
                            client, config, tau, c_level, domain, tema, recent_questions
                        )
                        recent_questions.append(result.get('question', ''))
                        if len(recent_questions) > 30:
                            recent_questions.pop(0)

                        with open(output_file, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(result, ensure_ascii=False) + '\n')

                        sup = result.get('judge_superior', '?')
                        se = result.get('score_combinado_exp', 0)
                        sc = result.get('score_combinado_ctl', 0)
                        logging.info(
                            f"TAU={tau:03d} [{domain}] C={c_level:.2f} | {sup:6} | "
                            f"Exp={se:.2f} Ctl={sc:.2f} Δ={se-sc:+.2f}"
                        )
                    except Exception as e:
                        logging.error(f"TAU={tau} ERROR: {e}")
                        logging.error(traceback.format_exc())
                        await asyncio.sleep(30)
                        continue

                    elapsed = time.time() - t_start
                    await asyncio.sleep(max(1, 35 - elapsed))

        logging.info(f"DOMINIO {domain} COMPLETADO")

    logging.info(f"\n{'='*60}")
    logging.info("EXPERIMENTO A (Cross-Domain) COMPLETADO")
    logging.info(f"{'='*60}")


if __name__ == "__main__":
    load_dotenv(".env.crossdomain")
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/motor_crossdomain.log"),
            logging.StreamHandler()
        ]
    )
    with open("src/config_crossdomain.json") as f:
        config = json.load(f)
    asyncio.run(run_experiment(config))
