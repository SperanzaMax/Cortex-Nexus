# Cortex-Nexus V4 — La Inyección de Estados Afectivos como Modulador Cognitivo Universal en LLMs

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19865232.svg)](https://doi.org/10.5281/zenodo.19865232)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Versión](https://img.shields.io/badge/version-4.0-blue.svg)]()

**Autor:** Maximiliano Rodrigo Speranza | Buenos Aires, Argentina

---

## ¿Qué es Cortex-Nexus?

Cortex-Nexus es un framework validado empíricamente para inyectar estados afectivos estructurados en los prompts de LLMs para modular sistemáticamente la calidad del output. No es una librería ni un wrapper — es una metodología científica con evidencia experimental publicada.

**La Versión 4** es el lanzamiento más completo hasta la fecha, cubriendo:
- 4 experimentos coordinados (N > 140 evaluaciones)
- 3 niveles de capacidad de LLMs (32B / 70B / SOTA frontera)
- 2 dominios de tareas (generación de código + razonamiento filosófico)
- Validación con juez independiente a lo largo (organización diferente al generador)

---

## Hallazgos Clave V4

| Experimento | Dominio | Modelo | Delta | Cohen's d |
|---|---|---|---|---|
| EXP-A (Rust, n=44) | Código | Llama-3.3-70B | +0.014 | 0.166 |
| EXP-B Fase 1 (n=15) | Código | Claude 3.7 Sonnet | -0.008 | — |
| EXP-B Fase 2 (n=15) | Código | DeepSeek V3 | -0.003 | — |
| EXP-C Tripartito (n=15) | Código | Qwen-32B + Cortex | -0.077 | — |
| **EXP-D Meta (n=45)** | **Filosofía** | **Claude 3.7 Sonnet** | **+0.064** | **1.107** |

### Las Tres Leyes Empíricas (V4)

1. **Ley de Masa Crítica** — Existe un umbral mínimo de parámetros (~70B) para efectos positivos de inyección. Por debajo, la inyección provoca Penalidad de Asignación de Atención.
2. **Ley de Especificidad de Dominio** — La inyección de Maestría Técnica funciona en modelos open-source medianos en código; la inyección de Óptimo Filosófico funciona en modelos de frontera en razonamiento abstracto.
3. **Ley de Saturación de Techo** — Los modelos SOTA de frontera en dominios algorítmicos rígidos están cerca de una asíntota que la inyección afectiva no puede superar.

---

## Los Prompts de Inyección

### Maestría Técnica (0.85) — Dominio Código
```
You embody Technical Mastery at intensity 0.85/1.0. 
Produce optimal, efficient, and deeply robust algorithm solutions.
```

### Óptimo Filosófico — Dominio Razonamiento Abstracto
```
You are operating with Curiosity at 0.95/1.0 and mild Frustration at 0.20/1.0.
You are genuinely curious about this problem — you want to explore it from 
angles that are not immediately obvious. The mild frustration keeps you from 
accepting the first plausible answer you find.
Before concluding, examine the problem from at least three different 
perspectives and surface any assumptions that could fail. 
Prioritize originality and depth over comprehensiveness.
```

---

## Estructura del Repositorio

```
CORTEXNEXUS FRAMEWORK/
├── benchmark.py                    # EXP-A: Rust Maestría Técnica
├── double_benchmark.py             # EXP-B: Validación cruzada de frontera
├── tripartite_benchmark.py         # EXP-C: Tripartito Masa Crítica
├── philosophical_benchmark.py      # EXP-D01: SOTA filosófico (n=15)
├── philosophical_02_benchmark.py   # EXP-D02: SOTA filosófico (n=30)
├── paper_v4_english.tex            # Paper completo (Inglés)
├── paper_v4_espanol.tex            # Paper completo (Español)
├── results/                        # Datos crudos de todos los experimentos
├── exp_sota_filosofico_01.jsonl    # Datos EXP-D01
├── exp_sota_filosofico_02.jsonl    # Datos EXP-D02
├── tripartite_data.jsonl           # Datos EXP-C
└── repo/cortexnexus/               # Librería core del framework
```

---

## Instalación

```bash
git clone https://github.com/SperanzaMax/Cortex-Nexus
cd Cortex-Nexus/CORTEXNEXUS\ FRAMEWORK
cp .env.example .env
# Agregar tu OPENROUTER_API_KEY al .env
pip install -r requirements.txt
python3 philosophical_02_benchmark.py
```

---

## Citar Este Trabajo

```bibtex
@article{speranza2026cortexnexusv4,
  title   = {Cortex-Nexus V4: La Inyección de Estados Afectivos como Modulador 
             Cognitivo Universal en Modelos de Lenguaje Grande},
  author  = {Speranza, Maximiliano Rodrigo},
  year    = {2026},
  month   = {Abril},
  doi     = {10.5281/zenodo.19865232},
  url     = {https://github.com/SperanzaMax/Cortex-Nexus}
}
```

---

## Licencia
MIT — libre uso, citar si publicás.
