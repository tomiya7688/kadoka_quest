# {
#   責務: [battle: 戦闘の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import random
from typing import Any

from kadoka_quest.core.battle_inference import BattleInference
from kadoka_quest.core.battle_learning import BattleLearning
from kadoka_quest.core.battle_context import describe_battle_context
from kadoka_quest.core.battle_decision_explanation import BattleDecisionExplanation
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.core.status_effects import (
    end_turn_status_damage,
    has_status,
    status_apply_chance,
    status_effect_id,
)
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
MULTI_TARGET_MARKERS = {"all", "all_enemies", "all_foes", "enemies", "foes"}


# {
#   責務: [BattleEngine: 個体AIの戦闘行動・資源変化・終了状態とログを管理する]
#   フィールド: [
#     repository: データ取得先
#     rng: 乱数供給元
#     learning_enabled: AI学習と対応する野生行動を有効にする設定
#     encounter_context: 野生遭遇などの行動文脈。模擬戦ではNone
#     data_loader: 戦闘用個体と種族定義を組み立てる読込依存
#     skill_catalog: 共有スキル定義
#     equipment_catalog: 共有装備定義
#     inference: AIのスキル選択依存
#     learning: 行動結果を学習へ反映する依存
#     allies: 味方
#     enemies: 敵
#     log: ログ（list[str]）
#     round_number: 実行済みラウンド数
#     outcome: 勝敗/逃走/スカウト等の終了状態
#   ]
# }
class BattleEngine:
    # {
    #   責務: [__init__: 戦闘・ルール処理が利用する初期状態と依存を設定する]
    #   処理: [1: 戦闘・ルール処理が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     repository: データ取得先（GameRepository）
    #     allies: 味方（list[MonsterRecord]）
    #     enemies: 敵（list[MonsterRecord]）
    #     rng: 乱数供給元（random.Random | None）
    #     learning_enabled: 学習・enabled（bool）
    #     data_loader: データ・loader（BattleDataLoader | None）
    #     inference: inference（BattleInference | None）
    #     learning: 学習（BattleLearning | None）
    #     encounter_context: encounter・判断用コンテキスト（str | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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
        encounter_context: str | None = None,
    ) -> None:
        self.repository = repository
        self.rng = rng or random.Random()
        self.learning_enabled = learning_enabled
        self.encounter_context = encounter_context
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

    # {
    #   責務: [_living: 陣営の一覧からaliveが真の戦闘個体だけを順序を保持して取り出します]
    #   処理: [1: 元の一覧を変更せず、生存条件を満たす参照の新しい一覧を返します]
    #   引数: [team: 生存個体を取り出す陣営の戦闘個体一覧（list[Combatant]）]
    #   戻り値: [result: aliveが真の個体への参照一覧。個体自体はコピーしません（list[Combatant]）]
    # }
    @staticmethod
    def _living(team: list[Combatant]) -> list[Combatant]:
        return [member for member in team if member.alive]

    # {
    #   責務: [_status_is_removable: 状態異常が治療候補にできるか、辞書のremovableから判断します]
    #   処理: [1: 辞書の解除可否を真偽値にし、省略時と文字列状態は解除可能とします]
    #   引数: [effect: 治療候補として確認する状態辞書または文字列ID（dict[str, Any] | str）]
    #   戻り値: [result: 解除可能ならTrue、辞書のremovableが偽ならFalse（bool）]
    # }
    @staticmethod
    def _status_is_removable(effect: dict[str, Any] | str) -> bool:
        if isinstance(effect, dict):
            return bool(effect.get("removable", True))
        return True

    # {
    #   責務: [_status_display_name: 状態異常の表示名を、定義のdisplay_name・id・既定名の順で求めます]
    #   処理: [1: 辞書なら表示名候補を選び、辞書でなければ文字列へ変換します]
    #   引数: [effect: 表示する状態異常の定義または名前（dict[str, Any] | str）]
    #   戻り値: [result: 戦闘ログに表示する状態異常名（str）]
    # }
    @staticmethod
    def _status_display_name(effect: dict[str, Any] | str) -> str:
        if isinstance(effect, dict):
            return str(effect.get("display_name") or effect.get("id") or "状態異常")
        return str(effect)

    # {
    #   責務: [_try_cure_status: 対象の最初の解除可能な状態異常を確率判定で一つだけ除去します]
    #   処理: [
    #     1: 対象の状態異常一覧から最初の解除可能な候補を探します
    #     2: 候補がある場合だけ0〜1に制限した確率で判定し、成立時に候補を除去します
    #   ]
    #   引数: [
    #     self: 乱数源と状態異常の解除判定を所有するBattleEngine
    #     target: 状態異常を治療する戦闘個体（Combatant）
    #     chance: 0〜1へ制限して使う治療成功確率（float）
    #   ]
    #   戻り値: [result: 除去した状態異常の表示名。候補なしまたは判定不成立ならNone（str | None）]
    # }
    def _try_cure_status(self, target: Combatant, chance: float) -> str | None:
        # 解除できない状態を飛ばし、解除可能な最初の一つだけを候補にする。
        candidate = next(
            (
                (index, effect)
                for index, effect in enumerate(target.status_effects)
                if self._status_is_removable(effect)
            ),
            None,
        )
        if candidate is None:
            return None
        # 候補がある場合の判定だけに乱数を使い、確率を0〜1へ制限する。
        if self.rng.random() >= max(0.0, min(1.0, chance)):
            return None
        index, effect = candidate
        del target.status_effects[index]
        return self._status_display_name(effect)

    # {
    #   責務: [_try_apply_status: 未付与の状態異常を、対象の状態耐性で補正した確率に従って付与します]
    #   処理: [
    #     1: ID欠落・重複・基礎確率が0以下の定義を拒否し、対象の耐性から付与確率を求めます
    #     2: 判定成立時だけ効果コピーを状態一覧へ加え、結果をログへ出します
    #   ]
    #   引数: [
    #     self: 乱数源と戦闘ログを所有するBattleEngine
    #     target: 状態異常を付与する戦闘個体（Combatant）
    #     effect: ID・基礎確率chance等を持つ状態異常定義（dict[str, Any]）
    #   ]
    #   戻り値: [result: 状態異常を付与した場合だけTrue（bool）]
    # }
    def _try_apply_status(self, target: Combatant, effect: dict[str, Any]) -> bool:
        status_id = str(effect.get("id", "")).strip()
        if not status_id or has_status(target.status_effects, status_id):
            return False

        base_chance = max(0.0, float(effect.get("chance", 0.0)))
        if base_chance <= 0.0:
            return False
        resistance = str(target.status_resistances.get(status_id, "normal"))
        chance = status_apply_chance(base_chance, resistance)
        display_name = str(effect.get("display_name") or status_id)
        if chance <= 0.0:
            self.log.append(f"{target.name}には{display_name}が効かなかった。")
            return False
        if self.rng.random() >= chance:
            return False

        applied = dict(effect)
        applied.pop("chance", None)
        applied["id"] = status_id
        applied.setdefault("display_name", display_name)
        applied.setdefault("removable", True)
        target.status_effects.append(applied)
        self.log.append(f"{target.name}は{display_name}状態になった。")
        return True

    # {
    #   責務: [_tick_end_turn_status: 生存対象へターン終了時の状態異常ダメージを順に適用します]
    #   処理: [1: 各状態の終了時ダメージをHP0まで適用してログへ出し、対象死亡時に残りの適用を止めます]
    #   引数: [
    #     self: 状態異常の終了時処理と戦闘ログを所有するBattleEngine
    #     target: 終了時ダメージを適用する戦闘個体（Combatant）
    #   ]
    #   戻り値: [result: なし（None）。対象のHPと戦闘ログを更新します]
    # }
    def _tick_end_turn_status(self, target: Combatant) -> None:
        if not target.alive:
            return
        for effect in list(target.status_effects):
            damage = end_turn_status_damage(effect, target.stats["hp"])
            if damage <= 0:
                continue
            before = target.hp
            target.hp = max(0, target.hp - damage)
            dealt = before - target.hp
            if dealt > 0:
                self.log.append(f"{target.name}は{self._status_display_name(effect)}で{dealt}ダメージ。")
            if not target.alive:
                break

    # {
    #   責務: [_buff_duration: スキルのdurationから、最低1ターンの継続時間または時間指定なしを求めます]
    #   処理: [1: 二要素以上の範囲は上下限を補正して抽選し、単値は最低1へ制限し、欠落や変換失敗はNoneを返します]
    #   引数: [
    #     self: 継続時間の抽選に使う乱数源を所有するBattleEngine
    #     skill: 任意のdurationを持つスキル定義（dict[str, Any]）
    #   ]
    #   戻り値: [result: 継続ターン数。指定なしやTypeError/ValueErrorならNone（int | None）]
    # }
    def _buff_duration(self, skill: dict[str, Any]) -> int | None:
        raw = skill.get("duration")
        if raw is None:
            return None
        try:
            if isinstance(raw, (list, tuple)) and len(raw) >= 2:
                low = max(1, int(raw[0]))
                high = max(low, int(raw[1]))
                return self.rng.randint(low, high)
            return max(1, int(raw))
        except (TypeError, ValueError):
            return None

    # {
    #   責務: [_apply_multiplier: multiplierを適用する]
    #   処理: [1: multiplierを適用する]
    #   引数: [
    #     target: 対象（Combatant）
    #     attribute: attribute（str）
    #     multiplier: multiplier（float）
    #     duration: 継続時間（int | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @staticmethod
    def _apply_multiplier(
        target: Combatant,
        attribute: str,
        multiplier: float,
        duration: int | None,
    ) -> None:
        current = float(getattr(target, attribute))
        if duration is None:
            setattr(target, attribute, max(current, multiplier))
            if attribute in target.timed_buff_baselines:
                target.timed_buff_baselines[attribute] = max(
                    target.timed_buff_baselines[attribute],
                    multiplier,
                )
            return

        if attribute not in target.timed_buff_turns:
            target.timed_buff_baselines[attribute] = current
        target.timed_buff_turns[attribute] = max(
            target.timed_buff_turns.get(attribute, 0),
            duration,
        )
        setattr(target, attribute, max(current, multiplier))

    # {
    #   責務: [_tick_timed_buffs: timed・buffsを時間経過を反映する]
    #   処理: [1: timed・buffsを時間経過を反映する]
    #   引数: [target: 対象（Combatant）]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @staticmethod
    def _tick_timed_buffs(target: Combatant) -> None:
        for attribute in list(target.timed_buff_turns):
            remaining = target.timed_buff_turns[attribute] - 1
            if remaining > 0:
                target.timed_buff_turns[attribute] = remaining
                continue
            baseline = target.timed_buff_baselines.pop(attribute, 1.0)
            setattr(target, attribute, baseline)
            del target.timed_buff_turns[attribute]

    # {
    #   責務: [_is_single_target_attack: single・対象・攻撃を該当するか判定する]
    #   処理: [1: single・対象・攻撃を該当するか判定する]
    #   引数: [skill: スキル（dict[str, Any]）]
    #   戻り値: [result: single・対象・攻撃を該当するか判定するための結果（bool）]
    # }
    @staticmethod
    def _is_single_target_attack(skill: dict[str, Any]) -> bool:
        if bool(skill.get("aoe")) or bool(skill.get("target_all")) or bool(skill.get("all_targets")):
            return False
        return str(skill.get("target", "single")) not in MULTI_TARGET_MARKERS

    # {
    #   責務: [_resolve_attack_target: 攻撃・対象を解決する]
    #   処理: [1: 攻撃・対象を解決する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     intended: intended（Combatant）
    #     defenders: defenders（list[Combatant]）
    #     skill: スキル（dict[str, Any]）
    #   ]
    #   戻り値: [result: 攻撃・対象を解決するための結果（Combatant）]
    # }
    def _resolve_attack_target(
        self,
        intended: Combatant,
        defenders: list[Combatant],
        skill: dict[str, Any],
    ) -> Combatant:
        if not self._is_single_target_attack(skill):
            return intended
        protector = next(
            (
                member
                for member in defenders
                if member.alive and member.protect_ally and member is not intended
            ),
            None,
        )
        if protector is None:
            return intended
        self.log.append(f"{protector.name}が{intended.name}をかばった。")
        return protector

    # {
    #   責務: [_counter_skill: 戦闘・ルール処理のcounter・スキルを求める]
    #   処理: [1: 戦闘・ルール処理のcounter・スキルを求める]
    #   引数: [actor: 行動個体（Combatant）]
    #   戻り値: [result: 戦闘・ルール処理のcounter・スキルを求めるための結果（dict[str, Any] | None）]
    # }
    @staticmethod
    def _counter_skill(actor: Combatant) -> dict[str, Any] | None:
        return next((skill for skill in actor.skills if str(skill.get("id")) == "attack"), None)

    # {
    #   責務: [_resolve_counter: counterを解決する]
    #   処理: [1: counterを解決する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     defender: defender（Combatant）
    #     attacker: attacker（Combatant）
    #     incoming_skill: incoming・スキル（dict[str, Any]）
    #     dealt: dealt（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _resolve_counter(
        self,
        defender: Combatant,
        attacker: Combatant,
        incoming_skill: dict[str, Any],
        dealt: int,
    ) -> None:
        if dealt <= 0 or not defender.alive or not attacker.alive:
            return
        if not defender.counter_ready or not self._is_single_target_attack(incoming_skill):
            return
        counter_skill = self._counter_skill(defender)
        if counter_skill is None:
            return
        self.log.append(f"{defender.name}が反撃！")
        self._attack(defender, attacker, counter_skill, allow_counter=False)

    # {
    #   責務: [_check_end: endを検査する]
    #   処理: [1: endを検査する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _check_end(self) -> None:
        if not self._living(self.enemies):
            if self.enemies and all(member.fled for member in self.enemies):
                self.outcome = "enemies_fled"
                self.log.append("相手は全員逃げ去った。")
            else:
                self.outcome = "victory"
                self.log.append("勝利した！")
        elif not self._living(self.allies):
            self.outcome = "defeat"
            self.log.append("パーティは戦闘不能になった。")

    # {
    #   責務: [run_round: 生存個体の速度順に戦闘行動を実行しラウンド末の一時効果を解除する]
    #   処理: [
    #     1: 生存参加者をshuffleして速度順に並べる
    #     2: 行動直前に最新生存と敵の有無を確認し行動・終了判定を進める
    #     3: 全参加者の防御・回避・反撃等のラウンド限定状態を解除する
    #   ]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 今回追加された戦闘ログ。戦闘状態も更新する]
    # }
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
            if friends is not self.enemies or not self._try_enemy_flee(actor):
                self._take_action(actor, self._living(foes), self._living(friends))
            self._check_end()
            if self.outcome:
                break

        if not self.outcome:
            for member in self.allies + self.enemies:
                self._tick_end_turn_status(member)
            self._check_end()

        for member in self.allies + self.enemies:
            member.guard = 1.0
            member.evade_physical = False
            member.evade_physical_source = None
            member.evade_element = None
            member.counter_ready = False
            member.protect_ally = False
            if member.physical_locked:
                member.physical_locked -= 1
            self._tick_timed_buffs(member)
        return self.log[start_index:]

    # {
    #   責務: [_try_enemy_flee: 敵・fleeを実行可能な場合に処理する]
    #   処理: [1: 敵・fleeを実行可能な場合に処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actor: 行動個体（Combatant）
    #   ]
    #   戻り値: [result: 敵・fleeを実行可能な場合に処理するための結果（bool）]
    # }
    def _try_enemy_flee(self, actor: Combatant) -> bool:
        # encounter_contextを持つ学習有効の野生戦闘だけで敵の逃走を判定し、シミュレーションでは判定しません。
        if not actor.alive or not self.learning_enabled or self.encounter_context is None:
            return False
        try:
            chance = float(actor.flee_rates.get(self.encounter_context, 0.0))
        except (TypeError, ValueError):
            return False
        if not 0.0 < chance <= 1.0 or self.rng.random() >= chance:
            return False
        actor.fled = True
        self.log.append(f"{actor.name}は逃げ出した！")
        return True

    # {
    #   責務: [_take_action: 現在資源で使用可能なスキルをAIへ選択依頼し、MP消費後に担当処理を呼び、学習有効時だけ結果を記録します]
    #   処理: [
    #     1: MPと物理封印から使用可能スキルを絞り、戦闘状況のタグでAIへ選択を依頼します
    #     2: 選択したスキルのMPを消費し、攻撃・回復・防御・回避・強化の担当処理を呼びます
    #     3: 学習有効時だけ個体AIへ選択結果の評価を渡します
    #   ]
    #   引数: [
    #     self: 戦闘資源・AI選択/学習・乱数源・ログを所有するBattleEngine
    #     actor: 行動個体（Combatant）
    #     foes: 攻撃対象と戦闘状況判定に使う敵候補列（list[Combatant]）
    #     friends: 回復・強化の対象と戦闘状況判定に使う友軍候補列（list[Combatant]）
    #   ]
    #   戻り値: [result: なし（None）。戦闘中の資源・行動履歴・ログと、学習有効時の個体AIを更新します]
    # }
    def _take_action(self, actor: Combatant, foes: list[Combatant], friends: list[Combatant]) -> None:
        # 選択前に使用条件を絞り、AIへ最新のHP/MPと参加者状況を渡す。
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
        self.log.append(
            f"{actor.name}: "
            + BattleDecisionExplanation.describe(actor.record.ai, chosen, context_tags)
        )
        actor.mp = max(0, actor.mp - int(chosen.get("mp_cost", 0)))
        kind = str(chosen.get("kind", "physical"))
        reward = 0.0
        actor.action_history.append(str(chosen["id"]))

        if kind in {"physical", "magic", "drain_mp", "random"}:
            intended = min(foes, key=lambda item: item.hp / item.stats["hp"])
            target = self._resolve_attack_target(intended, foes, chosen)
            reward = self._attack(actor, target, chosen)
        elif kind == "heal":
            # 回復量は対象の最大HPから求める。魔力や装備倍率は使わず、満HPでは実回復0になる。
            target = min(friends, key=lambda item: item.hp / item.stats["hp"])
            amount = max(1, int(target.stats["hp"] * float(chosen.get("heal_ratio", 0.15))))
            before = target.hp
            target.hp = min(target.stats["hp"], target.hp + amount)
            reward = (target.hp - before) / max(1, target.stats["hp"])
            self.log.append(f"{actor.name}の{chosen['display_name']}。{target.name}が{target.hp - before}回復。")
            # 状態異常の治療判定はHP回復と別効果として、対象の解除可能な状態にだけ行う。
            cure_chance = float(chosen.get("status_cure_chance", 0.0))
            cured_status = self._try_cure_status(target, cure_chance)
            if cured_status is not None:
                self.log.append(f"{target.name}の{cured_status}が治った。")
        elif kind == "defend":
            actor.guard = float(chosen.get("damage_multiplier", 0.5))
            actor.counter_ready = bool(chosen.get("counter", False))
            actor.protect_ally = bool(chosen.get("protect_ally", False))
            reward = 0.1
            if actor.counter_ready:
                self.log.append(f"{actor.name}は反撃のかまえをとった。")
            elif actor.protect_ally:
                self.log.append(f"{actor.name}は味方をかばう構えに入った。")
            else:
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
            duration = self._buff_duration(chosen)
            if chosen.get("speed_multiplier"):
                self._apply_multiplier(
                    target,
                    "speed_multiplier",
                    float(chosen["speed_multiplier"]),
                    duration,
                )
                effect = "素早さ"
            else:
                self._apply_multiplier(
                    target,
                    "attack_multiplier",
                    float(chosen.get("attack_multiplier", 1.0)),
                    duration,
                )
                effect = "次の攻撃"
            reward = 0.1
            self.log.append(f"{actor.name}の{chosen['display_name']}。{target.name}の{effect}が強くなった。")

        if self.learning_enabled:
            self.learning.learn(actor.record.ai, str(chosen["id"]), reward, context_tags)

    # {
    #   責務: [
    #     _attack: 攻撃種別に応じて回避・会心・耐性・HP/MP・追加効果を解決する
    #   ]
    #   処理: [
    #     1: 乱数攻撃と回避を解決し、魔法耐性または物理の防御/会心で基礎ダメージを求める
    #     2: 装備追加、物理限定guard、無効/吸収/最低ダメージを適用してHPを更新する
    #     3: 代償HP、MP吸収、状態異常、許可された反撃と撃破ログを反映する
    #   ]
    #   引数: [
    #     self: 戦闘ログと乱数源を所有するBattleEngine
    #     actor: 攻撃する戦闘個体（Combatant）
    #     target: ダメージまたは吸収回復を受ける戦闘個体（Combatant）
    #     skill: 攻撃種別・威力・属性・追加効果を持つ選択スキル定義（dict[str, Any]）
    #     allow_counter: Trueなら対象の反撃待機を判定し反撃を実行し、Falseなら反撃しません（bool）
    #   ]
    #   戻り値: [
    #     result: 実HP減少を対象最大HPで割った比率。吸収回復時は負の値
    #   ]
    # }
    def _attack(
        self,
        actor: Combatant,
        target: Combatant,
        skill: dict[str, Any],
        *,
        allow_counter: bool = True,
    ) -> float:
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

        resistance_kind = str(target.resistances.get(element, "normal"))
        resistance_blocks_effect = False
        resistance_absorbs = False
        if actual_kind in {"magic", "drain_mp"}:
            resistance = RESISTANCE_MULTIPLIER.get(resistance_kind, 1.0)
            damage = int(actor.stats["magic"] * power * resistance)
            resistance_blocks_effect = resistance_kind == "immune"
            resistance_absorbs = resistance_kind == "absorb"
        else:
            attack = int(actor.stats["attack"] * actor.attack_multiplier)
            actor.attack_multiplier = 1.0
            actor.timed_buff_turns.pop("attack_multiplier", None)
            actor.timed_buff_baselines.pop("attack_multiplier", None)
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
                damage = int(attack * power - target.defense * 0.42)

        if actor.equipment and not (resistance_blocks_effect or resistance_absorbs):
            damage += int(actor.equipment.get("fixed_bonus_damage", 0))

        guard_multiplier = target.guard if actual_kind == "physical" else 1.0
        before = target.hp
        if resistance_blocks_effect:
            dealt = 0
            self.log.append(f"{target.name}には{skill['display_name']}が効かなかった。")
        elif resistance_absorbs:
            recovery = max(1, int(abs(damage) * self.rng.uniform(0.92, 1.08)))
            target.hp = min(target.stats["hp"], target.hp + recovery)
            healed = target.hp - before
            dealt = -healed
            self.log.append(f"{target.name}は{skill['display_name']}を吸収し、HPが{healed}回復。")
        else:
            damage = max(1, int(damage * guard_multiplier * self.rng.uniform(0.92, 1.08)))
            target.hp = max(0, target.hp - damage)
            dealt = before - target.hp

        if skill.get("self_damage_ratio"):
            # 対象が無効・吸収でも代償を支払い、術者のHPは最低1残す。ログ量と実減少は異なり得る。
            self_damage = max(1, int(actor.stats["hp"] * float(skill["self_damage_ratio"])))
            actor.hp = max(1, actor.hp - self_damage)
            self.log.append(f"{actor.name}は代償としてHPを{self_damage}消耗。")

        if actual_kind == "drain_mp":
            # HP効果で敵を倒してもMPを奪うが、属性の無効・吸収では追加効果を行わない。
            if not (resistance_blocks_effect or resistance_absorbs):
                # 奪った量と術者の回復量は別。最大MPで余っても敵の喪失量を減らさない。
                drained = min(target.mp, max(1, int(actor.stats["magic"] * float(skill.get("mp_power", 0.12)))))
                target.mp -= drained
                actor.mp = min(actor.stats["mp"], actor.mp + drained)
                self.log.append(f"{actor.name}の{skill['display_name']}。{target.name}のMPを{drained}奪った。")
        elif not (resistance_blocks_effect or resistance_absorbs):
            self.log.append(f"{actor.name}の{skill['display_name']}。{target.name}に{dealt}ダメージ。")

        status_effect = skill.get("status_effect")
        if dealt > 0 and target.alive and isinstance(status_effect, dict):
            self._try_apply_status(target, status_effect)

        if allow_counter:
            self._resolve_counter(target, actor, skill, dealt)

        if not target.alive:
            message = self.data_loader.species_definition(target.record.species_id).get("defeat_message")
            self.log.append(str(message or f"{target.name}はたおれた！"))
        return dealt / max(1, target.stats["hp"])

    # {
    #   責務: [try_scout: 最初の生存敵にスカウトを試み、成功時に戦闘結果をscoutedへ更新します]
    #   処理: [
    #     1: 戦闘終了・生存敵なし・種族のスカウト禁止なら拒否します
    #     2: 生存味方の攻撃力合計と敵の能力から成功率を計算し、倍率と固定加算を反映します
    #     3: 乱数で成功を判定し、ログと成功時の戦闘結果を更新します
    #   ]
    #   引数: [
    #     self: 味方・敵・戦闘結果・ログ・乱数源を所有するBattleEngine
    #     multiplier: 基礎スカウト率へ掛ける倍率（float）
    #     fixed_bonus: 倍率適用後に成功率へ足す固定値（float）
    #   ]
    #   戻り値: [result: 成功フラグ・成功時の敵レコード（失敗時None）・成功率。事前拒否ならFalse/None/0（tuple）]
    # }
    def try_scout(self, multiplier: float = 1.0, fixed_bonus: float = 0.0) -> tuple[bool, MonsterRecord | None, float]:
        # 戦闘終了後や対象不在・禁止種族では乱数を引かず、成功率0で拒否する。
        if self.outcome:
            return False, None, 0.0
        target = next((item for item in self.enemies if item.alive), None)
        if not target:
            return False, None, 0.0
        definition = self.data_loader.species_definition(target.record.species_id)
        if not bool(definition.get("recruit", {}).get("scoutable", True)):
            self.log.append(f"{target.name}はスカウトできない。")
            return False, None, 0.0
        # 生存味方の攻撃力と対象の攻撃・防御・最大HPから、上限付きの成功率を計算する。
        party_attack = sum(member.stats["attack"] for member in self._living(self.allies))
        target_power = sum(target.stats[key] for key in ("attack", "defense", "hp"))
        base = max(0.02, min(0.75, party_attack / max(1, target_power) * 0.32))
        chance = min(1.0, base * multiplier + fixed_bonus)
        # 成功時だけ戦闘をscoutedで終了し、取得候補として敵の元レコードを返す。
        success = self.rng.random() < chance
        self.log.append(f"スカウト率 {chance * 100:.1f}%：{'成功！' if success else '失敗。'}")
        if success:
            self.outcome = "scouted"
        return success, target.record if success else None, chance

    # {
    #   責務: [use_party_item: みかんで生存味方のHPを最大HPの20%分、最大HPまで回復します]
    #   処理: [
    #     1: 生存味方の最大HPの20%を整数化し、最低回復量1を求めて最大HPまで回復します
    #     2: パーティ回復のログを追加します
    #   ]
    #   引数: [self: 味方の戦闘中HPとログを所有するBattleEngine]
    #   戻り値: [result: なし（None）。所持アイテム数の減算はこのメソッドでは行いません]
    # }
    def use_party_item(self) -> None:
        # 死亡した味方は対象外とし、回復によって最大HPを超えないようにする。
        for member in self._living(self.allies):
            amount = max(1, int(member.stats["hp"] * 0.2))
            member.hp = min(member.stats["hp"], member.hp + amount)
        self.log.append("みかんを分けた。パーティのHPが回復した。")

    # {
    #   責務: [try_run: 70%の確率で逃走を試み、成功時に戦闘結果をescapedへ更新します]
    #   処理: [
    #     1: 乱数で逃走を判定します
    #     2: ログと成功時の戦闘結果を更新します
    #   ]
    #   引数: [self: 乱数源・戦闘結果・ログを所有するBattleEngine]
    #   戻り値: [result: 逃走に成功した場合True、失敗した場合False（bool）]
    # }
    def try_run(self) -> bool:
        # 逃走に失敗した場合は既存の戦闘結果を変更せず、成否だけをログへ記録する。
        success = self.rng.random() < 0.7
        self.log.append("逃げ切った。" if success else "逃げられなかった。")
        if success:
            self.outcome = "escaped"
        return success

    # {
    #   責務: [mark_battle_complete: 戦闘・completeを状態を記録する]
    #   処理: [1: 戦闘・completeを状態を記録する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def mark_battle_complete(self) -> None:
        if not self.learning_enabled:
            return
        for member in self.allies:
            member.record.ai["battles"] = int(member.record.ai.get("battles", 0)) + 1
