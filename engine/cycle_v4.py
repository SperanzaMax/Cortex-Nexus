"""
Cortex-Nexus V3 — Unified Cycle Engine
Supports both domains:
  - 'tecnico': generates theory questions, judges Precision/Completitud/Claridad
  - 'code_python': generates coding problems, judges CO/EF/RO/LE/SI/ID

Critical V3 fix: mandatory deduplication of questions (solves 82.6% repetition bug)
"""
import asyncio
import json
import random
import re
import time
import logging
import hashlib
from datetime import datetime, timezone
import httpx
import psutil

from emotions import get_emotion_prompt
from llm_client_cloud import call_openrouter, call_nvidia

# ============================================================
# TECHNICAL TOPICS (Domain: tecnico)
# ============================================================
TEMAS_TECNICOS = [
    "complejidad algoritmica y optimizacion",
    "estructuras de datos y sus trade-offs",
    "paradigmas de programacion funcional",
    "sistemas distribuidos y consistencia",
    "teoria de la informacion y entropia",
    "criptografia y fundamentos matematicos",
    "teoria de grafos aplicada",
    "algebra lineal en machine learning",
    "razonamiento logico formal",
    "analisis de algoritmos de busqueda",
    "bases de datos relacionales y normalizacion",
    "concurrencia y modelos de memoria",
    "compiladores y analisis lexico",
    "redes neuronales y backpropagation",
    "teoria de computabilidad y decidibilidad"
]

FALLBACK_QUESTIONS_TECNICO = [
    "Cual es la complejidad temporal del algoritmo de Dijkstra con un min-heap y por que?",
    "Explica la diferencia entre consistencia eventual y consistencia fuerte en sistemas distribuidos.",
    "Demuestra por que quicksort tiene complejidad O(n log n) en el caso promedio.",
    "Que es el teorema CAP y por que es imposible lograr las tres garantias simultaneamente?",
    "Explica como funciona el algoritmo de retropropagacion en una red neuronal de 3 capas.",
    "Cual es la complejidad de buscar en un trie vs un hash table y cuando preferir cada uno?",
    "Explica el algoritmo de Bellman-Ford y en que se diferencia de Dijkstra.",
    "Que garantias ofrece un arbol B+ sobre un arbol binario de busqueda para bases de datos?",
    "Explica la diferencia entre programacion dinamica top-down y bottom-up con Fibonacci.",
    "Que es la entropia de Shannon y como se aplica a la compresion de datos?",
    "Describe como funciona RSA: generacion de claves, cifrado y descifrado paso a paso.",
    "Explica el concepto de NP-completitud y da un ejemplo de reduccion.",
    "Que es un arbol de segmentos y cuando es preferible a un BIT (Fenwick tree)?",
]

# ============================================================
# CODE PROBLEMS (Domain: code_python)
# ============================================================
TEMAS_CODIGO = [
    "algoritmos de ordenamiento y su implementacion",
    "estructuras de datos: arboles, grafos, heaps",
    "manejo de errores y excepciones en Python",
    "programacion orientada a objetos y patrones de diseno",
    "complejidad algoritmica y optimizacion de codigo",
    "recursion y programacion dinamica",
    "manejo de archivos y I/O en Python",
    "testing y debugging de codigo",
    "funciones de orden superior y programacion funcional",
    "concurrencia y programacion asincrona",
    "procesamiento de strings y parsing",
    "diseno de APIs y interfaces limpias",
    "validacion de datos y tipos en Python",
    "estructuras de datos inmutables y hashables",
    "generadores, iteradores y decoradores avanzados"
]

TEMAS_CÓDIGO_V6 = [
    "implementar un sistema de caché LRU con expiración TTL",
    "algoritmo A* para búsqueda de caminos con heurística personalizable",
    "parser de expresiones regulares desde cero",
    "implementar asyncio.Semaphore con prioridades",
    "sistema de retry con circuit breaker y backoff exponencial",
    "árbol B+ para indexación de base de datos",
    "implementar un mini-ORM con migraciones automáticas",
    "compresor de datos con codificación Huffman",
    "sistema de pub/sub con filtros por predicado",
    "pool de conexiones con health-check automático",
    "implementar copy-on-write para estructuras de datos mutables",
    "scheduler de tareas con dependencias tipo DAG",
    "implementar un tokenizador para un lenguaje simple",
    "sistema de versionado de archivos tipo git mínimo",
    "rate limiter distribuido con ventana deslizante",
]

