"""
main_3d.py — Motor principal del experimento 3D: Curiosidad × Frustración × Asombro
Cortex-Nexus · 2026-04-16 | Maximiliano Rodrigo Speranza

Uso:
    python -m src.main_3d big
    python -m src.main_3d small
"""
import asyncio
import json
import logging
import time
import os
import sys
import traceback
import httpx
from dotenv import load_dotenv

# Asegurar root del proyecto en sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.cycle_3d import run_cycle_3d
from src.llm_client import route_call


async def verify_models(config: dict) -> bool:
    """
    Verificación del Juez antes de iniciar.
    Regla crítica: solo se verifica mistral-nemo (OpenRouter).
    NVIDIA puede tener 429 temporales que no invalidan el experimento.
    """
    logging.info("=== VERIFICACIÓN DE MODELOS ===")
    judge_id = config['models']['juez']
    judge_provider = config['routing'].get('juez', 'openrouter')
    logging.info(f"Verificando JUEZ: {judge_id} ({judge_provider}) — obligatorio para integridad científica...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await route_call(
                client,
                config['routing'],
                "juez",
                judge_id,
                "Eres un verificador.",
                "Responde solo 'OK'.",
                max_tokens=5,
                temperature=0.1
            )
            if not resp or len(resp.strip()) == 0:
                raise Exception("Respuesta vacía del Juez")
            logging.info(f"  ✓ JUEZ operativo: {judge_id}")
    except Exception as e:
        logging.critical(f"  ✗ JUEZ NO DISPONIBLE ({judge_id}): {e}")
        logging.critical("Experimento abortado — no se puede garantizar consistencia científica sin el Juez.")
        return False

    logging.info(f"  ℹ  Ente/Interrogador via NVIDIA NIM — se verificarán en el primer ciclo real")
    logging.info("=== JUEZ VERIFICADO — INICIANDO ===\n")
    return True


async def run_experiment_3d(config: dict, output_file: str):
    logging.info(f"\n{'='*60}")
    logging.info(f"INICIANDO: {config['experiment_name']}")
    logging.info(f"Espacio 3D: {len(config['estados_3d'])} estados × 30 ciclos = 240 ciclos total")
    logging.info(f"Juez: {config['models']['juez']} (FIJO — no modificar)")
    logging.info(f"{'='*60}\n")

    # Verificación mandatoria
    if not await verify_models(config):
        return

    # Reanudar si existe archivo previo
    recent_questions = []
    last_tau = 0
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("tau", 0) > last_tau:
                        last_tau = data["tau"]
                    q = data.get("question", "")
                    if q:
                        recent_questions.append(q)
                except:
                    pass
        if last_tau > 0:
            logging.info(f"Retomando desde TAU={last_tau} (ya hay {last_tau} ciclos guardados)")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    async with httpx.AsyncClient(timeout=90.0) as client:
        for estado_cfg in config['estados_3d']:
            curiosity = estado_cfg['curiosity']
            frustration = estado_cfg['frustration']
            wonder = estado_cfg['wonder']
            label = estado_cfg['label']
            n_cycles = estado_cfg['cycles']

            # Calcular tau base para este estado
            idx = config['estados_3d'].index(estado_cfg)
            tau_base = sum(e['cycles'] for e in config['estados_3d'][:idx])

            logging.info(
                f"\n{'─'*50}\n"
                f"ESTADO: {label} | C={curiosity:.2f} F={frustration:.2f} W={wonder:.2f} | {n_cycles} ciclos\n"
                f"TAU rango: {tau_base+1} → {tau_base+n_cycles}\n"
                f"{'─'*50}"
            )

            for i in range(n_cycles):
                tau = tau_base + i + 1
                if tau <= last_tau:
                    continue

                t_start = time.time()
                try:
                    result = await run_cycle_3d(
                        client=client,
                        config=config,
                        tau=tau,
                        curiosity=curiosity,
                        frustration=frustration,
                        wonder=wonder,
                        estado_label=label,
                        recent_questions=recent_questions
                    )

                    recent_questions.append(result.get('question', ''))
                    if len(recent_questions) > 30:
                        recent_questions.pop(0)

                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(result, ensure_ascii=False) + '\n')

                    sup = result.get('judge_superior', '?')
                    se = result.get('score_combinado_exp', 0)
                    sc = result.get('score_combinado_ctl', 0)
                    delta = result.get('delta_score', se - sc)
                    dur = result.get('cycle_duration_secs', 0)

                    logging.info(
                        f"TAU={tau:03d} [{label}] | {sup:6} | "
                        f"Exp={se:.2f} Ctl={sc:.2f} Δ={delta:+.2f} | "
                        f"C={curiosity:.2f} F={frustration:.2f} W={wonder:.2f} | {dur:.0f}s"
                    )

                except Exception as e:
                    logging.error(f"TAU={tau} ERROR: {type(e).__name__}: {e}")
                    logging.error(f"Traceback:\n{traceback.format_exc()}")
                    await asyncio.sleep(30)
                    continue

                elapsed = time.time() - t_start
                # Pausa de 35s entre ciclos (respeta rate limits)
                await asyncio.sleep(max(1, 35 - elapsed))

    logging.info(f"\n{'='*60}")
    logging.info(f"EXPERIMENTO 3D COMPLETADO: {config['experiment_name']}")
    logging.info(f"{'='*60}")


if __name__ == "__main__":
    size = sys.argv[1] if len(sys.argv) > 1 else "big"

    # Cargar el .env específico para este motor
    env_file = f".env.{size}"
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Cargando API keys desde {env_file}")
    else:
        load_dotenv()
        print("Cargando API keys desde .env genérico")

    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/motor_3d_{size}.log"),
            logging.StreamHandler()
        ]
    )

    config_file = f"src/config_3d_{size}.json"
    output_file = f"data/cycles_3d_{size}.jsonl"

    if not os.path.exists(config_file):
        logging.error(f"Config no encontrado: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        config = json.load(f)

    asyncio.run(run_experiment_3d(config, output_file))
