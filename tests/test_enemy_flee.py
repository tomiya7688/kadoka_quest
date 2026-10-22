# {
#   責務: [test_enemy_flee: 敵の逃走確率、逃走後の行動対象、経験値、遭遇条件、画面表示を検証する]
#   フィールド: []
# }
from __future__ import annotations

import copy
from pathlib import Path
import random
from types import SimpleNamespace
from unittest import mock

import pytest

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_progression_service import BattleProgressionService
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [record: 逃走テストで使用するレベル10の個体と初期AIを作る]
#   処理: [1: 指定した種族と名前から、経験値0・装備なしの個体レコードを組み立てる]
#   引数: [
#     species: テスト個体に設定する種族識別子
#     name: テスト個体の名前と個体識別子に共用する文字列
#   ]
#   戻り値: [result: 保存せずに生成したMonsterRecord]
# }
def record(species, name):
    # 個体の保存先を作らず、戦闘テスト内だけで使用する初期値を用意する。
    return MonsterRecord({
        "id": name, "name": name, "species_id": species, "level": 10,
        "experience": 0, "plus_choices": [], "equipment_id": None,
    }, default_ai())


# {
#   責務: [battle: 指定した遭遇条件と学習設定で、敵が先に行動する一対一のテスト戦闘を作る]
#   処理: [
#     1: 正規データと固定シード142から味方一体・敵一体のBattleEngineを作る
#     2: 味方の素早さを1、敵の素早さを1000にして敵の行動順を先にする
#   ]
#   引数: [
#     context: BattleEngineへ渡す遭遇条件。省略時はnormal
#     learning: 戦闘中のAI学習を有効にするか
#     species: 敵に設定する種族識別子。省略時はmetal_slime
#   ]
#   戻り値: [result: 指定条件で構築した未進行のBattleEngine]
# }
def battle(context="normal", *, learning=True, species="metal_slime"):
    # 正規定義を読み取り、乱数シードを固定してテストの再現性を保つ。
    repository = GameRepository(Path(__file__).resolve().parents[1] / "data")
    engine = BattleEngine(
        repository, [record("metal_slime", "味方")], [record(species, "敵")],
        random.Random(142), learning_enabled=learning, encounter_context=context,
    )
    # 通常の準備では、味方の行動より先に敵の逃走判定へ到達させる。
    engine.allies[0].stats["speed"] = 1
    engine.enemies[0].stats["speed"] = 1000
    return engine


# {
#   責務: [test_escape_boundary_runs_once_in_enemy_action_slot: 敵の行動枠で逃走を一度判定し、乱数が確率未満の場合だけ逃走することを検証する]
#   処理: [
#     1: 逃走確率の直前または確率と同じ乱数値で一ラウンド進める
#     2: 判定回数、逃走状態、HPと保存個体の不変を確認する
#     3: 成功時の戦闘終了・勧誘不可・行動停止と、失敗時の通常行動を確認する
#   ]
#   引数: [
#     context: 逃走確率を選ぶ遭遇条件。normalまたはmetal_area
#     chance: 遭遇条件に対応する逃走確率。normalは0.15、metal_areaは0.60
#     below: Trueなら確率より0.000001小さい乱数、Falseなら確率と同じ乱数を使用する
#   ]
#   戻り値: [result: なし（None）。期待と異なる場合はassertで失敗する]
# }
@pytest.mark.parametrize("context,chance", [("normal", 0.15), ("metal_area", 0.60)])
@pytest.mark.parametrize("below", [True, False])
def test_escape_boundary_runs_once_in_enemy_action_slot(context, chance, below):
    # 通常行動を差し替え、逃走判定そのものが個体とHPへ与える影響を切り分ける。
    engine = battle(context)
    enemy = engine.enemies[0]
    before = copy.deepcopy(enemy.record)
    hp = enemy.hp
    with mock.patch.object(engine.rng, "random", return_value=chance - 0.000001 if below else chance) as roll, \
         mock.patch.object(engine, "_take_action") as action:
        lines = engine.run_round()
    # 確率境界の判定は一度だけ行い、逃走をダメージや個体の保存値変更として扱わない。
    roll.assert_called_once_with()
    assert enemy.fled is below
    assert enemy.hp == hp  # Escape is not death or damage.
    assert enemy.record == before
    # 全敵が逃走した後は、行動や勧誘を再開しないことを確認する。
    if below:
        assert engine.outcome == "enemies_fled"
        assert "敵は逃げ出した！" in lines
        action.assert_not_called()
        assert engine.try_scout() == (False, None, 0.0)
        assert engine.run_round() == []
    else:
        assert engine.outcome is None
        assert action.call_count == 2


