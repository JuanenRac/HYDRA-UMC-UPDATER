<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b></p>

### 📦 HYDRA-UMC/URTC エコシステム全体の検出、インストール、手動更新

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only CLI core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
</p>

> **ビジュアルデスクトップモード：** 既定のデスクトップ画面は、任意の
> `PySide6` GUI ランタイムを通じて **Qt Quick / QML** を使用します。更新コアと
> `--cli` はヘッドレス CM5 向けに標準ライブラリのみを維持します。
>
> **Windows 起動と証跡：** `run-gui.vbs` をダブルクリックするか、引数なしの
> `run.bat` を実行するとコンソールなしの GUI が起動します。更新パネルには、
> 実際の事前確認、ソース更新、マニフェスト検証、ビルドテスト、完了のチェックポイントと
> 取得した証跡を表示します。`run.bat --cli ...` は診断用ターミナルを維持します。
> インストールはチェックアウトがない場合だけ、更新は GitHub が新しい場合だけ有効です。
> 承認済み操作中はチェックポイントがプロジェクト操作を置き換え、別のプロジェクトを
> 選ぶと操作を復元します。
> **不足分をすべてインストール**と**古い項目をすべて更新**は、同じ実際の状態と
> 安全経路に基づく、別途確認される順次一括アクションです。

---

## 1. 🛠️ 技術概要

HYDRA-UMC-UPDATER は、小さなツールです——デフォルトはウィンドウ付き
GUI、`--cli` で完全な CLI が利用可能——実際の CM5 本体上、または開発者
自身の Windows/Linux/macOS マシン（同じ方法でチェックアウトされた任意の
ワークスペース）で実行されることを意図しており、エコシステムの他の 54
プロジェクトそれぞれについて 3 つの問いに答えます：

1. **ここに実際に何がインストールされていて、そのバージョンは何か？**
2. **GitHub 上に公開されている最新バージョンは何か？**
3. **もし GitHub の方が新しければ、そのプロジェクト 1 つだけを、手動で更新させてほしい。**

最後のポイントは意図的であり、譲れないものです：このツールは、1 回の
コマンドで 2 つ以上のプロジェクトを更新することは決してなく、また自ら
の意思で自動的に更新することも決してありません。ロボット制御セルは、
一晩のうちに勝手に自動更新されてほしいものではありません——実際の更新
はすべて、1 つの指定されたプロジェクトに対して人間がトリガーしたコマ
ンド（あるいは GUI のテーブルで 1 行を選択してのボタンクリック）であ
り、その結果は次のプロジェクトに触れる前に確認できます。

54 プロジェクトのすべてが CM5 本体に属するわけでもありません——ほとんど
の URTC プレフィックスのリポジトリと一部の HYDRA-UMC のリポジトリは、
開発者自身の PC から実行されるツールです（ファームウェアはワークステー
ションからコンパイル/書き込まれるのであって、セル上でビルドされるので
はありません）、あるいはスマートフォン/ウォッチにインストールされる
アプリです。`registry.py` 自身の `deploy` フィールドがどれがどれかを
記録しており（第 3 節参照）、GUI のプロジェクトテーブルはそれに基づい
てフィルタリングします——Linux（実際の CM5 自身の OS）上で実行されて
いることを検知した場合はデフォルトで「CM5 のみ」、Windows/macOS では
「すべて表示」となります。

```
$ hydra-umc-updater --cli status
Workspace root: /home/pi/HYDRA-UMC
Checking GitHub... 54/54
PROJECT                        STACK       LOCAL     GITHUB    STATE
--------------------------------------------------------------------
HYDRA-UMC                      firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER               node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO               node        0.0.8     0.1.3     OUTDATED
...
54/54 installed, 2 outdated

$ hydra-umc-updater --cli update HYDRA-UMC-SERVER
Updating HYDRA-UMC-SERVER into /home/pi/HYDRA-UMC ...
OK  Pulled latest into /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER
OK  build.sh completed successfully.
```

