from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any

from kadoka_quest.core.ai import choose_skill, learn_from_action
from kadoka_quest.core.monster import MonsterRecord, available_skill_ids, calculate_stats
from kadoka_quest.data.repository import GameRepository


RESISTANCE_MULTIPLIER = {
    "absorb": -0.5,
    "immune": 0.0,
    "strong": 0.6,
    "normal": 1.0,
    "weak": 1.4,
}


@dataclass
class Combatant:
    record: MonsterRecord
    stats: dict[str, int]
    skills: list[dict[str, Any]]
    resistances: dict[str, str]
    equipment: dict[str, Any] | None = None
    hp: int = 0
    mp: int = 0
    guard: float = 1.0
    evade_physical: bool = False
    evade_element: str | None = None
    speed_multiplier: float = 1.0
    attack_multiplier: float = 1.0
    physical_locked: int = 0
    action_history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.hp = self.hp or self.stats["hp"]
        self.mp = self.mp or self.stats["mp"]

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def name(self) -> str:
        return self.record.name

    @property
    def speed(self) -> int:
        return max(1, int(self.stats["speed"] * self.speed_multiplier))


class BattleEngine:
    def __init__(
        self,
        repository: GameRepository,
        allies: list[MonsterRecord],
        enemies: list[MonsterRecord],
        rng: random.Random | None = None,
        learning_enabled: bool = True,
    ) -> None:
        self.repository = repository
        self.rng = rng or random.Random()
        self.learning_enabled = learning_enabled
        self.skill_catalog = repository.get_skills()
        self.equipment_catalog = repository.get_equipment()
        self.allies = [self._build(record) for record in allies[:4]]
        self.enemies = [self._build(record) for record in enemies[:4]]
        self.log: list[str] = ["戦闘開始。個体AIが行動を決めます。"]
        self.round_number = 0
        self.outcome: str | None = None

    def _build(self, record: MonsterRecord) -> Combatant:
        bundle = self.repository.get_species(record.species_id)
        skill_ids = available_skill_ids(self.repository, record)
        skills = [self.skill_catalog[item] for item in skill_ids if item in self.skill_catalog]
        equipment = self.equipment_catalog.get(record.equipment_id or "")
        resistances = dict(bundle.definition.get("resistances", {}))
        if equipment:
            scale = ["weak", "normal", "strong", "immune", "absorb"]
            for element, steps in equipment.get("resistance_steps", {}).items():
                current = resistances.get(element, "normal")
                index = scale.index(current) if current in scale else 1
                resistances[element] = scale[max(0, min(len(scale) - 1, index + int(steps)))]
        return Combatant(record, calculate_stats(self.repository, record), skills, resistances, equipment)

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
        chosen = choose_skill(
            actor.record.ai,
            usable,
            actor.hp / actor.stats["hp"],
            missing,
            actor.mp / actor.stats["mp"],
            self.rng,
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
            learn_from_action(actor.record.ai, str(chosen["id"]), reward)

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
            self.log.append(f"{target.name}は{skill['display_name']}をすり抜けた。")
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
            damage = int(attack * power - target.stats["defense"] * 0.42)
            if self.rng.random() < 0.05 * float(skill.get("critical_multiplier", 1.0)):
                damage = int(damage * 1.5)
                self.log.append("会心！")
        if actor.equipment:
            damage += int(actor.equipment.get("fixed_bonus_damage", 0))
        damage = max(1, int(damage * target.guard * self.rng.uniform(0.92, 1.08)))
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
            message = self.repository.get_species(target.record.species_id).definition.get("defeat_message")
            self.log.append(str(message or f"{target.name}はたおれた！"))
        return dealt / max(1, target.stats["hp"])

    def try_scout(self, multiplier: float = 1.0, fixed_bonus: float = 0.0) -> tuple[bool, MonsterRecord | None, float]:
        if self.outcome:
            return False, None, 0.0
        target = next((item for item in self.enemies if item.alive), None)
        if not target:
            return False, None, 0.0
        definition = self.repository.get_species(target.record.species_id).definition
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

