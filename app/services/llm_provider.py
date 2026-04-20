from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

import httpx

from app.config import settings


class BaseLLMProvider(ABC):
    provider_name: str

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    provider_name = "mock"

    async def generate(self, prompt: str) -> str:
        await asyncio.sleep(1)
        return (
            "[MOCK LLM RESPONSE]\n\n"
            f"Prompt received: {prompt}\n\n"
            "This is a mock response generated for local testing. "
            "Replace the provider with OpenAI or another real LLM in production."
        )


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_name = "openai"

    async def generate(self, prompt: str) -> str:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing")

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


def get_provider() -> BaseLLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return OpenAICompatibleProvider()
    return MockLLMProvider()
