import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_model(model_id):
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Hola, responde brevemente."}],
        "max_tokens": 50
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        print(f"Model: {model_id}")
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
        print("-" * 20)

async def main():
    models = [
        "google/gemma-3-4b-it",
        "meta-llama/llama-3.1-405b-instruct",
        "nvidia/nemotron-mini-4b-instruct",
        "z-ai/glm-4.7-flash"
    ]
    for m in models:
        await test_model(m)

if __name__ == "__main__":
    asyncio.run(main())
