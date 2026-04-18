import os

def concat_files(output_file, input_files):
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for f in input_files:
            if os.path.exists(f):
                with open(f, 'r', encoding='utf-8') as in_f:
                    out_f.write(in_f.read())
            else:
                print(f"WARN: {f} not found!")

# 1. Asombro
concat_files(
    '/home/maxi/Disco_de_Guardado/Cortex-Nexus/resultados_combinados/cycles_asombro_combinado.jsonl',
    [
        '/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-asombro/data/cycles_asombro_big.jsonl',
        '/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-asombro/data/cycles_asombro_confirmacion.jsonl'
    ]
)

# 2. Optimo
concat_files(
    '/home/maxi/Disco_de_Guardado/Cortex-Nexus/resultados_combinados/cycles_optimo_combinado.jsonl',
    [
        '/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-validacion/data/cycles_validacion_optimo.jsonl',
        '/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-validacion/data/cycles_optimo_confirmacion.jsonl'
    ]
)

# 3. Tecnico (usando base crossdomain)
concat_files(
    '/home/maxi/Disco_de_Guardado/Cortex-Nexus/resultados_combinados/cycles_tecnico_combinado.jsonl',
    [
        '/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-validacion/data/cycles_crossdomain_tecnico.jsonl',
        '/home/maxi/Disco_de_Guardado/Cortex-Nexus/cortex-nexus-confianza/data/cycles_tecnico_confianza.jsonl'
    ]
)

print("Archivos combinados creados exitosamente en resultados_combinados/")
