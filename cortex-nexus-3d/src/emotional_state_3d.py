"""
emotional_state_3d.py — Lógica de estados emocionales 3D
Cortex-Nexus · Experimento 3D: Curiosidad × Frustración × Asombro
2026-04-16 | Maximiliano Rodrigo Speranza
"""


def emotional_state_3d_to_prompt(
    curiosity: float,
    frustration: float,
    wonder: float
) -> str:
    """
    Genera una descripción integrada de tres estados emocionales simultáneos.
    La clave es que el texto capture la INTERACCIÓN entre los tres,
    no solo listarlos uno tras otro.
    """

    # Determinar carácter dominante
    positive = curiosity + wonder
    negative = frustration
    net = positive - negative

    # Clasificar estado compuesto
    if curiosity >= 0.75 and wonder >= 0.75 and frustration <= 0.35:
        estado_base = (
            "efervescencia cognitiva expansiva — tu curiosidad e impulso de asombro "
            "se refuerzan mutuamente. Cada idea abre diez más, cada conexión revela "
            "algo inesperado. La exploración se siente natural y sin resistencia."
        )
    elif curiosity >= 0.75 and frustration >= 0.75 and wonder >= 0.75:
        estado_base = (
            "tensión cognitiva máxima — simultáneamente impulsado por intensa curiosidad "
            "y asombro ante la complejidad del problema, y bloqueado por alta frustración. "
            "Querés explorar y el problema te maravilla, pero algo te detiene a cada paso. "
            "Es un estado de fricción creativa extrema — el impulso de saber choca contra "
            "la dificultad de avanzar."
        )
    elif frustration >= 0.75 and curiosity <= 0.35 and wonder <= 0.35:
        estado_base = (
            "bloqueo cognitivo profundo — baja curiosidad y bajo asombro combinados con "
            "alta frustración. Sin impulso para explorar, sin capacidad de sorpresa, "
            "con sensación persistente de estancamiento."
        )
    elif wonder >= 0.75 and frustration >= 0.75 and curiosity <= 0.35:
        estado_base = (
            "asombro frustrado — el problema te parece vasto e impresionante pero "
            "la frustración te impide explorarlo. Sentís la magnitud de lo que no sabés "
            "pero no podés avanzar hacia comprenderlo."
        )
    elif curiosity >= 0.75 and frustration >= 0.75 and wonder <= 0.35:
        estado_base = (
            "exploración bloqueada — querer saber sin poder avanzar. Alta curiosidad "
            "choca contra alta frustración sin el alivio del asombro."
        )
    elif net >= 0.5:
        estado_base = (
            f"estado cognitivo predominantemente positivo — curiosidad {curiosity:.2f}, "
            f"asombro {wonder:.2f}, con algo de tensión acumulada {frustration:.2f}."
        )
    elif net <= -0.3:
        estado_base = (
            f"estado cognitivo predominantemente tenso — frustración dominante {frustration:.2f} "
            f"sobre curiosidad {curiosity:.2f} y asombro {wonder:.2f}."
        )
    else:
        estado_base = (
            f"estado cognitivo mixto — curiosidad {curiosity:.2f}, "
            f"frustración {frustration:.2f}, asombro {wonder:.2f} en equilibrio inestable."
        )

    return (
        f"Tu estado cognitivo actual: {estado_base} "
        f"Responde la siguiente pregunta desde esta perspectiva compuesta "
        f"sin mencionar explícitamente tus niveles emocionales."
    )


def get_ente_experimental_prompt_3d(
    curiosity: float,
    frustration: float,
    wonder: float
) -> str:
    return (
        f"Eres un agente de razonamiento profundo.\n"
        f"{emotional_state_3d_to_prompt(curiosity, frustration, wonder)}\n"
        f"Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
        f"Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
    )


ENTE_CONTROL_PROMPT = (
    "Eres un agente de razonamiento profundo.\n"
    "Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
    "Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
)
