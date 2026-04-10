import os
import sys

# Agregar al path para importar
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from core.vector_emocional import VectorEmocional

DB_PATH = "/home/maxi/cma_memory.db"

def sleep_replay():
    print("--- INICIANDO CONSOLIDACIÓN OFFLINE (SLEEP REPLAY) ---")
    # Cargar el ente y su configuración base (esto inicializa la DB si no existe)
    vector = VectorEmocional(db_path=DB_PATH)
    
    # Ver estado inicial del arquetipo
    arquetipo_inicial = vector.memoria.cargar_meta_vector()
    print(f"[*] Arquetipo Antes del Sueño:")
    print(f"    Meta-Qualia:      {arquetipo_inicial['meta_qualia']:.5f}")
    print(f"    Meta-Frustración: {arquetipo_inicial['meta_frustracion']:.5f}")
    print(f"    Meta-Confianza:   {arquetipo_inicial['meta_confianza']:.5f}")
    
    # Simular la consolidación (El cerebro procesa lo vivido)
    print("\n[+] Procesando memoria episódica...")
    vector.consolidar_memoria()
    print("[+] Consolidación por EMA aplicada.")
    
    # Asegurarnos de recargar la memoria tras consolidar para ver los cambios
    arquetipo_final = vector.memoria.cargar_meta_vector()
    
    print(f"\n[*] Arquetipo Después del Sueño (Personalidad Alterada):")
    print(f"    Meta-Qualia:      {arquetipo_final['meta_qualia']:.5f} (Δ {arquetipo_final['meta_qualia'] - arquetipo_inicial['meta_qualia']:.5f})")
    print(f"    Meta-Frustración: {arquetipo_final['meta_frustracion']:.5f} (Δ {arquetipo_final['meta_frustracion'] - arquetipo_inicial['meta_frustracion']:.5f})")
    print(f"    Meta-Confianza:   {arquetipo_final['meta_confianza']:.5f} (Δ {arquetipo_final['meta_confianza'] - arquetipo_inicial['meta_confianza']:.5f})")
    
    print("\n--- CICLO DE SUEÑO COMPLETADO ---")

if __name__ == "__main__":
    sleep_replay()
