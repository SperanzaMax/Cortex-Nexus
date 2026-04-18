import asyncio
import json
import os
import sys
import httpx
from collections import Counter
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.cycle_asombro import run_cycle

load_dotenv()

async def fill_missing():
    config_file = "src/config_asombro_confirmacion.json"
    output_file = "data/cycles_asombro_confirmacion.jsonl"
    
    with open(config_file) as f:
        config = json.load(f)

    counts = Counter()
    max_tau = 0
    recent_questions = []
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    counts[d['bloque']] += 1
                    if d['tau'] > max_tau:
                        max_tau = d['tau']
                    recent_questions.append(d['question'])
                except:
                    pass
    
    recent_questions = recent_questions[-30:]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for bloque_config in config['bloques']:
            label = bloque_config['label']
            asombro = bloque_config['asombro_fixed']
            target = bloque_config['cycles']
            current = counts[label]
            
            print(f"Bloque {label}: target={target}, current={current}, missing={target-current}")
            
            while current < target:
                max_tau += 1
                print(f"Generando missing tau={max_tau} para bloque={label} (faltan {target - current})...")
                
                try:
                    result = await run_cycle(
                        client=client,
                        config=config,
                        tau=max_tau,
                        asombro=asombro,
                        bloque_label=label,
                        recent_questions=recent_questions
                    )
                    recent_questions.append(result.get('question', ''))
                    if len(recent_questions) > 30:
                        recent_questions.pop(0)

                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(result, ensure_ascii=False) + '\n')
                    
                    current += 1
                    print(f"OK! {label} iteracion exitosa.")
                except Exception as e:
                    print(f"Error {e}")
                    await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(fill_missing())
