import sys

with open('src/main_confianza.py', 'r') as f:
    content = f.read()

content = content.replace('f"src/config_confianza_{size}.json"', '"src/config_tecnico_confianza.json"')
content = content.replace('f"data/cycles_confianza_{size}.jsonl"', '"data/cycles_tecnico_confianza.jsonl"')

with open('src/main_tecnico_confianza.py', 'w') as f:
    f.write(content)

