from __future__ import annotations

import argparse
from dataclasses import dataclass
from statistics import median
from time import perf_counter_ns
from typing import Callable

from kadoka_quest.application.app_command import AppCommand, is_plain_data
from kadoka_quest.application.command_bus import CommandBus


Operation = Callable[[], object]


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    operation: Operation
    limit_ns: float


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    ns_per_operation: float
    limit_ns: float

    @property
    def passed(self) -> bool:
        return self.ns_per_operation <= self.limit_ns


def measure(operation: Operation, iterations: int, samples: int, warmup: int) -> float:
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


def build_benchmark_cases() -> list[BenchmarkCase]:
    """Return representative hot-path checks; extend this list as Kadoka Quest grows."""
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

    return [
        BenchmarkCase("dispatch", lambda: bus.dispatch(command), 20_000.0),
        BenchmarkCase("command", lambda: AppCommand("field", "move", payload), 40_000.0),
        BenchmarkCase("payload", lambda: is_plain_data(payload), 30_000.0),
        BenchmarkCase(
            "end-to-end",
            lambda: bus.dispatch(AppCommand("field", "move", payload)),
            60_000.0,
        ),
    ]


def run_benchmarks(
    iterations: int,
    samples: int,
    warmup: int,
    only: set[str] | None = None,
) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    for case in build_benchmark_cases():
        if only and case.name not in only:
            continue
        measured_ns = measure(case.operation, iterations, samples, warmup)
        results.append(BenchmarkResult(case.name, measured_ns, case.limit_ns))
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Kadoka Quest runtime performance guardrails.")
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="NAME",
        help="Run only the named benchmark. Repeat to select multiple cases.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List benchmark names without running them.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cases = build_benchmark_cases()
    available = {case.name for case in cases}

    if args.list:
        for case in cases:
            print(case.name)
        return 0

    requested = set(args.only)
    unknown = requested - available
    if unknown:
        print(f"FAIL unknown benchmark: {', '.join(sorted(unknown))}")
        return 2

    iterations = max(1, args.iterations)
    samples = max(1, args.samples)
    warmup = max(0, args.warmup)

    results = run_benchmarks(iterations, samples, warmup, requested or None)
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