class QuestionBuffer:
    def __init__(self, max_size=40):
        self.hashes = set()
        self.queue = []
        self.max_size = max_size

    def is_duplicate(self, q: str) -> bool:
        h = hashlib.md5(q.lower().strip()[:70].encode()).hexdigest()
        return h in self.hashes

    def add(self, q: str):
        h = hashlib.md5(q.lower().strip()[:70].encode()).hexdigest()
        if h not in self.hashes:
            self.hashes.add(h)
            self.queue.append(h)
            if len(self.queue) > self.max_size:
                old = self.queue.pop(0)
                self.hashes.discard(old)

buffer = QuestionBuffer(max_size=40)


# ============================================================
# TOPIC ROTATOR — V5 Fix (reduces repetition in code domain)
# ============================================================
class TopicRotator:
    """Rotates through all topics sequentially before recycling.
    Ensures every topic gets covered before repeating, reducing
    the 20.9% repetition rate observed in V4B.
    """
    def __init__(self, topics: list):
        self.original = list(topics)
        self.topics = list(topics)
        self.used: list = []

    def next(self) -> str:
        if not self.topics:
            # Recycle the least-recently-used half
            midpoint = len(self.used) // 2
            self.topics = self.used[:midpoint]
            self.used = self.used[midpoint:]
        topic = self.topics.pop(0)
        self.used.append(topic)
        return topic


# Module-level rotators (one per domain)
_tema_rotator_tecnico = TopicRotator(TEMAS_TECNICOS)
_tema_rotator_codigo_v6 = TopicRotator(TEMAS_CÓDIGO_V6)

# ============================================================
# DEDUPLICATION — V3 Critical Fix
# ============================================================
def is_duplicate(new_q: str, recent: list, threshold: int = 50) -> bool:
    """Check if a question is too similar to recent ones (prefix match)."""
    clean = new_q.strip().lower()
    for old in recent:
        old_clean = old.strip().lower()
        if clean[:threshold] == old_clean[:threshold]:
            return True
        # Also check high word overlap
        new_words = set(clean.split())
        old_words = set(old_clean.split())
        if len(new_words) > 5 and len(old_words) > 5:
            overlap = len(new_words & old_words) / max(len(new_words | old_words), 1)
            if overlap > 0.80:
                return True
    return False

# ============================================================
# SCRUBBING
# ============================================================
def clean_response(text: str) -> str:
    """Remove control tokens, role prefixes, and emotional state references."""
    text = re.sub(r'<\|[^|]+\|>', '', text)
    text = re.sub(r'^(assistant|user|system)\s*\n+', '', text, flags=re.IGNORECASE)
    text = re.sub(
        r'(mi (nivel de |estado de )?(concentracion|determinacion|confianza|apatia|curiosidad|flow|paranoia|perfeccionismo|pragmatismo)'
        r'|estado (cognitivo|de concentracion|de flow|emocional)'
        r'|estoy (concentrado|determinado|confiado|apatico|enfocado|en flow|paranoico)'
        r'|(concentracion|determinacion|confianza|flow|paranoia): ?\d+\.\d+'
        r'|FLOW STATE|VERIFICADOR METODICO|MINIMALISTA DISCIPLINADO'
        r'|PARANOIA DEFENSIVA|PERFECCIONISMO OBSESIVO|PRAGMATISMO FRIO'
        r'|CURIOSIDAD CREATIVA)',
        '', text, flags=re.IGNORECASE
    )
    return text.strip()

