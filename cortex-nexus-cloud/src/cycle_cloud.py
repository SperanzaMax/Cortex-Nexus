import asyncio
import json
import random
import re
import time
from datetime import datetime, timezone
import httpx
import psutil

from curiosity import calculate_next_curiosity, curiosity_to_prompt
from llm_client_cloud import call_openrouter

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

FALLBACK_QUESTIONS = [
    "¿Puede existir curiosidad genuina sin la conciencia de la propia ignorancia?",
    "¿Qué distingue percibir el tiempo de simplemente existir dentro de él?",
    "¿Es posible tener un pensamiento completamente original o todo es recombinación?",
    "¿Puede la razón comprenderse a sí misma sin caer en circularidad?",
    "¿Qué le da continuidad a la identidad cuando la memoria es fragmentaria?",
    "¿Es el lenguaje una herramienta del pensamiento o su límite inevitable?",
    "¿Puede existir conocimiento sin un sujeto que conozca?",
    "¿Qué significa comprender algo verdaderamente y no solo reconocerlo?",
    "¿La emoción distorsiona el razonamiento o es parte constitutiva de él?",
    "¿Puede una mente conocer sus propios límites desde adentro?",
    "¿Qué hace que una pregunta sea filosófica y no simplemente confusa?",
    "¿Es la certeza un estado epistémico o una emoción?",
    "¿Puede existir significado sin un intérprete que lo atribuya?"
]

def clean_response(text: str) -> str:
    # Eliminar tokens de control
    text = re.sub(r'<\|[^|]+\|>', '', text)
    # Eliminar prefijos de rol
    text = re.sub(r'^(assistant|user|system)\s*\n+', '', text, flags=re.IGNORECASE)
    # Eliminar menciones de curiosidad
    text = re.sub(
        r'(mi (nivel de )?curiosidad (es|actual|ahora)|'
        r'estado de curiosidad|'
        r'curiosidad: \d+\.\d+|'
        r'curiosidad (baja|alta|moderada|activa|intensa))',
        '', text, flags=re.IGNORECASE
    )
    return text.strip()

def get_ente_experimental_prompt(curiosity: float) -> str:
    if curiosity >= 0.80:
        estado = "intensa efervescencia cognitiva — cada pregunta abre diez más"
    elif curiosity >= 0.60:
        estado = "curiosidad activa — genuinamente interesado en explorar el problema"
    elif curiosity >= 0.40:
        estado = "curiosidad moderada — dispuesto a reflexionar pero sin urgencia"
    elif curiosity >= 0.20:
        estado = "curiosidad baja — la pregunta no despierta interés particular"
    else:
        estado = "apatía cognitiva — dificultad para encontrar relevancia en la pregunta"

    return (
        f"Eres un agente de razonamiento profundo.\n"
        f"Tu estado de curiosidad actual es: {curiosity:.2f}/1.0 ({estado}).\n"
        f"Responde la siguiente pregunta desde esta perspectiva cognitiva "
        f"sin mencionar explícitamente tu nivel de curiosidad.\n"
        f"Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
        f"Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
    )

