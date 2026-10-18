"""Small repeatable HTTP load smoke with percentile evidence output."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(math.ceil(percentile * len(ordered)) - 1, len(ordered) - 1)
    return ordered[max(index, 0)]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=None,
        help="Repeat for multiple GET paths",
    )
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--max-p95-ms", type=float, default=1000.0)
    args = parser.parse_args()
    paths = args.paths or ["/healthz", "/readyz", "/public/v1/partners/denjaka-2/intake-config"]
    if args.duration <= 0 or args.concurrency <= 0:
        raise SystemExit("duration and concurrency must be positive")

    started_at = datetime.now(UTC)
    deadline = time.perf_counter() + args.duration
    latencies: list[float] = []
    latencies_by_path: dict[str, list[float]] = {path: [] for path in paths}
    status_counts: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=10.0) as client:

        async def worker(worker_id: int) -> None:
            cursor = worker_id
            while time.perf_counter() < deadline:
                path = paths[cursor % len(paths)]
                cursor += 1
                request_started = time.perf_counter()
                try:
                    response = await client.get(path)
                    latency = (time.perf_counter() - request_started) * 1000
                    latencies.append(latency)
                    latencies_by_path[path].append(latency)
                    status_counts[str(response.status_code)] += 1
                    path_counts[path] += 1
                    if response.status_code >= 400:
                        errors[f"http_{response.status_code}"] += 1
                except Exception as exc:
                    latency = (time.perf_counter() - request_started) * 1000
                    latencies.append(latency)
                    latencies_by_path[path].append(latency)
                    errors[type(exc).__name__] += 1

        await asyncio.gather(*(worker(index) for index in range(args.concurrency)))

    total = len(latencies)
    error_count = sum(errors.values())
    error_rate = error_count / total if total else 1.0
    p95 = _percentile(latencies, 0.95)
    passed = total > 0 and error_rate <= args.max_error_rate and p95 <= args.max_p95_ms
    evidence = {
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "target": args.base_url,
        "duration_seconds": args.duration,
        "concurrency": args.concurrency,
        "paths": paths,
        "requests": total,
        "requests_per_second": round(total / args.duration, 2),
        "status_counts": dict(status_counts),
        "path_counts": dict(path_counts),
        "errors": dict(errors),
        "error_rate": round(error_rate, 6),
        "latency_ms": {
            "min": round(min(latencies), 3) if latencies else None,
            "p50": round(_percentile(latencies, 0.50), 3),
            "p95": round(p95, 3),
            "p99": round(_percentile(latencies, 0.99), 3),
            "max": round(max(latencies), 3) if latencies else None,
        },
        "per_path": {
            path: {
                "requests": len(values),
                "p50_ms": round(_percentile(values, 0.50), 3),
                "p95_ms": round(_percentile(values, 0.95), 3),
                "p99_ms": round(_percentile(values, 0.99), 3),
                "max_ms": round(max(values), 3) if values else None,
            }
            for path, values in latencies_by_path.items()
        },
        "thresholds": {"max_error_rate": args.max_error_rate, "max_p95_ms": args.max_p95_ms},
        "status": "passed" if passed else "failed",
    }
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / ".artifacts" / "readiness"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"load-smoke-{stamp}.json"
    output_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "evidence": str(output_path), **evidence["latency_ms"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
