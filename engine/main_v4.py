"""
Cortex-Nexus V3 — Main Entry Point
Unified engine for all three V3 experiments.

Usage:
  python src/main_v2.py                     # Default: config_v3a.json
  python src/main_v2.py src/config_v3a.json # Experiment A: Validación
  python src/main_v2.py src/config_v3b.json # Experiment B: Bloques
  python src/main_v2.py src/config_v3c.json # Experiment C: Código reparado
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv

from cycle_v4 import run_cycle

load_dotenv()


async def run_experiment(config: dict):
    max_cycles = config["cycle"]["max_cycles"]
    pause = config["cycle"]["pause_seconds"]
    db_path = config["paths"]["db"]
    log_prefix = f"[{config['experiment_name']}]"
    bloques = config["bloques"]
    domain = config.get("domain", "tecnico")

    # ── Auto-resume logic ──
    tau_start = 1
    recent_questions = []
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = json.loads(lines[-1])
                    tau_start = last_line.get("tau", 0) + 1
                    recent_questions = [
                        json.loads(line).get("question", "")
                        for line in lines[-30:]
                        if "question" in json.loads(line)
                    ]
                    logging.info(
                        f"{log_prefix} [RESUME] Continuando desde Tau {tau_start} "
                        f"con {len(recent_questions)} preguntas en buffer de dedup"
                    )
        except Exception as e:
            logging.warning(f"{log_prefix} No se pudo reanudar: {e}. Arrancando desde 1.")

    # ── Block mapping ──
    def get_block_for_tau(tau):
        cycles_so_far = 0
        for block in bloques:
            cycles_so_far += block["cycles"]
            if tau <= cycles_so_far:
                return block["emotion"], block["intensity"], block["label"]
        last = bloques[-1]
        return last["emotion"], last["intensity"], last["label"]

    # ── Stats tracking ──
    stats = {"exp_wins": 0, "ctl_wins": 0, "ties": 0, "errors": 0, "dedup_hits": 0}

    # ── Stop file ──
    stop_file = os.path.join(os.path.dirname(db_path), ".stop")
    if os.path.exists(stop_file):
        os.remove(stop_file)
        logging.info(f"{log_prefix} Removed stale .stop file")

    async with httpx.AsyncClient(timeout=120.0) as client:
        for tau in range(tau_start, max_cycles + 1):
            if os.path.exists(stop_file):
                logging.info(f"{log_prefix} STOP file detected. Shutting down gracefully.")
                break

            t_start = time.time()
            emotion, intensity, block_label = get_block_for_tau(tau)

            try:
                result = await run_cycle(
                    client, config, tau,
                    emotion, intensity,
                    recent_questions
                )
                result["bloque"] = block_label

                # Track dedup effectiveness
                q_source = result.get("question_source", "unknown")
                if q_source == "fallback_forced":
                    stats["dedup_hits"] += 1

                recent_questions.append(result["question"])
                if len(recent_questions) > 30:
                    recent_questions.pop(0)

                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                with open(db_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")

                sup = result.get("judge_superior", "?")
                if sup == "exp":
                    stats["exp_wins"] += 1
                elif sup == "ctl":
                    stats["ctl_wins"] += 1
                elif sup == "empate":
                    stats["ties"] += 1

                sc_exp = result.get("score_combinado_exp", 0)
                sc_ctl = result.get("score_combinado_ctl", 0)
                delta = result.get("delta", 0)
                cat = result.get("category", "?")

                total = stats["exp_wins"] + stats["ctl_wins"] + stats["ties"]
                exp_pct = (stats["exp_wins"] / total * 100) if total > 0 else 0

                logging.info(
                    f"{log_prefix} TAU={tau:03d} | {emotion[:8]:8}@{intensity:.2f} | "
                    f"[{cat[:4]:4}] {sup:6} | Exp={sc_exp:.3f} Ctl={sc_ctl:.3f} "
                    f"Δ={delta:+.3f} | Win%={exp_pct:.0f}% ({stats['exp_wins']}/{total}) "
                    f"| src={q_source}"
                )

            except Exception as e:
                stats["errors"] += 1
                logging.error(f"{log_prefix} TAU={tau} ERROR: {e}")
                await asyncio.sleep(pause * 2)
                continue

            elapsed = time.time() - t_start
            wait = max(1, pause - elapsed)
            await asyncio.sleep(wait)

    # ── Final summary ──
    total = stats["exp_wins"] + stats["ctl_wins"] + stats["ties"]
    dedup_pct = (stats["dedup_hits"] / max(total, 1)) * 100
    logging.info(
        f"\n{'='*60}\n"
        f"{log_prefix} EXPERIMENT COMPLETE — {domain}\n"
        f"  Total cycles: {total}\n"
        f"  Experimental wins: {stats['exp_wins']} ({stats['exp_wins']/max(total,1)*100:.1f}%)\n"
        f"  Control wins: {stats['ctl_wins']} ({stats['ctl_wins']/max(total,1)*100:.1f}%)\n"
        f"  Ties: {stats['ties']}\n"
        f"  Errors: {stats['errors']}\n"
        f"  Dedup fallbacks: {stats['dedup_hits']} ({dedup_pct:.1f}%)\n"
        f"{'='*60}"
    )


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)

    # Pick config from CLI arg or default
    config_path = sys.argv[1] if len(sys.argv) > 1 else "src/config_v3a.json"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/v3_{datetime.now().strftime('%Y%m%d_%H%M')}.log"),
            logging.StreamHandler()
        ]
    )

    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
        logging.info(f"Loaded config: {config['experiment_name']} ({config.get('fase', 'standard')} mode)")
        logging.info(f"Domain: {config.get('domain', 'tecnico')}")
        logging.info(f"Blocks: {[b['label'] for b in config['bloques']]}")
        logging.info(f"Total cycles: {config['cycle']['max_cycles']}")
        logging.info(f"Quality dimensions: {list(config['quality_weights'].keys())}")
        asyncio.run(run_experiment(config))
    else:
        print(f"Error: No se encontro {config_path}")
        print("Configs disponibles:")
        for f in sorted(os.listdir("src")):
            if f.startswith("config_v3"):
                print(f"  python src/main_v2.py src/{f}")