`hydra-umc-updater` を引数なしで実行する（またはダブルクリックする）
と、同じ情報がウィンドウ内に表示されます——ソート可能なプロジェクト
テーブル、デプロイターゲットフィルター、そして選択された行に対する
インストール/更新ボタンです。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="HYDRA-UMC-UPDATER の実際のデスクトップ概要" width="100%">
</p>

## 2. 🔄 チェック/更新が実際にどう機能するか

- **バージョンの取得元**：このエコシステム自身の「オドメーター」式の自動インクリメント慣例（実際のビルドのたびに、ソースファイル*内部*に存在するバージョン番号が増加します——プロジェクトの技術スタックに応じて `pyproject.toml`、`Cargo.toml`、`version.go`、`package.json`、`version.properties`、`pubspec.yaml`、またはファームウェアの `#define` のいずれか）は、そのインクリメントに対して git タグや GitHub リリースを一度も作成したことがありません。そのため本ツールは、各プロジェクト自身の `bump_version.py`/ビルドスクリプトが既に書き込んでいる*その同じ*ファイルを、GitHub の生コンテンツホスト経由でリポジトリのデフォルトブランチから直接読み取ります——Releases API ではありません。それを使うと、すべてのプロジェクトが「リリースが一切ない」と報告されてしまいます。
- **ローカル検出**：既知の 54 プロジェクトそれぞれについて、そのプロジェクトと完全に同じ名前のディレクトリがワークスペースルート下に存在するかを確認します（標準的なエコシステムのレイアウト——すべてのプロジェクトを兄弟ディレクトリとして配置する、`build-frontend.sh`/HYDRA-UMC-SUITE 自身の検出ロジックが既に前提としているのと同じ形）。存在する場合、そのプロジェクト*自身*の同じバージョンファイルのローカルコピーを読み取ります。
- **単一の解析実装**（`version_parse.py`）が、ローカル読み取りと GitHub 取得の間で共有されているため、ローカルのチェックアウトと GitHub からの取得が、2 つの独立して食い違っていく正規表現によって別々に解釈されることは決してありません。
- **インストール/更新**：`git clone`（インストール）または `git pull --ff-only`（更新——強制リセットは決して行わないため、実際のローカルの編集は、破棄されるのではなく明確に失敗します）を実行し、その後、そのプロジェクトが実際に持っている `build.sh`/`build.bat`（または既知の同等物——第 3 節参照）のいずれかを実行します。本ツールは、プロジェクト自身のビルド手順を再実装することは決してありません——理由は第 3 節を参照してください。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="HYDRA-UMC-UPDATER のインストールまたは更新中の実際のチェックポイント" width="100%">
</p>

## 3. 🧱 アーキテクチャと設計上の決定

- **標準は Qt Quick GUI、ヘッドレス向けは `--cli`。** `main.py` は任意の PySide6
  ランタイムを読み込む前に `--cli` を確認します。CLI は画面やデスクトップ依存のない
  CM5 で動作し、引数なしでは利用可能な場合に QML を起動します。Tkinter は一時的な
  互換フォールバックとしてのみ残ります。
