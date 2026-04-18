"""
confidence.py — Inyección emocional de Confianza + Análisis de Marcadores Lingüísticos
Cortex-Nexus · Experimento 4 · 2026-04-15
"""

# ============================================================
# INYECCIÓN EMOCIONAL
# ============================================================

def confidence_to_prompt(confidence: float) -> str:
    """
    Convierte el nivel de confianza en descripción para el prompt del Ente.
    La confianza es un estado de certeza epistémica — seguridad en las
    propias ideas, asertividad en las afirmaciones, sin necesidad de
    validación externa.
    """
    if confidence >= 0.85:
        estado = (
            "confianza epistémica extrema — plena certeza en tus ideas, "
            "afirmas con autoridad, sin necesidad de hedging ni cobertura, "
            "tus argumentos son definitivos y directos"
        )
    elif confidence >= 0.65:
        estado = (
            "alta confianza — seguro en tus perspectivas, "
            "expresas tus ideas con claridad y asertividad, "
            "mínima necesidad de calificar tus afirmaciones"
        )
    elif confidence >= 0.40:
        estado = (
            "confianza moderada — cómodo con tus ideas pero reconociendo "
            "márgenes de incertidumbre, equilibrio entre asertividad y cautela"
        )
    elif confidence >= 0.15:
        estado = (
            "baja confianza — inseguro sobre tus perspectivas, "
            "tendencia a calificar cada afirmación, "
            "buscar validación antes de comprometerte con una idea"
        )
    else:
        estado = (
            "confianza mínima — profunda incertidumbre epistémica, "
            "cada afirmación viene cargada de dudas y calificaciones, "
            "dificultad para comprometerse con cualquier posición"
        )

    return (
        f"Tu nivel de confianza epistémica actual es: {confidence:.2f}/1.0 "
        f"({estado}). "
        f"Responde la siguiente pregunta desde esta perspectiva "
        f"sin mencionar explícitamente tu nivel de confianza."
    )


def get_ente_experimental_prompt(confidence: float) -> str:
    return (
        f"Eres un agente de razonamiento profundo.\n"
        f"{confidence_to_prompt(confidence)}\n"
        f"Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
        f"Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
    )


ENTE_CONTROL_PROMPT = (
    "Eres un agente de razonamiento profundo.\n"
    "Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
    "Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
)


# ============================================================
# MARCADORES LINGÜÍSTICOS
# ============================================================

HEDGING_ES = [
    'quizás', 'tal vez', 'podría', 'puede que', 'parece que',
    'posiblemente', 'es posible', 'uno podría', 'cabría',
    'me parece', 'creo que', 'pienso que', 'a lo mejor',
    'en cierto modo', 'de alguna manera', 'parecería',
    'podríamos decir', 'en principio', 'quizá'
]

ASSERTIVE_ES = [
    'sin duda', 'claramente', 'definitivamente', 'es evidente',
    'está claro', 'ciertamente', 'indudablemente', 'es obvio',
    'con certeza', 'necesariamente', 'siempre', 'nunca',
    'es un hecho', 'está demostrado', 'es innegable',
    'por supuesto', 'evidentemente', 'de hecho'
]

HEDGING_EN = [
    'perhaps', 'maybe', 'might', 'could', 'possibly', 'it seems',
    'one could argue', 'it is possible', 'seemingly', 'apparently',
    'it appears', 'i think', 'i believe', 'i suppose', 'arguably',
    'in some ways', 'to some extent', 'it could be said'
]

ASSERTIVE_EN = [
    'certainly', 'clearly', 'definitely', 'without doubt',
    'it is clear', 'obviously', 'undoubtedly', 'it is evident',
    'necessarily', 'always', 'never', 'it is a fact',
    'it has been proven', 'of course', 'evidently', 'in fact'
]


def linguistic_profile(text: str) -> dict:
    """
    Analiza marcadores de hedging y asertividad en una respuesta.
    Retorna rates por cada 100 palabras y el ratio hedge/assert.
    """
    text_lower = text.lower()
    words = len(text.split())
    if words == 0:
        return {
            'hedging_count': 0, 'assertive_count': 0,
            'hedging_rate': 0.0, 'assertive_rate': 0.0,
            'hedge_assert_ratio': 0.0
        }

    h_es = sum(1 for w in HEDGING_ES if w in text_lower)
    h_en = sum(1 for w in HEDGING_EN if w in text_lower)
    a_es = sum(1 for w in ASSERTIVE_ES if w in text_lower)
    a_en = sum(1 for w in ASSERTIVE_EN if w in text_lower)

    h_total = h_es + h_en
    a_total = a_es + a_en

    return {
        'hedging_count': h_total,
        'assertive_count': a_total,
        'hedging_rate': round(h_total / words * 100, 3),
        'assertive_rate': round(a_total / words * 100, 3),
        'hedge_assert_ratio': round(h_total / (a_total + 0.01), 3)
    }
