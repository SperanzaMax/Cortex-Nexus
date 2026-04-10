class ModuladorParametrico:
    """
    Traduce el vector emocional a hiper-parámetros de inferencia LLM.
    """
    def __init__(self, config_base=None):
        self.config_base = config_base or {
            "temperature": 0.7,
            "top_p": 0.9,
            "repetition_penalty": 1.1,
            "max_tokens": 128
        }

    def modular(self, vector):
        """
        Aplica transformaciones basadas en el estado emocional.
        """
        estado = vector.estado
        config = self.config_base.copy()

        # 1. Temperatura (Creatividad/Caos)
        # Sube con aburrimiento (búsqueda de novedad) y qualia (inspiración).
        # Baja con frustración (intento de ser más determinista/seguro).
        mod_temp = 1.0 + (estado["aburrimiento"] * 0.5) + (estado["qualia"] * 0.2) - (estado["frustracion"] * 0.3)
        config["temperature"] = float(max(0.1, min(1.5, config["temperature"] * mod_temp)))

        # 2. Top_P (Focalización)
        # Menor confianza -> Reducir Top_P para ser más conservador.
        mod_top_p = 1.0 - (1.0 - estado["autoConfianza"]) * 0.4
        config["top_p"] = float(max(0.1, min(1.0, config["top_p"] * mod_top_p)))

        # 3. Penalización de Repetición
        # Sube con la frustración para evitar bucles infinitos.
        config["repetition_penalty"] += (estado["frustracion"] * 0.5)

        # 4. Estrategia Narrativa (Metadata para el sistema)
        if estado["aburrimiento"] > 0.8:
            config["estrategia"] = "exploratoria_caotica"
        elif estado["frustracion"] > 0.6:
            config["estrategia"] = "segura_determinista"
        elif estado["satisfaccion"] > 0.7:
            config["estrategia"] = "conservadora_exitosa"
        else:
            config["estrategia"] = "estandar"

        return config
