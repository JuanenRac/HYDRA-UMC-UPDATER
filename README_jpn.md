<!-- =============================================================================
HYDRA-UMC-UPDATER - Installs and updates the HYDRA-UMC projects
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 📦 HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📦 HYDRA-UMC エコシステム全体の検出、インストール、手動更新

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="Core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Tests-181%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.5.0-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

> **安全性とセキュリティの現状:** このエコシステムは認証された安全システムではありません。ハードウェアの E-STOP 経路、ファームウェアが強制する制限やインターロック、検証済みの動作コマンドはまだありません。ファームウェアイメージは CRC-32 と Ed25519 署名で検査し、リリースビルドは公開済みの開発用鍵を拒否します(リレーの先のツールヘッドと拡張ボードは引き続き URTC のブートローダーを使い、署名ではなく共有鍵の HMAC-SHA256 を使います)。TLS と相互 TLS は任意で、既定では無効です。独自基板はまだ実装も試験もされていません。ここに書かれた内容を人の安全のために頼る前に、[セキュリティベースライン](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)と[脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)をお読みください。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.5.0` |
| 成熟度 | 確立 |
| テスト | 181 (`python -m pytest -q tests`) |
| 技術 | Python 3.10+ / PySide6 / Qt Quick (QML) / Tkinter (legacy fallback) / Git / GitHub raw content |
| 対象 | 利用者の PC |
| 実機での確認 | 対象外：ここにあるものはハードウェア上では動きません |

**移動：** [概要](#-概要) · [アーキテクチャ](#-アーキテクチャ) · [セキュリティと安全](#-セキュリティと安全) · [設定](#-設定) · [クイックスタート](#-クイックスタート) · [テスト](#-テスト) · [トラブルシューティング](#-トラブルシューティング) · [リポジトリの構成](#-リポジトリの構成) · [関連プロジェクト](#-関連プロジェクト)

## 🚦 プロジェクトの状況

各行はこのリポジトリの一部分で、信号は今日どこまで進んでいるかを示します。計画ではなく、リポジトリが示せるもの（テスト、ビルド、実行）に基づいて書かれています。

🟢 完了・検証済み · 🟡 動作する（既知の制限あり） · 🟠 一部のみ、または未検証 · 🔴 未実装または動作しない

| 領域 | 状態 | ここでの意味 |
|---|---|---|
| ソフトウェア | 🟢 | 目的に対して完成していて安定しています。既知の制限は上の正直さの確認に書かれています |
| テスト | 🟢 | 自動テスト 181 件。変更のたびに実行されます |
| 実機 | 🟢 | 対象外：ここにあるものはハードウェア上では動きません |
| ドキュメント | 🟢 | 8 言語の README。変更のたびにマニフェストと照合されます |

## 🎯 概要

HYDRA-UMC-UPDATER は、小さなツールです——デフォルトはウィンドウ付き
GUI、`--cli` で完全な CLI が利用可能——実際の CM5 本体上、または開発者
自身の Windows/Linux/macOS マシン（同じ方法でチェックアウトされた任意の
ワークスペース）で実行されることを意図しており、各隣接チェックアウト
自身の `hydra-umc.project.json` マニフェストを通じて発見する、他の
すべての実在するプロジェクトそれぞれについて 3 つの問いに答えます
——この数自体はエコシステムとともに増えていくため、ここでは決して
固定値としてハードコードされていません：

1. **ここに実際に何がインストールされていて、そのバージョンは何か？**
2. **GitHub 上に公開されている最新バージョンは何か？**
3. **GitHub の方が新しければ、1 つのプロジェクトまたは確認済みの順次一括操作を選ばせてほしい。**

最後のポイントは意図的であり、譲れないものです：このツールが独自の判断
でプロジェクトを変更することは決してありません。選択したプロジェクトの
操作には常に明示的な確認が必要です。GUI は**不足分をすべてインストール**
または**古い項目をすべて更新**も提供できますが、いずれも個別確認された
順次一括操作で、同じマニフェスト・バージョン・安全ゲートを通ります。
人の承認なしに夜間自動更新されることはありません。確認ダイアログには、一括操作の対象プロジェクトが実行順に正確に表示されます。

発見されたプロジェクトのすべてが CM5 本体に属するわけでもありません。開発者が自分の PC から実行するツール（ファームウェアはセル上ではなくワークステーションからコンパイル/書き込みします）や、スマートフォン/ウォッチにインストールするアプリもあります。どれに当たるかは各プロジェクト自身のマニフェストに記録されており（第 3 節参照）、GUI のプロジェクト表はそれで絞り込めます。既定ではすべてのプロジェクトを表示するため、アップデーター自身も SDK も隠れません。

実例（以下のプロジェクト数と各バージョン番号は出力の形を示すために
作成したものであり、実際にキャプチャした実行結果ではありません——実際の
数は常にその時点で `registry.py` が発見するものであり、この文書に
固定された数値ではありません）：

```
$ hydra-umc-updater --cli status
Workspace root: /home/pi/HYDRA-UMC
PROJECT           MATURITY     ROLE      STACK       LOCAL     GITHUB    STATE
-----------------------------------------------------------------------------
HYDRA-UMC         functional   firmware  firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER  functional   service   node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO  functional   client    node        0.0.8     0.1.3     OUTDATED
...
59/59 installed, 2 outdated
Run `hydra-umc-updater update <project>` to update one by hand - never automatic, see this tool's own README.

