<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📦 检测、安装并手动更新整个 HYDRA-UMC/URTC 生态系统

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Dependencies-stdlib%20only-brightgreen.svg" alt="stdlib only">
</p>

---

## 1. 🛠️ 技术概述

HYDRA-UMC-UPDATER 是一个小型工具——默认为窗口化 GUI，通过 `--cli` 可
获得完整的 CLI——旨在运行在真实的 CM5 本机上，或运行在开发者自己的
Windows/Linux/macOS 计算机上（任何以相同方式检出的工作区），它为生态
系统中另外 44 个项目中的每一个都回答三个问题：

1. **这里实际安装了什么，版本是多少？**
2. **GitHub 上发布的最新版本是什么？**
3. **如果 GitHub 上的版本更新，那就手动让我更新那一个项目。**

最后一点是刻意为之、不容妥协的：本工具每次命令绝不会更新超过一个项目，
也绝不会主动自行更新。一个机器人控制单元并不是那种你希望它一夜之间
自动更新自己的东西——每一次真实的更新，都是一个人为一个指定项目触发的
一条命令（或在 GUI 表格中选中一行后点击的一个按钮），其结果在触碰下
一个项目之前就能看到。

44 个项目中也并非每一个都属于 CM5 本机——大多数以 URTC 为前缀的仓库和
少数 HYDRA-UMC 仓库，是开发者从自己的 PC 上运行的工具（固件是从工作站
编译/刷写的，而非在单元本机上构建的），或是安装在手机/手表上的应用。
`registry.py` 自身的 `deploy` 字段记录了哪个属于哪种（见第 3 节），
GUI 的项目表格会据此进行筛选——当检测到运行在 Linux（真实 CM5 自身的
操作系统）上时默认为"仅 CM5"，在 Windows/macOS 上则默认为"显示全部"。

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

不带任何参数运行 `hydra-umc-updater`（或直接双击它）会在窗口中打开同样
的信息——一个可排序的项目表格、一个部署目标筛选器，以及针对当前所选行
的安装/更新按钮。

## 2. 🔄 检查/更新实际是如何工作的

- **版本来源**：本生态系统自身的"里程表"式自动递增惯例（每次真实构建都会递增一个存在于源文件*内部*的版本号——根据项目所用技术栈的不同，可能是 `pyproject.toml`、`Cargo.toml`、`version.go`、`package.json`、`version.properties`、`pubspec.yaml`，或一个固件 `#define`）从未为该次递增创建过 git 标签或 GitHub Release。因此本工具直接通过 GitHub 的原始内容托管，读取每个项目自身的 `bump_version.py`/构建脚本已经在写入的那个*同一个*文件的仓库默认分支版本——而非 Releases API，后者会把每个项目都报告为"完全没有发布记录"。
- **本地检测**：对于 44 个已知项目中的每一个，检查工作区根目录下是否存在一个与该项目名称完全一致的目录（标准的生态系统布局——每个项目作为同级目录，这正是 `build-frontend.sh`/HYDRA-UMC-SUITE 自身的发现逻辑已经假定的方式），如果存在，则读取该项目*自身*的本地版本文件副本。
- **单一解析实现**（`version_parse.py`）在本地读取和 GitHub 抓取之间共享，因此本地检出和 GitHub 抓取绝不会被两个独立漂移的正则表达式分别解读。
- **安装/更新**：`git clone`（安装）或 `git pull --ff-only`（更新——绝不使用强制重置，因此真实的本地修改会明确失败，而非被丢弃），然后运行该项目自身实际拥有的 `build.sh`/`build.bat`（或某个已知等效项——见第 3 节）中的任意一个。本工具从不重新实现某个项目自身的构建步骤——原因见第 3 节。

## 3. 🧱 架构与设计决策

