# Cortex-Nexus: Domain-Specific Emotional Prompt Engineering for LLMs

[![DOI](https://img.shields.io/badge/DOI-pending-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Paper: PeerJ CS](https://img.shields.io/badge/Paper-PeerJ%20CS-orange)]()

## Overview

Cortex-Nexus is an automated experimental platform for studying domain-specific emotional prompt engineering in Large Language Models. Through **912 controlled evaluation cycles** across **8 experimental phases**, we demonstrate that:

1. **Each task domain has a distinct optimal emotional configuration** — curiosity for philosophical tasks, concentration for technical tasks, and technical mastery for code generation
2. **Subtle emotional intensity outperforms extreme intensity** (the "Subtlety Effect")
3. **Combining multiple emotional axes produces cognitive interference** rather than synergy
4. **Self-refinement pipelines amplify emotional effects** by 7× in code generation

These findings are formalized as the **Task-Emotion Alignment Hypothesis**.

## Key Results

| Domain | Optimal Emotion | Δ (Effect) | p-value | Cohen's d |
|---|---|---|---|---|
| Philosophical | Curiosity (0.95) | +0.192 | 0.022 | — |
| Technical | Concentration (0.50) | +0.178 | <0.05 | — |
| **Code** | **Mastery (0.30–0.85)** | **+0.357** | **0.003** | **0.528** |

## Architecture

```
Question Generator (Gemma-3-4B) → MD5 Dedup Buffer
        ↓
Ente (Llama-3.3-70B) × 2: [Emotional] + [Neutral]
        ↓ (optional: Self-Refinement Pipeline)
Pass 1: Emotional Generation → Pass 2: Neutral Critique → Pass 3: Neutral Refinement
        ↓
Judge (Qwen-2.5-72B) — Blind, randomized order
        ↓
Δ = Score_exp − Score_ctl → JSONL persistence
```

## Repository Structure

```
├── engine/              # Experimental engine source code
│   ├── main_v4.py       # Main entry point
│   ├── cycle_v4.py      # Core cycle engine (question gen → response → judge)
│   ├── emotions.py      # Emotional state definitions (all 15+ states)
│   └── llm_client_cloud.py  # Multi-backend LLM client (NVIDIA NIM + OpenRouter)
│
├── configs/             # Experiment configuration files (JSON)
│   ├── config_v3c.json  # V3C: Self-refinement pilot
│   ├── config_v4a.json  # V4A: Curiosity intensity ladder (technical)
│   ├── config_v4b.json  # V4B: Perfectionism validation (code)
│   ├── config_v5a.json  # V5A: Cross-domain transfer
│   ├── config_v5b.json  # V5B: Bidimensional comparison
│   ├── config_v5c.json  # V5C: Mastery discovery
│   ├── config_v6a.json  # V6A: Mastery intensity ladder
│   └── config_v6b.json  # V6B: Synergy test (mastery × precision)
│
├── data/                # Raw experimental data (JSONL)
│   ├── cycles_v3c_refinement.jsonl  (n=128)
│   ├── cycles_v4a_tecnico.jsonl     (n=122)
│   ├── cycles_v4b_code.jsonl        (n=91)
│   ├── cycles_v5a_tecnico.jsonl     (n=123)
│   ├── cycles_v5b_tecnico.jsonl     (n=98)
│   ├── cycles_v5c_code.jsonl        (n=116)
│   ├── cycles_v6a_code.jsonl        (n=115)
│   └── cycles_v6b_code.jsonl        (n=119)
│
├── paper/               # LaTeX manuscript (PeerJ CS format)
│   ├── cortex_nexus_peerj.tex
│   ├── peerj.bib
│   └── wlpeerj.cls
│
└── LICENSE
```

## Experimental Phases

| Phase | Domain | Focus | n |
|---|---|---|---|
| V3C | Code | Self-refinement pilot (Perfectionism vs Minimalism) | 128 |
| V4A | Technical | Curiosity intensity ladder (0.20–0.95) | 122 |
| V4B | Code | Perfectionism validation | 91 |
| V5A | Technical | Cross-domain transfer test | 123 |
| V5B | Technical | Bidimensional comparison | 98 |
| V5C | Code | **Mastery discovery** (breakthrough) | 116 |
| V6A | Code | Mastery intensity ladder (subtlety effect) | 115 |
| V6B | Code | Synergy test (mastery × precision → interference) | 119 |
| | | **Total** | **912** |

## Reproduction

### Requirements

- Python 3.12+
- API keys: NVIDIA NIM (`NVIDIA_API_KEY_ENTE`) and/or OpenRouter (`OPENROUTER_API_KEY`)
- Dependencies: `httpx`, `python-dotenv`, `psutil`

### Running an Experiment

```bash
# Set API keys
export NVIDIA_API_KEY_ENTE="your-key"
export OPENROUTER_API_KEY="your-key"

# Run a specific phase
python engine/main_v4.py configs/config_v5c.json
```

### Data Format

Each JSONL record contains:
- `tau`: cycle number
- `emotion`, `intensity`: experimental condition
- `question`: generated task prompt
- `ente_response_experimental`: emotionally-prompted response
- `ente_response_control`: neutral baseline response
- `score_combinado_exp`, `score_combinado_ctl`: weighted quality scores
- `delta`: per-cycle effect (Score_exp − Score_ctl)
- `judge_order`: randomization indicator (exp_first/ctl_first)

## Citation

If you use this work, please cite:

```bibtex
@article{speranza2026cortexnexus,
  title={Cortex-Nexus: Domain-Specific Emotional Prompt Engineering for Large Language Models},
  author={Speranza, Maximiliano Rodrigo},
  year={2026},
  journal={PeerJ Computer Science},
  note={Under review}
}
```

## License

MIT License — see [LICENSE](LICENSE).

## Author

**Maximiliano Rodrigo Speranza**  
Independent Researcher, Buenos Aires, Argentina  
[GitHub](https://github.com/SperanzaMax) · [LinkedIn](https://linkedin.com/in/speranzamax)
