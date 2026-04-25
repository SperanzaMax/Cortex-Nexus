"""
Cortex-Nexus V2 — Multi-backend LLM Client
Supports OpenRouter (Interrogador) and NVIDIA NIM (Ente + Juez)
with separate API keys to avoid rate limit collisions.
"""
import asyncio
import os
import httpx
from typing import List

HEADERS = {
    "HTTP-Referer": "https://cortex-nexus-v2",
    "X-Title": "Cortex-Nexus-V2-Tecnico"
}

# ============================================================
# OpenRouter — for Interrogador (small models)
# ============================================================
async def call_openrouter(
    client: httpx.AsyncClient,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 300,
    temperature: float = 0.85,
    backoff: List[int] = [5, 15, 30]
) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {**HEADERS, "Authorization": f"Bearer {api_key}"}
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    
    print(f"DEBUG qwen max_tokens={max_tokens} temp={temperature}")
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    last_error = None
    for attempt, wait in enumerate([0] + backoff):
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 429:
                last_error = "Rate limit 429"
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_error = str(e)
            if attempt == len(backoff):
                raise Exception(f"OpenRouter agotado para {model}: {last_error}")
            continue

    raise Exception(f"OpenRouter fallo tras {len(backoff) + 1} intentos: {last_error}")

# ============================================================
# NVIDIA NIM — for Ente (70B) and Juez (Nemo)
# ============================================================
async def call_nvidia(
    client: httpx.AsyncClient,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 300,
    temperature: float = 0.85,
    api_key_env: str = "NVIDIA_API_KEY_ENTE",
    backoff: List[int] = [5, 15, 30]
) -> str:
    """
    Call NVIDIA NIM API with a specific API key environment variable.
    api_key_env controls which key to use:
      - NVIDIA_API_KEY_ENTE for the experimental/control model
      - NVIDIA_API_KEY_JUEZ for the judge model
    """
    api_key = os.environ.get(api_key_env, "")
    if not api_key:
        raise Exception(f"Missing env var: {api_key_env}")
    
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    
    print(f"DEBUG qwen max_tokens={max_tokens} temp={temperature}")
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    import random
    last_error = None
    for attempt, wait in enumerate([0] + [10, 30, 60, 120]):
        if wait > 0:
            jitter = random.uniform(1, 15)
            await asyncio.sleep(wait + jitter)
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                last_error = "Rate limit 429"
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_error = str(e)
            if attempt == len(backoff):
                raise Exception(f"NVIDIA NIM agotado para {model}: {last_error}")
            continue

    raise Exception(f"NVIDIA NIM fallo tras {len(backoff) + 1} intentos: {last_error}")