- **默认为窗口化 GUI，`--cli` 用于无头模式。** Tkinter/ttk（标准库，无新增依赖）——与本生态系统中 `URTC-FLASHER`/`URTC-TESTER` 已经使用的相同 GUI 工具包和双入口点模式：`main.py` 会在*任何*导入 `tkinter` 之前检查 `sys.argv` 中是否有 `--cli`，因此 `--cli` 模式可以在一个真正无头、未安装 `python3-tk` 也没有显示器的 CM5 上工作，而不带参数的裸调用则在其他所有场景（包括带本地桌面/VNC 会话的 CM5，以及开发者自己的 PC）下获得更友好的窗口化体验。
- **`deploy` 是一种分类，而非一种限制。** 把全部 44 个项目都当作"属于 CM5 的东西"是错误的——固件仓库是从 PC 编译并刷写的（CM5 只需要通过 CAN-OTA 得到最终的二进制文件，从不需要本仓库自身的源代码），而若干工具（URTC-FLASHER、HYDRA-UMC-SUITE、HYDRA-UMC-TOOL-CLI……）本应运行在操作员自己的工作站上，而非单元本机内部。`registry.py` 的 `deploy` 字段（"cm5" / "user-pc" / "mobile" / "wearable"）记录了这一点，GUI 的筛选器将其作为一个合理的起点使用——而非硬性限制，因为这个同一工具也可以运行在开发者自己的 PC 上，此时全部 44 个项目都可以被检查。
- **本工具中不包含针对特定技术栈的构建逻辑。** 本生态系统横跨 7 种工具链（Python、Rust、Go、Node/TS、Android/Kotlin、Flutter、ARM 固件）。在*这里*重新实现 `npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` 等，会制造出第二个声称知道如何构建每个项目的地方，注定会与该项目自身真实的（且已经正确的）`build.sh`/`.bat` 逐渐脱节。`install.py` 转而探测一个已知的构建脚本名称（`build.sh`、`build_firmware.sh`、`build_exe.sh`、`build-android.sh` 及其 `.bat` 等效版本——这些是横跨 44 个项目实际使用的真实名称），并运行其中实际存在的那一个。
- **使用 GitHub 原始内容，而非 Releases API。** 见上方第 2 节——本生态系统的版本控制惯例从不创建标签/发布，因此在这里使用 Releases API 不仅不够方便，而且是彻底错误的做法。
- **`install`/`update` 始终需要一个明确的项目名称。** 不存在"更新全部"这样的子命令，这是一项设计决策，而非缺失的功能——一支真实的机器人车队不是那种可以放任其无人值守地自动更新的东西。`status` 显示哪些已过期；由人来决定实际要动哪一个。
- **仅使用标准库。** `urllib` 用于 GitHub 抓取（`github_client.py`），`subprocess` 用于 git/构建脚本调用（`install.py`），仅此而已——一个负责维护其他*所有*项目依赖健全性的工具，其自身保持零依赖，这是刻意为之的。
- **已知的简化处理**：HYDRA-UMC 和 URTC 是真正的多组件固件仓库（各自分别有 6 个和 4 个独立版本管理的二进制文件——见各自的 `VERSION_CHECKLIST.txt`/`build_firmware.sh`），并不存在单一的"那个"版本号。`registry.py` 每个仓库只跟踪*一个*代表性组件——足以回答"这个仓库大致是否是最新的"，但不能替代 `build_firmware.sh` 自身的 `firmware_manifest.json` 用于真实的刷写场景。

