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
ワークスペース）で実行されることを意図しており、エコシステムの他の 44
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

44 プロジェクトのすべてが CM5 本体に属するわけでもありません——ほとんど
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
Checking GitHub... 44/44
PROJECT                        STACK       LOCAL     GITHUB    STATE
--------------------------------------------------------------------
HYDRA-UMC                      firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER               node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO               node        0.0.8     0.1.3     OUTDATED
...
44/44 installed, 2 outdated

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
- **ローカル検出**：既知の 44 プロジェクトそれぞれについて、そのプロジェクトと完全に同じ名前のディレクトリがワークスペースルート下に存在するかを確認します（標準的なエコシステムのレイアウト——すべてのプロジェクトを兄弟ディレクトリとして配置する、`build-frontend.sh`/HYDRA-UMC-SUITE 自身の検出ロジックが既に前提としているのと同じ形）。存在する場合、そのプロジェクト*自身*の同じバージョンファイルのローカルコピーを読み取ります。
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
- **`deploy` は制限ではなく分類です。** 44 のプロジェクトすべてを「CM5 に属するもの」として扱うのは誤りでした——ファームウェアリポジトリは PC からコンパイル・書き込みされます（CM5 は CAN-OTA 経由で最終的なバイナリだけを必要とし、このリポジトリ自身のソースコードを必要とすることは決してありません）。また、いくつかのツール（URTC-FLASHER、HYDRA-UMC-SUITE、HYDRA-UMC-TOOL-CLI……）は、セル自体の内部ではなく、オペレーター自身のワークステーションで実行されることを意図しています。`registry.py` の `deploy` フィールド（"cm5" / "user-pc" / "mobile" / "wearable"）がそれを記録しており、GUI のフィルターはそれを妥当な出発点として使用します——厳格な制限ではありません。なぜなら、この同じツールは開発者自身の PC 上でも実行されることを意図しており、その場合は 44 のすべてが検査対象になり得るからです。
- **本ツールには技術スタックごとのビルドロジックがありません。** このエコシステムは 7 つのツールチェーン（Python、Rust、Go、Node/TS、Android/Kotlin、Flutter、ARM ファームウェア）にまたがっています。`npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` などを*ここで*再実装すると、各プロジェクトのビルド方法を知っていると主張する 2 つ目の場所ができてしまい、そのプロジェクト自身の実際の（そして既に正しい）`build.sh`/`.bat` から必ず食い違っていきます。代わりに `install.py` は、既知のビルドスクリプト名（`build.sh`、`build_firmware.sh`、`build_exe.sh`、`build-android.sh`、およびそれらの `.bat` 相当版——44 のプロジェクト全体で実際に使用されている名前）を探し、実際に存在するものを実行します。
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
│   ├── registry.py        # 44 のプロジェクト：リポジトリ、技術スタック、バージョンファイル、パターン、デプロイターゲット
│   ├── version_parse.py   # ローカル+GitHub 共通の単一の正規表現抽出実装
│   ├── detect.py          # ワークスペースルートをスキャンし、何がインストールされているかを検出
│   ├── github_client.py   # 生コンテンツの並行取得 + 一時的なネットワークエラーに対する本物の再試行/バックオフ
│   ├── install.py         # git clone/pull + プロジェクト自身のビルドスクリプトへの委譲
│   ├── qt_gui.py           # 実際の検出/更新サービスへの Qt Quick ブリッジ
│   ├── qml/Main.qml        # テーマ、チェックポイント、About を持つデスクトップ画面
│   ├── gui.py              # PySide6 がない場合の Tkinter 互換フォールバック
│   └── main.py             # ディスパッチ：デフォルトは GUI、--cli で status/install/update
├── build.sh / build.bat    # venv + editable インストール + コンパイルチェック
├── run.sh / run.bat        # 標準 GUI / CLI エントリポイント
├── run-gui.vbs             # コンソールなしの Windows GUI ランチャー
└── bump_version.py         # エコシステム全体で統一されたオドメーター式インクリメント（pyproject.toml + __init__.py）
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

本ツールの目的全体は、エコシステム内の他のすべてのプロジェクトを管理
することです——ここに 44 すべてを列挙するのではなく（権威ある正確な
リストは `registry.py` を参照）、役割上最も近い 2 つを挙げます：

- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— 本ツールが実際の CM5 ハードウェア上でインストール済みかつ最新の状態に保つことを目指す、フラッグシップのマルチロボットセルコントローラー。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** —— セルコントローラーと並行して実行されることを意図した、もう 1 つの独立した Python ツールで、役割上最も近い同族プロジェクト（ロボット制御パス自体の一部ではなく、CM5 側に特化したユーティリティ）。

**エコシステムのその他の部分**（本ツールが検出/インストール/更新できる
すべてのプロジェクト）：最初の 12 プロジェクト（ファームウェア、サーバー、
モバイル/デスクトップアプリ）、視覚/認知 AI ノード、Rust のオーケストレー
ション/シミュレーションサービス、Go のインフラ/CLI ツール、Node の産業用
ゲートウェイ、そして URTC の工具ヘッドファームウェア/PC ツール——完全な
最新のリストは `registry.py` 自身のグルーピング（本 README 自身のディレ
クトリ構成コメントと対応）を参照してください。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 ライセンス

GPL-3.0（ソフトウェア）/ CC BY-SA 4.0（ドキュメント）—— 詳細は
[LICENSE.md](LICENSE.md) を参照してください。
