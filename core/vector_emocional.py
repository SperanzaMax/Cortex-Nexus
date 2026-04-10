import numpy as np
from datetime import datetime
from .memoria_consolidada import MemoriaConsolidada

class VectorEmocional:
    """
    Gestiona el estado homeostático de la IA mediante un vector de variables afectivas.
    Implementa decaimientos asimétricos y actualización por interocepción computacional.
    """
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.memoria = MemoriaConsolidada(db_path) if db_path else None
        
        # Primero obtenemos el Arquetipo Lento si hay persistencia
        meta = self.memoria.cargar_meta_vector() if self.memoria else {"meta_qualia": 0.0, "meta_frustracion": 0.0, "meta_confianza": 0.5}
        
        # Set points iniciales (Homeostasis mezclada con Arquetipo Personal)
        self.estado = {
            "qualia": meta["meta_qualia"],          # Hereda de largo plazo
            "satisfaccion": 0.0,    
            "frustracion": meta["meta_frustracion"], # Hereda de largo plazo
            "aburrimiento": 0.1,    
            "autoConfianza": meta["meta_confianza"], # Hereda de largo plazo
            "fatiga": 0.0           
        }
        
        # Factores de decaimiento (Lambda) - Asimetría temporal
        self.lambdas = {
            "qualia": 0.01,
            "satisfaccion": 0.20,   # Cae rápido (placer efímero)
            "frustracion": 0.05,    # Cae lento (el trauma persiste)
            "aburrimiento": 0.10,
            "autoConfianza": 0.02,  # Muy estable
            "fatiga": 0.15          # Recuperación moderada en reposo
        }
        
        # Buffer de delay para Anti-Wireheading (latencia de 3 turnos)
        self.buffer_qualia = []

    def actualizar(self, interocepcion: dict, utilidad_externa: float = 0.5):
        """
        Actualiza el vector basado en señales del entorno y del modelo (logits).
        interocepcion: {
            "novedad": float, (0-1)
            "complejidad": float, (0-1)
            "confianza_real": float, (0-1)
            "confianza_esperada": float, (0-1)
            "exito_tarea": bool
        }
        utilidad_externa: float (0.0 a 1.0). Representa el feedback del mundo real.
        """
        # 1. Aplicar decaimiento natural (Homeostasis)
        for var in self.estado:
            self.estado[var] *= (1 - self.lambdas[var])

        # 2. Procesar señales interoceptivas
        novedad = interocepcion.get("novedad", 0.0)
        complejidad = interocepcion.get("complejidad", 0.0)
        c_real = interocepcion.get("confianza_real", 0.5)
        c_esperada = interocepcion.get("confianza_esperada", 0.5)
        exito = interocepcion.get("exito_tarea", False)

        # Cálculo de Frustración (Disonancia)
        if not exito:
            delta_f = max(0, c_esperada - c_real) * (1 + complejidad)
            self.estado["frustracion"] += delta_f
            self.estado["autoConfianza"] -= 0.05 * delta_f
        else:
            # Satisfacción por resolución
            self.estado["satisfaccion"] += c_real * complejidad
            self.estado["autoConfianza"] += 0.02 * c_real

        # Acumulación de Qualia (Novedad con propósito) - Anti-Wireheading Gate
        qualia_bruto = novedad * complejidad * (1 - self.estado["fatiga"])
        self.buffer_qualia.append(qualia_bruto)
        
        # Delay de 3 turnos para aplicación de Qualia
        if len(self.buffer_qualia) >= 3:
            qualia_diferido = self.buffer_qualia.pop(0)
            # Gate: solo se acumula si hubo utilidad externa
            qualia_efectivo = qualia_diferido * (utilidad_externa * 1.5) # Scale factor
            self.estado["qualia"] += qualia_efectivo
        else:
            # Durante los primeros turnos acumula un pequeño proxy
            self.estado["qualia"] += qualia_bruto * 0.1
        # Aburrimiento vs Estimulación
        if novedad < 0.2:
            self.estado["aburrimiento"] += 0.05 * (1 - novedad)
        else:
            self.estado["aburrimiento"] -= 0.1 * novedad

        # Fatiga Cognitiva
        self.estado["fatiga"] += 0.01 * complejidad

        # Clip de valores (0, 1.5) para evitar divergencias
        for var in self.estado:
            self.estado[var] = float(np.clip(self.estado[var], 0.0, 1.5))

    def obtener_estado(self):
        return self.estado.copy()

    def persistir_snapshot(self, metadata=None):
        """Llamado manualmente o al final de tarea para serializar en Disco"""
        if self.memoria:
            self.memoria.guardar_snapshot(self.estado, metadata)
            
    def consolidar_memoria(self):
        """Simula el Sleep Replay consolidando el modelo EMA en SQLite"""
        if self.memoria:
            self.memoria.consolidar_arquetipo_ema()

    def __repr__(self):
        return f"VectorEmocional({ {k: round(v, 3) for k, v in self.estado.items()} })"
