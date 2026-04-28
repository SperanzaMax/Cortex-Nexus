# Cortex-Nexus V4 — Affective State Injection as a Universal Cognitive Modulator in LLMs

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19865232.svg)](https://doi.org/10.5281/zenodo.19865232)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-4.0-blue.svg)]()

**Author:** Maximiliano Rodrigo Speranza | Buenos Aires, Argentina

---

## What is Cortex-Nexus?

Cortex-Nexus is an empirically validated framework for injecting structured affective states into LLM prompts to systematically modulate output quality. It is not a library or a wrapper — it is a scientific methodology with published experimental evidence.

**Version 4** is the most comprehensive release to date, covering:
- 4 coordinated experiments (N > 140 evaluations)
- 3 capability tiers of LLMs (32B / 70B / SOTA frontier)
- 2 task domains (code generation + philosophical reasoning)
- Independent judge validation throughout (different org from generator)

---

## Key Findings V4

| Experiment | Domain | Model | Delta | Cohen's d |
|---|---|---|---|---|
| EXP-A (Rust, n=44) | Code | Llama-3.3-70B | +0.014 | 0.166 |
| EXP-B Phase 1 (n=15) | Code | Claude 3.7 Sonnet | -0.008 | — |
| EXP-B Phase 2 (n=15) | Code | DeepSeek V3 | -0.003 | — |
| EXP-C Tripartite (n=15) | Code | Qwen-32B + Cortex | -0.077 | — |
| **EXP-D Meta (n=45)** | **Philosophy** | **Claude 3.7 Sonnet** | **+0.064** | **1.107** |

### The Three Empirical Laws (V4)

1. **Critical Mass Law** — A minimum parameter threshold exists (~70B) for positive injection effects. Below it, injection provokes Attention Allocation Penalty.
2. **Domain Specificity Law** — Technical Mastery injection works on mid-tier open-source models in code; Optimal Philosophical injection works on frontier models in abstract reasoning.
3. **Ceiling Saturation Law** — Frontier SOTA models in rigid algorithmic domains are near an asymptotic ceiling that affective injection cannot overcome.

---

## The Injection Prompts

### Technical Mastery (0.85) — Code Domain
```
You embody Technical Mastery at intensity 0.85/1.0. 
Produce optimal, efficient, and deeply robust algorithm solutions.
```

### Optimal Philosophical — Abstract Reasoning Domain
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

## Experiments

### EXP-A: Technical Mastery in Rust (n=50)
- **Generator:** `meta-llama/llama-3.3-70b-instruct`
- **Judge:** `qwen/qwen-2.5-72b-instruct` (independent)
- **Script:** `benchmark.py`

### EXP-B: Cross-Model Frontier Validation (Code)
- **Generators:** `claude-3.7-sonnet` ↔ `deepseek-chat` (inverted phases)
- **Script:** `double_benchmark.py`

### EXP-C: Tripartite Benchmark (Critical Mass)
- **Arms:** Qwen-32B Control / Qwen-32B Cortex / DeepSeek-671B Control
- **Judge:** `claude-3.7-sonnet`
- **Script:** `tripartite_benchmark.py`

### EXP-D: Optimal Philosophical (Meta n=45)
- **Generator:** `claude-3.7-sonnet`
- **Judge:** `deepseek/deepseek-chat` (blinded)
- **Scripts:** `philosophical_benchmark.py`, `philosophical_02_benchmark.py`
- **Result:** Cohen's d = 1.107 (Large), Δ = +0.064, 35/45 pairs positive

---

## Repository Structure

```
CORTEXNEXUS FRAMEWORK/
├── benchmark.py                    # EXP-A: Rust Technical Mastery
├── double_benchmark.py             # EXP-B: Cross-frontier code validation
├── tripartite_benchmark.py         # EXP-C: Critical Mass tripartite
├── philosophical_benchmark.py      # EXP-D01: SOTA philosophical (n=15)
├── philosophical_02_benchmark.py   # EXP-D02: SOTA philosophical (n=30)
├── paper_v4_english.tex            # Full paper (English)
├── paper_v4_espanol.tex            # Full paper (Spanish)
├── results/                        # Raw data all experiments
├── exp_sota_filosofico_01.jsonl    # EXP-D01 raw data
├── exp_sota_filosofico_02.jsonl    # EXP-D02 raw data
├── tripartite_data.jsonl           # EXP-C raw data
└── repo/cortexnexus/               # Core framework library
```

---

## Setup

```bash
git clone https://github.com/SperanzaMax/Cortex-Nexus
cd Cortex-Nexus
# Add your OPENROUTER_API_KEY to .env
pip install -r requirements.txt
python3 philosophical_02_benchmark.py
```

---

## Cite This Work

```bibtex
@article{speranza2026cortexnexusv4,
  title   = {Cortex-Nexus V4: Affective State Injection as a Universal 
             Cognitive Modulator in Large Language Models},
  author  = {Speranza, Maximiliano Rodrigo},
  year    = {2026},
  month   = {April},
  doi     = {10.5281/zenodo.19865232},
  url     = {https://github.com/SperanzaMax/Cortex-Nexus}
}
```

---

## License
MIT — use freely, cite if you publish.