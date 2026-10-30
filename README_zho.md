<!-- =============================================================================
HYDRA-UMC-UPDATER - Installs and updates the HYDRA-UMC projects
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 📦 HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📦 检测、安装并手动更新整个 HYDRA-UMC 生态系统

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="Core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="Desktop">
  <img src="https://img.shields.io/badge/Tests-163%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.5.0-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

> **安全与安防现状:**本生态系统不是经认证的安全系统。目前尚无硬件 E-STOP 通路,没有由固件强制执行的限位或联锁,也没有经过验证的运动指令;固件映像使用 CRC-32 和 Ed25519 签名校验,发布构建会拒绝已公开的开发密钥(中继之后的工具头和扩展板仍运行 URTC 的引导程序,它们使用共享密钥的 HMAC-SHA256 而不是签名);TLS 与双向 TLS 均为可选项,默认关闭;自制电路板尚未组装或测试。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.5.0` |
| 成熟度 | 成熟 |
| 测试 | 163 (`python -m pytest -q tests`) |
| 技术栈 | Python 3.10+ / PySide6 / Qt Quick (QML) / Tkinter (legacy fallback) / Git / GitHub raw content |
| 目标 | 使用者的电脑 |
| 真实硬件 | 不适用：这里的内容不在硬件上运行 |

**跳转：** [概述](#-概述) · [架构](#-架构) · [安全与防护](#-安全与防护) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [故障排除](#-故障排除) · [仓库结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟢 | 就其用途而言已完整且稳定；上面的诚实性检查列出了已知限制 |
| 测试 | 🟢 | 163 项自动测试，每次变更都会运行 |
| 真实硬件 | 🟢 | 不适用：这里的内容不在硬件上运行 |
| 文档 | 🟢 | 八种语言的 README，每次变更都会与清单核对 |

## 🎯 概述

HYDRA-UMC-UPDATER 是一个小型工具——默认为窗口化 GUI，通过 `--cli` 可
获得完整的 CLI——旨在运行在真实的 CM5 本机上，或运行在开发者自己的
Windows/Linux/macOS 计算机上（任何以相同方式检出的工作区），它为生态
系统中通过每个相邻检出自身的 `hydra-umc.project.json` 清单发现的
每一个其他真实项目都回答三个问题——这个数量本身在此从不写死，
因为它会随着生态系统一起增长：

1. **这里实际安装了什么，版本是多少？**
2. **GitHub 上发布的最新版本是什么？**
3. **如果 GitHub 上的版本更新，让我选择一个项目或已确认的顺序批量操作。**

最后一点是刻意为之、不容妥协的：本工具绝不会自行更改任何项目。对选定
项目的操作始终需要明确确认。GUI 还可以提供**安装全部缺失项目**或**更新
全部过期项目**；二者都是分别确认的顺序批量操作，并经过相同的清单、版本
和安全检查。不存在无人批准的夜间自动更新。确认对话框会按执行顺序列出该批量操作的确切项目。

发现的项目中也并非每一个都属于 CM5 本机——有些是开发者从自己的 PC 上运行的工具（固件是从工作站编译/刷写的，而非在单元本机上构建的），或是安装在手机/手表上的应用。每个项目自己的清单记录了它属于哪一种（见第 3 节），GUI 的项目表格可据此筛选——默认显示所有项目，因此更新器自身和 SDK 都不会被隐藏。

示例说明（下面的项目数量和每个版本号都是为了展示输出格式而虚构的，
并非真实捕获的执行结果——真实数量始终是 `registry.py` 当下实际发现的
数量，绝不是写死在本文档中的固定数字）：

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

不带任何参数运行 `hydra-umc-updater`（或直接双击它）会在窗口中打开同样
的信息——一个可排序的项目表格、一个部署目标筛选器，以及针对当前所选行
的安装/更新按钮。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="HYDRA-UMC-UPDATER 真实桌面总览" width="100%">
</p>

## 🧩 在 HYDRA-UMC 中的角色

**HYDRA-UMC-UPDATER** 在所运行的机器上查找、安装并更新 HYDRA-UMC 项目，手动且一次一个项目。新版本先在暂存文件夹中克隆并构建，然后才移入位置，旧版本保留为备份，每次尝试都会留下一行证据。它有命令行和桌面窗口，二者调用同一个核心。

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-UPDATER architecture" width="100%">
</p>

### 检查/更新实际是如何工作的

因此本工具直接通过 GitHub 的原始内容托管，读取每个项目自身的 `bump_version.py`/构建脚本已经在写入的那个*同一个*文件的仓库默认分支版本——而非 Releases API，后者会把每个项目都报告为"完全没有发布记录"。
- **本地检测**：对于每一个发现的项目，检查工作区根目录下是否存在一个与该项目名称完全一致的目录（标准的生态系统布局——每个项目作为同级目录，这正是 `build-frontend.sh`/HYDRA-UMC-SUITE 自身的发现逻辑已经假定的方式），如果存在，则读取该项目*自身*的本地版本文件副本。
- **单一解析实现**（`version_parse.py`）在本地读取和 GitHub 抓取之间共享，因此本地检出和 GitHub 抓取绝不会被两个独立漂移的正则表达式分别解读。
- **安装/更新**：`git clone`（安装）之后作为单独的一步再编译。更新一个已存在的检出则改为「通过验证实现原子性」：候选版本先被克隆、进行快进合并（绝不使用强制重置，因此真实的本地修改会明确失败，而非被丢弃），然后首先在一个完全独立的暂存克隆中编译/验证——只有当那次暂存编译真正成功时，实际安装才会被触碰（通过两次连续的目录重命名，之前的安装会被保留在 `<name>.backup-xxxxxxxx` 中，而不是被删除）。在最终提升之前的任何时刻发生编译失败、检出分叉/存在未提交修改、崩溃或磁盘写满，都会让之前的安装完全不受影响、继续保持可运行——详见 `install.py` 自身 `clone_or_pull` 的 docstring。暂存克隆自身的 git 远程仓库会在创建后立即恢复为真实的 GitHub 上游（否则一个普通的本地克隆会指向旧的安装路径，一旦被提升就会在不知不觉中终止所有未来的更新），并且已安装检出自身真实的本地数据（任何 git 视为未跟踪或被忽略的内容——`data/settings.json` 及类似文件，不包括可重新生成的构建产物）会在编译前被带入暂存克隆，这样一个项目自身真实的运行状态就能在更新后保留下来，而不是被困在保留的 `.backup` 检出中。无论哪种情况，只要该项目自身实际拥有 `build-test.sh`/`build-test.bat`（不递增版本号的检查——见第 3 节），就会运行它。本工具从不重新实现某个项目自身的构建步骤。

- **可选的签名检查**：候选版本的 `build-test` 脚本是候选版本自带的代码，会在任何东西证明该提交确属维护者之前就在本机运行。设置 `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1` 后，更新器会先在暂存克隆中对已接受的候选版本执行 `git verify-commit`；若该提交没有本机信任的签名（密钥环中的 gpg 密钥，或 `gpg.ssh.allowedSignersFile` 中的 ssh 签名者），就在此停止：不会构建也不会运行任何内容，正在使用的安装保持原样。默认关闭，因为它需要本机上有信任维护者密钥的密钥环。

- **每次升级后重建 `.venv`**：被替换的安装若有 `.venv`，升级后的检出会得到一个新的（`python -m venv`，项目有 `requirements.txt` 时再执行 `pip install -r requirements.txt`），而不是什么都没有；旧的留在 `.backup` 中。可用 `HYDRA_UMC_UPDATER_RECREATE_VENV=0` 或已保存的设置 `recreate_venv` 关闭。若无法创建，更新会被报告为失败，并指出仍保存着旧 `.venv` 的备份。
- **更多安全保障**：每个工作区同一时间只运行一次安装或更新（锁文件）；每条 git 命令和每个 build-test 都有时间限制，且绝不会索要凭据；意外错误会在窗口和证据文件中表现为失败结果，而不会让窗口永远停在"工作中"；签名检查也适用于首次安装，并可在已保存的设置中开启（`require_signed_commits`；无法读取的设置文件视为开启），关闭期间窗口会显示红色提示；导致无法快进的本地提交会在拒绝信息中点名；构建失败的全新安装会被再次移除；过期的暂存文件夹会在每次运行开始时清理，`--cli prune-backups [--keep N] [--dry-run]` 仅在你要求时才删除旧的 `<名称>.backup-xxxxxxxx` 文件夹。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="HYDRA-UMC-UPDATER 安装或更新期间的真实检查点" width="100%">
</p>

### 架构与设计决策

- **默认 Qt Quick GUI，`--cli` 用于无桌面环境。** `main.py` 会在导入可选 PySide6
  运行时之前检查 `--cli`。CLI 可在没有显示器或桌面依赖的 CM5 上工作；无参数时会在
  可用条件下启动 QML，Tkinter 仅保留为临时兼容回退。
- **带窗口的 GUI 是真实的,支持 8 种语言的多语言(`i18n.py`)—— `--cli` 则刻意不支持。** 每个真实的控件都会根据保存的偏好或操作系统自身的区域设置,从语言 `Combobox`(en/es/fr/it/de/zh/ja/pt,与公开仪表盘和每份 README 提供的相同 8 种语言)实时重新标注。项目/家族名称以及每个项目自身真实的 `notes`/`tech` 文本保持未翻译——`registry.py` 是它们唯一的真相来源,而 8 份并行的真实工程文档副本会破坏这一点。`--cli` 的输出刻意只保留英文:它是为脚本化/管道化设计的,在这种场景下,稳定、可 grep 的文本比本地化更重要。
- **`deploy` 是一种分类，而非一种限制。** 把每一个发现的项目都当作"属于 CM5 的东西"是错误的——固件仓库是从 PC 编译并刷写的（CM5 只需要通过 CAN-OTA 得到最终的二进制文件，从不需要本仓库自身的源代码），而若干工具（URTC-FLASHER、HYDRA-UMC-SUITE、HYDRA-UMC-TOOL-CLI……）本应运行在操作员自己的工作站上，而非单元本机内部。`registry.py` 的 `deploy` 字段（"cm5" / "user-pc" / "mobile" / "wearable" / "dev-server"）记录了这一点，GUI 的筛选器将其作为一个合理的起点使用——而非硬性限制，因为这个同一工具也可以运行在开发者自己的 PC 上，此时每一个发现的项目都可以被检查。
- **本工具中不包含针对特定技术栈的构建逻辑。** 本生态系统横跨 7 种工具链（Python、Rust、Go、Node/TS、Android/Kotlin、Flutter、ARM 固件）。在*这里*重新实现 `npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` 等，会产生第二个自称知道如何构建每个项目的地方，注定会与该项目自身真实（且已经正确）的检查产生偏差。`install.py` 转而只运行项目自己的不改版本的 `build-test.sh`（Windows 上为 `build-test.bat`），它只做验证而不递增任何版本；没有它的项目会被拒绝，并提示 "No non-versioning build-test.sh/.bat found"。
- **使用 GitHub 原始内容，而非 Releases API。** 见上方第 2 节——本生态系统的版本控制惯例从不创建标签/发布，因此在这里使用 Releases API 不仅不够方便，而且是彻底错误的做法。
- **临时性网络故障会获得真正的重试；确定性的回应则永远不会。** 每一次真实的 GitHub 请求（`github_client.py` 的 `_urlopen_with_retries`）最多重试 3 次并带有退避延迟，但仅限于连接从未获得任何响应的情况（DNS/超时/重置）。GitHub 实际返回的真实 HTTP 状态——404、403、500——永远不会被重试：GitHub 已经给出了答复，再次请求只会消耗更多的速率限制额度而得到相同的结果。
- **格式错误的远程目录会响亮地失败；单个格式错误的项目不会。** 如果 GitHub 的仓库列表本身无法访问或无法解析，`discover_remote_projects()` 会抛出异常——`gui.py` 和 `main.py` 都已经捕获了这一点，并回退到本地发现的项目列表，而不是显示一次损坏或空白的扫描。相反，单个仓库格式错误的清单会被隔离到该次扫描自己的 `errors` 列表中，绝不会中止对其余项目的发现——一个真实的、基于夹具服务器的测试（`tests/test_github_client.py`）证明了这两条路径。
- **CLI 操作保持明确；GUI 批量操作保持确认。** CLI 的 `install`/`update`
  命令需要一个项目名称。桌面 GUI 可以执行**安装全部缺失项目**或**更新全部
  过期项目**，但只会在独立确认后，并按顺序通过相同安全检查执行。不存在
  无人值守的自动更新。
- **仅使用标准库。** `urllib` 用于 GitHub 抓取（`github_client.py`），`subprocess` 用于 git/构建脚本调用（`install.py`），仅此而已——一个负责维护其他*所有*项目依赖健全性的工具，其自身保持零依赖，这是刻意为之的。
- **已知的简化处理**：HYDRA-UMC 和 URTC 是真正的多组件固件仓库（各自分别有 6 个和 4 个独立版本管理的二进制文件——见各自的 `VERSION_CHECKLIST.txt`/`build_firmware.sh`），并不存在单一的"那个"版本号。`registry.py` 每个仓库只跟踪*一个*代表性组件——足以回答"这个仓库大致是否是最新的"，但不能替代 `build_firmware.sh` 自身的 `firmware_manifest.json` 用于真实的刷写场景。

## 🔒 安全与防护

| 威胁 | 防御 | 位置 |
|---|---|---|
| 无法构建的新版本留下更新到一半的项目 | 候选版本先在单独的暂存文件夹中克隆、合并并构建；成功之前不会碰已安装的文件夹，成功后通过两次重命名换入，并把旧版本保留为 `<name>.backup` | `install.py` |
| 实际上是回滚的更新，或丢弃本地工作的更新 | 获取的清单会经过校验，较低的版本会被拒绝；只使用快进合并，已跟踪的本地修改会让更新明确停止 | `install.py`, `project_manifest.py` |
| 运行并非维护者提交的代码 | 设置 `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1`（或已保存的设置）后，克隆的提交必须先通过 `git verify-commit`，才会运行其中的任何内容；缺少工具、提交未签名或密钥未知都视为未签名 | `install.py` |

**它绝不做的事：** 自行更新。每一次安装和更新都是有人运行的命令，它可读取的 `GITHUB_TOKEN` 是可选的，且只需要读取权限。

## ⚙️ 配置

| 变量 | 默认值 | 设置内容 |
|---|---|---|
| `GITHUB_TOKEN` | 无 | 可选的只读令牌；没有它时 GitHub 每小时允许 60 次请求 |
| `HYDRA_UMC_UPDATER_REQUIRE_SIGNED` | `0` | `1`、`true`、`yes` 或 `on` 要求克隆的提交带有有效签名 |
| `HYDRA_UMC_UPDATER_RECREATE_VENV` | 开启 | `0` 表示升级后保留旧虚拟环境，而不是新建一个 |
| `--workspace` | 本文件夹的上级文件夹 | 每个项目一个子文件夹的父文件夹 |

## 🚀 快速开始

需要 Python 3.10 或更高版本。

```bash
./build.sh  # Linux, macOS (build.bat on Windows)
./run.sh --cli status --offline
./run.sh --cli status --workspace ~/hydra
./run.sh --cli install HYDRA-UMC-DATALAKE
./run.sh --cli update HYDRA-UMC-DATALAKE
./run.sh --cli prune-backups --keep 2 --dry-run
```

## 🧪 测试

运行 `python -m pytest -q tests` 会执行 163 个自动测试。 不需要硬件，也不需要这台机器以外的任何东西。

CI 运行 `HYDRA_UMC_CI=1 python tools/ci_validate.py`，检查清单、文档、八个 README 和图片。

## 🏗️ 构建与发布

```bash
chmod +x build.sh   # 仅需一次
./build.sh          # 创建 .venv，pip install -e .，对一切进行编译检查
./run.sh                              # 窗口化 GUI（默认）
./run.sh --cli status                 # 已安装的内容，本地版本与 GitHub 版本对比
./run.sh --cli status --offline       # 相同，但跳过 GitHub 检查
./run.sh --cli install <PROJECT-NAME> # 克隆 + 构建一个尚未安装的项目
./run.sh --cli update  <PROJECT-NAME> # 拉取 + 重新构建一个已安装的项目
./run.sh --cli prune-backups --keep 2  # 删除旧的 <名称>.backup-xxxxxxxx 文件夹（每个项目保留最新的 2 个）
```

在 Windows 上：先 `build.bat`，然后 `run.bat`（GUI）/ `run.bat --cli
status` / `run.bat --cli install <name>` / `run.bat --cli update
<name>`。

首选 GUI 需要可选 Qt 运行时（`pip install -e ".[gui]"`；
`build.bat`/`build.sh` 已经安装它）。`--cli` 没有图形依赖，适合无桌面的
CM5。没有 Qt 时，旧 Tkinter 窗口仅作为兼容回退。

**故障排查**

- `status` 对某个项目的本地或 GitHub 版本显示 `?`：它的版本文件存在，但该项目自己的 `hydra-umc.project.json` 中的 `native_version` 条目已不再对应其版本的真实位置——请修正该项目的清单。
- `status` 对 GitHub 显示 `-` 但没有显示任何错误：运行 `status`（不带 `--offline`）——`-` 只会在 GitHub 检查被完全跳过时出现。
- `install`/`update` 失败并提示 "No non-versioning build-test.sh/.bat found"：该项目还没有 `build-test.sh`/`build-test.bat`——请为它添加生态系统的标准脚本（它必须在不递增任何版本的情况下完成验证）。
- `git merge --ff-only failed`：本地检出的历史已分叉或存在本地提交（提示信息会点名）——请先移走或丢弃它们（在该项目自身目录中运行 `git status`/`git log`），再重试 `update`。已跟踪文件中未提交的修改会被直接拒绝。本工具从不对检出目录执行强制重置。

## 🩺 故障排除

| 你看到 | 原因 | 处理 |
|---|---|---|
| `unauthenticated requests are capped at 60/hour` | 已达到 GitHub 对无令牌请求的限制 | 等待，使用 `status --offline`，或设置只读的 `GITHUB_TOKEN` |
| the update stops and names changed files | 项目中已跟踪的文件在这台机器上被修改 | 自行提交、暂存或丢弃该修改，然后再次运行 `update` |

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-UPDATER" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/     源代码
│   ├── __init__.py            包说明与版本
│   ├── registry.py            ProjectEntry —— 没有静态目录;在发现时从每个仓库自身的清单构建
│   ├── project_manifest.py    读取/校验仓库自身的 hydra-umc.project.json
│   ├── ecosystem_catalog.py   JuanenRac 生态系统公开发现目录的解析器
│   ├── version_parse.py       单一的正则表达式提取实现，本地+GitHub 通用
│   ├── detect.py              扫描工作区根目录，检测已安装的内容
│   ├── github_client.py       并发抓取原始内容 + 针对临时性网络错误的真实重试/退避机制
│   ├── install.py             git clone/pull + 委托给项目自身的构建脚本
│   ├── i18n.py                真实、完整的 GUI 翻译（8 种语言）
│   ├── qt_gui.py              通向真实发现/更新服务的 Qt Quick 桥接层
│   ├── qml/Main.qml           带主题、检查点和 About 的桌面界面
│   ├── gui.py                 PySide6 不可用时的 Tkinter 兼容回退
│   ├── main.py                分发逻辑：默认 GUI，--cli 用于 status/install/update
│   ├── evidence.py            每次安装或更新尝试留一行证据: 项目、之前、之后、提交与结果
│   ├── assets/                应用程序图标 (HYDRA_UMC_ICON.ico 和 .svg)
│   ├── i18n_pt.py             界面的葡萄牙语翻译
│   └── settings.py            持久保存的用户设置 (工作区根目录等界面在两次启动之间记住的选择)
├── tests/                     真实测试：github_client、i18n、install、project_manifest、registry
├── docs/                      项目文档
├── images/                    媒体、应用图标与界面截图
├── tools/                     项目工具和 CI 检查
├── .github/                   CI 工作流和 Issue 模板
├── .env.example               环境变量模板
├── build.sh / build.bat       venv + 可编辑安装 + 编译检查
├── run.sh / run.bat           默认 GUI / CLI 入口
├── run-gui.vbs                无控制台窗口的 Windows 图形启动器
├── bump_version.py            显式提升版本
├── bump_manifest_version.py   将 hydra-umc.project.json 的版本与原生版本同步(--sync)
├── CHANGELOG.md               每个版本的变更
├── build-test.sh              不修改内容的构建检查
├── hydra-umc.project.json     清单：版本、成熟度、系列
├── pyproject.toml             包的元数据
└── test.sh                    运行测试
```