## 📂 目录结构

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py        # 44 个项目：仓库、技术栈、版本文件、匹配模式、部署目标
│   ├── version_parse.py   # 单一的正则表达式提取实现，本地+GitHub 通用
│   ├── detect.py          # 扫描工作区根目录，检测已安装的内容
│   ├── github_client.py   # 并发抓取 GitHub 最新版本的原始内容
│   ├── install.py         # git clone/pull + 委托给项目自身的构建脚本
│   ├── gui.py              # 窗口化 GUI（Tkinter/ttk）——默认入口点
│   └── main.py             # 分发逻辑：默认 GUI，--cli 用于 status/install/update
├── build.sh / build.bat    # venv + 可编辑安装 + 编译检查
├── run.sh / run.bat        # 运行本工具（转发所有参数——见下方"用法"）
└── bump_version.py         # 生态系统统一的里程表式版本递增（pyproject.toml + __init__.py）
```

## ⚙️ 构建与运行

```bash
chmod +x build.sh   # 仅需一次
./build.sh          # 创建 .venv，pip install -e .，对一切进行编译检查
./run.sh                              # 窗口化 GUI（默认）
./run.sh --cli status                 # 已安装的内容，本地版本与 GitHub 版本对比
./run.sh --cli status --offline       # 相同，但跳过 GitHub 检查
./run.sh --cli install <PROJECT-NAME> # 克隆 + 构建一个尚未安装的项目
./run.sh --cli update  <PROJECT-NAME> # 拉取 + 重新构建一个已安装的项目
```

在 Windows 上：先 `build.bat`，然后 `run.bat`（GUI）/ `run.bat --cli
status` / `run.bat --cli install <name>` / `run.bat --cli update
<name>`。

GUI 需要在基于源代码构建的 Linux Python 上安装 `python3-tk`
（Debian/Raspberry Pi OS：`sudo apt install python3-tk`）——python.org
提供的 Windows/macOS 安装程序已经内置。如果没有它，裸调用会打印一条
简短提示，并回退到 `--cli` 自身的帮助文本，而非崩溃。

**故障排查**

- `status` 对某个项目的本地或 GitHub 版本显示 `?`：其版本文件存在，但该项目自身的惯例自 `registry.py` 上次更新以来发生了变化——请对照该项目真实的、当前的版本文件，检查 `registry.py` 中对应的条目。
- `status` 对 GitHub 显示 `-` 但没有显示任何错误：运行 `status`（不带 `--offline`）——`-` 只会在 GitHub 检查被完全跳过时出现。
- `install`/`update` 失败并提示"未找到 build.sh/.bat"：该项目使用了本工具尚未识别的构建脚本名称——请查阅其自身的 README 以获取真实名称，并考虑将其添加到 `install.py` 自身的 `BUILD_SCRIPT_CANDIDATES_*` 列表中。
- `git pull --ff-only` 失败：本地检出存在未提交的修改，或历史已分叉——请手动解决该问题（在该项目自身的目录中运行 `git status`）后再重试 `update`。本工具从不对检出进行强制重置。

## 🚀 路线图

- 一个打包的独立 GUI 可执行文件（PyInstaller，与 HYDRA-UMC-SUITE 自身的 `build_exe.bat`/`.sh` 惯例一致），实现完全无需 `pip`/venv 步骤的双击安装——目前的 GUI 仍然需要像 CLI 一样先执行 `./build.sh`。
- 可选的逐项目依赖预检查（在 `install` 中途失败之前，报告缺失的工具链——未安装 Rust/Go/Android SDK/Flutter）。
- 为 `status` 提供 `--json` 输出模式，便于对其进行脚本化调用。
- 针对 HYDRA-UMC/URTC 自身多二进制固件的逐组件跟踪（见第 3 节中的"已知的简化处理"），一旦出现超出目前所跟踪的单一代表性组件的真实需求。

## 🔗 相关项目

本工具的全部目的就是管理生态系统中的每一个其他项目——与其在此列出全部
44 个（权威的、准确的列表见 `registry.py`），不如列出角色上最接近的
两个：

- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— 本工具旨在保持其在真实 CM5 硬件上安装并保持最新的旗舰级多机器人单元控制器。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** —— 另一个旨在与单元控制器并行运行的独立 Python 工具，是角色上最接近的同族项目（一个专注于 CM5 端的实用工具，而非机器人控制路径本身的一部分）。

**生态系统的其余部分**（本工具能够检测/安装/更新的每一个项目）：最初
的 12 个项目（固件、服务器、移动端/桌面端应用）、视觉/认知 AI 节点、
Rust 编排/仿真服务、Go 基础设施/CLI 工具、Node 工业网关，以及 URTC
刀头固件/PC 工具——完整的、最新的列表请见 `registry.py` 自身的分组
（与本 README 自身的目录结构注释相对应）。

## 👤 作者

**JuanenRac（Electro Hobby 3D）**
邮箱：electrohobby3d@gmail.com
YouTube：[youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 许可证

GPL-3.0（软件）/ CC BY-SA 4.0（文档）—— 详见 [LICENSE.md](LICENSE.md)。

## 🛠️ BUILD & RUN

请在发布构建前使用不改动版本的构建检查：

| 操作 | Windows | Linux / macOS |
|---|---|---|
| 构建检查（不修改版本或 CHANGELOG） | `build-test.bat` | `./build-test.sh` |
| 运行 / 开发（如提供） | `run*.bat` 或 `dev*.bat` | `./run*.sh` 或 `./dev*.sh` |

`build-test.bat` 和 `build-test.sh` 会编译或验证项目技术栈，但不会递增 `hydra-umc.project.json`，也不会修改 `CHANGELOG.md`。它们仅可能生成正常的编译器输出。现有的 `build*.bat`、`build*.sh`、`run*` 和 `dev*` 脚本保留各自的版本化或运行时行为；需要该行为时请使用它们。

> **Updater 安全性：** 自动 install 和 update 仅运行 build-test，绝不运行版本化构建。发布构建仍是明确的人为操作。