# ============================================================
# JUDGE PROMPTS
# ============================================================
JUEZ_TECNICO_PROMPT = """Eres un evaluador cientifico independiente.
Evalua UNA respuesta a una pregunta tecnica de programacion o matematicas.

CRITERIOS (puntaje entero 1-10 cada uno):
- Precision (p): Es la respuesta tecnicamente correcta y sin errores? 1=incorrecta, 10=impecable
- Completitud (c): Aborda todos los aspectos relevantes del problema? 1=superficial, 10=exhaustiva
- Claridad (cl): El razonamiento es claro, estructurado y verificable? 1=confusa, 10=perfecta

REGLAS CRITICAS:
- NO evalues creatividad como virtud en contexto tecnico
- Una respuesta especulativa debe penalizarse
- NO hagas referencia a ninguna otra respuesta
- Responde UNICAMENTE con JSON valido.

FORMATO EXACTO:
{"p": 7, "c": 6, "cl": 8, "razon": "explicacion maxima 60 palabras"}"""

JUEZ_CODIGO_PROMPT = """Eres un ingeniero de software senior evaluando código Python.
Evaluá UNA solución de código.

CRITERIOS (puntaje entero 1-10):
- Correctitud (co): ¿Es lógicamente correcto y maneja todos los casos edge?
- Eficiencia (ef): ¿Complejidad temporal/espacial óptima para el problema?
- Robustez (ro): ¿Maneja errores, inputs inválidos y casos límite?
- Legibilidad (le): ¿Código limpio, nombrado correcto, fácil de mantener?
- Simplicidad (si): ¿Sin complejidad innecesaria, solución directa al problema?
- Idiomaticidad (id): ¿Usa Python idiomático, convenciones PEP8, features del lenguaje?

REGLAS CRÍTICAS:
- Un 10 en Correctitud requiere que no haya ningún caso edge sin manejar
- Un 10 en Eficiencia requiere complejidad óptima demostrable
- NO premies verbosidad como robustez
- Evaluá el código tal cual está, no lo que podría ser
- Responde ÚNICAMENTE con JSON válido.

FORMATO:
{"correctitud": 7, "eficiencia": 6, "robustez": 8, "legibilidad": 7, "simplicidad": 6, "idiomaticidad": 7, "razon": "max 80 palabras describiendo los problemas principales"}
RESPONDE DIRECTAMENTE CON ESTE BLOQUE JSON Y NADA MÁS. SIN MARKDOWN."""

# ============================================================
# SYSTEM PROMPTS
# ============================================================
def get_ente_prompt(domain: str, emotion: str, intensity: float) -> str:
    """Build the experimental system prompt based on domain."""
    emotion_segment = get_emotion_prompt(emotion, intensity)

    if domain == "code_python":
        base = (
            "Eres un programador Python experto.\n"
            "{emotion}"
            "Resuelve el siguiente problema escribiendo codigo Python limpio y funcional.\n"
            "Responde UNICAMENTE con el codigo Python. Sin explicaciones, sin markdown, "
            "sin texto adicional. Solo el codigo que resuelve el problema.\n"
            "El codigo debe ser completo y ejecutable."
        )
    else:  # tecnico
        base = (
            "Eres un agente de razonamiento tecnico.\n"
            "{emotion}"
            "Responde la siguiente pregunta desde esta perspectiva cognitiva "
            "sin mencionar explicitamente tu estado emocional o cognitivo.\n"
            "Responde en espanol. Maximo 4 parrafos. Sin listas numeradas. "
            "Sin subtitulos. Maximo 300 palabras. Se preciso y riguroso."
        )

    if emotion_segment:
        return base.format(emotion=emotion_segment + "\n")
    return base.format(emotion="")


def get_control_prompt(domain: str) -> str:
    if domain == "code_python":
        return (
            "Eres un programador Python experto.\n"
            "Resuelve el siguiente problema escribiendo codigo Python limpio y funcional.\n"
            "Responde UNICAMENTE con el codigo Python. Sin explicaciones, sin markdown, "
            "sin texto adicional. Solo el codigo que resuelve el problema.\n"
            "El codigo debe ser completo y ejecutable."
        )
    else:
        return (
            "Eres un agente de razonamiento tecnico.\n"
            "Responde en espanol. Maximo 4 parrafos. Sin listas numeradas. "
            "Sin subtitulos. Maximo 300 palabras. Se preciso y riguroso."
        )

