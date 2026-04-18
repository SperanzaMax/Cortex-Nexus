import asyncio
import json
import logging
import time
import os
import sys
import httpx
from dotenv import load_dotenv

# Asegurar que el directorio root del proyecto esté en sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.cycle_asombro import run_cycle
from src.llm_client import route_call

load_dotenv()

async def verify_models(config: dict):
    """Verifica disponibilidad de modelos en sus respectivos proveedores."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for role in ["interrogador", "ente", "juez"]:
            model_id = config['models'][role]
            provider = config['routing'].get(role, "nvidia")
            logging.info(f"Verificando {role}: {model_id} via {provider}...")
            try:
                # Test minimal call
                resp = await route_call(
                    client, 
                    config['routing'], 
                    role,
                    model_id,
                    "Eres un tester de sistemas científicos.", 
                    "Responde únicamente la palabra 'OK'.",
                    max_tokens=10,
                    temperature=0.1
                )
                if not resp or len(resp.strip()) == 0:
                    raise Exception("Respuesta vacía")
                logging.info(f"✓ {role} operativo.")
            except Exception as e:
                logging.error(f"✗ ERROR en {role} ({model_id}): {e}")
                return False
    return True

async def run_experiment(config: dict, output_file: str):
    logging.info(f"Iniciando {config['experiment_name']} (Modo Híbrido)")
    
    # Verificación inicial de modelos
    if not await verify_models(config):
        logging.error("No se pudo verificar la conectividad de los modelos. Abortando inicio.")
        return

    recent_questions = []

    # Crear carpeta de data si no existe
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    last_tau = 0
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("tau", 0) > last_tau:
                        last_tau = data["tau"]
                except:
                    pass
    if last_tau > 0:
        logging.info(f"Retomando experimento desde TAU={last_tau}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        for bloque_config in config['bloques']:
            asombro = bloque_config['asombro_fixed']
            label = bloque_config['label']
            n_cycles = bloque_config['cycles']

            logging.info(f"\n=== BLOQUE {label.upper()} | awe={asombro} | {n_cycles} ciclos ===")

            for i in range(n_cycles):
                tau = sum(b['cycles'] for b in config['bloques'][:config['bloques'].index(bloque_config)]) + i + 1
                if tau <= last_tau:
                    continue
                t_start = time.time()

                try:
                    result = await run_cycle(
                        client=client,
                        config=config,
                        tau=tau,
                        asombro=asombro,
                        bloque_label=label,
                        recent_questions=recent_questions
                    )

                    # Actualizar buffer de preguntas
                    recent_questions.append(result.get('question', ''))
                    if len(recent_questions) > 30:
                        recent_questions.pop(0)

                    # Guardar
                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(result, ensure_ascii=False) + '\n')

                    sup = result.get('judge_superior', '?')
                    se = result.get('score_combinado_exp', 0)
                    sc = result.get('score_combinado_ctl', 0)
                    logging.info(
                        f"TAU={tau:03d} [{label}] | {sup:6} | "
                        f"Exp={se:.2f} Ctl={sc:.2f} Δ={se-sc:+.2f} | "
                        f"Asombro={asombro:.2f}"
                    )

                except Exception as e:
                    logging.error(f"TAU={tau} ERROR: {e}")
                    await asyncio.sleep(30)
                    continue

                elapsed = time.time() - t_start
                # Mantener un ritmo constante
                await asyncio.sleep(max(1, 40 - elapsed))

    logging.info("Experimento completado.")

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    size = sys.argv[1] if len(sys.argv) > 1 else "big"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/motor_asombro_{size}.log"),
            logging.StreamHandler()
        ]
    )

    config_file = f"src/config_asombro_{size}.json"
    output_file = f"data/cycles_asombro_{size}.jsonl"

    if not os.path.exists(config_file):
        logging.error(f"Config file not found: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        config = json.load(f)

    asyncio.run(run_experiment(config, output_file))
