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


@dataclass(frozen=True)
class BalanceSettings:
    levels: tuple[int, ...] = (1, 25, 50, 75, 100)
    battles_per_pair: int = 20
    seed: int = 1
    max_rounds: int = 80

    def __post_init__(self) -> None:
        if not self.levels or any(not 1 <= level <= 100 for level in self.levels):
            raise ValueError("levels must contain values from 1 to 100")
        if self.battles_per_pair < 1:
            raise ValueError("battles_per_pair must be at least 1")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")


class BalanceAnalyzer:
    """Runs deterministic, non-learning 1v1 battles and produces advisory data."""

    def __init__(self, repository: GameRepository, settings: BalanceSettings | None = None) -> None:
        self.repository = repository
        self.settings = settings or BalanceSettings()

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

    @staticmethod
    def _resistance_score(definition: dict[str, Any]) -> float:
        return sum(_RESISTANCE_SCORE.get(str(value), 0.0) for value in definition.get("resistances", {}).values())

    @staticmethod
    def _confidence(evidence: int, deviation: float) -> str:
        strength = min(1.0, evidence / 40) * min(1.0, deviation / 0.3)
        return "high" if strength >= 0.65 else "medium" if strength >= 0.3 else "low"

    @staticmethod
    def _resistance_candidate(resistance_delta: float, direction: int, confidence: str) -> dict[str, Any] | None:
        if direction < 0 and resistance_delta >= 1.0:
            return {"direction": "weaken", "reason": "平均より耐性合計が高い", "confidence": confidence}
        if direction > 0 and resistance_delta <= -1.0:
            return {"direction": "strengthen", "reason": "平均より耐性合計が低い", "confidence": confidence}
        return None
