# GDScript通常攻撃・防御・会心の数値契約

#221の純粋な数値部分。実装は `gdscript/engine/attack_numbers.gd`、比較は `tests/test_gdscript_attack_numbers.py` と実Godotの `run_attack_probe.gd`。Python正本は `core/battle.py::_attack` と `Combatant.defense`。戦闘Sceneやターンを進めるAPIではない。

## 入力と責務

`normal_attack(request)` はplainな辞書を受け取る。呼出側が#220の補正後能力値と許可装備を渡す。装備許可の再判定、能力値表の読込、状態異常の解決はしない。

| 入力 | 意味 / 省略時 |
| --- | --- |
| `attack`, `defense`, `target_hp` | 必須。攻撃値、解決済み防御値、現在HP。防御値は最低0、HPは0以上。 |
| `critical_roll` | 必須。0以上1未満の会心乱数。 |
| `variance` | 必須。0.92以上1.08以下のダメージ倍率そのもの。 |
| `attack_multiplier`, `power`, `critical_multiplier` | 攻撃一時倍率、通常攻撃威力、会心率倍率。各1。 |
| `guard` | 防御コマンド等の軽減倍率。1。 |
| `equipment` | 許可済み装備の定義。省略/空/nullは効果なし。通常攻撃の威力倍率と固定追加値だけを使用。 |
| `kind`, `skill_id` | 任意。指定するならphysical / attackのみ。他の攻撃は拒否。 |

整数入力はPythonのint相当で0方向へ切り捨てる。有限数値/ASCII数値文字列を扱い、bool、不正型、非有限値、安全なJSON整数精度を超える値/演算を理由付きで拒否する。倍率や威力の負数を勝手に修復しない点も現Python版に合わせる。未知キーは読まず、入力を変更しない。

乱数生成器、時刻、UI、ファイルI/O、AIをエンジンへ持ち込まない。2つの乱数値を明示入力することでPythonと同じ条件で比較できる。Python/Godotの同じseedで乱数列が同じになるという契約ではない。将来の呼出側が乱数の取得/消費順を担当する。

## Pythonと同じ計算順

`int` は偶数丸めや四捨五入ではなく、0方向への切捨て。

```text
A = int(attack × attack_multiplier)
P = power × equipment.skill_modifiers.attack.power_multiplier（省略1）
C = min(1, (1/16) × critical_multiplier)
会心 = critical_roll < C
B = int(A × P)                               # 会心時、防御値を使わない
B = int(A × P - max(0, defense) × 0.42)       # 非会心時
B += int(equipment.fixed_bonus_damage)        # 省略0
D = max(1, int(B × guard × variance))         # 会心でもguardは掛かる
残HP = max(0, target_hp - D)
実与ダメージ = target_hp - 残HP
```

標準会心率は1/16。ちょうど1/16の乱数は非会心。会心倍率は上限1のみで、下限を新設しない（負の倍率なら会心しない）。最低ダメージ1の判定は最後。固定追加値も防御倍率と揺らぎの対象になる。一時攻撃倍率を1へ戻す/バフを消費する状態変更は、この数値APIでは行わない。

成功結果は `ok / scope: normal_attack_numbers / effective_attack / effective_power / critical_chance / critical / raw_damage / damage / applied_guard / variance / dealt / remaining_hp`。`raw_damage` は固定追加後・防御倍率/揺らぎ前、`damage` は計算ダメージ、`dealt` は現在HPで制限した実与ダメージ。HP0への計算ならdamageは最低1でもdealtは0。#230の[行動契約](GDScript通常攻撃行動契約.md)が最新生存敵と単一ticketを検証し、実HPへ適用する。対象自動選択/AI/Sceneは未接続。

#251の[基本防御行動](GDScript基本防御行動契約.md)がguardをSessionへ保持し、通常攻撃Actionが対象の現在倍率を使います。数値APIの魔法/drain_mp検証を魔法行動実装と扱いません。

例: 攻100/防10、非会心、guard=0.5、variance=1、現在HP40なら、raw_damage=95、damage=47、dealt=40、remaining_hp=0。各段階を丸め直すとPython正本と異なるため、途中のintを省略しない。

失敗は `ok: false / error: invalid_attack_numbers / message` を返し、damageやHPの代替結果を作らない。

## 防御と共通の最終数値

`defend_multiplier(definition)` は `kind: defend` の `damage_multiplier`（省略0.5）から `ok / guard / scope: defend_multiplier_only` を返す。省略した辞書も基本防御の0.5。HP/MP、guard状態、ターン、counter/protect等の特殊防御は変更しない。

`finish_damage(request)` は `kind / damage / target_hp / variance` と任意の `guard` を受け、切捨て→最低1→HP制限だけを行う。kindはphysical/magic/drain_mp。physicalだけguardを使い、magic/drain_mpでは1に固定する。戻りのscopeは `positive_damage_finalization`。魔法の基礎値/耐性/吸収/MP吸収までの実装ではない。無効化/吸収/回避経路はこの関数へ入れず、後続の戦闘処理で別に解決する必要がある。

## 検証と未移植範囲

実GodotとPython BattleEngineへ同じ数値/固定乱数を渡し、通常/防御/会心の600組、1/16の境界、16等分入力の1会心、低攻撃/高防御、0.92/1.08と近接境界、各段階の切捨て、装備威力/固定追加、非物理への防御漏れ、HP0/過剰ダメージ、数値文字列、不正型/非有限/精度超過を比較する。#220の実JSON再構築結果から許可/拒否/未知装備を渡す経路と、原本/個体/AI byte不変も専用コピーで確認する。

このAPIをフィールドや戦闘Sceneへまだ接続していない。ターン進行、勝敗/経験値/保存、全スキル、回避/耐性/吸収/状態異常/反撃、AI推論/学習、演出、エディタ、配布exportの完了証拠ではない。正規JSONやPython runtimeは変更しない。
