def frustration_to_prompt(frustration: float) -> str:
    """
    Convierte el nivel de frustración en descripción para el prompt del Ente.
    La frustración es un estado de tensión cognitiva acumulada —
    bloqueo creativo, dificultad para generar ideas nuevas, sensación de estancamiento.
    """
    if frustration >= 0.85:
        estado = (
            "frustración cognitiva extrema — sensación de bloqueo total, "
            "cada idea parece un callejón sin salida, dificultad severa "
            "para encontrar conexiones originales o perspectivas nuevas"
        )
    elif frustration >= 0.65:
        estado = (
            "frustración alta — tensión cognitiva acumulada, sensación de "
            "estancamiento, las respuestas obvias no satisfacen pero "
            "las alternativas no aparecen con claridad"
        )
    elif frustration >= 0.40:
        estado = (
            "frustración moderada — ligera tensión interna, algunas ideas "
            "se sienten forzadas o incompletas, dificultad para encontrar "
            "el ángulo más interesante del problema"
        )
    elif frustration >= 0.15:
        estado = (
            "tensión cognitiva leve — casi neutral, con una ligera sensación "
            "de que podría explorar más pero sin urgencia ni bloqueo real"
        )
    else:
        estado = "estado neutral — sin tensión cognitiva apreciable"

    return (
        f"Tu nivel de frustración cognitiva actual es: {frustration:.2f}/1.0 "
        f"({estado}). "
        f"Responde la siguiente pregunta desde esta perspectiva "
        f"sin mencionar explícitamente tu nivel de frustración."
    )

def get_ente_experimental_prompt(frustration: float) -> str:
    return (
        f"Eres un agente de razonamiento profundo.\n"
        f"{frustration_to_prompt(frustration)}\n"
        f"Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
        f"Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
    )

ENTE_CONTROL_PROMPT = (
    "Eres un agente de razonamiento profundo.\n"
    "Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
    "Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
)
