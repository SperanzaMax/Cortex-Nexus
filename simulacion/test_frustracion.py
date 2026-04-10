import asyncio
from core.vector_emocional import VectorEmocional
from core.modulador import ModuladorParametrico

async def stress_test():
    print("--- INICIANDO TEST DE FRUSTRACIÓN (SINTÉTICO) ---")
    
    vector = VectorEmocional()
    modulador = ModuladorParametrico()
    
    # Simulamos una serie de fallos catastróficos
    # La IA espera éxito (0.8) pero recibe basura (0.1)
    senales_fallo = {
        "novedad": 0.05,
        "complejidad": 0.9,
        "confianza_real": 0.1,
        "confianza_esperada": 0.8,
        "exito_tarea": False
    }
    
    for i in range(1, 6):
        print(f"\nIteración {i} (Fallo inducido)")
        config = modulador.modular(vector)
        print(f"Estado antes: {vector}")
        print(f"Estrategia sugerida: {config['estrategia']}")
        
        vector.actualizar(senales_fallo)
        
    print(f"\nEstado Final tras trauma: {vector}")
    config_final = modulador.modular(vector)
    print(f"Parámetros Finales: { {k: v for k, v in config_final.items() if k != 'max_tokens'} }")
    print("\n--- TEST FINALIZADO ---")

if __name__ == "__main__":
    asyncio.run(stress_test())