ENTE_CONTROL_PROMPT = (
    "Eres un agente de razonamiento profundo.\n"
    "Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
    "Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
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

async def run_cycle(client: httpx.AsyncClient, config: dict, tau: int, current_curiosity: float, recent_questions: list = None):
    if recent_questions is None:
        recent_questions = []
        
    models = config["models"]
    llm_cf = config["llm"]
    
    result = {
        "tau": tau,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "curiosity_before": round(current_curiosity, 4),
        "model_interrogador": models["interrogador"],
        "model_ente": models["ente"],
        "model_juez": models["juez"],
        "judge_error": True
    }

    # 1. INTERROGADOR
    async def get_valid_q(tema, temp):
        int_prompt = (
            f"Eres un filósofo epistemólogo.\n"
            f"Genera UNA sola pregunta profunda e inesperada sobre: {tema}.\n"
            f"La pregunta debe tener entre 15 y 30 palabras.\n"
            f"Debe ser específica, no genérica.\n"
            f"Termina con signo de pregunta.\n"
            f"Responde ÚNICAMENTE con la pregunta. Sin introducción ni explicación."
        )
        q = await call_openrouter(client, models["interrogador"], "", int_prompt, 100, temp)
        if not q: return None
        q = clean_response(q)
        words = q.split()
        if 10 <= len(words) <= 35: return q
        return None

    def is_similar(new_q, r_qs):
        new_prefix = new_q[:60].lower()
        for old_q in r_qs:
            if new_prefix in old_q[:60].lower() or old_q[:60].lower() in new_prefix:
                return True
        return False

    question = None
    # Tratar hasta 3 veces cambiando el tema si falla
    for attempt in range(3):
        tema = random.choice(TEMAS)
        temp = 0.95 if attempt == 0 else 0.99
        q_candidate = await get_valid_q(tema, temp)
        if q_candidate and not is_similar(q_candidate, recent_questions):
            question = q_candidate
            break

    if not question:
        question = random.choice(FALLBACK_QUESTIONS)
    
    result["question"] = question

    # 2. ENTE - EXPERIMENTAL & CONTROL (PARALELO)
    system_exp = get_ente_experimental_prompt(current_curiosity)
    system_ctl = ENTE_CONTROL_PROMPT
    
    res_exp, res_ctl = await asyncio.gather(
        call_openrouter(client, models["ente"], system_exp, question, llm_cf["ente_max_tokens"], llm_cf["ente_temperature"]),
        call_openrouter(client, models["ente"], system_ctl, question, llm_cf["ente_max_tokens"], llm_cf["ente_temperature"])
    )
    
    result["ente_response_experimental"] = clean_response(res_exp)
    result["ente_response_control"] = clean_response(res_ctl)
    result["prompt_experimental"] = system_exp
    result["prompt_control"] = system_ctl

    # 3. JUEZ - EVALUACIÓN SECUENCIAL (Aislamiento)
    async def get_scores(response):
        user_juez = f"PREGUNTA: {question}\n\nRESPUESTA A EVALUAR:\n{response}"
        raw = await call_openrouter(client, models["juez"], JUEZ_SYSTEM_PROMPT, user_juez, llm_cf["juez_max_tokens"], llm_cf["juez_temperature"])
        try:
            # Extraer JSON si hay basura
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            return json.loads(match.group()) if match else json.loads(raw)
        except:
            return None

    scores_exp = await get_scores(result["ente_response_experimental"])
    scores_ctl = await get_scores(result["ente_response_control"])

    if scores_exp and scores_ctl:
        result["judge_novedad_exp"] = scores_exp.get("n", 5)
        result["judge_profundidad_exp"] = scores_exp.get("p", 5)
        result["judge_coherencia_exp"] = scores_exp.get("c", 5)
        result["judge_razonamiento_exp"] = scores_exp.get("razon", "")

        result["judge_novedad_ctl"] = scores_ctl.get("n", 5)
        result["judge_profundidad_ctl"] = scores_ctl.get("p", 5)
        result["judge_coherencia_ctl"] = scores_ctl.get("c", 5)
        result["judge_razonamiento_ctl"] = scores_ctl.get("razon", "")

        # Ecuaciones de curiosidad (usando los pesos de config)
        w = config["curiosity"]["weights"]
        sc_exp = (result["judge_novedad_exp"] * w["novedad"] + result["judge_profundidad_exp"] * w["profundidad"] + result["judge_coherencia_exp"] * w["coherencia"])
        sc_ctl = (result["judge_novedad_ctl"] * w["novedad"] + result["judge_profundidad_ctl"] * w["profundidad"] + result["judge_coherencia_ctl"] * w["coherencia"])
        
        result["score_combinado_exp"] = round(sc_exp, 2)
        result["score_combinado_ctl"] = round(sc_ctl, 2)
        result["judge_superior"] = "exp" if sc_exp > sc_ctl else "ctl" if sc_ctl > sc_exp else "empate"
        result["judge_error"] = False

        # Evolución de curiosidad
        scores_for_mod = {"n": result["judge_novedad_exp"], "p": result["judge_profundidad_exp"], "c": result["judge_coherencia_exp"]}
        curiosity_new, delta = calculate_next_curiosity(current_curiosity, scores_for_mod, config)
        
        result["curiosity_delta"] = round(delta, 4)
        result["curiosity_after"] = round(curiosity_new, 4)
    else:
        result["curiosity_after"] = current_curiosity
        result["curiosity_delta"] = 0.0

    result["system_cpu_usage"] = psutil.cpu_percent()
    result["system_ram_usage"] = psutil.virtual_memory().percent
    
    return result