</details>

## 🗺️ 路线图与已知限制

**当前已知限制**

- 一个打包的独立 GUI 可执行文件（PyInstaller，与 HYDRA-UMC-SUITE 自身的 `build_exe.bat`/`.sh` 惯例一致），实现完全无需 `pip`/venv 步骤的双击安装——目前的 GUI 仍然需要像 CLI 一样先执行 `./build.sh`。
- 可选的逐项目依赖预检查（在 `install` 中途失败之前，报告缺失的工具链——未安装 Rust/Go/Android SDK/Flutter）。
- 针对 HYDRA-UMC/URTC 自身多二进制固件的逐组件跟踪（见第 3 节中的"已知的简化处理"），一旦出现超出目前所跟踪的单一代表性组件的真实需求。

## 🌍 语言

本 README 和仓库文档提供八种语言：英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙语（葡萄牙）。它们同时编写，并由 CI 检查八个文件拥有相同的章节和相同的链接。

## 🔗 相关项目

本项目是同一作者(JuanenRac / Electro Hobby 3D)打造的 HYDRA-UMC 机器人生态系统的一部分。值得了解,因为某个请求实际上可能是关于这些项目之一,而非本仓库本身。

**直接相关**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 机器人手臂主板设计——CM5 主机 + 双核 STM32H745,目标是通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂(固件处于早期阶段,尚无已组装的电路板)。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 面向多台服务器的桌面(PySide6)集群指挥中心，打包为独立可执行文件 —— 另一个旨在与单元控制器并行运行的独立 Python 工具,是角色上最接近的兄弟项目(专注于 CM5 端的实用工具,并非机器人控制路径本身的一部分)。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** —— 在构建全新 CM5 镜像时，依赖本项目作为真实的库来完成自身的 GitHub 生态系统发现，而不是另建一份可能独立漂移的实现。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 维护事件协调器：一个低权限的边缘角色采集经过脱敏的库存/健康快照，一个控制面角色以只读方式渲染它，并请求某个 AI 提供方给出诊断建议——从不应用补丁，也从不部署任何内容。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 可复现的开发主机（Raspberry Pi 5 / CM5），保存整个生态系统的源代码，并在持久队列下运行有界的构建/测试任务；这是专用的开发角色，明确区别于运行中的 CM5。

