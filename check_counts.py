import json
from collections import Counter

def count_file(path, keys_to_check):
    counts = Counter()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                d = json.loads(line)
                for key in keys_to_check:
                    if key in d:
                        counts[d[key]] += 1
                        break
    except Exception as e:
        print(f"Error {path}: {e}")
    return counts

print("Asombro:", count_file("/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-asombro/data/cycles_asombro_confirmacion.jsonl", ["bloque", "condicion"]))
print("Optimo:", count_file("/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-validacion/data/cycles_optimo_confirmacion.jsonl", ["condicion", "bloque"]))
print("Tecnico:", count_file("/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-confianza/data/cycles_tecnico_confianza.jsonl", ["condicion", "bloque"]))
