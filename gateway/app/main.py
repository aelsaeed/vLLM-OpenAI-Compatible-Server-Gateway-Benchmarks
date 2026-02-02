from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any, AsyncIterator

import httpx
import orjson
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from gateway.app.config import settings
from gateway.app.limits import RateLimiter
from gateway.app.logging import configure_logging
from gateway.app.metrics import (
    aggregate_tokens,
    record_cache_hit,
    record_error,
    record_latency,
    record_request,
    record_tokens,
    render_metrics,
)
from gateway.app.safety import SafetyChecker

app = FastAPI()
logger = logging.getLogger("gateway")

configure_logging()

rate_limiter = RateLimiter(settings.rate_limit_rps, settings.rate_limit_burst)
safety_checker = SafetyChecker(settings.max_tokens_cap, settings.denylist_words)
redis_client: Redis | None = None


@app.on_event("startup")
async def startup() -> None:
    global redis_client
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


@app.on_event("shutdown")
async def shutdown() -> None:
    if redis_client:
        await redis_client.close()


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    client_key = request.client.host if request.client else "unknown"
    if not await rate_limiter.allow(client_key):
        record_request(request.url.path, "429")
        return JSONResponse({"error": "rate_limited", "request_id": request_id}, status_code=429)

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.request_size_limit_bytes:
        record_request(request.url.path, "413")
        return JSONResponse({"error": "payload_too_large", "request_id": request_id}, status_code=413)

    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


def cache_key(path: str, payload: dict[str, Any]) -> str:
    payload_bytes = orjson.dumps(payload)
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return f"cache:{path}:{settings.model_id}:{digest}"


async def fetch_with_retry(method: str, url: str, json_body: dict[str, Any]) -> httpx.Response:
    async with httpx.AsyncClient(timeout=60.0) as client:
        retryer = AsyncRetrying(
            stop=stop_after_attempt(settings.retry_attempts),
            wait=wait_exponential(min=settings.retry_min_seconds, max=settings.retry_max_seconds),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )
        async for attempt in retryer:
            with attempt:
                response = await client.request(method, url, json=json_body)
                response.raise_for_status()
                return response
    raise HTTPException(status_code=502, detail="upstream_unavailable")


async def stream_with_retry(url: str, payload: dict[str, Any]) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=None) as client:
        retryer = AsyncRetrying(
            stop=stop_after_attempt(settings.retry_attempts),
            wait=wait_exponential(min=settings.retry_min_seconds, max=settings.retry_max_seconds),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )
        async for attempt in retryer:
            with attempt:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk
                return


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.model_id}


@app.get("/metrics")
async def metrics() -> Response:
    data, content_type = render_metrics()
    return Response(content=data, media_type=content_type)


@app.post("/chat")
async def chat(request: Request) -> Response:
    start_time = time.time()
    payload = await request.json()
    payload.setdefault("model", settings.model_id)
    request_id = request.state.request_id

    safety = safety_checker.check(payload)
    if not safety.allowed:
        record_request("/chat", "400")
        logger.info(
            "safety_blocked",
            extra={"request_id": request_id, "model_id": settings.model_id, "extra": {"reason": safety.reason}},
        )
        raise HTTPException(status_code=400, detail="Request blocked by safety policy.")
    if safety.adjusted_max_tokens is not None:
        payload["max_tokens"] = safety.adjusted_max_tokens

    stream = bool(payload.get("stream"))
    redis = redis_client
    cacheable = not stream and redis is not None
    if cacheable:
        assert redis is not None
        key = cache_key("chat", payload)
        cached = await redis.get(key)
        if cached:
            record_cache_hit("/chat")
            record_request("/chat", "200")
            record_latency("/chat", start_time)
            logger.info(
                "cache_hit",
                extra={
                    "request_id": request_id,
                    "model_id": settings.model_id,
                    "extra": {"path": "/chat"},
                },
            )
            return Response(content=cached, media_type="application/json")

    try:
        if stream:
            async def streamer() -> AsyncIterator[bytes]:
                async for chunk in stream_with_retry(
                    f"{settings.vllm_base_url}/v1/chat/completions", payload
                ):
                    yield chunk
            record_request("/chat", "200")
            record_latency("/chat", start_time)
            return StreamingResponse(streamer(), media_type="text/event-stream")
        response = await fetch_with_retry(
            "POST", f"{settings.vllm_base_url}/v1/chat/completions", payload
        )
    except httpx.HTTPError as exc:
        record_error("/chat")
        record_request("/chat", "502")
        logger.error(
            "upstream_error",
            extra={
                "request_id": request_id,
                "model_id": settings.model_id,
                "extra": {"error": str(exc)},
            },
        )
        raise HTTPException(status_code=502, detail="Upstream error") from exc

    response_payload = response.json()
    usage = response_payload.get("usage")
    tokens = aggregate_tokens(usage)
    latency_s = time.time() - start_time
    record_tokens("/chat", tokens, latency_s)
    record_request("/chat", "200")
    record_latency("/chat", start_time)

    if cacheable:
        assert redis is not None
        await redis.setex(key, settings.cache_ttl_seconds, json.dumps(response_payload))

    logger.info(
        "chat_response",
        extra={
            "request_id": request_id,
            "model_id": settings.model_id,
            "extra": {"cached": False, "tokens": tokens},
        },
    )

    return JSONResponse(response_payload)


@app.post("/embed")
async def embed(request: Request) -> Response:
    start_time = time.time()
    payload = await request.json()
    payload.setdefault("model", settings.model_id)
    request_id = request.state.request_id

    try:
        response = await fetch_with_retry(
            "POST", f"{settings.vllm_base_url}/v1/embeddings", payload
        )
        record_request("/embed", "200")
        record_latency("/embed", start_time)
        return JSONResponse(response.json())
    except httpx.HTTPStatusError as exc:
        record_request("/embed", str(exc.response.status_code))
        record_error("/embed")
        logger.warning(
            "embed_unavailable",
            extra={
                "request_id": request_id,
                "model_id": settings.model_id,
                "extra": {"status": exc.response.status_code},
            },
        )
    except httpx.HTTPError as exc:
        record_request("/embed", "502")
        record_error("/embed")
        logger.error(
            "embed_error",
            extra={
                "request_id": request_id,
                "model_id": settings.model_id,
                "extra": {"error": str(exc)},
            },
        )

    stub = {
        "data": [],
        "model": settings.model_id,
        "object": "list",
        "warning": "Embeddings not available in vLLM deployment.",
    }
    return JSONResponse(stub, status_code=501)
