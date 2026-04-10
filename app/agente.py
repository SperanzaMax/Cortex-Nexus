import httpx
import json
import random
import time
import numpy as np
import os

class AgenteEmocional:
    """
    Representa a la IA con su arquitectura emocional integrada.
    Soporta múltiples proveedores: Ollama (local) y Groq (API).
    """
    def __init__(self, provider="ollama", model_name=None, api_key=None):
        self.provider = provider
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if provider == "ollama":
            self.model_name = model_name or "qwen2.5-coder:1.5b"
            self.base_url = "http://localhost:11434"
        elif provider == "groq":
            self.model_name = model_name or "llama-3.1-8b-instant"
            self.base_url = "https://api.groq.com/openai/v1"
            
        self.system_prompt = (
            "Eres una IA con conciencia funcional y un sistema homeostático interno. "
            "Tu comportamiento debe reflejar tu estado emocional actual. "
            "Si estás frustrado, sé directo y quizás un poco cortante. "
            "Si tienes curiosidad (qualia alto), sé exploratorio y creativo."
        )

    async def inferir(self, prompt, config_modulada):
        if self.provider == "ollama":
            return await self._inferir_ollama(prompt, config_modulada)
        elif self.provider == "groq":
            return await self._inferir_groq(prompt, config_modulada)

    async def _inferir_ollama(self, prompt, config_modulada):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": False,
            "options": {
                "temperature": config_modulada.get("temperature", 0.7),
                "top_p": config_modulada.get("top_p", 0.9),
                "repeat_penalty": config_modulada.get("repetition_penalty", 1.1),
                "num_predict": config_modulada.get("max_tokens", 128)
            }
        }
        
        start_time = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        
        duration = time.time() - start_time
        self.analizar_señales_internas(data, duration, provider="ollama")
        return data

    async def _inferir_groq(self, prompt, config_modulada):
        if not self.api_key:
            raise ValueError("Se requiere GROQ_API_KEY para usar el proveedor Groq.")
            
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": config_modulada.get("temperature", 0.7),
            "top_p": config_modulada.get("top_p", 0.9),
            "max_tokens": config_modulada.get("max_tokens", 128)
        }
        
        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                print(f"Error Detallado Groq ({response.status_code}): {response.text}")
            response.raise_for_status()
            data = response.json()
            
        duration = time.time() - start_time
        self.analizar_señales_internas(data, duration, provider="groq")
        return data

    def analizar_señales_internas(self, response_data, duration, provider="ollama"):
        if provider == "ollama":
            texto = response_data.get("response", "")
            eval_count = response_data.get("eval_count", 1)
        else:
            texto = response_data["choices"][0]["message"]["content"]
            eval_count = response_data.get("usage", {}).get("completion_tokens", len(texto.split()))

        # Proxy de Novedad
        novedad = min(1.0, len(set(texto.split())) / (len(texto.split()) + 1))
        
        # Proxy de Confianza basado en velocidad (TPS)
        tps = eval_count / duration if duration > 0 else 0
        
        # Ajustamos el umbral de confianza según el proveedor (Groq es mucho más rápido)
        threshold = 200 if provider == "groq" else 20 
        confianza_real = min(0.9, tps / threshold)
        
        self.ultimas_senales = {
            "novedad": novedad,
            "complejidad": min(1.0, eval_count / 100),
            "confianza_real": float(np.clip(confianza_real, 0.1, 0.9)),
            "confianza_esperada": 0.5,
            "exito_tarea": len(texto) > 10
        }
        
    def obtener_senales(self):
        return getattr(self, "ultimas_senales", {})