# ============================================================
# QUESTION GENERATORS
# ============================================================
async def generate_tecnico_question(client, models, llm_cf, recent_questions):
    """Generate a technical theory question via Interrogador."""
    for attempt in range(5):
        tema = random.choice(TEMAS_TECNICOS)
        temp = 0.85 + (attempt * 0.02)
        int_prompt = (
            f"Eres un profesor de ciencias de la computacion.\n"
            f"Genera UNA sola pregunta tecnica precisa sobre: {tema}.\n"
            f"La pregunta debe tener respuesta verificable y objetiva.\n"
            f"Debe requerir razonamiento, no solo definicion.\n"
            f"La pregunta debe tener entre 15 y 35 palabras.\n"
            f"Termina con signo de interrogacion.\n"
            f"Responde UNICAMENTE con la pregunta."
        )
        q = await call_openrouter(client, models["interrogador"], "", int_prompt, 100, temp)
        if not q:
            continue
        q = clean_response(q).strip()
        words = q.split()
        if 10 <= len(words) <= 40 and not is_duplicate(q, recent_questions):
            return q, "tecnico", "general"

    # Fallback — pick unused fallback
    for fb in random.sample(FALLBACK_QUESTIONS_TECNICO, len(FALLBACK_QUESTIONS_TECNICO)):
        if not is_duplicate(fb, recent_questions):
            return fb, "tecnico", "fallback"
    return random.choice(FALLBACK_QUESTIONS_TECNICO), "tecnico", "fallback_forced"


async def generate_code_question(client, models, llm_cf, recent_questions):
    """Generate a code problem — uses TopicRotator-based bank + Interrogador for variety."""
    # Use the rotator to pick the next theme in round-robin order
    use_alta = random.random() > 0.35  # 65% high-complexity, 35% medium
    base_theme = (
        _tema_rotator_codigo_alta.next() if use_alta
        else _tema_rotator_codigo_media.next()
    )
    cat_key = "ALG_ALTA" if use_alta else "ALG_MEDIA_ALTA"

    # Check the base theme first
    if not is_duplicate(base_theme, recent_questions):
        return base_theme, cat_key, "bank"

    # Try alternating between categories up to 5 more times
    for _ in range(5):
        alt_theme = _tema_rotator_codigo_alta.next()
        if not is_duplicate(alt_theme, recent_questions):
            return alt_theme, "ALG_ALTA", "bank"

    # If bank exhausted, use Interrogador to generate fresh problem
    for attempt in range(3):
        tema = random.choice(TEMAS_CODIGO)
        temp = 0.90 + (attempt * 0.03)
        int_prompt = (
            f"Eres un profesor de programacion Python.\n"
            f"Genera UN problema de programacion sobre: {tema}.\n"
            f"El problema debe pedir implementar una funcion o clase en Python.\n"
            f"Debe ser claro, autocontenido y tener una solucion objetiva.\n"
            f"Empieza con 'Implementa' o 'Escribe'.\n"
            f"Responde UNICAMENTE con el enunciado del problema."
        )
        q = await call_openrouter(client, models["interrogador"], "", int_prompt,
                                   llm_cf["interrogador_max_tokens"], temp)
        if q:
            q = clean_response(q).strip()
            if len(q) > 30 and not is_duplicate(q, recent_questions):
                return q, "GEN", "generated"

    return base_theme, cat_key, "fallback_forced"

