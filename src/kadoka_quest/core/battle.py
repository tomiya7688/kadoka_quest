from __future__ import annotations

import random
from typing import Any

from kadoka_quest.core.battle_inference import BattleInference
from kadoka_quest.core.battle_learning import BattleLearning
from kadoka_quest.core.battle_context import describe_battle_context
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.repository import GameRepository


RESISTANCE_MULTIPLIER = {
    "absorb": -0.5,
    "immune": 0.0,
    "strong": 0.6,
    "normal": 1.0,
    "weak": 1.4,
}
NORMAL_ATTACK_CRITICAL_CHANCE = 1 / 16


class BattleEngine:
    def __init__(
        self,
        repository: GameRepository,
        allies: list[MonsterRecord],
        enemies: list[MonsterRecord],
        rng: random.Random | None = None,
        learning_enabled: bool = True,
        data_loader: BattleDataLoader | None = None,
        inference: BattleInference | None = None,
        learning: BattleLearning | None = None,
    ) -> None:
        self.repository = repository
        self.rng = rng or random.Random()
        self.learning_enabled = learning_enabled
        self.data_loader = data_loader or BattleDataLoader(repository)
        self.skill_catalog = self.data_loader.skill_catalog
        self.equipment_catalog = self.data_loader.equipment_catalog
        self.inference = inference or BattleInference()
        self.learning = learning or BattleLearning()
        self.allies = [self.data_loader.build_combatant(record) for record in allies[:4]]
        self.enemies = [self.data_loader.build_combatant(record) for record in enemies[:4]]
        self.log: list[str] = ["戦闘開始。個体AIが行動を決めます。"]
        self.round_number = 0
        self.outcome: str | None = None

    @staticmethod
    def _living(team: list[Combatant]) -> list[Combatant]:
        return [member for member in team if member.alive]

    def _check_end(self) -> None:
        if not self._living(self.enemies):
            self.outcome = "victory"
            self.log.append("勝利した！")
        elif not self._living(self.allies):
            self.outcome = "defeat"
            self.log.append("パーティは戦闘不能になった。")

    def run_round(self) -> list[str]:
        if self.outcome:
            return []
        start_index = len(self.log)
        self.round_number += 1
        self.log.append(f"--- {self.round_number}ターン ---")
        actors = [(member, self.enemies, self.allies) for member in self._living(self.allies)]
        actors += [(member, self.allies, self.enemies) for member in self._living(self.enemies)]
        self.rng.shuffle(actors)
        actors.sort(key=lambda item: item[0].speed, reverse=True)

        for actor, foes, friends in actors:
            if not actor.alive or not self._living(foes):
                continue
            self._take_action(actor, self._living(foes), self._living(friends))
            self._check_end()
            if self.outcome:
                break

        for member in self.allies + self.enemies:
            member.guard = 1.0
            member.evade_physical = False
            member.evade_physical_source = None
            member.evade_element = None
            if member.physical_locked:
                member.physical_locked -= 1
        return self.log[start_index:]

    def _take_action(self, actor: Combatant, foes: list[Combatant], friends: list[Combatant]) -> None:
        if actor.mp <= 0:
            self.log.append(f"{actor.name}はMPが尽きて動けない。")
            return
        usable = [skill for skill in actor.skills if int(skill.get("mp_cost", 0)) <= actor.mp]
        if actor.physical_locked:
            usable = [skill for skill in usable if skill.get("kind") != "physical"]
        missing = max((1.0 - friend.hp / friend.stats["hp"] for friend in friends), default=0.0)
        context_tags = describe_battle_context(
            actor.hp / actor.stats["hp"],
            missing,
            actor.mp / actor.stats["mp"],
            len(friends),
            len(foes),
            min((foe.hp / foe.stats["hp"] for foe in foes), default=1.0),
            actor.record.level,
            max((foe.record.level for foe in foes), default=actor.record.level),
        )
        chosen = self.inference.choose(
            actor.record.ai,
            usable,
            actor.hp / actor.stats["hp"],
            missing,
            actor.mp / actor.stats["mp"],
            self.rng,
            context_tags,
        )
        if not chosen:
            self.log.append(f"{actor.name}は様子を見ている。")
            return
        actor.mp = max(0, actor.mp - int(chosen.get("mp_cost", 0)))
        kind = str(chosen.get("kind", "physical"))
        reward = 0.0
        actor.action_history.append(str(chosen["id"]))

        if kind in {"physical", "magic", "drain_mp", "random"}:
            target = min(foes, key=lambda item: item.hp / item.stats["hp"])
            reward = self._attack(actor, target, chosen)
        elif kind == "heal":
            target = min(friends, key=lambda item: item.hp / item.stats["hp"])
            amount = max(1, int(target.stats["hp"] * float(chosen.get("heal_ratio", 0.15))))
            before = target.hp
            target.hp = min(target.stats["hp"], target.hp + amount)
            reward = (target.hp - before) / max(1, target.stats["hp"])
            self.log.append(f"{actor.name}の{chosen['display_name']}。{target.name}が{target.hp - before}回復。")
        elif kind == "defend":
            actor.guard = float(chosen.get("damage_multiplier", 0.5))
            reward = 0.1
            self.log.append(f"{actor.name}は防御した。")
        elif kind == "evade":
            actor.evade_physical = bool(chosen.get("physical", False))
            actor.evade_physical_source = str(chosen.get("id")) if actor.evade_physical else None
            actor.evade_element = chosen.get("element")
            if chosen.get("lock_physical_next_turn"):
                actor.physical_locked = 2
            reward = 0.08
            self.log.append(f"{actor.name}は{chosen['display_name']}。")
        elif kind == "buff":
            if chosen.get("target") == "self":
                target = actor
            elif chosen.get("attack_multiplier"):
                target = min(friends, key=lambda item: item.attack_multiplier)
            else:
                target = min(friends, key=lambda item: item.speed_multiplier)
            if chosen.get("speed_multiplier"):
                target.speed_multiplier = max(target.speed_multiplier, float(chosen["speed_multiplier"]))
                effect = "素早さ"
            else:
                target.attack_multiplier = max(target.attack_multiplier, float(chosen.get("attack_multiplier", 1.0)))
                effect = "次の攻撃"
            reward = 0.1
            self.log.append(f"{actor.name}の{chosen['display_name']}。{target.name}の{effect}が強くなった。")

        if self.learning_enabled:
            self.learning.learn(actor.record.ai, str(chosen["id"]), reward, context_tags)

    def _attack(self, actor: Combatant, target: Combatant, skill: dict[str, Any]) -> float:
        kind = str(skill.get("kind"))
        actual_kind = kind
        power = float(skill.get("power", 1.0))
        if kind == "random":
            roll = self.rng.randint(1, 6)
            power *= (0.45, 0.7, 1.0, 1.25, 1.55, 2.0)[roll - 1]
            actual_kind = str(skill.get("roll_kind", "physical"))
            self.log.append(f"{actor.name}のサイコロは{roll}！")
        element = str(skill.get("element", "physical"))
        if actual_kind == "physical" and target.evade_physical:
            if target.record.species_id in {"maru", "kadoka"}:
                message = f"{target.name}は{skill['display_name']}をすり抜けた。"
            elif target.evade_physical_source == "fluid_defense":
                message = f"{target.name}は流体防御で{skill['display_name']}を受け流した。"
            else:
                message = f"{target.name}は{skill['display_name']}をかわした。"
            self.log.append(message)
            return 0.0
        if target.evade_element == element:
            self.log.append(f"{target.name}は{element}属性を避けた。")
            return 0.0

        if actual_kind in {"magic", "drain_mp"}:
            resistance = RESISTANCE_MULTIPLIER.get(target.resistances.get(element, "normal"), 1.0)
            damage = int(actor.stats["magic"] * power * resistance)
        else:
            attack = int(actor.stats["attack"] * actor.attack_multiplier)
            actor.attack_multiplier = 1.0
            if actor.equipment:
                modifier = actor.equipment.get("skill_modifiers", {}).get(str(skill.get("id")), {})
                power *= float(modifier.get("power_multiplier", 1.0))
            critical_chance = min(
                1.0,
                NORMAL_ATTACK_CRITICAL_CHANCE * float(skill.get("critical_multiplier", 1.0)),
            )
            critical = self.rng.random() < critical_chance
            if critical:
                damage = int(attack * power)
                self.log.append("会心！相手の防御力を無視した！")
            else:
                damage = int(attack * power - target.stats["defense"] * 0.42)
        if actor.equipment:
            damage += int(actor.equipment.get("fixed_bonus_damage", 0))
        guard_multiplier = target.guard if actual_kind == "physical" else 1.0
        damage = max(1, int(damage * guard_multiplier * self.rng.uniform(0.92, 1.08)))
        before = target.hp
        target.hp = max(0, target.hp - damage)
        dealt = before - target.hp
        if skill.get("self_damage_ratio"):
            self_damage = max(1, int(actor.stats["hp"] * float(skill["self_damage_ratio"])))
            actor.hp = max(1, actor.hp - self_damage)
            self.log.append(f"{actor.name}は代償としてHPを{self_damage}消耗。")
        if actual_kind == "drain_mp":
            drained = min(target.mp, max(1, int(actor.stats["magic"] * float(skill.get("mp_power", 0.12)))))
            target.mp -= drained
            actor.mp = min(actor.stats["mp"], actor.mp + drained)
            self.log.append(f"{actor.name}の{skill['display_name']}。{target.name}のMPを{drained}奪った。")
        else:
            self.log.append(f"{actor.name}の{skill['display_name']}。{target.name}に{dealt}ダメージ。")
        if not target.alive:
            message = self.data_loader.species_definition(target.record.species_id).get("defeat_message")
            self.log.append(str(message or f"{target.name}はたおれた！"))
        return dealt / max(1, target.stats["hp"])

    def try_scout(self, multiplier: float = 1.0, fixed_bonus: float = 0.0) -> tuple[bool, MonsterRecord | None, float]:
        if self.outcome:
            return False, None, 0.0
        target = next((item for item in self.enemies if item.alive), None)
        if not target:
            return False, None, 0.0
        definition = self.data_loader.species_definition(target.record.species_id)
        if not bool(definition.get("recruit", {}).get("scoutable", True)):
            self.log.append(f"{target.name}はスカウトできない。")
            return False, None, 0.0
        party_attack = sum(member.stats["attack"] for member in self._living(self.allies))
        target_power = sum(target.stats[key] for key in ("attack", "defense", "hp"))
        base = max(0.02, min(0.75, party_attack / max(1, target_power) * 0.32))
        chance = min(1.0, base * multiplier + fixed_bonus)
        success = self.rng.random() < chance
        self.log.append(f"スカウト率 {chance * 100:.1f}%：{'成功！' if success else '失敗。'}")
        if success:
            self.outcome = "scouted"
        return success, target.record if success else None, chance

    def use_party_item(self) -> None:
        for member in self._living(self.allies):
            amount = max(1, int(member.stats["hp"] * 0.2))
            member.hp = min(member.stats["hp"], member.hp + amount)
        self.log.append("みかんを分けた。パーティのHPが回復した。")

    def try_run(self) -> bool:
        success = self.rng.random() < 0.7
        self.log.append("逃げ切った。" if success else "逃げられなかった。")
        if success:
            self.outcome = "escaped"
        return success

    def mark_battle_complete(self) -> None:
        if not self.learning_enabled:
            return
        for member in self.allies:
            member.record.ai["battles"] = int(member.record.ai.get("battles", 0)) + 1