$ hydra-umc-updater --cli update HYDRA-UMC-SERVER
Updating HYDRA-UMC-SERVER into /home/pi/HYDRA-UMC ...
OK  Updated /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER to v0.0.9 (commit 1a2b3c4d5e6f) after a verified build; previous installation kept at /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER.backup-9f3c2d1a
```

`hydra-umc-updater` を引数なしで実行する（またはダブルクリックする）
と、同じ情報がウィンドウ内に表示されます——ソート可能なプロジェクト
テーブル、デプロイターゲットフィルター、そして選択された行に対する
インストール/更新ボタンです。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="HYDRA-UMC-UPDATER の実際のデスクトップ概要" width="100%">
</p>

## 🧩 HYDRA-UMC での役割

**HYDRA-UMC-UPDATER** は、実行しているマシン上の HYDRA-UMC プロジェクトを見つけ、インストールし、手動で 1 つずつ更新します。新しいバージョンはまずステージングフォルダーでクローンとビルドが行われ、その後で所定の場所へ移されます。以前のものはバックアップとして残り、試行ごとに証跡が 1 行残ります。同じコアを呼ぶコマンドラインとデスクトップウィンドウがあります。

## 🏛️ アーキテクチャ

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-UPDATER architecture" width="100%">
</p>

### チェック/更新が実際にどう機能するか

- **バージョンの取得元**。そのため本ツールは、各プロジェクト自身の `bump_version.py`/ビルドスクリプトが既に書き込んでいる*その同じ*ファイルを、GitHub の生コンテンツホスト経由でリポジトリのデフォルトブランチから直接読み取ります——Releases API ではありません。それを使うと、すべてのプロジェクトが「リリースが一切ない」と報告されてしまいます。
- **ローカル検出**：発見されたプロジェクトそれぞれについて、そのプロジェクトと完全に同じ名前のディレクトリがワークスペースルート下に存在するかを確認します（標準的なエコシステムのレイアウト——すべてのプロジェクトを兄弟ディレクトリとして配置する、`build-frontend.sh`/HYDRA-UMC-SUITE 自身の検出ロジックが既に前提としているのと同じ形）。存在する場合、そのプロジェクト*自身*の同じバージョンファイルのローカルコピーを読み取ります。
- **単一の解析実装**（`version_parse.py`）が、ローカル読み取りと GitHub 取得の間で共有されているため、ローカルのチェックアウトと GitHub からの取得が、2 つの独立して食い違っていく正規表現によって別々に解釈されることは決してありません。
- **インストール/更新**：`git clone`（インストール）はその後、別のステップとしてビルドします。既存のチェックアウトの更新は代わりに「検証による原子性」です——候補はクローンされ、ファストフォワードでマージされ(強制リセットは決して行わないため、実際のローカルの編集は破棄されるのではなく明確に失敗します)、まず完全に独立したステージング用クローンの中でビルド・検証されます——実際にインストールされているものが実際に触られるのは(2 回連続のディレクトリのリネームによって、以前のインストールは削除されずに `<name>.backup-xxxxxxxx` として保持されます)、そのステージングビルドが本当に成功した場合だけです。ビルドの失敗、分岐した/汚れたチェックアウト、クラッシュ、あるいは最終的な昇格の前のどの時点でのディスクフルも、以前のインストールを完全に無傷のまま、稼働可能な状態に保ちます——詳細は `install.py` 自身の `clone_or_pull` の docstring を参照してください。ステージング用クローン自身の git リモートは、作成された直後に実際の GitHub アップストリームへ復元されます(そうしないと、単なるローカルクローンは古いインストールパスを指したままになり、昇格された時点で今後のすべての更新を静かに終わらせてしまいます)。また、インストール済みチェックアウト自身の実際のローカルデータ(git が未追跡または無視対象とみなすもの——`data/settings.json` などで、再生成可能なビルド成果物は除く)は、ビルドの前にステージング用クローンへ持ち込まれるため、プロジェクト自身の実際の運用状態は、保持された `.backup` チェックアウトに取り残されることなく、更新を乗り越えます。いずれにせよ、そのプロジェクトが実際に持っている `build-test.sh`/`build-test.bat`(バージョンを上げない非破壊チェック——第 3 節参照)があれば、それを実行します。本ツールは、プロジェクト自身のビルド手順を再実装することは決してありません。

- **オプションの署名チェック**：候補の `build-test` スクリプトは候補自身が持ち込むコードであり、そのコミットがメンテナーのものだと何も証明されないうちに、ここで実行されます。`HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1` を設定すると、アップデーターはまずステージングクローン内で受け入れた候補に対して `git verify-commit` を実行し、このマシンが信頼する署名（キーリングの gpg 鍵、または `gpg.ssh.allowedSignersFile` の ssh 署名者）がコミットになければそこで停止します。何もビルドも実行もされず、稼働中のインストールには一切触れません。メンテナーの鍵を信頼するキーリングがマシンに必要なため、既定では無効です。

- **昇格のたびに新しい `.venv`**：置き換える側のインストールに `.venv` があった場合、昇格したチェックアウトには何もない状態ではなく新しい `.venv` が作られます（`python -m venv`、プロジェクトに `requirements.txt` があれば続けて `pip install -r requirements.txt`）。古いものは `.backup` の中に残ります。`HYDRA_UMC_UPDATER_RECREATE_VENV=0` または保存済み設定 `recreate_venv` で無効にできます。作成できない場合、更新は失敗として報告され、古い `.venv` を保持しているバックアップが示されます。
- **さらなる安全策**：ワークスペースごとにインストールや更新は同時に 1 つだけ（ロックファイル）。すべての git コマンドと build-test に時間制限があり、認証情報を尋ねることはありません。想定外のエラーはウィンドウと証跡ファイルで失敗結果となり、「作業中」のまま止まることはありません。署名チェックは初回インストールにも適用され、保存済みの設定（`require_signed_commits`。読めない設定ファイルは有効とみなします）で有効にでき、無効の間はウィンドウに赤い警告を表示します。早送りを不可能にするローカルコミットは拒否メッセージで示され、ビルドに失敗した新規インストールは再び削除されます。古いステージングフォルダーは実行の開始時に整理され、`--cli prune-backups [--keep N] [--dry-run]` は要求があったときだけ古い `<名前>.backup-xxxxxxxx` フォルダーを削除します。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="HYDRA-UMC-UPDATER のインストールまたは更新中の実際のチェックポイント" width="100%">
</p>

### アーキテクチャと設計上の決定

- **標準は Qt Quick GUI、ヘッドレス向けは `--cli`。** `main.py` は任意の PySide6
  ランタイムを読み込む前に `--cli` を確認します。CLI は画面やデスクトップ依存のない
  CM5 で動作し、引数なしでは利用可能な場合に QML を起動します。Tkinter は一時的な
  互換フォールバックとしてのみ残ります。
- **ウィンドウ表示のGUIは実在し、8言語対応の多言語です(`i18n.py`)—— `--cli` は意図的にそうなっていません。** 実在するすべてのウィジェットは、言語 `Combobox`(en/es/fr/it/de/zh/ja/pt、公開ダッシュボードとすべてのREADMEが提供するのと同じ8言語)から保存された設定またはOS自身のロケールに基づいて検出され、リアルタイムでラベルが再表示されます。プロジェクト/ファミリー名と各プロジェクト自身の実際の `notes`/`tech` テキストは未翻訳のままです—— `registry.py` がそれらの唯一の信頼できる情報源であり、8つの並行した実際のエンジニアリングドキュメントのコピーはそれを妨げてしまいます。`--cli` の出力は意図的に英語のみのままです:これはスクリプト化/パイプ処理を想定しており、安定してgrep可能なテキストがローカライゼーションよりも重要な場面のためです。
- **`deploy` は制限ではなく分類です。** 発見されたプロジェクトすべてを「CM5 に属するもの」として扱うのは誤りでした——ファームウェアリポジトリは PC からコンパイル・書き込みされます（CM5 は CAN-OTA 経由で最終的なバイナリだけを必要とし、このリポジトリ自身のソースコードを必要とすることは決してありません）。また、いくつかのツール（URTC-FLASHER、HYDRA-UMC-SUITE、HYDRA-UMC-TOOL-CLI……）は、セル自体の内部ではなく、オペレーター自身のワークステーションで実行されることを意図しています。`registry.py` の `deploy` フィールド（"cm5" / "user-pc" / "mobile" / "wearable" / "dev-server"）がそれを記録しており、GUI のフィルターはそれを妥当な出発点として使用します——厳格な制限ではありません。なぜなら、この同じツールは開発者自身の PC 上でも実行されることを意図しており、その場合は発見されたプロジェクトのすべてが検査対象になり得るからです。
- **本ツールには技術スタックごとのビルドロジックがありません。** このエコシステムは 7 つのツールチェーン（Python、Rust、Go、Node/TS、Android/Kotlin、Flutter、ARM ファームウェア）にまたがります。`npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` などを*ここで*再実装すると、各プロジェクトのビルド方法を知っていると主張する場所がもう 1 つ増え、そのプロジェクト自身の実際の（すでに正しい）チェックから必ずずれていきます。代わりに `install.py` は、プロジェクト自身のバージョンを上げない `build-test.sh`（Windows では `build-test.bat`）だけを実行します。これはバージョンを上げずに検証を行うもので、無いプロジェクトは "No non-versioning build-test.sh/.bat found" で拒否されます。
- **Releases API ではなく GitHub の生コンテンツを使用。** 上記の第 2 節を参照——このエコシステムのバージョン管理慣例はタグ/リリースを一切作成しないため、ここで Releases API を使うことは、単に不便なだけでなく、積極的に間違っています。
- **一時的なネットワーク障害には本物の再試行があるが、確定的な応答には決してない。** 実際の GitHub へのリクエストはすべて（`github_client.py` の `_urlopen_with_retries`）、接続がまったく応答を得られなかった場合（DNS/タイムアウト/リセット）に限り、バックオフを伴って最大 3 回まで再試行します。GitHub が実際に返した本物の HTTP ステータス——404、403、500——は決して再試行されません。GitHub はすでに応答しており、再度叩いても同じ結果のためにレート制限をさらに消費するだけだからです。
- **不正な形式のリモートカタログは大きく失敗するが、1 つの不正なプロジェクトはそうではない。** GitHub のリポジトリ一覧そのものに到達できない、または解析できない場合、`discover_remote_projects()` は例外を送出します——`gui.py` と `main.py` はどちらもすでにこれを捕捉し、壊れた、あるいは空のスキャンを表示する代わりに、ローカルで発見されたプロジェクト一覧にフォールバックします。対照的に、単一リポジトリの不正な形式のマニフェストは、そのスキャン自身の `errors` リストに隔離され、残りの発見処理を決して中断させません——実際のフィクスチャサーバーを使ったテスト（`tests/test_github_client.py`）が両方の経路を証明しています。
- **CLI 操作は明示的、GUI の一括操作は確認付きです。** CLI の
  `install`/`update` は 1 つのプロジェクト名を必要とします。デスクトップ
  GUI は**不足分をすべてインストール**または**古い項目をすべて更新**を
  実行できますが、個別確認後に同じ安全ゲートを通して順次実行します。
  無人の自動更新は存在しません。
- **標準ライブラリのみ。** GitHub の取得には `urllib`（`github_client.py`）、git/ビルドスクリプトの呼び出しには `subprocess`（`install.py`）を使用し、それ以外は何もありません——他の*すべての*プロジェクトの依存関係を健全に保つ責任を持つツール自体が依存関係を持たないでいることは、意図的なものです。
- **既知の簡略化**：HYDRA-UMC と URTC は、実際には複数コンポーネントからなるファームウェアリポジトリです（それぞれ 6 個と 4 個の独立してバージョン管理されるバイナリを持ちます——それぞれの `VERSION_CHECKLIST.txt`/`build_firmware.sh` を参照）。単一の「これが」バージョン番号というものは存在しません。`registry.py` はリポジトリごとに 1 つの代表的なコンポーネントのみを追跡します——「このリポジトリはおおむね最新か」に答えるには十分ですが、実際のフラッシュ用の `build_firmware.sh` 自身の `firmware_manifest.json` の代替にはなりません。

## 🔒 セキュリティと安全

| 脅威 | 防御 | 場所 |
|---|---|---|
| ビルドに失敗した新バージョンが、更新途中のプロジェクトを残す | 候補はまず別のステージングフォルダーでクローン、マージ、ビルドされ、成功するまでインストール済みフォルダーには触れません。成功後に 2 回の名前変更で入れ替え、古いものは `<name>.backup` として残ります | `install.py` |
| 実際にはロールバックになる更新や、ローカルの作業を捨ててしまう更新 | 取得したマニフェストは検証され、低いバージョンは拒否されます。使うのは fast-forward マージだけで、追跡対象のローカル変更があれば更新ははっきり停止します | `install.py`, `project_manifest.py` |
| メンテナーのものではないコミットのコードを実行してしまう | `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1`（または保存済みの設定）がある場合、クローンしたコミットは、その内容を実行する前に `git verify-commit` に通る必要があります。ツールが無い、署名が無い、鍵が未知のいずれも未署名として扱われます | `install.py` |

**絶対にしないこと：** 勝手に更新すること。インストールも更新も誰かが実行するコマンドで、読み取れる `GITHUB_TOKEN` は任意であり、読み取り権限だけで足ります。

## ⚙️ 設定

| 変数 | 既定値 | 設定する内容 |
|---|---|---|
| `GITHUB_TOKEN` | なし | 任意の読み取り専用トークン。無い場合 GitHub は 1 時間あたり 60 リクエストまで |
| `HYDRA_UMC_UPDATER_REQUIRE_SIGNED` | `0` | `1`、`true`、`yes`、`on` でクローンしたコミットに有効な署名を要求 |
| `HYDRA_UMC_UPDATER_RECREATE_VENV` | オン | `0` で、昇格後に新しい仮想環境を作らず古いものを使い続けます |
| `--workspace` | このフォルダーの親 | プロジェクトごとのサブフォルダーを持つフォルダー |

## 🚀 クイックスタート

Python 3.10 以上が必要です。

```bash
./build.sh  # Linux, macOS (build.bat on Windows)
./run.sh --cli status --offline
./run.sh --cli status --workspace ~/hydra
./run.sh --cli install HYDRA-UMC-DATALAKE
./run.sh --cli update HYDRA-UMC-DATALAKE
./run.sh --cli prune-backups --keep 2 --dry-run
```

## 🧪 テスト

`python -m pytest -q tests` で自動テスト 181 件を実行します。 ハードウェアも、このマシンの外にあるものも必要ありません。

CI は `HYDRA_UMC_CI=1 python tools/ci_validate.py` を実行し、マニフェスト、文書、8 つの README、図を検査します。

## 🏗️ ビルドとリリース

```bash
chmod +x build.sh   # 初回のみ
./build.sh          # .venv を作成、pip install -e .、すべてをコンパイルチェック
./run.sh                              # ウィンドウ付き GUI（デフォルト）
./run.sh --cli status                 # 何がインストールされているか、ローカル対 GitHub のバージョン
./run.sh --cli status --offline       # 同上、GitHub チェックをスキップ
./run.sh --cli install <PROJECT-NAME> # まだインストールされていない 1 プロジェクトをクローン + ビルド
./run.sh --cli update  <PROJECT-NAME> # 既にインストールされている 1 プロジェクトをプル + 再ビルド
./run.sh --cli prune-backups --keep 2  # 古い <名前>.backup-xxxxxxxx フォルダーを削除（各プロジェクトで新しい 2 つを残す）
```

Windows では：先に `build.bat`、その後 `run.bat`（GUI）/ `run.bat
--cli status` / `run.bat --cli install <name>` / `run.bat --cli
update <name>`。

優先 GUI にはオプションの Qt ランタイムが必要です（`pip install -e ".[gui]"`;
`build.bat`/`build.sh` は既にこれを導入します）。`--cli` には GUI 依存がなく、
ヘッドレス CM5 の正しい入口です。Qt がない場合、古い Tkinter ウィンドウは
互換フォールバックとしてのみ残ります。

**トラブルシューティング**

- `status` があるプロジェクトのローカルまたは GitHub のバージョンに `?` を表示する：バージョンファイルは存在しますが、そのプロジェクト自身の `hydra-umc.project.json` の `native_version` が、実際にバージョンがある場所と一致しなくなっています——そのプロジェクトのマニフェストを修正してください。
- `status` が GitHub についてエラーを表示せずに `-` を表示する：（`--offline` なしで）`status` を実行してください——`-` は GitHub チェックが完全にスキップされた場合にのみ表示されます。
- `install`/`update` が "No non-versioning build-test.sh/.bat found" で失敗する：そのプロジェクトにはまだ `build-test.sh`/`build-test.bat` がありません——エコシステム標準のものを追加してください（バージョンを上げずに検証するものである必要があります）。
- `git merge --ff-only failed`：ローカルのチェックアウトの履歴が分岐しているか、ローカルコミットがあります（メッセージで示されます）——`update` を再試行する前に、（そのプロジェクト自身のディレクトリで `git status`/`git log` を実行して）それらを移動または破棄してください。追跡ファイルの未コミットの変更は最初に拒否されます。本ツールがチェックアウトを強制リセットすることはありません。

## 🩺 トラブルシューティング

| 表示 | 原因 | 対処 |
|---|---|---|
| `unauthenticated requests are capped at 60/hour` | トークン無しのリクエストに対する GitHub の上限に達した | 待つか、`status --offline` を使うか、読み取り専用の `GITHUB_TOKEN` を設定します |
| the update stops and names changed files | プロジェクトの追跡対象ファイルがこのマシンで編集されている | その変更を自分でコミット、退避、または破棄してから、`update` を再実行します |

## 📂 リポジトリの構成

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-UPDATER" width="100%">
</p>

<details>
<summary>ツリーのテキスト版</summary>

```text
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/     ソースコード
│   ├── __init__.py            パッケージの説明とバージョン
│   ├── registry.py            ProjectEntry - 静的カタログなし。各リポジトリ自身のマニフェストから検出時に構築
│   ├── project_manifest.py    リポジトリ自身の hydra-umc.project.json を読み取り/検証
│   ├── ecosystem_catalog.py   JuanenRac エコシステムの公開検出カタログのパーサー
│   ├── version_parse.py       ローカル+GitHub 共通の単一の正規表現抽出実装
│   ├── detect.py              ワークスペースルートをスキャンし、何がインストールされているかを検出
│   ├── github_client.py       生コンテンツの並行取得 + 一時的なネットワークエラーに対する本物の再試行/バックオフ
│   ├── install.py             git clone/pull + プロジェクト自身のビルドスクリプトへの委譲
│   ├── i18n.py                実際の完全なGUI翻訳(8言語)
│   ├── qt_gui.py              実際の検出/更新サービスへの Qt Quick ブリッジ
│   ├── qml/Main.qml           テーマ、チェックポイント、About を持つデスクトップ画面
│   ├── gui.py                 PySide6 がない場合の Tkinter 互換フォールバック
│   ├── main.py                ディスパッチ：デフォルトは GUI、--cli で status/install/update
│   ├── evidence.py            インストールや更新の試行ごとの証跡1行: プロジェクト、変更前、変更後、コミット、結果
│   ├── assets/                アプリケーションのアイコン (HYDRA_UMC_ICON.ico と .svg)
│   ├── i18n_pt.py             GUI のポルトガル語訳
│   └── settings.py            保存されるユーザー設定 (ワークスペースのルートなど、GUI が起動間で記憶する選択)
├── tests/                     実際のテスト：github_client、i18n、install、project_manifest、registry
├── docs/                      プロジェクトの文書
├── images/                    メディア、アプリアイコン、インターフェースのスクリーンショット
├── tools/                     プロジェクトのツールと CI の検査
├── .github/                   CI ワークフローと Issue テンプレート
├── .env.example               環境変数テンプレート
├── build.sh / build.bat       venv + editable インストール + コンパイルチェック
├── run.sh / run.bat           標準 GUI / CLI エントリポイント
├── run-gui.vbs                コンソールなしの Windows GUI ランチャー
├── bump_version.py            明示的なバージョン更新
├── bump_manifest_version.py   hydra-umc.project.json のバージョンをネイティブ版と同期(--sync)
├── CHANGELOG.md               各バージョンの変更点
├── build-test.sh              変更を伴わないビルド確認
├── hydra-umc.project.json     マニフェスト：バージョン、成熟度、ファミリー
├── pyproject.toml             パッケージのメタデータ
└── test.sh                    テストを実行
```

</details>

## 🗺️ ロードマップと既知の制限

**現時点の既知の制限**

- パッケージ化された独立の GUI 実行ファイル（PyInstaller、HYDRA-UMC-SUITE 自身の `build_exe.bat`/`.sh` の慣例と一致）——`pip`/venv のステップを一切必要としないダブルクリックインストールのため。現在の GUI は、CLI と同様にまず `./build.sh` を必要とします。
- オプションのプロジェクトごとの依存関係の事前チェック（`install` が途中で失敗する前に、不足しているツールチェーン——Rust/Go/Android SDK/Flutter が未インストールであること——を報告）。
- HYDRA-UMC/URTC 自身のマルチバイナリファームウェアのコンポーネントごとの追跡（第 3 節の「既知の簡略化」を参照）、今日追跡している単一の代表的コンポーネントを超える実際の必要性が生じた時点で。

## 🌍 言語

この README とリポジトリの文書は、英語・スペイン語・ドイツ語・フランス語・イタリア語・日本語・中国語・ポルトガル語（ポルトガル）の 8 言語で提供されています。8 つのファイルは同時に書かれ、同じ節と同じリンクを持つことを CI が確認します。

## 🔗 関連プロジェクト

本プロジェクトは、同じ作者(JuanenRac / Electro Hobby 3D)による HYDRA-UMC ロボティクスエコシステムの一部です。リクエストが実はこの中のどれかについてのものである可能性があるため、知っておく価値があります。

**直接関連**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — ロボットアームのマザーボードの設計——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括することを目指す(ファームウェアは初期段階で、実装済みの基板はまだない)。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数のサーバーを同時に扱えるデスクトップ(PySide6)スウォームコマンドセンター、スタンドアロン実行ファイルとしてパッケージ化 ——セルコントローラーと並行して動作することを意図した、もう一つのスタンドアロン Python ツールであり、役割上最も近い兄弟にあたる(CM5 側に特化したユーティリティであり、ロボット制御パス自体の一部ではない)。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — 新しいCM5イメージを構築する際、独自にGitHubエコシステムを検出するための実際のライブラリとしてこのプロジェクトに依存しており、独立して乖離しうる第二の実装を持たない。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 保守インシデントコーディネーター: 低権限のエッジ役割がサニタイズされたインベントリ/ヘルスのスナップショットを収集し、コントロールプレーン役割がそれを読み取り専用でレンダリングして AI プロバイダーに診断の提案を依頼します - パッチを適用することも、何かをデプロイすることも決してありません。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 再現可能な開発ホスト（Raspberry Pi 5 / CM5）。エコシステムのソースコードを保管し、永続キューのもとで境界の明確なビルド/テストタスクを実行する。運用中の CM5 とは明確に異なる、開発専用の役割。

**エコシステムの他のプロジェクト**

*コアハードウェア&プラットフォーム*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層——読み取り専用エージェント、検証済み設定/プロファイル、WiFi 初回接続プロビジョニング。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — すべてのブリッジが自身のコマンドを検証する共有 JSON-Schema 契約とソフトウェアのジョブゲート境界(認証済みの安全機能ではない)。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 外部マシン用コネクタのための宣言的アダプターマニフェストのレジストリとバリデーター。SDK 自身の契約という発想を外部マシンにまで拡張し、産業用ゲートウェイ系のプロジェクトを置き換えることはありません。

*コアバックエンド&クライアント*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する、本物のヘッドレスバックエンド(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット 3D 可視化を備えたウェブ制御ダッシュボード。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 本体搭載の 7 インチ DSI タッチスクリーン向けネイティブタッチ UI、CM5 自体に組み込み。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログへ送信するデスクトップ用グラフィカル URDF 作成/編集ツール。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — HYDRA-UMC-EDITOR-URDF も編集する同じモデルカタログ内で、実在するパーツを変換/置換/削除/追加するデスクトップ STL モデルエディタ。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界(エミュレートしたフリートに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター(エミュレーターに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界(エミュレーターに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — キー/筐体/インターロックの GPIO 信号 3 系統を読み取るレーザーセルのコーディネーター(模擬チップに対してのみテスト済み。レーザーの武装や発射はできない)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピックアンドプレースの基板フローを安全に統括する高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際にゲート制御されたジョブコマンドを持つ、Moonraker/Klipper 3D プリンター向けの安全な調整境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 遅延インポートの rclpy ROS 2 トランスポートを持つコーディネーター(ROS 2 環境ではまだ実行していない)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界(エミュレーターに対してのみテスト済み)。

*ビジョン AI ノード(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 ビジョンパイプラインの統合ハブ、段階ごとの実際のハードウェア準備状況チェック付き。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を持つ、実際の GStreamer パイプライン + MediaMTX 設定生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ゾーン状態を条件に承認する Position-Based Visual Servoing 補正則。カメラによる姿勢推定はまだない。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — ファイルから物体位置を受け取る、ゾーン侵入・キャリブレーション鮮度・E-STOP 要求の v0 ロジック。検出器は接続されておらず、物理 E-STOP もまだ配線されていない。

*コグニティブ AI ノード(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10 コグニティブパイプライン(LLM/VLA/音声オーケストレーション)の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 確認ゲート付きの限定的な Watch リレーを備えた、実際の音声フロントエンド(VAD + 意図解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味的エラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — エコシステム自身のための、ローカルでポリシーゲート付きのAIメンテナンス技術者 — 観察、診断し、修正を提案する;最上位の2つのリスクレベルは意図的にまだ実装されていない。

*オーケストレーション&スウォーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッションステートマシンを持つ統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際の HTTP API 上に構築された、優先度ベースの実際のジョブキュー(重複排除付き)。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフとアイデンティティ不一致検出を備えた、実際の gRPC ベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/ワークスペース衝突検証を備えた、実際の RRT ベースの 3D 経路プランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 複数セルの収束についてプロパティテストされた、実際の CRDT LWW-Element-Map 状態同期。

*デジタルツイン&シミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を持つ、デジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実機の間にソフトウェアの衝突インターロックを備えたハードウェア・イン・ザ・ループのルーター(実機なしでテスト済み)。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 実際の URDF サブセットに対する、実際の順運動学と関節限界検証。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — YOLO/COCO アノテーションのエクスポート機能を持つ、実際のプロシージャル 2D シーンジェネレーター。

*データ&分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 実際の取り込み/クエリ HTTP API を備えた、実際の sqlite3 ベースの時系列ストア。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — ドリフト監視を備えた、実際の FFT + 統計ベースラインによる異常検知器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — DATALAKE の履歴に対する実際の OEE/稼働率計算、再現可能な CSV エクスポート付き。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — シーケンス重複排除機能を備えた、DATALAKE への実際の CAN/WebSocket 取り込みパイプライン。

*産業用ゲートウェイ*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 実際のコマンド許可リスト/バックプレッシャー層を持つ、産業用プロトコルへ中継する統合ハブ。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 実際のバイナリプロトコルクライアントセッションで検証された、実際の OPC-UA アドレス空間。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — クライアント単位のオプション認証とトピック ACL を備えた、実際の MQTT ブローカー。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 縮退モード出力を備えた、実際の MTConnect `/probe` および `/current` XML エンドポイント。

*補完ツール&エコシステム運用*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 誠実な統計フォールバックを備えた、DATALAKE/ANOMALY-DETECTOR 上のスマートサマリーと異常ハイライトパネル。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際の安定した終了コード契約を持つフリート CLI、HYDRA-UMC-SERVER 自身の API の本物のライブクライアント。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 触覚アラートのパターンとペアリング済みスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ(物理的なウォッチではまだ実行していない)。

## 📚 ドキュメント

さらに読むには：

* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — すべての `--cli` サブコマンド、実際にインストールされた環境から取得した実際の出力、そして終了コード契約。
* **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — Qt Quick/QML デスクトップクライアントがどのように構成されているか、そして `--cli` と同じバックエンドの上に立つ実際のコントロールサーフェスであり続ける理由(2つ目の実装ではない)。
* [エコシステムのセキュリティ基準](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [エコシステムの脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [このリポジトリのライセンス](LICENSE.md)

## 🤝 コントリビュートとコミュニティ

* プルリクエストの前に `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（または `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）を実行してください。`CI_VALIDATION=PASS` と表示される必要があります。この確認に `build.sh` や `build.bat` は使わないでください。ビルドは検査ではありません。
* 8 つの README は HYDRA-UMC-DOCS の 1 つのソースから書かれます。手で編集しないでください。ソースを変更し、`tools/make_readmes.py` で書き直します。
* 実行していないことを README に書かないでください。事実であれば「シミュレーションのみ」「実機では未確認」と書きます。
* [CONTRIBUTING.md](CONTRIBUTING.md)、[行動規範](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md)、[SUPPORT.md](SUPPORT.md) を参照してください。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE).