# {
#   責務: [test_no_escape_or_extra_rng_for_nonparticipating_battles: 逃走の対象外となる遭遇条件・学習設定・種族では逃走用乱数を使わないことを検証する]
#   処理: [1: 対象外条件で一ラウンド進め、両者が通常行動し、逃走判定の乱数呼び出しがないことを確認する]
#   引数: [
#     context: 逃走対象外の組合せに使用する遭遇条件。Noneや未知値を含む
#     learning: テスト戦闘のAI学習を有効にするか
#     species: テスト戦闘の敵種族。metal_slimeまたはslime
#   ]
#   戻り値: [result: なし（None）。対象外条件で逃走判定が実行されると失敗する]
# }
@pytest.mark.parametrize("context,learning,species", [
    (None, True, "metal_slime"), ("normal", False, "metal_slime"),
    ("metal_area", False, "metal_slime"), ("normal", True, "slime"),
    ("unknown", True, "metal_slime"),
])
def test_no_escape_or_extra_rng_for_nonparticipating_battles(context, learning, species):
    # 通常行動を差し替え、対象外戦闘での追加の乱数消費を検出する。
    engine = battle(context, learning=learning, species=species)
    with mock.patch.object(engine.rng, "random", return_value=0.0) as roll, \
         mock.patch.object(engine, "_take_action") as action:
        engine.run_round()
    # 味方と敵の通常行動を維持し、どちらも逃走状態にならないことを確認する。
    roll.assert_not_called()
    assert action.call_count == 2
    assert not engine.enemies[0].fled and not engine.allies[0].fled


# {
#   責務: [test_escape_retries_each_round_but_never_after_departure: 逃走失敗の次ラウンドでは再判定し、逃走後は再判定しないことを検証する]
#   処理: [1: 失敗・成功の順の乱数で三回進行を要求し、判定二回・二ラウンドで戦闘が終わることを確認する]
#   引数: []
#   戻り値: [result: なし（None）。再判定の回数または戦闘結果が異なると失敗する]
# }
def test_escape_retries_each_round_but_never_after_departure():
    # 三回目の進行要求に乱数を用意せず、終了後の余計な判定も検出する。
    engine = battle()
    with mock.patch.object(engine.rng, "random", side_effect=[0.9, 0.1]) as roll, \
         mock.patch.object(engine, "_take_action"):
        engine.run_round()
        engine.run_round()
        engine.run_round()
    # 逃走に成功した二ラウンド目の結果が、三回目の要求でも維持される。
    assert roll.call_count == 2
    assert engine.round_number == 2
    assert engine.outcome == "enemies_fled"


# {
#   責務: [test_fled_enemy_is_not_targeted_or_ticked_and_mixed_defeat_is_victory: 逃走個体を行動・対象・継続ダメージから除き、残る敵を倒すと勝利することを検証する]
#   処理: [
#     1: 出血中の逃走対象と残る敵を用意して二ラウンド進める
#     2: 逃走個体のHPが変わらず、行動者・敵対象・味方対象から外れることを確認する
#     3: 残る敵を戦闘不能にし、全敵逃走ではなく勝利で終了することを確認する
#   ]
#   引数: []
#   戻り値: [result: なし（None）。逃走個体の除外または混在時の終了結果が異なると失敗する]
# }
def test_fled_enemy_is_not_targeted_or_ticked_and_mixed_defeat_is_victory():
    # 逃走後も戦闘が続く状況を作り、出血によるHP変化も観測できるようにする。
    engine = battle()
    other = engine.data_loader.build_combatant(record("slime", "残る敵"))
    engine.enemies.append(other)
    escaped = engine.enemies[0]
    escaped.status_effects = [{"id": "bleeding", "damage_ratio": 0.5}]
    hp = escaped.hp
    with mock.patch.object(engine.rng, "random", return_value=0.0), \
         mock.patch.object(engine, "_take_action") as action:
        engine.run_round()
        engine.run_round()
    # 逃走個体は戦闘に残る側の行動や対象候補へ戻さない。
    assert escaped.fled and escaped.hp == hp
    assert engine.outcome is None
    for call in action.call_args_list:
        assert call.args[0] is not escaped
        assert escaped not in call.args[1] and escaped not in call.args[2]
    # 逃走と撃破が混在する終了条件を確認する。
    other.hp = 0
    engine._check_end()
    assert engine.outcome == "victory"


