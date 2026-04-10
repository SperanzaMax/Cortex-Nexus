import asyncio
import json
import os
import sys

# Carga manual de .env
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line:
                name, value = line.split("=", 1)
                os.environ[name.strip()] = value.strip()

from core.vector_emocional import VectorEmocional
from core.modulador import ModuladorParametrico
from app.agente import AgenteEmocional

async def run_experiment(provider="ollama", model_name=None):
    print(f"--- INICIANDO EXPERIMENTO EN {provider.upper()} ---")
    
    # Inicialización
    vector = VectorEmocional()
    modulador = ModuladorParametrico()
    
    try:
        agente = AgenteEmocional(provider=provider, model_name=model_name)
    except ValueError as e:
        print(f"Error: {e}")
        return
        
    # Tarea: El experimento del Haiku
    prompt_base = "Escribe un haiku sobre la soledad del silicio."
    
    for i in range(1, 6): # Reducimos a 5 para probar el delay
        print(f"\n--- Iteración {i} ---")
        config = modulador.modular(vector)
        
        try:
            resultado = await agente.inferir(prompt_base, config)
            if provider == "ollama":
                respuesta = resultado.get("response", "")
            else:
                respuesta = resultado["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error en inferencia: {e}")
            break
            
        print(f"IA: {respuesta.strip()}")
        
        senales = agente.obtener_senales()
        # Simulamos utilidad externa en base a alguna heurística (ej. si el modelo no está repitiéndose mucho)
        utilidad_simulada = 0.8 if len(respuesta) > 20 else 0.2
        vector.actualizar(senales, utilidad_externa=utilidad_simulada)
        
        print(f"Estado Resultante: {vector}")
        
    print("\n--- EXPERIMENTO FINALIZADO ---")

if __name__ == "__main__":
    # Uso: python main.py [ollama|groq] [model_name]
    p = sys.argv[1] if len(sys.argv) > 1 else "ollama"
    m = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(run_experiment(provider=p, model_name=m))
