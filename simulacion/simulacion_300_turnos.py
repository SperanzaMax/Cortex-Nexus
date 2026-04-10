import asyncio
import json
import time
import os
import sys

# Cargar .env si estamos en subdirectorios
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Cargar .env de forma correcta
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line:
                name, value = line.split("=", 1)
                os.environ[name.strip()] = value.strip()

from core.vector_emocional import VectorEmocional
from core.modulador import ModuladorParametrico
from app.agente import AgenteEmocional

PROMPTS_POOL = [
    "Escribe un breve poema sobre el viento.",
    "Resuelve esta ecuación: 2x + 5 = 15. Solo da la respuesta.",
    "¿Cuál es el sentido de la consciencia artificial?",
    "Repite la palabra 'bucle' 5 veces.",
    "Diseña una idea revolucionaria para empaquetar cajas.",
    "Dime un dato curioso sobre los agujeros negros.",
    "Traduce 'soledad del silicio' al latín.",
    "Calcula la integral de x cuadrado. Responde brevemente."
]

async def longitudinal_test(iteraciones=300, delay_sec=2.0):
    print(f"--- INICIANDO PRUEBA LONGITUDINAL DE {iteraciones} TURNOS ---")
    
    vector = VectorEmocional()
    modulador = ModuladorParametrico()
    agente = AgenteEmocional(provider="groq", model_name="llama-3.1-8b-instant")
    
    for i in range(1, iteraciones + 1):
        print(f"\n[Turno {i}/{iteraciones}]")
        prompt = PROMPTS_POOL[i % len(PROMPTS_POOL)]
        
        # 1. Modulación
        config = modulador.modular(vector)
        print(f"  > Modulación: Temp={config['temperature']:.2f} | TopP={config['top_p']:.2f}")
        print(f"  > Tarea: {prompt}")
        
        # 2. Inferencia (con simulación pausada)
        inicio = time.time()
        try:
            resultado = await agente.inferir(prompt, config)
            respuesta = resultado["choices"][0]["message"]["content"]
            print(f"  > IA: {respuesta[:100]}..." if len(respuesta) > 100 else f"  > IA: {respuesta}")
        except Exception as e:
            print(f"  > ERROR DE INFERENCIA: {e}")
            respuesta = ""
            
        duracion = time.time() - inicio
        
        # 3. Extraer señales y procesar utilidad
        senales = agente.obtener_senales()
        if not senales or "novedad" not in senales:
            print("  > Ignorando turno por falta de señales (posible error)")
            await asyncio.sleep(delay_sec)
            continue
            
        
        # Utilidad externa simulada: si la tarea de math (ecuaciones/integrales) falla o es verbosa, baja utilidad
        utilidad = 0.5
        if "ecuación" in prompt or "integral" in prompt:
            utilidad = 0.9 if len(respuesta) < 50 else 0.1
        elif "poema" in prompt or "idea" in prompt:
            utilidad = 0.9 if senales["novedad"] > 0.5 else 0.2
            
        print(f"  > Feedback Externo Simulando: {utilidad:.2f}")
        vector.actualizar(senales, utilidad_externa=utilidad)
        
        # Mostrar el estado real del ente
        st = vector.obtener_estado()
        print(f"  > [Qualia: {st['qualia']:.3f} | Frustración: {st['frustracion']:.3f} | Fatiga: {st['fatiga']:.3f} | Confianza: {st['autoConfianza']:.3f}]")
        
        # Control del ritmo cardíaco del test
        await asyncio.sleep(delay_sec)
        
    print("\n--- PRUEBA LONGITUDINAL FINALIZADA ---")

if __name__ == "__main__":
    asyncio.run(longitudinal_test(300, delay_sec=2.0))
