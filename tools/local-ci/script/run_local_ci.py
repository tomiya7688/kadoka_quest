"""CIのPython quality workflowと同じ検査を、Godotを必須にしてローカルで順に実行します。"""

# {
#   責務: [run_local_ci: .github/workflows/python-app.ymlの各ジョブと同じコマンドを、実Godotを必須にしてローカルで実行し、成功・失敗・未実行を区別して報告します]
#   フィールド: [
#     ROOT: リポジトリ直下のパス（Path）
#     STEPS: CIと同じ順序の検査の一覧（tuple[LocalCiStep, ...]）
#     PACKAGE_COMMANDS: package-integrityジョブのうち、build_and_install_packageが実行するCIのコマンド（tuple[str, ...]）
#     REQUIRED_MODULES: 検査に必要なPythonの道具と、導入するパッケージ名の対応（dict[str, str]）
#   ]
# }
from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [LocalCiStep: CIのワークフローに書かれた一つの検査コマンドと、それが属するジョブを表します]
#   フィールド: [
#     job: CIのジョブID。test・godot・project-integrity・package-integrityのいずれかです（str）
#     name: 報告に表示する検査名（str）
#     command: CIのrunに書かれたコマンドそのもの。pythonは実行中のPythonへ置き換えて実行します（str）
#     covers: この検査が代わりに満たす別のジョブID。--skipでそのジョブを除いた場合も未実行にします（tuple[str, ...]）
#   ]
# }
@dataclass(frozen=True)
class LocalCiStep:
    job: str
    name: str
    command: str
    covers: tuple[str, ...] = ()


STEPS = (
    LocalCiStep("test", "flake8 syntax", "flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics"),
    # CIと同じく、形式の指摘は件数を表示するだけで失敗にしません。
    LocalCiStep(
        "test",
        "flake8 style report (non-blocking)",
        "flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics",
    ),
    LocalCiStep("godot", "Godot import", '"$KADOKA_GODOT_EXECUTABLE" --headless --path gdscript --editor --import --quit'),
    # CIのtestジョブ（Godotなし）とgodotジョブ（-m godot）を、Godot必須の一回の全体実行でまとめて満たします。
    LocalCiStep("test", "pytest (all, Godot required)", "python -m pytest", covers=("godot",)),
    LocalCiStep(
        "project-integrity", "format check (added Python files)", "python tools/format/script/format_changed.py --check"
    ),
    LocalCiStep("project-integrity", "project rules", "python tools/project-integrity/script/check_project_rules.py"),
    LocalCiStep("project-integrity", "declaration comments", "python tools/comment-check/script/check_comments.py"),
    LocalCiStep("project-integrity", "repo map", "python tools/code-docs/script/generate_repo_map.py --check"),
    LocalCiStep("project-integrity", "UPD checker", "python tools/upd-commander/script/check.py"),
    LocalCiStep(
        "project-integrity",
        "application class diagram",
        "python tools/code-docs/script/generate_class_diagram.py --source src/kadoka_quest/application"
        " --output docs/generated/application_class_diagram.mmd --check",
    ),
    LocalCiStep(
        "project-integrity", "runtime performance", "python tools/performance-check/script/check_runtime_performance.py"
    ),
    LocalCiStep("project-integrity", "Player project validation", "python developer_launcher.py --validate-project"),
)
PACKAGE_COMMANDS = ("python -m build", "python -m twine check dist/*")
# CIのgodotジョブが導入する版です。版を上げるときは.github/workflows/python-app.ymlのGODOT_VERSIONと同時に更新してください。
# mono版は別のビルドのため、公式の標準版（official）まで照合します。
EXPECTED_GODOT_VERSION = "4.7.2.stable.official"
# UPD checkerはCIと同じく上流mainから、RuffはCIと同じ固定版をrequirementsで導入します。
REQUIRED_MODULES = {
    "pytest": "pytest",
    "flake8": "flake8",
    "build": "build",
    "twine": "twine",
    "upd_commander_checker": "-r tools/upd-commander/requirements.txt",
    "ruff": "-r tools/format/requirements.txt",
}


# {
#   責務: [resolve_command: CIのコマンド文字列を、実行中のPythonとローカルのGodotを使う引数列へ変換します]
#   処理: [1: Godotの参照を実際のパスへ置き換え、先頭のpythonを実行中のPythonへ、flake8をpython -m flake8へ置き換えます]
#   引数: [
#     command: CIのrunに書かれた一つのコマンド（str）
#     godot: Godotの実行ファイルのパス（str）
#   ]
#   戻り値: [result: subprocessへ渡す引数の一覧（list[str]）]
# }
def resolve_command(command: str, godot: str) -> list[str]:
    parts = shlex.split(command.replace('"$KADOKA_GODOT_EXECUTABLE"', shlex.quote(godot)))
    # CIと同じPythonの版でなくても、同じ環境の道具を使うよう実行中のPythonへ揃えます。
    if parts[0] == "python":
        parts[0] = sys.executable
    elif parts[0] == "flake8":
        parts = [sys.executable, "-m", "flake8", *parts[1:]]
    return parts