- **ウィンドウ表示のGUIは実在し、7言語対応の多言語です(`i18n.py`)—— `--cli` は意図的にそうなっていません。** 実在するすべてのウィジェットは、言語 `Combobox`(en/es/fr/it/de/zh/ja、公開ダッシュボードとすべてのREADMEが提供するのと同じ7言語)から保存された設定またはOS自身のロケールに基づいて検出され、リアルタイムでラベルが再表示されます。プロジェクト/ファミリー名と各プロジェクト自身の実際の `notes`/`tech` テキストは未翻訳のままです—— `registry.py` がそれらの唯一の信頼できる情報源であり、7つの並行した実際のエンジニアリングドキュメントのコピーはそれを妨げてしまいます。`--cli` の出力は意図的に英語のみのままです:これはスクリプト化/パイプ処理を想定しており、安定してgrep可能なテキストがローカライゼーションよりも重要な場面のためです。
- **`deploy` は制限ではなく分類です。** 54 のプロジェクトすべてを「CM5 に属するもの」として扱うのは誤りでした——ファームウェアリポジトリは PC からコンパイル・書き込みされます（CM5 は CAN-OTA 経由で最終的なバイナリだけを必要とし、このリポジトリ自身のソースコードを必要とすることは決してありません）。また、いくつかのツール（URTC-FLASHER、HYDRA-UMC-SUITE、HYDRA-UMC-TOOL-CLI……）は、セル自体の内部ではなく、オペレーター自身のワークステーションで実行されることを意図しています。`registry.py` の `deploy` フィールド（"cm5" / "user-pc" / "mobile" / "wearable"）がそれを記録しており、GUI のフィルターはそれを妥当な出発点として使用します——厳格な制限ではありません。なぜなら、この同じツールは開発者自身の PC 上でも実行されることを意図しており、その場合は 54 のすべてが検査対象になり得るからです。
- **本ツールには技術スタックごとのビルドロジックがありません。** このエコシステムは 7 つのツールチェーン（Python、Rust、Go、Node/TS、Android/Kotlin、Flutter、ARM ファームウェア）にまたがっています。`npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` などを*ここで*再実装すると、各プロジェクトのビルド方法を知っていると主張する 2 つ目の場所ができてしまい、そのプロジェクト自身の実際の（そして既に正しい）`build.sh`/`.bat` から必ず食い違っていきます。代わりに `install.py` は、既知のビルドスクリプト名（`build.sh`、`build_firmware.sh`、`build_exe.sh`、`build-android.sh`、およびそれらの `.bat` 相当版——54 のプロジェクト全体で実際に使用されている名前）を探し、実際に存在するものを実行します。
- **Releases API ではなく GitHub の生コンテンツを使用。** 上記の第 2 節を参照——このエコシステムのバージョン管理慣例はタグ/リリースを一切作成しないため、ここで Releases API を使うことは、単に不便なだけでなく、積極的に間違っています。
- **一時的なネットワーク障害には本物の再試行があるが、確定的な応答には決してない。** 実際の GitHub へのリクエストはすべて（`github_client.py` の `_urlopen_with_retries`）、接続がまったく応答を得られなかった場合（DNS/タイムアウト/リセット）に限り、バックオフを伴って最大 3 回まで再試行します。GitHub が実際に返した本物の HTTP ステータス——404、403、500——は決して再試行されません。GitHub はすでに応答しており、再度叩いても同じ結果のためにレート制限をさらに消費するだけだからです。
- **不正な形式のリモートカタログは大きく失敗するが、1 つの不正なプロジェクトはそうではない。** GitHub のリポジトリ一覧そのものに到達できない、または解析できない場合、`discover_remote_projects()` は例外を送出します——`gui.py` と `main.py` はどちらもすでにこれを捕捉し、壊れた、あるいは空のスキャンを表示する代わりに、ローカルで発見されたプロジェクト一覧にフォールバックします。対照的に、単一リポジトリの不正な形式のマニフェストは、そのスキャン自身の `errors` リストに隔離され、残りの発見処理を決して中断させません——実際のフィクスチャサーバーを使ったテスト（`tests/test_github_client.py`）が両方の経路を証明しています。
- **`install`/`update` は常に明示的な 1 つのプロジェクト名を必要とします。** 「すべてを更新する」というサブコマンドは存在せず、これは欠けている機能ではなく設計上の決定です——実際のロボットの艦隊は、無人のまま自動更新させておくべきものではありません。`status` は何が古くなっているかを表示します。実際にどれに触れるかは人間が選びます。
- **標準ライブラリのみ。** GitHub の取得には `urllib`（`github_client.py`）、git/ビルドスクリプトの呼び出しには `subprocess`（`install.py`）を使用し、それ以外は何もありません——他の*すべての*プロジェクトの依存関係を健全に保つ責任を持つツール自体が依存関係を持たないでいることは、意図的なものです。
- **既知の簡略化**：HYDRA-UMC と URTC は、実際には複数コンポーネントからなるファームウェアリポジトリです（それぞれ 6 個と 4 個の独立してバージョン管理されるバイナリを持ちます——それぞれの `VERSION_CHECKLIST.txt`/`build_firmware.sh` を参照）。単一の「これが」バージョン番号というものは存在しません。`registry.py` はリポジトリごとに 1 つの代表的なコンポーネントのみを追跡します——「このリポジトリはおおむね最新か」に答えるには十分ですが、実際のフラッシュ用の `build_firmware.sh` 自身の `firmware_manifest.json` の代替にはなりません。

