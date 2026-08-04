from dataclasses import dataclass

import httpx

from app.config import Settings
from app.services.rag import RetrievedChunk


@dataclass(frozen=True)
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class AnswerGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def answer(self, question: str, chunks: list[RetrievedChunk]) -> LLMResult:
        context = "\n\n".join(
            f"[{index + 1}] {chunk.content}" for index, chunk in enumerate(chunks)
        )
        if not self.settings.openai_api_key:
            return self._deterministic_answer(question, chunks)

        prompt = (
            "You are a customer-service voice agent. Answer only from the supplied context. "
            "Be concise enough to speak aloud. If the context is insufficient, say you need to "
            "transfer the caller.\n\n"
            f"CONTEXT\n{context}\n\nQUESTION\n{question}"
        )
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                json={
                    "model": self.settings.openai_model,
                    "input": prompt,
                    "max_output_tokens": 220,
                    "store": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
        text = payload.get("output_text", "").strip()
        usage = payload.get("usage", {})
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        cost = (
            input_tokens * self.settings.openai_input_cost_per_million
            + output_tokens * self.settings.openai_output_cost_per_million
        ) / 1_000_000
        return LLMResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

    def _deterministic_answer(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> LLMResult:
        if not chunks or chunks[0].score < 0.18:
            text = "I do not have enough approved information to answer that. I will transfer you."
        else:
            text = chunks[0].content.strip().split("\n")[0]
        input_tokens = max(
            1,
            len(question.split()) + sum(len(chunk.content.split()) for chunk in chunks),
        )
        output_tokens = max(1, len(text.split()))
        return LLMResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
        )