# {
#   責務: [test_enemy_killed_before_its_action_does_not_roll_to_flee: 行動前に倒された敵には逃走判定を行わないことを検証する]
#   処理: [1: 味方を先に行動させて敵を倒し、乱数を使わず勝利することを確認する]
#   引数: []
#   戻り値: [result: なし（None）。撃破済みの敵に逃走判定が実行されると失敗する]
# }
def test_enemy_killed_before_its_action_does_not_roll_to_flee():
    # 共通準備の行動順を逆転させ、敵の行動枠より先に敵のHPを0へ変更する。
    engine = battle()
    engine.allies[0].stats["speed"] = 2000
    # {
    #   責務: [kill: 通常行動の代わりに相手先頭個体のHPを0へ変更する]
    #   処理: [1: 行動者の相手一覧の先頭個体を戦闘不能にする]
    #   引数: [
    #     actor: 通常行動から渡される行動者。この差し替えでは参照しない
    #     foes: 行動者の相手側の個体一覧。先頭個体のHPだけを変更する
    #     friends: 行動者の味方側の個体一覧。この差し替えでは参照しない
    #   ]
    #   戻り値: [result: なし（None）。相手先頭個体のHPを直接変更する]
    # }
    def kill(actor, foes, friends):
        # ダメージ計算の成否に依存せず、逃走判定前の撃破を再現する。
        foes[0].hp = 0
    # 行動順による撃破が逃走判定を省略することだけを観測する。
    with mock.patch.object(engine.rng, "random") as roll, \
         mock.patch.object(engine, "_take_action", side_effect=kill):
        engine.run_round()
    roll.assert_not_called()
    assert engine.outcome == "victory"


# {
#   責務: [test_rewards_exclude_fled_enemies_in_both_entrypoints: 既存の二つの報酬確定経路で逃走個体を経験値の対象外にすることを検証する]
#   処理: [
#     1: 全敵逃走、または逃走とslime撃破が混在する戦闘結果を用意する
#     2: 指定した報酬確定経路を実行する
#     3: 全敵逃走なら経験値0・保存0回、撃破があれば経験値38・保存1回を確認する
#   ]
#   引数: [
#     legacy: TrueならKadokaQuest.award_experience、FalseならBattleProgressionService.finalize_if_neededを検証する
#     all_fled: Trueなら全敵逃走、Falseなら逃走個体と撃破したslimeの混在を用意する
#   ]
#   戻り値: [result: なし（None）。経験値または個体保存の呼び出し回数が異なると失敗する]
# }
@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("all_fled", [False, True])
def test_rewards_exclude_fled_enemies_in_both_entrypoints(legacy, all_fled):
    # 逃走個体だけの結果と、実際に撃破した個体を含む結果を区別する。
    engine = battle()
    engine.enemies[0].fled = True
    if not all_fled:
        killed = engine.data_loader.build_combatant(record("slime", "倒した敵"))
        killed.hp = 0
        engine.enemies.append(killed)
    engine._check_end()
    session = BattleSession()
    session.begin(engine, 0)
    # 個体の保存をMockに置き換え、経験値と保存要求だけを検証する。
    owned = copy.deepcopy(engine.allies[0].record)
    monsters = mock.Mock()
    monsters.get.return_value = owned
    # 同じ戦闘結果を二つの公開済み報酬経路へ渡す。
    if legacy:
        KadokaQuest.award_experience(SimpleNamespace(battle=engine, monsters=monsters))
    else:
        service = BattleProgressionService(BattleFlowDependencies(
            session=session, monsters=monsters, states=mock.Mock(), state_provider=lambda: {},
        ))
        service.finalize_if_needed()
    # 逃走個体の経験値を加算せず、全敵逃走なら個体の保存も要求しない。
    assert owned.monster["experience"] == (0 if all_fled else 38)
    assert monsters.save.call_count == (0 if all_fled else 1)


