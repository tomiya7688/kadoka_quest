from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from statistics import median
from time import perf_counter_ns
from types import SimpleNamespace
from typing import Callable

from kadoka_engine.field_ai import choose_field_ai
from kadoka_engine.chase_traffic import ChaseTraffic
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_quest.application.app_command import AppCommand, is_plain_data
from kadoka_quest.application.command_bus import CommandBus
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.progress_session import ProgressSession
from kadoka_quest.core.field_engine import FieldEngine
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.battle_rewards import battle_experience
from kadoka_quest.core.spawn_levels import metal_area_level_range


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

    field = FieldEngine(
        {
            "width": 3,
            "height": 3,
            "tiles": [["floor", "floor", "floor"] for _ in range(3)],
            "events": [],
        },
        {"floor": {"player_walkable": True}},
    )

    battle_session = BattleSession()
    battle_runtime = SimpleNamespace(
        battle_session=battle_session,
        monsters=object(),
        states=object(),
        progress_session=ProgressSession({}),
        status="",
        mode="battle",
    )
    battle_application = BattleCommandApplication(battle_runtime)
    battle_selection_command = AppCommand("battle", "selection.move", {"amount": 1})

    # Isolate per-actor escape checks from repository I/O and skill resolution.
    flee_engine = SimpleNamespace(
        learning_enabled=True, encounter_context="normal",
        rng=SimpleNamespace(random=lambda: 0.99),
    )
    flee_actor = SimpleNamespace(alive=True, flee_rates={"normal": 0.15})
    reward_enemies = [SimpleNamespace(
        fled=False, hp=0, record=SimpleNamespace(level=100),
        experience_reward={"base": 300, "per_level": 35, "squared_divisor": 10},
    ) for _ in range(4)]

    field_ai_rng = random.Random(146)
    wild_world = {"width": 16, "height": 16, "tiles": [["floor"] * 16 for _ in range(16)]}
    wild_blocks = {"floor": {"enemy_walkable": True}}
    wild = HiddenEnemyController(FieldEngine(wild_world, wild_blocks), random.Random(147))
    wild.set_world(wild_world, wild_blocks)
    wild.monsters = [
        {"x": index % 8, "y": index // 8, "ai": ("random", "chase", "idle")[index % 3]}
        for index in range(24)
    ]
    fork_world = {"width": 10, "height": 5, "tiles": [list(row) for row in (
        "##########", "#........#", "#...###..#", "#........#", "##########",
    )]}
    fork_field = FieldEngine(fork_world, {".": {"enemy_walkable": True}, "#": {"enemy_walkable": False}})
    traffic = ChaseTraffic(fork_field)

    def chase_fork() -> object:
        traffic.clear()
        traffic.begin(1000, {1, 2})
        traffic.plan(1, (3, 2), (8, 2), set(), set(), 320)
        return traffic.plan(2, (2, 2), (8, 2), {(3, 2)}, set(), 320)

    return [
        BenchmarkCase("chase-fork-two", chase_fork, 1_000_000.0),
        BenchmarkCase("wild-movement-24", lambda: wild.move_all((12, 1), set()), 1_000_000.0),
        BenchmarkCase(
            "field-ai-assignment",
            lambda: choose_field_ai(field_ai_rng, {"random": 70, "chase": 25, "idle": 5}),
            30_000.0,
        ),
        BenchmarkCase(
            "metal-area-levels",
            lambda: metal_area_level_range([
                SimpleNamespace(species_id="maru", level=90),
                SimpleNamespace(species_id="slime", level=60),
                SimpleNamespace(species_id="slime", level=40),
                SimpleNamespace(species_id="kadoka", level=20),
            ]),
            30_000.0,
        ),
        BenchmarkCase("battle-rewards", lambda: battle_experience(reward_enemies), 50_000.0),
        BenchmarkCase(
            "enemy-flee-check",
            lambda: BattleEngine._try_enemy_flee(flee_engine, flee_actor),
            20_000.0,
        ),
        BenchmarkCase("dispatch", lambda: bus.dispatch(command), 20_000.0),
        BenchmarkCase("command", lambda: AppCommand("field", "move", payload), 40_000.0),
        BenchmarkCase("payload", lambda: is_plain_data(payload), 30_000.0),
        BenchmarkCase(
            "end-to-end",
            lambda: bus.dispatch(AppCommand("field", "move", payload)),
            60_000.0,
        ),
        BenchmarkCase(
            "field-move",
            lambda: field.resolve_player_move(1, 1, 1, 0, "front", [], []),
            40_000.0,
        ),
        BenchmarkCase(
            "battle-routing",
            lambda: battle_application.handle(battle_selection_command),
            40_000.0,
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