## 📂 リポジトリ構成

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py         # ProjectEntry - 静的カタログなし。各リポジトリ自身のマニフェストから検出時に構築
│   ├── project_manifest.py # リポジトリ自身の hydra-umc.project.json を読み取り/検証
│   ├── ecosystem_catalog.py # JuanenRac エコシステムの公開検出カタログのパーサー
│   ├── version_parse.py   # ローカル+GitHub 共通の単一の正規表現抽出実装
│   ├── detect.py          # ワークスペースルートをスキャンし、何がインストールされているかを検出
│   ├── github_client.py   # 生コンテンツの並行取得 + 一時的なネットワークエラーに対する本物の再試行/バックオフ
│   ├── install.py         # git clone/pull + プロジェクト自身のビルドスクリプトへの委譲
│   ├── i18n.py             # 実際の完全なGUI翻訳(7言語)
│   ├── qt_gui.py           # 実際の検出/更新サービスへの Qt Quick ブリッジ
│   ├── qml/Main.qml        # テーマ、チェックポイント、About を持つデスクトップ画面
│   ├── gui.py              # PySide6 がない場合の Tkinter 互換フォールバック
│   └── main.py             # ディスパッチ：デフォルトは GUI、--cli で status/install/update
├── tests/                  # 実際のテスト：github_client、i18n、install、project_manifest、registry
├── docs/
│   ├── CLI_REFERENCE.md     # コマンドリファレンス
│   └── QML_DESKTOP_GUI.md   # Qt Quick GUIのアーキテクチャ
├── images/                 # メディア、アプリアイコン、インターフェースのスクリーンショット
├── tools/
│   ├── build_test.py        # バージョンを増やさないビルドチェック
│   ├── ci_validate.py       # CI が使用するマニフェスト/CHANGELOG/ドキュメント検証
│   ├── generate_app_icon.py # 公開HYDRA-UMC SVGをWindowsが使用するアイコンにレンダリング
│   ├── migrate_project_manifests.py  # 一度限りのマニフェスト移行後のワークスペース監査
│   └── validate_project_manifests.py # リポジトリ自身のマニフェスト+ネイティブビルドバージョンを検証
├── .env.example            # 環境変数テンプレート
├── build.sh / build.bat    # venv + editable インストール + コンパイルチェック
├── run.sh / run.bat        # 標準 GUI / CLI エントリポイント
├── run-gui.vbs             # コンソールなしの Windows GUI ランチャー
├── bump_version.py         # エコシステム全体で統一されたオドメーター式インクリメント（pyproject.toml + __init__.py）
└── bump_manifest_version.py # hydra-umc.project.json のバージョンをネイティブ版と同期(--sync)
```

## ⚙️ ビルドと実行

```bash
chmod +x build.sh   # 初回のみ
./build.sh          # .venv を作成、pip install -e .、すべてをコンパイルチェック
./run.sh                              # ウィンドウ付き GUI（デフォルト）
./run.sh --cli status                 # 何がインストールされているか、ローカル対 GitHub のバージョン
./run.sh --cli status --offline       # 同上、GitHub チェックをスキップ
./run.sh --cli install <PROJECT-NAME> # まだインストールされていない 1 プロジェクトをクローン + ビルド
./run.sh --cli update  <PROJECT-NAME> # 既にインストールされている 1 プロジェクトをプル + 再ビルド
```

Windows では：先に `build.bat`、その後 `run.bat`（GUI）/ `run.bat
--cli status` / `run.bat --cli install <name>` / `run.bat --cli
update <name>`。

優先 GUI にはオプションの Qt ランタイムが必要です（`pip install -e ".[gui]"`;
`build.bat`/`build.sh` は既にこれを導入します）。`--cli` には GUI 依存がなく、
ヘッドレス CM5 の正しい入口です。Qt がない場合、古い Tkinter ウィンドウは
互換フォールバックとしてのみ残ります。

**トラブルシューティング**

- `status` が、あるプロジェクトのローカルまたは GitHub バージョンに `?` を表示する：そのバージョンファイルは存在しますが、そのプロジェクト自身の慣例が `registry.py` の最終更新以降に変わっています——そのプロジェクトの実際の現在のバージョンファイルと照らし合わせて、`registry.py` の該当エントリを確認してください。
- `status` が GitHub についてエラーを表示せずに `-` を表示する：（`--offline` なしで）`status` を実行してください——`-` は GitHub チェックが完全にスキップされた場合にのみ表示されます。
- `install`/`update` が「build.sh/.bat が見つかりません」で失敗する：そのプロジェクトは、本ツールがまだ認識していないビルドスクリプト名を使用しています——実際の名前についてはそのプロジェクト自身の README を確認し、`install.py` 自身の `BUILD_SCRIPT_CANDIDATES_*` リストへの追加を検討してください。
- `git pull --ff-only` が失敗する：ローカルのチェックアウトに未コミットの変更があるか、履歴が分岐しています——`update` を再試行する前に、（そのプロジェクト自身のディレクトリで `git status` を実行して）手動で解決してください。本ツールはチェックアウトを強制リセットすることは決してありません。

## 🚀 ロードマップ

- パッケージ化された独立の GUI 実行ファイル（PyInstaller、HYDRA-UMC-SUITE 自身の `build_exe.bat`/`.sh` の慣例と一致）——`pip`/venv のステップを一切必要としないダブルクリックインストールのため。現在の GUI は、CLI と同様にまず `./build.sh` を必要とします。
- オプションのプロジェクトごとの依存関係の事前チェック（`install` が途中で失敗する前に、不足しているツールチェーン——Rust/Go/Android SDK/Flutter が未インストールであること——を報告）。
- `status` 用の `--json` 出力モード、これに対するスクリプト化のため。
- HYDRA-UMC/URTC 自身のマルチバイナリファームウェアのコンポーネントごとの追跡（第 3 節の「既知の簡略化」を参照）、今日追跡している単一の代表的コンポーネントを超える実際の必要性が生じた時点で。

## 🔗 関連プロジェクト

本プロジェクトは、同じ作者(JuanenRac / Electro Hobby 3D)による HYDRA-UMC ロボティクスエコシステムの一部です。リクエストが実はこの中のどれかについてのものである可能性があるため、知っておく価値があります。

**直接関連**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 実際のロボットアームのマザーボード——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括 ——本ツールが実際の CM5 ハードウェア上でインストール済み・最新の状態に保つことを目的とする、フラッグシップのマルチロボットセルコントローラー。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数のサーバーを同時に扱えるデスクトップ(PySide6)スウォームコマンドセンター、スタンドアロン実行ファイルとしてパッケージ化 ——セルコントローラーと並行して動作することを意図した、もう一つのスタンドアロン Python ツールであり、役割上最も近い兄弟にあたる(CM5 側に特化したユーティリティであり、ロボット制御パス自体の一部ではない)。

**エコシステムの他のプロジェクト**

*コアハードウェア&プラットフォーム*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層——読み取り専用エージェント、検証済み設定/プロファイル、WiFi 初回接続プロビジョニング。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — すべてのブリッジが自身のコマンドを検証する共有 JSON-Schema 契約と安全ゲートの境界。

*コアバックエンド&クライアント*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する、本物のヘッドレスバックエンド(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット 3D 可視化を備えたウェブ制御ダッシュボード。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 本体搭載の 7 インチ DSI タッチスクリーン向けネイティブタッチ UI、CM5 自体に組み込み。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログへ送信するデスクトップ用グラフィカル URDF 作成/編集ツール。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 実際の VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 実際の GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 実際の Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 実際のキー/筐体/インターロック GPIO セーフガード 3 系統を読み取る、レーザーセルの安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピックアンドプレースの基板フローを安全に統括する高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際にゲート制御されたジョブコマンドを持つ、Moonraker/Klipper 3D プリンター向けの安全な調整境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 実際の遅延インポート rclpy ROS 2 トランスポートを持つ安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 実際の MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界。

*URTC ツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的な Universal Robot Tool Controller 基板向けファームウェア、CAN バス経由の 25 以上のツールプロファイル。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTC 基板用のデスクトップ GUI 書き込みツール、CAN-OTA およびフルチップ SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTC 基板向けのデスクトップ CAN バスライブ診断ツール、ツールプロファイルごとに 1 パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API を使ったブラウザベースの URTC-TESTER の代替、ローカルインストール不要。

*ビジョン AI ノード(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 ビジョンパイプラインの統合ハブ、段階ごとの実際のハードウェア準備状況チェック付き。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を持つ、実際の GStreamer パイプライン + MediaMTX 設定生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 上流のゾーン状態に応じて安全ゲート制御される、実際の Position-Based Visual Servoing 補正則。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — キャリブレーションの鮮度を強制する、実際のゾーン侵入チェックと E-STOP 要求。

*コグニティブ AI ノード(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10 コグニティブパイプライン(LLM/VLA/音声オーケストレーション)の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 確認ゲート付きの限定的な Watch リレーを備えた、実際の音声フロントエンド(VAD + 意図解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味的エラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。

*オーケストレーション&スウォーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッションステートマシンを持つ統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際の HTTP API 上に構築された、優先度ベースの実際のジョブキュー(重複排除付き)。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフとアイデンティティ不一致検出を備えた、実際の gRPC ベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/ワークスペース衝突検証を備えた、実際の RRT ベースの 3D 経路プランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 複数セルの収束についてプロパティテストされた、実際の CRDT LWW-Element-Map 状態同期。

*デジタルツイン&シミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を持つ、デジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実際のハードウェアの間でコマンドをルーティングする、実際のハードウェア・イン・ザ・ループ安全インターロック。
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 実際の触覚アラートとペアリングされたスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際の工具 ID デコードと Smart Idle 予熱ロジックを備えた、基板搭載ラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB 検査ツールヘッド向けの、ファームウェアと実際の Python ビジョンコンパニオン。

---

## 📚 ドキュメント & コミュニティ

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — すべての `--cli` サブコマンド、実際にインストールされた環境から取得した実際の出力、そして終了コード契約。
- **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — Qt Quick/QML デスクトップクライアントがどのように構成されているか、そして `--cli` と同じバックエンドの上に立つ実際のコントロールサーフェスであり続ける理由(2つ目の実装ではない)。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— プルリクエストのための技術スタックとコーディング指針。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— このコミュニティで期待される行動規範。
- **[SECURITY.md](SECURITY.md)** —— 脆弱性の報告方法と、このプロジェクトの実際のセキュリティ重点領域。
- **[SUPPORT.md](SUPPORT.md)** —— 質問の投稿先とバグの報告先。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 ライセンス

GPL-3.0（ソフトウェア）/ CC BY-SA 4.0（ドキュメント）—— 詳細は
[LICENSE.md](LICENSE.md) を参照してください。
