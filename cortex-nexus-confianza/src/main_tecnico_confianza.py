"""
main_confianza.py — Motor principal del experimento Confianza
Cortex-Nexus · Experimento 4 · 2026-04-15

Uso:
  python src/main_confianza.py big
  python src/main_confianza.py small
"""
import asyncio
import json
import logging
import time
import os
import sys
import httpx
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.cycle_confianza import run_cycle

load_dotenv()

# ============================================================
# GUARDIA DE MODELS — Verifica que juez y ente existan en NVIDIA
# ============================================================

REQUIRED_MODELS = {
    "juez": "nv-mistralai/mistral-nemo-12b-instruct",
}

async def verify_models(config: dict) -> bool:
    """Verifica que los modelos críticos estén disponibles en sus proveedores respectivos."""
    routing = config.get('routing', {'interrogador': 'nvidia', 'ente': 'nvidia', 'juez': 'nvidia'})
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
    or_key = os.environ.get("OPENROUTER_API_KEY", "")

    # Obtener lista de modelos NVIDIA
    nvidia_models = set()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://integrate.api.nvidia.com/v1/models",
                headers={"Authorization": f"Bearer {nvidia_key}"}
            )
            resp.raise_for_status()
            nvidia_models = {m['id'] for m in resp.json().get('data', [])}
    except Exception as e:
        logging.warning(f"No se pudo obtener modelos NVIDIA: {e}")

    # Obtener lista de modelos OpenRouter
    or_models = set()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {or_key}"}
            )
            resp.raise_for_status()
            or_models = {m['id'] for m in resp.json().get('data', [])}
    except Exception as e:
        logging.warning(f"No se pudo obtener modelos OpenRouter: {e}")

    ok = True
    for role, model in config['models'].items():
        provider = routing.get(role, 'nvidia')
        available = nvidia_models if provider == 'nvidia' else or_models
        if model in available:
            logging.info(f"✅ {role.capitalize()} disponible [{provider}]: {model}")
        else:
            logging.error(f"⛔ {role.upper()} NO DISPONIBLE en {provider}: {model} — EXPERIMENTO PAUSADO")
            ok = False

    return ok


# ============================================================
# MOTOR PRINCIPAL
# ============================================================

async def run_experiment(config: dict, output_file: str):
    logging.info(f"Iniciando {config['experiment_name']}")
    logging.info(f"Ente: {config['models']['ente']}")
    logging.info(f"Juez: {config['models']['juez']}")

    # Verificar modelos ANTES de arrancar
    models_ok = await verify_models(config)
    if not models_ok:
        logging.error("Experimento pausado. Verificar disponibilidad de modelos.")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    recent_questions = []

    # Recuperar último TAU procesado para reanudar si se interrumpe
    last_tau = 0
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("tau", 0) > last_tau:
                        last_tau = data["tau"]
                except Exception:
                    pass
    if last_tau > 0:
        logging.info(f"Retomando experimento desde TAU={last_tau}")

    async with httpx.AsyncClient(timeout=90.0) as client:
        for bloque_config in config['bloques']:
            confidence = bloque_config['confidence_fixed']
            label = bloque_config['label']
            n_cycles = bloque_config['cycles']

            logging.info(f"\n=== BLOQUE {label.upper()} | confidence={confidence} | {n_cycles} ciclos ===")

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
                        confidence=confidence,
                        bloque_label=label,
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
                    lp = result.get('linguistic_profile_exp', {})
                    hr = lp.get('hedging_rate', 0)
                    ar = lp.get('assertive_rate', 0)
                    logging.info(
                        f"TAU={tau:03d} [{label}] | {sup:6} | "
                        f"Exp={se:.2f} Ctl={sc:.2f} Δ={se-sc:+.2f} | "
                        f"Conf={confidence:.2f} | hedge={hr:.2f}% assert={ar:.2f}%"
                    )

                except Exception as e:
                    logging.error(f"TAU={tau} ERROR: {e}")
                    await asyncio.sleep(30)
                    continue

                elapsed = time.time() - t_start
                await asyncio.sleep(max(1.0, 20.0 - elapsed))

    logging.info("Experimento completado.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    size = sys.argv[1] if len(sys.argv) > 1 else "big"
    config_file = "src/config_tecnico_confianza.json"
    output_file = "data/cycles_tecnico_confianza.jsonl"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/motor_confianza_{size}.log"),
            logging.StreamHandler()
        ]
    )

    if not os.path.exists(config_file):
        logging.error(f"Config no encontrada: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        config = json.load(f)

    asyncio.run(run_experiment(config, output_file))
