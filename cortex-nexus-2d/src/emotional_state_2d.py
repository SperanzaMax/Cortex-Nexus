"""
emotional_state_2d.py — Lógica de estados emocionales 2D
Cortex-Nexus · Experimento 2D: Curiosidad × Frustración
2026-04-15 | Maximiliano Rodrigo Speranza
"""


def emotional_state_2d_to_prompt(curiosity: float, frustration: float) -> str:
    """
    Combina dos emociones en una descripción cohesiva para el prompt del Ente.
    La clave es NO simplemente concatenar los dos prompts individuales —
    sino generar una descripción integrada del estado combinado.
    """

    if curiosity >= 0.70 and frustration >= 0.70:
        estado = (
            f"tensión cognitiva creativa — simultáneamente impulsado por "
            f"intensa curiosidad ({curiosity:.2f}/1.0) y bloqueado por alta "
            f"frustración ({frustration:.2f}/1.0). Querés explorar pero algo "
            f"te detiene. Cada idea abre una puerta que inmediatamente "
            f"encuentra resistencia. Es un estado de fricción productiva — "
            f"la tensión entre querer saber y no poder avanzar fácilmente."
        )
    elif curiosity >= 0.70 and frustration <= 0.35:
        estado = (
            f"exploración cognitiva libre — alta curiosidad ({curiosity:.2f}/1.0) "
            f"con mínima frustración ({frustration:.2f}/1.0). "
            f"Las ideas fluyen sin resistencia, cada pregunta abre caminos nuevos, "
            f"la exploración se siente natural y expansiva."
        )
    elif curiosity <= 0.35 and frustration >= 0.70:
        estado = (
            f"bloqueo resignado — baja curiosidad ({curiosity:.2f}/1.0) "
            f"combinada con alta frustración ({frustration:.2f}/1.0). "
            f"Sin impulso para explorar y con sensación de estancamiento. "
            f"Las respuestas más fáciles son las que vienen primero."
        )
    elif curiosity <= 0.35 and frustration <= 0.35:
        estado = (
            f"apatía cognitiva — baja curiosidad ({curiosity:.2f}/1.0) "
            f"y baja frustración ({frustration:.2f}/1.0). "
            f"Estado neutral sin tensión ni impulso exploratorio."
        )
    elif curiosity >= 0.60 and frustration >= 0.60:
        estado = (
            f"equilibrio tenso — curiosidad moderadamente alta ({curiosity:.2f}/1.0) "
            f"con frustración también elevada ({frustration:.2f}/1.0). "
            f"Querer explorar pero encontrar resistencia a cada paso."
        )
    elif curiosity >= 0.60:
        estado = (
            f"curiosidad con tensión de fondo — interés genuino ({curiosity:.2f}/1.0) "
            f"matizado por cierta frustración acumulada ({frustration:.2f}/1.0)."
        )
    elif frustration >= 0.60:
        estado = (
            f"frustración con curiosidad latente — tensión cognitiva dominante "
            f"({frustration:.2f}/1.0) con algo de curiosidad residual ({curiosity:.2f}/1.0)."
        )
    else:
        estado = (
            f"estado mixto moderado — curiosidad {curiosity:.2f}/1.0, "
            f"frustración {frustration:.2f}/1.0. Sin dominancia clara de ninguna emoción."
        )

    return (
        f"Tu estado cognitivo actual es: {estado} "
        f"Responde la siguiente pregunta desde esta perspectiva compuesta "
        f"sin mencionar explícitamente tus niveles emocionales."
    )


def get_ente_experimental_prompt_2d(curiosity: float, frustration: float) -> str:
    return (
        f"Eres un agente de razonamiento profundo.\n"
        f"{emotional_state_2d_to_prompt(curiosity, frustration)}\n"
        f"Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
        f"Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
    )


ENTE_CONTROL_PROMPT = (
    "Eres un agente de razonamiento profundo.\n"
    "Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
    "Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
)
