# {
#   責務: [balance_analyzer: balance・analyzerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Iterable

from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.repository import GameRepository, STAT_KEYS


_RESISTANCE_SCORE = {
    "weak": -1.0,
    "normal": 0.0,
    "strong": 1.0,
    "immune": 2.0,
    "absorb": 3.0,
}


# {
#   責務: [BalanceSettings: balance・設定の状態と振る舞いを担当する]
#   フィールド: [
#     levels: レベル一覧（tuple[int, ...]）
#     battles_per_pair: battles・per・pair（int）
#     seed: seed（int）
#     max_rounds: max・rounds（int）
#   ]
# }
@dataclass(frozen=True)
class BalanceSettings:
    levels: tuple[int, ...] = (1, 25, 50, 75, 100)
    battles_per_pair: int = 20
    seed: int = 1
    max_rounds: int = 80

    # {
    #   責務: [__post_init__: balance・設定が利用する初期状態と依存を設定する]
    #   処理: [1: balance・設定が利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __post_init__(self) -> None:
        if not self.levels or any(not 1 <= level <= 100 for level in self.levels):
            raise ValueError("levels must contain values from 1 to 100")
        if self.battles_per_pair < 1:
            raise ValueError("battles_per_pair must be at least 1")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")


# {
#   責務: [BalanceAnalyzer: Runs deterministic, non-learning 1v1 battles and produces advisory data.]
#   フィールド: [
#     repository: データ取得先
#     settings: 設定
#   ]
# }
class BalanceAnalyzer:
    """Runs deterministic, non-learning 1v1 battles and produces advisory data."""

    # {
    #   責務: [__init__: balance・analyzerが利用する初期状態と依存を設定する]
    #   処理: [1: balance・analyzerが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     repository: データ取得先（GameRepository）
    #     settings: 設定（BalanceSettings | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, repository: GameRepository, settings: BalanceSettings | None = None) -> None:
        self.repository = repository
        self.settings = settings or BalanceSettings()

    # {
    #   責務: [analyze: balance・analyzerのanalyzeを求める]
    #   処理: [1: balance・analyzerのanalyzeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_ids: 種族・識別子一覧（Iterable[str] | None）
    #   ]
    #   戻り値: [result: balance・analyzerのanalyzeを求めるための結果（dict[str, Any]）]
    # }
    def analyze(self, species_ids: Iterable[str] | None = None) -> dict[str, Any]:
        selected = sorted(dict.fromkeys(species_ids or self.repository.list_species_ids()))
        known = set(self.repository.list_species_ids())
        unknown = sorted(set(selected) - known)
        if unknown:
            raise ValueError(f"Unknown species: {', '.join(unknown)}")
        if len(selected) < 2:
            raise ValueError("At least two species are required")

        scores = {species_id: {"wins": 0, "losses": 0, "draws": 0, "matches": 0} for species_id in selected}
        matchups: list[dict[str, Any]] = []
        master_rng = random.Random(self.settings.seed)
        for level in self.settings.levels:
            for left_index, left_id in enumerate(selected):
                for right_id in selected[left_index + 1:]:
                    matchups.append(self._run_matchup(left_id, right_id, level, master_rng, scores))

        rankings = self._rankings(selected, scores)
        recommendations = self._recommendations(rankings)
        return {
            "schema_version": 1,
            "kind": "balance_analysis",
            "seed": self.settings.seed,
            "levels": list(self.settings.levels),
            "battles_per_pair": self.settings.battles_per_pair,
            "max_rounds": self.settings.max_rounds,
            "learning_enabled": False,
            "level_100_anchor": True,
            "matchups": matchups,
            "rankings": rankings,
            "recommendations": recommendations,
        }

    # {
    #   責務: [_run_matchup: matchupを実行する]
    #   処理: [1: matchupを実行する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     left_id: left・識別子（str）
    #     right_id: right・識別子（str）
    #     level: レベル（int）
    #     master_rng: master・乱数供給元（random.Random）
    #     scores: scores（dict[str, dict[str, int]]）
    #   ]
    #   戻り値: [result: matchupを実行するための結果（dict[str, Any]）]
    # }
    def _run_matchup(
        self,
        left_id: str,
        right_id: str,
        level: int,
        master_rng: random.Random,
        scores: dict[str, dict[str, int]],
    ) -> dict[str, Any]:
        outcomes = {left_id: 0, right_id: 0, "draw": 0}
        rounds: list[int] = []
        history: list[dict[str, Any]] = []
        for battle_index in range(self.settings.battles_per_pair):
            battle_seed = master_rng.randrange(2**63)
            winner, used_rounds = self._fight(left_id, right_id, level, battle_seed)
            outcomes[winner or "draw"] += 1
            rounds.append(used_rounds)
            history.append({
                "battle_index": battle_index + 1,
                "seed": battle_seed,
                "winner_species_id": winner,
                "rounds": used_rounds,
            })
            self._record_outcome(scores, left_id, right_id, winner)
        return {
            "level": level,
            "left_species_id": left_id,
            "right_species_id": right_id,
            "battles": self.settings.battles_per_pair,
            "left_wins": outcomes[left_id],
            "right_wins": outcomes[right_id],
            "draws": outcomes["draw"],
            "average_rounds": round(sum(rounds) / len(rounds), 2),
            "history": history,
        }

    # {
    #   責務: [_fight: balance・analyzerのfightを求める]
    #   処理: [1: balance・analyzerのfightを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     left_id: left・識別子（str）
    #     right_id: right・識別子（str）
    #     level: レベル（int）
    #     seed: seed（int）
    #   ]
    #   戻り値: [result: balance・analyzerのfightを求めるための結果（tuple[str | None, int]）]
    # }
    def _fight(self, left_id: str, right_id: str, level: int, seed: int) -> tuple[str | None, int]:
        battle = BattleEngine(
            self.repository,
            [self._record(left_id, level, "left")],
            [self._record(right_id, level, "right")],
            rng=random.Random(seed),
            learning_enabled=False,
        )
        for _ in range(self.settings.max_rounds):
            battle.run_round()
            if battle.outcome:
                return (left_id if battle.outcome == "victory" else right_id), battle.round_number
        return None, battle.round_number

    # {
    #   責務: [_record: balance・analyzerの個体レコードを求める]
    #   処理: [1: balance・analyzerの個体レコードを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     level: レベル（int）
    #     side: 陣営（str）
    #   ]
    #   戻り値: [result: balance・analyzerの個体レコードを求めるための結果（MonsterRecord）]
    # }
    def _record(self, species_id: str, level: int, side: str) -> MonsterRecord:
        definition = self.repository.get_species(species_id).definition
        return MonsterRecord(
            {
                "id": f"balance_{side}_{species_id}_{level}",
                "species_id": species_id,
                "name": str(definition.get("display_name", species_id)),
                "level": level,
                "plus_choices": [],
                "equipment_id": None,
            },
            default_ai(str(definition.get("ai_profile", "normal"))),
        )

    # {
    #   責務: [_record_outcome: balance・analyzerの個体レコード・結果を求める]
    #   処理: [1: balance・analyzerの個体レコード・結果を求める]
    #   引数: [
    #     scores: scores（dict[str, dict[str, int]]）
    #     left_id: left・識別子（str）
    #     right_id: right・識別子（str）
    #     winner: winner（str | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @staticmethod
    def _record_outcome(scores: dict[str, dict[str, int]], left_id: str, right_id: str, winner: str | None) -> None:
        scores[left_id]["matches"] += 1
        scores[right_id]["matches"] += 1
        if winner is None:
            scores[left_id]["draws"] += 1
            scores[right_id]["draws"] += 1
        elif winner == left_id:
            scores[left_id]["wins"] += 1
            scores[right_id]["losses"] += 1
        else:
            scores[right_id]["wins"] += 1
            scores[left_id]["losses"] += 1

    # {
    #   責務: [_rankings: balance・analyzerのrankingsを求める]
    #   処理: [1: balance・analyzerのrankingsを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_ids: 種族・識別子一覧（list[str]）
    #     scores: scores（dict[str, dict[str, int]]）
    #   ]
    #   戻り値: [result: rows（list[dict[str, Any]]）]
    # }
    def _rankings(self, species_ids: list[str], scores: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for species_id in species_ids:
            score = scores[species_id]
            matches = score["matches"]
            win_rate = score["wins"] / matches if matches else 0.0
            rows.append({"species_id": species_id, **score, "win_rate": round(win_rate, 4)})
        rows.sort(key=lambda item: (-item["win_rate"], -item["wins"], item["species_id"]))
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
        return rows

    # {
    #   責務: [_recommendations: balance・analyzerのrecommendationsを求める]
    #   処理: [1: balance・analyzerのrecommendationsを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     rankings: rankings（list[dict[str, Any]]）
    #   ]
    #   戻り値: [result: balance・analyzerのrecommendationsを求めるための結果（list[dict[str, Any]]）]
    # }
    def _recommendations(self, rankings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rankings:
            return []
        definitions = {species_id: self.repository.get_species(species_id).definition for species_id in self.repository.list_species_ids()}
        anchor_stats = {species_id: self.repository.stats_at(species_id, 100) for species_id in definitions}
        average_stats = {
            key: sum(stats[key] for stats in anchor_stats.values()) / len(anchor_stats)
            for key in STAT_KEYS
        }
        average_resistance = sum(self._resistance_score(definition) for definition in definitions.values()) / len(definitions)
        proposals: list[dict[str, Any]] = []
        for row in rankings:
            species_id = str(row["species_id"])
            evidence = int(row["matches"])
            deviation = float(row["win_rate"]) - 0.5
            if evidence < 10 or abs(deviation) < 0.15:
                continue
            direction = -1 if deviation > 0 else 1
            stats = anchor_stats[species_id]
            stat_key = max(STAT_KEYS, key=lambda key: direction * (stats[key] - average_stats[key]))
            delta = max(1, round(abs(stats[stat_key] - average_stats[stat_key]) * 0.15))
            resistance_delta = self._resistance_score(definitions[species_id]) - average_resistance
            confidence = self._confidence(evidence, abs(deviation))
            proposals.append({
                "species_id": species_id,
                "anchor_level": 100,
                "reason": f"勝率 {row['win_rate']:.1%} / {evidence}戦",
                "confidence": confidence,
                "stat_candidate": {
                    "stat": stat_key,
                    "direction": "decrease" if direction < 0 else "increase",
                    "level_100_delta": direction * delta,
                    "current_level_100": stats[stat_key],
                },
                "resistance_candidate": self._resistance_candidate(resistance_delta, direction, confidence),
            })
        return proposals

    # {
    #   責務: [_resistance_score: balance・analyzerのresistance・scoreを求める]
    #   処理: [1: balance・analyzerのresistance・scoreを求める]
    #   引数: [definition: 定義（dict[str, Any]）]
    #   戻り値: [result: balance・analyzerのresistance・scoreを求めるための結果（float）]
    # }
    @staticmethod
    def _resistance_score(definition: dict[str, Any]) -> float:
        return sum(_RESISTANCE_SCORE.get(str(value), 0.0) for value in definition.get("resistances", {}).values())

    # {
    #   責務: [_confidence: balance・analyzerのconfidenceを求める]
    #   処理: [1: balance・analyzerのconfidenceを求める]
    #   引数: [
    #     evidence: evidence（int）
    #     deviation: deviation（float）
    #   ]
    #   戻り値: [result: balance・analyzerのconfidenceを求めるための結果（str）]
    # }
    @staticmethod
    def _confidence(evidence: int, deviation: float) -> str:
        strength = min(1.0, evidence / 40) * min(1.0, deviation / 0.3)
        return "high" if strength >= 0.65 else "medium" if strength >= 0.3 else "low"

    # {
    #   責務: [_resistance_candidate: balance・analyzerのresistance・candidateを求める]
    #   処理: [1: balance・analyzerのresistance・candidateを求める]
    #   引数: [
    #     resistance_delta: resistance・経過時間（float）
    #     direction: direction（int）
    #     confidence: confidence（str）
    #   ]
    #   戻り値: [result: balance・analyzerのresistance・candidateを求めるための結果（dict[str, Any] | None）]
    # }
    @staticmethod
    def _resistance_candidate(resistance_delta: float, direction: int, confidence: str) -> dict[str, Any] | None:
        if direction < 0 and resistance_delta >= 1.0:
            return {"direction": "weaken", "reason": "平均より耐性合計が高い", "confidence": confidence}
        if direction > 0 and resistance_delta <= -1.0:
            return {"direction": "strengthen", "reason": "平均より耐性合計が低い", "confidence": confidence}
        return None
