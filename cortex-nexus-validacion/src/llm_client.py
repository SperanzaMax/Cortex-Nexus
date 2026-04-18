"""
llm_client.py — Cliente híbrido NVIDIA NIM + OpenRouter
Cortex-Nexus · Fase de Validación · 2026-04-16
"""
import asyncio
import os
import httpx
from typing import List

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

HEADERS_OPENROUTER = {
    "HTTP-Referer": "https://cortex-nexus-local",
    "X-Title": "Cortex-Nexus-Validacion"
}


async def _post_with_retry(client, url, headers, payload, model, backoff):
    last_error = None
    for attempt, wait in enumerate([0] + backoff):
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=90.0)
            if resp.status_code == 429:
                last_error = "Rate limit 429"
                retry_after = int(resp.headers.get("retry-after", 30))
                await asyncio.sleep(min(retry_after, 60))
                continue
            if resp.status_code in (503, 502):
                last_error = f"Service error {resp.status_code}"
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_error = str(e)
            print(f"  [{model}] try {attempt} error: {last_error[:100]}")
            if attempt == len(backoff):
                raise Exception(f"Agotados reintentos para {model}: {last_error}")
    raise Exception(f"Fallo tras {len(backoff)+1} intentos [{model}]: {last_error}")


async def call_nvidia(client, model, system_prompt, user_prompt, max_tokens=300, temperature=0.85, backoff=[5,15,30]):
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    url = f"{NVIDIA_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    return await _post_with_retry(client, url, headers, payload, model, backoff)


async def call_openrouter(client, model, system_prompt, user_prompt, max_tokens=300, temperature=0.10, backoff=[5,15,30]):
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = {**HEADERS_OPENROUTER, "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    return await _post_with_retry(client, url, headers, payload, model, backoff)


async def route_call(client, routing, role, model, system_prompt, user_prompt, max_tokens, temperature, backoff=[5,15,30]):
    provider = routing.get(role, "nvidia")
    if provider == "openrouter":
        return await call_openrouter(client, model, system_prompt, user_prompt, max_tokens, temperature, backoff)
    return await call_nvidia(client, model, system_prompt, user_prompt, max_tokens, temperature, backoff)