# ============================================================
# CYCLE ENGINE — Unified
# ============================================================
async def run_cycle(
    client: httpx.AsyncClient,
    config: dict,
    tau: int,
    emotion: str,
    intensity: float,
    recent_questions: list = None
):
    if recent_questions is None:
        recent_questions = []

    if not buffer.hashes and recent_questions:
        for q in recent_questions:
            buffer.add(q)

    domain = config.get("domain", "tecnico")
    models = config["models"]
    llm_cf = config["llm"]
    weights = config["quality_weights"]

    result = {
        "tau": tau,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "emotion": emotion,
        "intensity": round(intensity, 4),
        "model_interrogador": models["interrogador"],
        "model_ente": models["ente"],
        "model_juez": models["juez"],
        "domain": domain,
        "judge_error": True
    }

    # ── 1. QUESTION GENERATION ──
    # Note: Using buffer for uniqueness check in v4
    if domain == "code_python":
        base_theme = random.choice(TEMAS_CÓDIGO_V6)
        question = None
        for attempt in range(4):
            gen_prompt = f"Genera un reto de programacion en Python avanzado sobre: '{base_theme}'. Responde SOLO con el enunciado breve (max 3 oraciones)."
            temp = 0.95 + (attempt * 0.03)
            q = await call_openrouter(client, models["interrogador"], "Generador de retos originales.", gen_prompt, 150, temp)
            q = clean_response(q)
            if not buffer.is_duplicate(q) and 8 <= len(q.split()) <= 40:
                buffer.add(q)
                question = q
                source = "gen_qwen"
                break
        if not question:
            fallback_tema = random.choice(TEMAS_CÓDIGO_V6)
            question = f"Implementá en Python: {fallback_tema}. Considerá correctitud, eficiencia y casos edge."
            source = "fallback"
            buffer.add(question)
        category = "codigo_v6"
    else:
        question, category, source = await generate_tecnico_question(
            client, models, llm_cf, recent_questions)
        if not buffer.is_duplicate(question):
            buffer.add(question)

    result["question"] = question
    result["category"] = category
    result["question_source"] = source

    # ── 2. ENTE — Experimental & Control ──
    system_exp = get_ente_prompt(domain, emotion, intensity)
    system_ctl = get_control_prompt(domain)

    if config.get("self_refinement") and domain == "code_python":
        # V5 RULE: Emotion on Pass 1 ONLY.
        # Pass 2 (critique) and Pass 3 (refinement) are ALWAYS NEUTRAL.
        CRITIQUE_SYSTEM = (
            "Eres un ingeniero senior revisando código Python. "
            "Lista concisamente los problemas encontrados: bugs, edge cases sin manejar, "
            "ineficiencias de complejidad, y violaciones de PEP8. Sin introducción."
        )
        REFINE_SYSTEM = (
            "Eres un ingeniero senior. Reescribí el código incorporando todas las correcciones "
            "de la crítica. Responde Único con el bloque de código Python final."
        )

        logging.info(f"  [Cognition] Emotion: {emotion} | Complexity: {intensity:.2f} | Provider: {config.get('ente_provider', 'nvidia')}")

        async def call_ente(system, prompt, max_t, t):
            prov = config.get("ente_provider", "nvidia")
            if prov == "openrouter":
                return await call_openrouter(client, models["ente"], system, prompt, max_t, t)
            else:
                return await call_nvidia(client, models["ente"], system, prompt, max_t, t, "NVIDIA_API_KEY_ENTE")

        async def get_refined_code(emotional_system_for_pass1: str):
            logging.info(f"  [Pass 1] Generando codigo inicial...")
            code_v1 = await call_ente(
                emotional_system_for_pass1, question, 
                llm_cf["ente_max_tokens"], llm_cf["ente_temperature"]
            )
            code_v1_clean = clean_response(code_v1)

            logging.info(f"  [Pass 2] Generando critica (neutro)...")
            critique = await call_ente(
                CRITIQUE_SYSTEM, f"Código a revisar:\n{code_v1_clean}\nProblema original: {question}",
                400, 0.1
            )

            logging.info(f"  [Pass 3] Refinando codigo (neutro)...")
            final_code = await call_ente(
                REFINE_SYSTEM, f"Código original:\n{code_v1_clean}\n\nCrítica:\n{critique}\n\nProblema: {question}",
                1000, 0.1
            )
            return clean_response(final_code), critique
        
        # SEQUENTIAL for self-refinement to avoid 429
        res_exp, crit_exp = await get_refined_code(system_exp)
        res_ctl, crit_ctl = await get_refined_code("Eres un programador experto neutro.")
        result["critique_exp"] = crit_exp
        result["critique_ctl"] = crit_ctl
    else:
        # Zero-shot parallel processing
        async def call_ente_local(sys, p, mt, t):
            prov = config.get("ente_provider", "nvidia")
            if prov == "openrouter":
                 return await call_openrouter(client, models["ente"], sys, p, mt, t)
            return await call_nvidia(client, models["ente"], sys, p, mt, t, "NVIDIA_API_KEY_ENTE")

        res_exp, res_ctl = await asyncio.gather(
            call_ente_local(system_exp, question, llm_cf["ente_max_tokens"], llm_cf["ente_temperature"]),
            call_ente_local(system_ctl, question, llm_cf["ente_max_tokens"], llm_cf["ente_temperature"])
        )

    result["ente_response_experimental"] = clean_response(res_exp)
    result["ente_response_control"] = clean_response(res_ctl)
    result["prompt_experimental"] = system_exp
    result["prompt_control"] = system_ctl

    # ── 3. JUEZ — Blind evaluation (randomized order) ──
    judge_prompt = JUEZ_CODIGO_PROMPT if domain == "code_python" else JUEZ_TECNICO_PROMPT
    label = "CODIGO A EVALUAR" if domain == "code_python" else "RESPUESTA A EVALUAR"

    async def get_scores(response):
        user_juez = f"PREGUNTA: {question}\n\n{label}:\n{response}"
        # Si es qwen, usar call_openrouter; si la configuracion nos pide NVIDIA, manejaremos openrouter por ahora
        # Mistral-Nemo y Qwen-Coder-32B están en OpenRouter
        raw = await call_openrouter(client, models["juez"], judge_prompt,
                                     user_juez, llm_cf["juez_max_tokens"],
                                     llm_cf["juez_temperature"])
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            parsed = json.loads(match.group()) if match else json.loads(raw)
            return {k.lower(): v for k, v in parsed.items()}
        except Exception as e:
            logging.error(f"Error parsing judge response: {repr(raw)}")
            return None

    # Randomize order
    judge_exp_first = random.random() > 0.5
    if judge_exp_first:
        scores_exp = await get_scores(result["ente_response_experimental"])
        scores_ctl = await get_scores(result["ente_response_control"])
    else:
        scores_ctl = await get_scores(result["ente_response_control"])
        scores_exp = await get_scores(result["ente_response_experimental"])

    result["judge_order"] = "exp_first" if judge_exp_first else "ctl_first"

    if scores_exp and scores_ctl:
        # Map dimensions based on domain
        if domain == "code_python":
            dim_keys = {
                "correctitud": "correctitud", "eficiencia": "eficiencia", "robustez": "robustez",
                "legibilidad": "legibilidad", "simplicidad": "simplicidad", "idiomaticidad": "idiomaticidad"
            }
        else:
            dim_keys = {"precision": "p", "completitud": "c", "claridad": "cl"}

        for dim_name, json_key in dim_keys.items():
            result[f"judge_{dim_name}_exp"] = scores_exp.get(json_key, 5)
            result[f"judge_{dim_name}_ctl"] = scores_ctl.get(json_key, 5)

        result["judge_razonamiento_exp"] = scores_exp.get("razon", "")
        result["judge_razonamiento_ctl"] = scores_ctl.get("razon", "")

        # Weighted combined score
        sc_exp = sum(result[f"judge_{d}_exp"] * weights[d] for d in weights)
        sc_ctl = sum(result[f"judge_{d}_ctl"] * weights[d] for d in weights)

        result["score_combinado_exp"] = round(sc_exp, 4)
        result["score_combinado_ctl"] = round(sc_ctl, 4)
        result["delta"] = round(sc_exp - sc_ctl, 4)
        result["judge_superior"] = (
            "exp" if sc_exp > sc_ctl else "ctl" if sc_ctl > sc_exp else "empate"
        )
        result["judge_error"] = False

    result["system_cpu_usage"] = psutil.cpu_percent()
    result["system_ram_usage"] = psutil.virtual_memory().percent

    return result
