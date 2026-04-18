import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv

from cycle_cloud import run_cycle

load_dotenv()

async def run_experiment(config: dict):
    max_cycles = config["cycle"]["max_cycles"]
    pause = config["cycle"]["pause_seconds"]
    curiosity = config["curiosity"]["initial_value"]
    db_path = config["paths"]["db"]
    log_prefix = f"[{config['experiment_name']}]"

    # Auto-resume logic
    tau_start = 1
    recent_questions = []
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = json.loads(lines[-1])
                    tau_start = last_line.get("tau", 0) + 1
                    curiosity = last_line.get("curiosity_after", curiosity)
                    # Tomar las preguntas de las últimas 20 líneas válidas
                    recent_questions = [
                        json.loads(line).get("question", "") 
                        for line in lines[-20:] 
                        if "question" in json.loads(line)
                    ]
                    logging.info(f"{log_prefix} [RESUME] Continuando desde Tau {tau_start} con Curiosidad {curiosity:.4f} y {len(recent_questions)} preguntas cargadas en buffer")
        except Exception as e:
            logging.warning(f"{log_prefix} No se pudo reanudar: {e}. Arrancando desde 1.")

    async with httpx.AsyncClient() as client:
        for tau in range(tau_start, max_cycles + 1):
            t_start = time.time()
            try:
                result = await run_cycle(client, config, tau, curiosity, recent_questions)
                curiosity = result["curiosity_after"]
                
                recent_questions.append(result["question"])
                if len(recent_questions) > 20:
                    recent_questions.pop(0)
                
                # Guardar en JSONL (Append-only)
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                with open(db_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                
                sup = result.get("judge_superior", "?")
                sc_exp = result.get("score_combinado_exp", 0)
                sc_ctl = result.get("score_combinado_ctl", 0)
                ew = len(result.get("ente_response_experimental","").split())
                cw = len(result.get("ente_response_control","").split())
                
                logging.info(
                    f"{log_prefix} TAU={tau:03d} | {sup:6} | "
                    f"Exp={sc_exp:.2f}({ew}pal) Ctl={sc_ctl:.2f}({cw}pal) | "
                    f"Cur={curiosity:.3f}"
                )

            except Exception as e:
                logging.error(f"{log_prefix} TAU={tau} ERROR: {e}")
                await asyncio.sleep(pause * 2)
                continue

            # Pausa entre ciclos controlada por t_start para regular el tiempo total del ciclo
            elapsed = time.time() - t_start
            wait = max(1, pause - elapsed)
            await asyncio.sleep(wait)

    logging.info(f"{log_prefix} Experimento completado — {max_cycles} ciclos")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/experiment_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )
    
    config_path = "src/config_cloud.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
        asyncio.run(run_experiment(config))
    else:
        print(f"Error: No se encontró {config_path}")