**生态系统中的其他项目**

*核心硬件与平台*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — 面向 CM5 的可复现 Raspberry Pi OS 产品层——只读代理、经过验证的配置/配置文件、WiFi 首次配网。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 每个桥接都据此校验自身指令的共享 JSON-Schema 契约与软件作业门限边界(并非经认证的安全功能)。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 面向外部机器连接器的声明式适配器清单注册与校验工具；把 SDK 自身的契约理念扩展到外部机器，而不取代工业网关类项目。

*核心后端与客户端*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — 每个控制客户端真正通信的真实无头后端(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — 具有实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 具有生物识别登录和配对 Wear OS 伴侣应用的原生 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — 具有实时 WebSocket 同步的 iOS/iPadOS 控制应用(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 面向机载 7 英寸 DSI 触摸屏的原生触控界面，直接嵌入 CM5 本体。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 将完成的模型推送到 STUDIO 自身目录的桌面版图形化 URDF 创建/编辑工具。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — 桌面 STL 模型编辑器，在 HYDRA-UMC-EDITOR-URDF 编辑的同一模型目录中变换/替换/移除/添加真实部件。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 通过 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界(仅针对仿真车队测试)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 具备 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 面向足式/人形机器人的协调边界,带有 Boston Dynamics Spot 指令发送器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 读取 3 路钥匙/外壳/联锁 GPIO 信号的激光单元协调器(仅针对模拟芯片测试;无法使激光器上膛或发射)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — 面向 OpenPnP 贴片机板级流程的安全高层协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 面向 Moonraker/Klipper 3D 打印机的安全协调边界，具备真实的受控作业指令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 带有惰性导入 rclpy ROS 2 传输层的协调器(尚未在 ROS 2 环境中运行)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 面向搭载摄像头的无人机的协调边界,带有 MAVLink 指令发送器(仅针对模拟器测试)。

*视觉 AI 节点(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — 面向 Hailo-8 视觉流水线的集成中枢，具备逐阶段的真实硬件就绪检测。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — 具备 Hailo 架构/校验和安全加载验证的真实编译模型注册表。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 具备真实 HailoRT 集成边界的真实 GStreamer 流水线 + MediaMTX 配置生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 以区域状态为授权条件的 Position-Based Visual Servoing 修正律;尚无摄像头位姿估计。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 从文件读取物体位置的 v0 区域入侵、校准新鲜度与 E-STOP 请求逻辑;没有检测器为其供数,也尚未连接任何物理 E-STOP。

*认知 AI 节点(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — 面向 Hailo-10 认知流水线(LLM/VLA/语音编排)的集成中枢。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — 面向 Vision-Language-Action 模型的真实动作 token 编解码与轨迹生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 具备受限、需确认的 Watch 中继的真实语音前端(VAD + 意图解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — 基于真实规则的任务分解，以及针对 MCU 错误码的语义化错误恢复。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — 面向本生态系统自身 Markdown 文档的真实纯标准库 TF-IDF 文档检索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — 面向生态系统自身的本地、按策略门控的 AI 维护技师——观察、诊断并提出修复建议;两个最高风险等级目前特意尚未实现。

*编排与集群*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 具备真实 gRPC/Protobuf 健康报告契约与任务状态机的集成中枢。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 基于真实 HTTP API 的真实优先级任务队列，支持去重。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — 具备重试/退避与身份不匹配检测的真实基于 gRPC 的车队健康看门狗。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 具备真实障碍物/工作空间碰撞校验的真实基于 RRT 的三维路径规划器。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 经过多单元收敛属性测试的真实 CRDT LWW-Element-Map 状态同步。

*数字孪生与仿真*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 面向数字孪生引擎的集成中枢，具备真实的版本兼容性同步契约。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — 在仿真与真实硬件之间带有软件碰撞联锁的硬件在环路由器(未在真实硬件上测试)。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 面向真实 URDF 子集的真实正向运动学与关节限位校验。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — 具备 YOLO/COCO 标注导出功能的真实程序化 2D 场景生成器。

*数据与分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 具备真实数据摄入/查询 HTTP API 的真实 sqlite3 时序数据存储。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — 具备漂移监测能力的真实 FFT + 统计基线异常检测器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — 基于 DATALAKE 历史数据的真实 OEE/可用率计算，支持可复现的 CSV 导出。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — 面向 DATALAKE 的真实 CAN/WebSocket 数据摄入管道，支持序列去重。

*工业网关*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 中继至工业协议的集成中枢，具备真实的指令白名单/背压控制层。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 经真实二进制协议客户端会话验证的真实 OPC-UA 地址空间。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — 具备可选按客户端认证与主题 ACL 的真实 MQTT 代理。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 具备降级模式输出的真实 MTConnect `/probe` 与 `/current` XML 端点。

*辅助工具与生态系统运维*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 基于 DATALAKE/ANOMALY-DETECTOR 的智能摘要与异常高亮面板，具备诚实的统计回退机制。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 具备真实、稳定退出码契约的车队 CLI，是 HYDRA-UMC-SERVER 自身 API 的真实在线客户端。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 带有触觉提醒模式与配对手机语音中继的 WearOS 伴侣应用(尚未在实体手表上运行)。

## 📚 文档

更多阅读：

* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — 每一个 `--cli` 子命令、从真实安装环境中获取的真实输出，以及退出码契约。
* **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — Qt Quick/QML 桌面客户端的真实结构，以及它为何始终是同一个后端之上的真实控制界面（与 `--cli` 共用后端），而不是第二套实现。
* [生态系统的安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [生态系统的威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [本仓库的更新日志](CHANGELOG.md)
* [本仓库的许可证](LICENSE.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（或 `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）：它必须输出 `CI_VALIDATION=PASS`。此检查不要运行 `build.sh` 或 `build.bat`；构建不是检查。
* 八个 README 由 HYDRA-UMC-DOCS 中的同一个源生成；请勿手工编辑。修改源文件，再用 `tools/make_readmes.py` 重新生成。
* 不要在 README 中声称尚未运行过的内容：属实时请写“仅模拟”或“尚未在硬件上试过”。
* 请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)、[行为准则](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md) 和 [SUPPORT.md](SUPPORT.md)。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - [LICENSE](LICENSE).
