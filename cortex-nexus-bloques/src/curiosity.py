def calculate_next_curiosity(current_curiosity, judge_scores, config):
    """
    Implements the modulation logic from Paso 3 of the guidelines.
    """
    novedad = judge_scores.get('n', 5)
    profundidad = judge_scores.get('p', 5)
    coherencia = judge_scores.get('c', 5)
    
    # Weights from config provided as argument
    weights = config['curiosity']['weights']
    
    score = (novedad * weights['novedad']) + \
            (profundidad * weights['profundidad']) + \
            (coherencia * weights['coherencia'])
            
    score_norm = score / 10.0
    
    decaimiento_basal = config['curiosity']['basal_decay']
    
    # Delta logic
    if score_norm >= 0.75:
        delta = 0.08 * (1.0 - current_curiosity)
    elif score_norm >= 0.50:
        delta = 0.02 * (1.0 - current_curiosity)
    elif score_norm >= 0.30:
        delta = -0.03 * current_curiosity
    else:
        delta = -0.07 * current_curiosity
        
    new_curiosity = current_curiosity + delta - decaimiento_basal
    return max(0.0, min(1.0, new_curiosity)), delta

def curiosity_to_prompt(curiosity: float) -> str:
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
        f"Tu estado de curiosidad actual es: {curiosity:.2f}/1.0 ({estado}). "
        f"Responde la siguiente pregunta desde esta perspectiva cognitiva "
        f"sin mencionar explícitamente tu nivel de curiosidad."
    )
