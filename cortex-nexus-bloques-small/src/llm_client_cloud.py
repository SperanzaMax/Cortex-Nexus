import asyncio
import os
import httpx
from typing import List

HEADERS = {
    "HTTP-Referer": "https://cortex-nexus-local",
    "X-Title": "Cortex-Nexus-Cloud"
}

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
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    last_error = None
    # Ciclo de intentos: 0 (inmediato) + backoffs
    for attempt, wait in enumerate([0] + backoff):
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            resp = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=45
            )
            
            if resp.status_code == 429:
                last_error = "Rate limit 429"
                continue
                
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            last_error = str(e)
            if attempt == len(backoff):
                raise Exception(f"Agotados reintentos para {model}: {last_error}")
            continue

    raise Exception(f"Fallo tras {len(backoff) + 1} intentos: {last_error}")

async def call_nvidia(
    client: httpx.AsyncClient,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 300,
    temperature: float = 0.85,
    backoff: List[int] = [5, 15, 30]
) -> str:
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    
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
            resp = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=45
            )
            
            if resp.status_code == 429:
                last_error = "Rate limit 429"
                continue
                
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            last_error = str(e)
            if attempt == len(backoff):
                raise Exception(f"Agotados reintentos para NVIDIA {model}: {last_error}")
            continue

    raise Exception(f"Fallo NVIDIA tras {len(backoff) + 1} intentos: {last_error}")