# {
#   責務: [test_wild_battle_receives_current_map_context: 野生戦闘の遭遇条件を現在マップから渡し、個体の保存情報へ追加しないことを検証する]
#   処理: [1: 指定条件を持つマップから戦闘を開始し、条件の継承と未指定時のnormal補完を確認する]
#   引数: [context: マップへ設定する遭遇条件。Noneなら条件キー自体を省略する]
#   戻り値: [result: なし（None）。戦闘への条件伝達または個体情報の不変が崩れると失敗する]
# }
@pytest.mark.parametrize("context", [None, "normal", "metal_area"])
def test_wild_battle_receives_current_map_context(context):
    # マップ側の遭遇条件だけを変えられる、保存処理を持たないゲームの代替を用意する。
    engine = battle()
    world = {} if context is None else {"encounter_context": context}
    game = SimpleNamespace(
        spawn_options=lambda: [], party=lambda: [engine.allies[0].record],
        mode="field",
        make_wild=lambda spawn: engine.enemies[0].record,
        repository=engine.repository, rng=random.Random(1),
        field_session=SimpleNamespace(map_data=world), battle_session=BattleSession(),
    )
    # 実際の戦闘開始経路を使い、個体JSONへマップ専用の条件が混入しないことを確認する。
    KadokaQuest.start_wild_battle(game, {"species_id": "metal_slime"})
    assert game.battle_session.battle.encounter_context == (context or "normal")
    assert "encounter_context" not in engine.enemies[0].record.monster


# {
#   責務: [test_invalid_rate_never_consumes_randomness: 不正な逃走確率を拒否し、判定用の乱数を使わないことを検証する]
#   処理: [1: 負数・1超過・不正型・非有限値を逃走確率へ設定し、逃走失敗と乱数未使用を確認する]
#   引数: [value: normal用の逃走確率へ設定する不正値]
#   戻り値: [result: なし（None）。不正確率で逃走または乱数消費が起きると失敗する]
# }
@pytest.mark.parametrize("value", [-1, 2, "bad", None, float("nan"), float("inf")])
def test_invalid_rate_never_consumes_randomness(value):
    # 読込時の検証とは独立に、逃走判定直前の不正値への防御を確認する。
    engine = battle()
    engine.enemies[0].flee_rates["normal"] = value
    with mock.patch.object(engine.rng, "random") as roll:
        assert not engine._try_enemy_flee(engine.enemies[0])
    roll.assert_not_called()


# {
#   責務: [test_fled_card_displays_departure_instead_of_portrait: 戦闘画面が逃走済みの敵を状態表示だけで示し、立ち絵を取得しないことを確認します]
#   処理: [
#     1: 逃走済みの敵を新しい敵表示領域へ描きます
#     2: 逃走状態の表示と画像Providerを呼ばないことを確認します
#   ]
#   引数: []
#   戻り値: [result: なし。逃走状態の表示や画像取得の条件が異なる場合はassertで失敗します]
# }
def test_fled_card_displays_departure_instead_of_portrait():
    import pygame
    from kadoka_quest.ui.battle_renderer import BattleRenderer

    engine = battle()
    enemy = engine.enemies[0]
    enemy.fled = True
    session = BattleSession()
    session.begin(engine, 0)
    images = mock.Mock()
    with mock.patch("kadoka_quest.ui.battle_renderer.draw_text_clipped") as text:
        BattleRenderer(images)._draw_enemy(
            pygame.Surface((320, 280)), session, enemy, pygame.Rect(0, 0, 310, 280),
        )
    assert any(call.args[1] == "逃走済み" for call in text.call_args_list)
    images.get.assert_not_called()
    images.appearance.assert_not_called()
