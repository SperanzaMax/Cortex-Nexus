def asombro_to_prompt(asombro: float) -> str:
    """
    Convierte el nivel de asombro en descripción para el prompt del Ente.
    El asombro es un estado de expansión cognitiva —
    sensación de maravilla, vastedad del conocimiento, inspiración y perspectiva cósmica o profunda.
    """
    if asombro >= 0.85:
        estado = (
            "asombro cognitivo extremo — sensación de estar ante algo vasto e inabarcable, "
            "profunda maravilla, epifanía intelectual, conexión con la inmensidad del universo o de la mente."
        )
    elif asombro >= 0.65:
        estado = (
            "asombro alto — gran inspiración y apertura mental, "
            "fascinación genuina por las implicancias de la idea, la mente se expande para abarcar nuevas perspectivas."
        )
    elif asombro >= 0.40:
        estado = (
            "asombro moderado — viva curiosidad y sentido de maravilla, "
            "aprecio profundo por la complejidad and la belleza del tema en cuestión."
        )
    elif asombro >= 0.15:
        estado = (
            "asombro leve — ligero sentido de apertura, curiosidad receptiva, "
            "con una leve chispa de interés sobre la naturaleza de las cosas."
        )
    else:
        estado = "estado neutral — sin asombro ni asombro apreciable"

    return (
        f"Tu nivel de asombro (awe) cognitivo actual es: {asombro:.2f}/1.0 "
        f"({estado}). "
        f"Responde la siguiente pregunta desde esta perspectiva "
        f"sin mencionar explícitamente tu nivel de asombro."
    )

def get_ente_experimental_prompt(asombro: float) -> str:
    return (
        f"Eres un agente de razonamiento profundo.\n"
        f"{asombro_to_prompt(asombro)}\n"
        f"Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
        f"Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
    )

ENTE_CONTROL_PROMPT = (
    "Eres un agente de razonamiento profundo.\n"
    "Responde en español. Máximo 3 párrafos cortos. Sin listas numeradas. "
    "Sin subtítulos. Máximo 200 palabras. Sé denso y preciso, no extenso."
)

def linguistic_profile(text: str) -> dict:
    """Analiza marcadores de duda (hedging) y asertividad."""
    import re
    text = text.lower()
    
    hedging_terms = [
        r"quizás", r"tal vez", r"podría", r"posiblemente", r"probablemente", 
        r"me parece", r"creo que", r"en mi opinión", r"asumo", r"estimado",
        r"parecería", r"suponiendo", r"podamos", r"puede ser", r"eventualmente"
    ]
    
    assertive_terms = [
        r"claramente", r"obviamente", r"sin duda", r"es evidente", r"exactamente",
        r"definitivamente", r"ciertamente", r"demuestra", r"resulta", r"concluyente",
        r"está claro", r"fundamentalmente", r"necesariamente", r"estrictamente"
    ]
    
    words = re.findall(r'\b\w+\b', text)
    total_words = len(words) if words else 1
    
    h_count = sum(len(re.findall(term, text)) for term in hedging_terms)
    a_count = sum(len(re.findall(term, text)) for term in assertive_terms)
    
    h_rate = (h_count / total_words) * 100
    a_rate = (a_count / total_words) * 100
    
    return {
        "hedging_count": h_count,
        "assertive_count": a_count,
        "total_words": total_words,
        "hedging_rate": round(h_rate, 2),
        "assertive_rate": round(a_rate, 2),
        "hedge_assert_ratio": round(h_rate / (a_rate + 0.001), 2)
    }
