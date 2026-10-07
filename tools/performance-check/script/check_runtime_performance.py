# {
#   責務: [check_runtime_performance: 専用fixtureによる既存runtimeの性能を測定し、大きな性能退行を検出します]
#   フィールド: []
# }
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


# {
#   責務: [BenchmarkCase: 測定する処理と時間上限を保持します]
#   フィールド: [
#     name: 結果に表示する測定項目の名前（str）
#     operation: 一回分として反復する測定処理（Operation）
#     limit_ns: 処理一回あたりに許容する時間上限。単位はナノ秒です（float）
#   ]
# }
@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    operation: Operation
    limit_ns: float


# {
#   責務: [BenchmarkResult: 測定項目の中央値と時間上限を保持し、合否を判定します]
#   フィールド: [
#     name: 測定結果に表示する項目名（str）
#     ns_per_operation: 一回あたりの測定時間の中央値。単位はナノ秒です（float）
#     limit_ns: 一回あたりに許容する時間上限。単位はナノ秒です（float）
#   ]
# }
@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    ns_per_operation: float
    limit_ns: float

    # {
    #   責務: [passed: 測定時間が許容上限以下かを判定します]
    #   処理: [1: 測定時間が許容上限以下かを判定します]
    #   引数: [
    #     self: 測定中央値と時間上限を持つBenchmarkResult
    #   ]
    #   戻り値: [result: 測定中央値が上限以下ならTrue、それ以外はFalse（bool）]
    # }
    @property
    def passed(self) -> bool:
        return self.ns_per_operation <= self.limit_ns


# {
#   責務: [measure: 事前実行後に処理を反復し、一回あたりの時間の中央値を返します]
#   処理: [1: 事前実行後に処理を反復し、一回あたりの時間の中央値を返します]
#   引数: [
#     operation: 一回分として反復する測定処理（Operation）
#     iterations: 一つのサンプルで処理を反復する回数（int）
#     samples: 中央値を得るために測定するサンプル数（int）
#     warmup: 測定から除外する事前実行回数（int）
#   ]
#   戻り値: [result: 処理一回あたりの時間の中央値。単位はナノ秒です（float）]
# }
def measure(operation: Operation, iterations: int, samples: int, warmup: int) -> float:
    # 初回実行の影響を測定から除くため、指定回数の事前実行を行う。
    for _ in range(warmup):
        operation()

    # 各サンプルの反復時間を一回分へ換算し、同じ条件で比較できるようにする。
    timings: list[float] = []
    for _ in range(samples):
        started = perf_counter_ns()
        for _ in range(iterations):
            operation()
        elapsed = perf_counter_ns() - started
        timings.append(elapsed / iterations)
    # 一時的な負荷の影響を抑えるため、平均ではなくサンプル中央値を使う。
    return float(median(timings))


# {
#   責務: [build_benchmark_cases: 専用fixtureで実行する、代表的なruntime性能測定の項目を組み立てます]
#   処理: [1: 専用fixtureで実行する、代表的なruntime性能測定の項目を組み立てます]
#   引数: []
#   戻り値: [result: 測定処理と許容上限を持つBenchmarkCaseの一覧（list[BenchmarkCase]）]
# }
def build_benchmark_cases() -> list[BenchmarkCase]:
    """Return representative hot-path checks; extend this list as Kadoka Quest grows."""
    payload = {
        "screen": "field",
        "position": [12, 8],
        "flags": {"running": True, "mode": "normal"},
    }
    command = AppCommand("field", "move", payload)
    bus = CommandBus()

    # {
    #   責務: [handler: check・実行時・performanceのhandlerを求める]
    #   処理: [1: check・実行時・performanceのhandlerを求める]
    #   引数: [value: 値（AppCommand）]
    #   戻り値: [result: value.action（str）]
    # }
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
    spawn_world = {
        "width": 40, "height": 36, "tiles": [["floor"] * 40 for _ in range(36)],
        "pop_rate": 75, "spawns": [
            {"species_id": "slime", "weight": 0.6, "min_level": 3, "max_level": 8},
            {"species_id": "ghost", "weight": 0.3, "min_level": 4, "max_level": 9},
            {"species_id": "metal_slime", "weight": 0.01, "min_level": 1, "max_level": 2},
        ],
    }
    spawn_blocks = {"floor": {"enemy_spawnable": True, "enemy_walkable": True}}
    spawning = HiddenEnemyController(FieldEngine(spawn_world, spawn_blocks), random.Random(153))
    spawning.set_world(spawn_world, spawn_blocks)
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

    # {
    #   責務: [chase_fork: check・実行時・performanceのchase・forkを求める]
    #   処理: [1: check・実行時・performanceのchase・forkを求める]
    #   引数: []
    #   戻り値: [result: check・実行時・performanceのchase・forkを求めるための結果（object）]
    # }
    def chase_fork() -> object:
        traffic.clear()
        traffic.begin(1000, {1, 2})
        traffic.plan(1, (3, 2), (8, 2), set(), set(), 320)
        return traffic.plan(2, (2, 2), (8, 2), {(3, 2)}, set(), 320)

    return [
        BenchmarkCase("wild-population-24-slots", lambda: spawning.reset((0, 0), {}, 1000), 5_000_000.0),
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


# {
#   責務: [run_benchmarks: 指定した測定項目を反復計測し、項目名・中央値・時間上限の結果列を返します]
#   処理: [1: 対象名で絞った専用fixtureの処理を計測し、結果をBenchmarkResultへまとめます]
#   引数: [
#     iterations: 各サンプルで処理を反復する回数（int）
#     samples: 中央値を求める計測サンプル数（int）
#     warmup: 計測前に処理を実行する回数（int）
#     only: 測定項目名の絞り込み。未指定なら全項目（set[str] | None）
#   ]
#   戻り値: [result: 測定項目名・一回あたりの中央値ns・許容上限nsを持つ結果列（list[BenchmarkResult]）]
# }
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


# {
#   責務: [build_parser: 開発性能検査の反復・サンプル・事前実行・測定項目を指定するCLIパーサを作ります]
#   処理: [1: 性能計測条件と項目選択を受け取るコマンドライン引数を定義します]
#   引数: []
#   戻り値: [result: 開発性能検査の条件を解析するパーサ（argparse.ArgumentParser）]
# }
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


# {
#   責務: [main: check・実行時・performanceのエントリ処理を実行する]
#   処理: [1: check・実行時・performanceのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: check・実行時・performanceのエントリ処理を実行するための結果（int）]
# }
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
