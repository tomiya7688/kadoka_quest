from __future__ import annotations

import argparse
from dataclasses import dataclass
from statistics import median
from time import perf_counter_ns
from typing import Callable

from kadoka_quest.application.app_command import AppCommand, is_plain_data
from kadoka_quest.application.command_bus import CommandBus


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    ns_per_operation: float
    limit_ns: float

    @property
    def passed(self) -> bool:
        return self.ns_per_operation <= self.limit_ns


def measure(operation: Callable[[], object], iterations: int, samples: int, warmup: int) -> float:
    for _ in range(warmup):
        operation()

    timings: list[float] = []
    for _ in range(samples):
        started = perf_counter_ns()
        for _ in range(iterations):
            operation()
        elapsed = perf_counter_ns() - started
        timings.append(elapsed / iterations)
    return float(median(timings))


def run_benchmarks(iterations: int, samples: int, warmup: int) -> list[BenchmarkResult]:
    payload = {
        "screen": "field",
        "position": [12, 8],
        "flags": {"running": True, "mode": "normal"},
    }
    command = AppCommand("field", "move", payload)
    bus = CommandBus()

    def handler(value: AppCommand) -> str:
        return value.action

    bus.register("field", handler)

    direct_ns = measure(lambda: handler(command), iterations, samples, warmup)
    dispatch_ns = measure(lambda: bus.dispatch(command), iterations, samples, warmup)
    command_ns = measure(lambda: AppCommand("field", "move", payload), iterations, samples, warmup)
    validation_ns = measure(lambda: is_plain_data(payload), iterations, samples, warmup)
    end_to_end_ns = measure(
        lambda: bus.dispatch(AppCommand("field", "move", payload)),
        iterations,
        samples,
        warmup,
    )

    return [
        BenchmarkResult("dispatch", dispatch_ns, max(20_000.0, direct_ns * 25.0)),
        BenchmarkResult("command", command_ns, 40_000.0),
        BenchmarkResult("payload", validation_ns, 30_000.0),
        BenchmarkResult("end-to-end", end_to_end_ns, 60_000.0),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Kadoka Quest runtime routing overhead.")
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    iterations = max(1, args.iterations)
    samples = max(1, args.samples)
    warmup = max(0, args.warmup)

    results = run_benchmarks(iterations, samples, warmup)
    failed = False
    for result in results:
        status = "OK" if result.passed else "FAIL"
        print(
            f"{status} {result.name} "
            f"{result.ns_per_operation / 1000.0:.2f}us <= {result.limit_ns / 1000.0:.2f}us"
        )
        failed = failed or not result.passed

    print("FAIL performance" if failed else "OK performance")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