# {
#   責務: [run_step: 一つの検査を、CIと同じ環境変数でリポジトリ直下から実行し、終了コードと所要時間を返します]
#   処理: [1: 変換したコマンドを実行し、終了コードと経過秒数を返します]
#   引数: [
#     step: 実行する検査（LocalCiStep）
#     godot: Godotの実行ファイルのパス（str）
#     environment: 子プロセスへ渡す環境変数（dict[str, str]）
#   ]
#   戻り値: [result: 終了コードと秒数の組（tuple[int, float]）]
# }
def run_step(step: LocalCiStep, godot: str, environment: dict[str, str]) -> tuple[int, float]:
    started = time.monotonic()
    completed = subprocess.run(resolve_command(step.command, godot), cwd=ROOT, env=environment, check=False)
    return completed.returncode, time.monotonic() - started


# {
#   責務: [godot_version: 指定したGodotを起動して版の文字列を返し、起動できない場合はNoneを返します]
#   処理: [1: --headless --versionを実行し、成功時は標準出力の最後の行を返します]
#   引数: [godot: Godotの実行ファイルのパス（str）]
#   戻り値: [result: 例「4.7.2.stable.official.ed1daf0bf」。起動・応答できなければNone（str | None）]
# }
def godot_version(godot: str) -> str | None:
    try:
        completed = subprocess.run(
            [godot, "--headless", "--version"], capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = completed.stdout.strip().splitlines()
    return lines[-1].strip() if completed.returncode == 0 and lines else None


# {
#   責務: [build_and_install_package: package-integrityジョブと同じく、sdistとwheelを作ってtwineで検査し、wheelを独立した仮想環境へ入れてリポジトリ外からimportします]
#   処理: [
#     1: 開発者のdist/にある配布物を混ぜないよう、一時フォルダへbuildし、そのファイルだけをtwineで検査します
#     2: 一時フォルダの仮想環境へwheelを導入してpip checkを実行します
#     3: リポジトリ外を作業フォルダにしてkadoka_questをimportします
#   ]
#   引数: [environment: 子プロセスへ渡す環境変数（dict[str, str]）]
#   戻り値: [result: 終了コードと秒数の組（tuple[int, float]）]
# }
def build_and_install_package(environment: dict[str, str]) -> tuple[int, float]:
    started = time.monotonic()
    # 開発者のPYTHONPATHが作業ツリーのsrcを指していると、導入したwheelではなくsrcをimportして誤って成功するため除きます。
    isolated = {key: value for key, value in environment.items() if key not in ("PYTHONPATH", "PYTHONHOME")}
    with tempfile.TemporaryDirectory(prefix="kadoka-local-ci-package-") as folder:
        output = Path(folder) / "dist"
        venv = Path(folder) / "venv"
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        # CIはcheckout直後の空のdist/へ作ります。ローカルではdist/の既存のPyInstaller成果物を消さずに同じ状態を作ります。
        steps = [
            ([sys.executable, "-m", "build", "--outdir", str(output)], ROOT),
            (lambda: [sys.executable, "-m", "twine", "check", *map(str, sorted(output.iterdir()))], ROOT),
            ([sys.executable, "-m", "venv", str(venv)], Path(folder)),
            (lambda: [str(python), "-m", "pip", "install", "--quiet", *map(str, output.glob("*.whl"))], Path(folder)),
            ([str(python), "-m", "pip", "check"], Path(folder)),
            # import確認はリポジトリ外で実行し、作業ツリーのsrcを誤って読み込まないようにします。
            (
                [
                    str(python),
                    "-c",
                    "import pathlib, sys, kadoka_quest; path = pathlib.Path(kadoka_quest.__file__).resolve(); "
                    "assert pathlib.Path(sys.prefix).resolve() in path.parents, path; print(path)",
                ],
                Path(folder),
            ),
        ]
        for command, cwd in steps:
            arguments = command() if callable(command) else command
            # buildがwheelを作らなかった場合、pip installを対象なしで呼ぶのではなく理由を示して失敗にします。
            if arguments[1:4] == ["-m", "pip", "install"] and not any(output.glob("*.whl")):
                print(f"[ERROR] {output}にwheelがありません。")
                return 1, time.monotonic() - started
            completed = subprocess.run(arguments, cwd=cwd, env=isolated, check=False)
            if completed.returncode:
                return completed.returncode, time.monotonic() - started
    return 0, time.monotonic() - started


# {
#   責務: [missing_tools: 検査に必要なPythonの道具のうち、実行中のPythonへ導入されていないものを返します]
#   処理: [1: 必要なモジュールごとにimportできるかを確認し、導入されていないパッケージ名を集めます]
#   引数: []
#   戻り値: [result: 導入が必要なパッケージ名の一覧（list[str]）]
# }
def missing_tools() -> list[str]:
    return [package for module, package in REQUIRED_MODULES.items() if importlib.util.find_spec(module) is None]


# {
#   責務: [main: CIと同じ検査を順に実行し、成功・失敗・未実行の一覧と、全体の判定を表示します]
#   処理: [
#     1: Godotの実行ファイル・版と必要な道具を確認し、足りなければ何も実行せずに理由と対処を表示します
#     2: KADOKA_REQUIRE_GODOT=1とCIと同じSDLの設定で、選んだ検査とパッケージの検査を順に実行します
#     3: --skipで除いた検査は未実行として表示し、失敗があれば1、未実行だけなら3、全成功なら0を返します
#   ]
#   引数: [argv: コマンドライン引数。省略時はsys.argvを使います（list[str] | None）]
#   戻り値: [result: 終了コード。0は全成功、1は失敗あり、2は準備不足、3は未実行ありです（int）]
# }
def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    jobs = sorted({step.job for step in STEPS} | {"package-integrity"})
    parser.add_argument(
        "--skip", action="append", default=[], choices=jobs, help="未実行として報告するジョブ。全体の判定は成功になりません"
    )
    parser.add_argument("--list", action="store_true", help="実行する検査の一覧だけを表示します")
    args = parser.parse_args(argv)
    if args.list:
        for step in STEPS:
            print(f"[{step.job}] {step.name}: {step.command}")
        for command in PACKAGE_COMMANDS:
            print(f"[package-integrity] {command}（一時フォルダへ出力し、wheelの導入とimportまで確認）")
        return 0
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot or not Path(godot).is_file():
        print(
            "[ERROR] KADOKA_GODOT_EXECUTABLEへGodot 4.7.2のコンソール実行ファイルを設定してください。"
            "CIと同じくGodotの検査を必須にするため、Godotなしでは実行しません。"
        )
        return 2
    version = godot_version(godot)
    if version is None:
        print(f"[ERROR] {godot}を起動できないか、--versionに応答しません。Godot {EXPECTED_GODOT_VERSION}を指定してください。")
        return 2
    if not version.startswith(EXPECTED_GODOT_VERSION):
        print(f"[ERROR] {godot}の版は{version}です。CIと同じGodot {EXPECTED_GODOT_VERSION}を指定してください。")
        return 2
    missing = missing_tools()
    if missing:
        print(
            f"[ERROR] 次の道具が{sys.executable}にありません。リポジトリ直下で導入してから再実行してください: "
            f"{sys.executable} -m pip install {' '.join(missing)}"
        )
        return 2
    # CIのenvと同じ設定に、Godotの検査をskipで終わらせない設定を加えます。
    environment = dict(
        os.environ,
        KADOKA_GODOT_EXECUTABLE=godot,
        KADOKA_REQUIRE_GODOT="1",
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        PYGAME_HIDE_SUPPORT_PROMPT="1",
    )
    environment.pop("KADOKA_GDSCRIPT_SAVE_NAME", None)
    results: list[tuple[str, str, float]] = []
    for step in STEPS:
        label = f"[{'+'.join((step.job, *step.covers))}] {step.name}"
        # Godotのテストを含む全体pytestは、testとgodotのどちらを除いても未実行として報告します。
        if step.job in args.skip or any(job in args.skip for job in step.covers):
            results.append(("NOT RUN", label, 0.0))
            continue
        print(f"\n=== {label}", flush=True)
        code, seconds = run_step(step, godot, environment)
        results.append(("OK" if code == 0 else f"FAILED({code})", label, seconds))
    label = "[package-integrity] build, twine check, install wheel and import"
    if "package-integrity" in args.skip:
        results.append(("NOT RUN", label, 0.0))
    else:
        print(f"\n=== {label}", flush=True)
        code, seconds = build_and_install_package(environment)
        results.append(("OK" if code == 0 else f"FAILED({code})", label, seconds))
    print(f"\n# Local CI summary (Python {sys.version.split()[0]}, Godot {godot})")
    for status, name, seconds in results:
        print(f"{status:<11} {name}  {seconds:.1f}s")
    print("note: CIのtestジョブはPython 3.10と3.14で実行します。ここで実行したのは上記のPythonの版だけです。")
    print("note: Windows distribution workflowの配布物ビルドとsmokeは、この検査に含みません。")
    if any(status.startswith("FAILED") for status, _, _ in results):
        return 1
    return 3 if any(status == "NOT RUN" for status, _, _ in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
