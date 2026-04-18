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

from src.cycle_frustracion import run_cycle

load_dotenv()

async def run_experiment(config: dict, output_file: str):
    logging.info(f"Iniciando {config['experiment_name']}")
    recent_questions = []

    # Crear carpeta de data si no existe
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    async with httpx.AsyncClient(timeout=60.0) as client:
        for bloque_config in config['bloques']:
            frustration = bloque_config['frustration_fixed']
            label = bloque_config['label']
            n_cycles = bloque_config['cycles']

            logging.info(f"\n=== BLOQUE {label.upper()} | frustración={frustration} | {n_cycles} ciclos ===")

            for i in range(n_cycles):
                tau = sum(b['cycles'] for b in config['bloques'][:config['bloques'].index(bloque_config)]) + i + 1
                t_start = time.time()

                try:
                    result = await run_cycle(
                        client=client,
                        config=config,
                        tau=tau,
                        frustration=frustration,
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
                        f"Frust={frustration:.2f}"
                    )

                except Exception as e:
                    logging.error(f"TAU={tau} ERROR: {e}")
                    await asyncio.sleep(30)
                    continue

                elapsed = time.time() - t_start
                # Mantener un ritmo constante para no saturar APIs y por real-time monitoring
                await asyncio.sleep(max(1, 35 - elapsed))

    logging.info("Experimento completado.")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/motor_frustracion_{sys.argv[1] if len(sys.argv) > 1 else 'default'}.log"),
            logging.StreamHandler()
        ]
    )

    size = sys.argv[1] if len(sys.argv) > 1 else "big"
    config_file = f"src/config_frustracion_{size}.json"
    output_file = f"data/cycles_frustracion_{size}.jsonl"

    if not os.path.exists(config_file):
        logging.error(f"Config file not found: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        config = json.load(f)

    asyncio.run(run_experiment(config, output_file))
