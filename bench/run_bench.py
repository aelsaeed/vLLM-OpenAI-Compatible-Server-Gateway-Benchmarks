from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

PROMPTS_PATH = Path("data/prompts.jsonl")
REPORTS_DIR = Path("reports")




def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    k = int(round((pct / 100) * (len(sorted_values) - 1)))
    return sorted_values[k]



@dataclass
class BenchResult:
    latency_s: float
    tokens: int
    error: bool


def load_prompts() -> list[dict[str, Any]]:
    prompts = []
    with PROMPTS_PATH.open() as handle:
        for line in handle:
            prompts.append(json.loads(line))
    return prompts


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    model: str,
    payload: dict[str, Any],
) -> BenchResult:
    start = time.time()
    tokens = 0
    try:
        response = await client.post(
            url,
            json={
                "model": model,
                "messages": payload["messages"],
                "max_tokens": payload.get("max_tokens", 128),
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        tokens = sum(value for value in usage.values() if isinstance(value, int))
        return BenchResult(latency_s=time.time() - start, tokens=tokens, error=False)
    except (httpx.HTTPError, ValueError):
        return BenchResult(latency_s=time.time() - start, tokens=0, error=True)


async def run_benchmark(args: argparse.Namespace) -> None:
    prompts = load_prompts()
    total = args.total_requests
    concurrency = args.concurrency
    url = f"{args.gateway_url.rstrip('/')}/chat"

    results: list[BenchResult] = []
    start_time = time.time()

    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        async def worker() -> None:
            prompt = random.choice(prompts)
            async with sem:
                result = await send_request(client, url, args.model, prompt)
                results.append(result)

        await asyncio.gather(*(worker() for _ in range(total)))

    duration = time.time() - start_time
    latencies = [r.latency_s for r in results]
    errors = [r for r in results if r.error]
    tokens_total = sum(r.tokens for r in results)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    throughput = total / duration if duration else 0
    tokens_per_sec = tokens_total / duration if duration else 0
    error_rate = len(errors) / total if total else 0

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"bench-{int(time.time())}.md"
    report_path.write_text(
        "\n".join(
            [
                "# Benchmark Report",
                "",
                f"- Total requests: {total}",
                f"- Concurrency: {concurrency}",
                f"- Duration: {duration:.2f}s",
                f"- p50 latency: {p50:.3f}s",
                f"- p95 latency: {p95:.3f}s",
                f"- Throughput: {throughput:.2f} req/s",
                f"- Tokens/sec (approx): {tokens_per_sec:.2f}",
                f"- Error rate: {error_rate:.2%}",
            ]
        )
    )

    print(f"Report written to {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark gateway /chat endpoint")
    parser.add_argument("--gateway-url", default="http://localhost:8000")
    parser.add_argument("--model", default="Qwen/Qwen2-0.5B-Instruct")
    parser.add_argument("--total-requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_benchmark(parse_args()))
