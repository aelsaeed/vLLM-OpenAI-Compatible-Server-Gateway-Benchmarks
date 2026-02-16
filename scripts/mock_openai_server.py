from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="Mock OpenAI-Compatible Server")


def _token_estimate(messages: list[dict[str, Any]], max_tokens: int) -> int:
    prompt_chars = sum(len(str(message.get("content", ""))) for message in messages)
    prompt_tokens = max(1, prompt_chars // 4)
    completion_tokens = max(8, min(max_tokens, 32))
    return prompt_tokens + completion_tokens


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(payload: dict[str, Any]) -> Any:
    model = str(payload.get("model", "mock-model"))
    messages = payload.get("messages")
    if not isinstance(messages, list):
        messages = []
    max_tokens = payload.get("max_tokens")
    if not isinstance(max_tokens, int):
        max_tokens = 64

    content = "Mock response: gateway demo path is healthy."
    prompt_tokens = max(1, sum(len(str(msg.get("content", ""))) for msg in messages) // 4)

    if bool(payload.get("stream")):

        async def event_stream() -> AsyncIterator[bytes]:
            chunks = [
                '{"choices":[{"delta":{"content":"Mock response:"}}]}',
                '{"choices":[{"delta":{"content":" gateway demo path is healthy."}}]}',
                "[DONE]",
            ]
            for chunk in chunks:
                yield f"data: {chunk}\n\n".encode()

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    total_tokens = _token_estimate(messages, max_tokens)
    return {
        "id": "chatcmpl-mock-123",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": total_tokens - prompt_tokens,
            "total_tokens": total_tokens,
        },
    }


@app.post("/v1/embeddings")
def embeddings(payload: dict[str, Any]) -> dict[str, Any]:
    model = str(payload.get("model", "mock-model"))
    return {
        "object": "list",
        "model": model,
        "data": [{"index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}],
        "usage": {"prompt_tokens": 4, "total_tokens": 4},
    }
