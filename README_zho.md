<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📦 检测、安装并手动更新整个 HYDRA-UMC/URTC 生态系统

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only CLI core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
</p>

> **可视化桌面模式：** 默认桌面界面现通过可选的 `PySide6` GUI 运行时使用
> **Qt Quick / QML**。更新器核心与 `--cli` 模式仍仅使用标准库，适合无桌面的 CM5。
>
> **Windows 启动和操作证据：** 双击 `run-gui.vbs`（或不带参数运行
> `run.bat`）即可启动无控制台图形客户端。更新面板会显示真实的预检查、源更新、
> 清单验证、构建测试和完成检查点及捕获的证据；`run.bat --cli ...` 保留诊断终端。
> 仅在缺少检出时启用安装，仅在 GitHub 版本更高时启用更新。已批准操作期间，
> 检查点会替换项目控制区；选择其他项目即可恢复控制区。
> **安装全部缺失项目**和**更新全部过期项目**是分别确认的顺序批量操作，使用相同的
> 实时状态和安全流程。

---

## 1. 🛠️ 技术概述

HYDRA-UMC-UPDATER 是一个小型工具——默认为窗口化 GUI，通过 `--cli` 可
获得完整的 CLI——旨在运行在真实的 CM5 本机上，或运行在开发者自己的
Windows/Linux/macOS 计算机上（任何以相同方式检出的工作区），它为生态
系统中另外 54 个项目中的每一个都回答三个问题：

1. **这里实际安装了什么，版本是多少？**
2. **GitHub 上发布的最新版本是什么？**
3. **如果 GitHub 上的版本更新，那就手动让我更新那一个项目。**

最后一点是刻意为之、不容妥协的：本工具每次命令绝不会更新超过一个项目，
也绝不会主动自行更新。一个机器人控制单元并不是那种你希望它一夜之间
自动更新自己的东西——每一次真实的更新，都是一个人为一个指定项目触发的
一条命令（或在 GUI 表格中选中一行后点击的一个按钮），其结果在触碰下
一个项目之前就能看到。

54 个项目中也并非每一个都属于 CM5 本机——大多数以 URTC 为前缀的仓库和
少数 HYDRA-UMC 仓库，是开发者从自己的 PC 上运行的工具（固件是从工作站
编译/刷写的，而非在单元本机上构建的），或是安装在手机/手表上的应用。
`registry.py` 自身的 `deploy` 字段记录了哪个属于哪种（见第 3 节），
GUI 的项目表格会据此进行筛选——当检测到运行在 Linux（真实 CM5 自身的
操作系统）上时默认为"仅 CM5"，在 Windows/macOS 上则默认为"显示全部"。

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

不带任何参数运行 `hydra-umc-updater`（或直接双击它）会在窗口中打开同样
的信息——一个可排序的项目表格、一个部署目标筛选器，以及针对当前所选行
的安装/更新按钮。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="HYDRA-UMC-UPDATER 真实桌面总览" width="100%">
</p>

## 2. 🔄 检查/更新实际是如何工作的

- **版本来源**：本生态系统自身的"里程表"式自动递增惯例（每次真实构建都会递增一个存在于源文件*内部*的版本号——根据项目所用技术栈的不同，可能是 `pyproject.toml`、`Cargo.toml`、`version.go`、`package.json`、`version.properties`、`pubspec.yaml`，或一个固件 `#define`）从未为该次递增创建过 git 标签或 GitHub Release。因此本工具直接通过 GitHub 的原始内容托管，读取每个项目自身的 `bump_version.py`/构建脚本已经在写入的那个*同一个*文件的仓库默认分支版本——而非 Releases API，后者会把每个项目都报告为"完全没有发布记录"。
- **本地检测**：对于 54 个已知项目中的每一个，检查工作区根目录下是否存在一个与该项目名称完全一致的目录（标准的生态系统布局——每个项目作为同级目录，这正是 `build-frontend.sh`/HYDRA-UMC-SUITE 自身的发现逻辑已经假定的方式），如果存在，则读取该项目*自身*的本地版本文件副本。
- **单一解析实现**（`version_parse.py`）在本地读取和 GitHub 抓取之间共享，因此本地检出和 GitHub 抓取绝不会被两个独立漂移的正则表达式分别解读。
- **安装/更新**：`git clone`（安装）或 `git pull --ff-only`（更新——绝不使用强制重置，因此真实的本地修改会明确失败，而非被丢弃），然后运行该项目自身实际拥有的 `build.sh`/`build.bat`（或某个已知等效项——见第 3 节）中的任意一个。本工具从不重新实现某个项目自身的构建步骤——原因见第 3 节。

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="HYDRA-UMC-UPDATER 安装或更新期间的真实检查点" width="100%">
</p>

## 3. 🧱 架构与设计决策

- **默认 Qt Quick GUI，`--cli` 用于无桌面环境。** `main.py` 会在导入可选 PySide6
  运行时之前检查 `--cli`。CLI 可在没有显示器或桌面依赖的 CM5 上工作；无参数时会在
  可用条件下启动 QML，Tkinter 仅保留为临时兼容回退。
- **带窗口的 GUI 是真实的,支持 7 种语言的多语言(`i18n.py`)—— `--cli` 则刻意不支持。** 每个真实的控件都会根据保存的偏好或操作系统自身的区域设置,从语言 `Combobox`(en/es/fr/it/de/zh/ja,与公开仪表盘和每份 README 提供的相同 7 种语言)实时重新标注。项目/家族名称以及每个项目自身真实的 `notes`/`tech` 文本保持未翻译——`registry.py` 是它们唯一的真相来源,而 7 份并行的真实工程文档副本会破坏这一点。`--cli` 的输出刻意只保留英文:它是为脚本化/管道化设计的,在这种场景下,稳定、可 grep 的文本比本地化更重要。
- **`deploy` 是一种分类，而非一种限制。** 把全部 54 个项目都当作"属于 CM5 的东西"是错误的——固件仓库是从 PC 编译并刷写的（CM5 只需要通过 CAN-OTA 得到最终的二进制文件，从不需要本仓库自身的源代码），而若干工具（URTC-FLASHER、HYDRA-UMC-SUITE、HYDRA-UMC-TOOL-CLI……）本应运行在操作员自己的工作站上，而非单元本机内部。`registry.py` 的 `deploy` 字段（"cm5" / "user-pc" / "mobile" / "wearable"）记录了这一点，GUI 的筛选器将其作为一个合理的起点使用——而非硬性限制，因为这个同一工具也可以运行在开发者自己的 PC 上，此时全部 54 个项目都可以被检查。
- **本工具中不包含针对特定技术栈的构建逻辑。** 本生态系统横跨 7 种工具链（Python、Rust、Go、Node/TS、Android/Kotlin、Flutter、ARM 固件）。在*这里*重新实现 `npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` 等，会制造出第二个声称知道如何构建每个项目的地方，注定会与该项目自身真实的（且已经正确的）`build.sh`/`.bat` 逐渐脱节。`install.py` 转而探测一个已知的构建脚本名称（`build.sh`、`build_firmware.sh`、`build_exe.sh`、`build-android.sh` 及其 `.bat` 等效版本——这些是横跨 54 个项目实际使用的真实名称），并运行其中实际存在的那一个。
- **使用 GitHub 原始内容，而非 Releases API。** 见上方第 2 节——本生态系统的版本控制惯例从不创建标签/发布，因此在这里使用 Releases API 不仅不够方便，而且是彻底错误的做法。
- **临时性网络故障会获得真正的重试；确定性的回应则永远不会。** 每一次真实的 GitHub 请求（`github_client.py` 的 `_urlopen_with_retries`）最多重试 3 次并带有退避延迟，但仅限于连接从未获得任何响应的情况（DNS/超时/重置）。GitHub 实际返回的真实 HTTP 状态——404、403、500——永远不会被重试：GitHub 已经给出了答复，再次请求只会消耗更多的速率限制额度而得到相同的结果。
- **格式错误的远程目录会响亮地失败；单个格式错误的项目不会。** 如果 GitHub 的仓库列表本身无法访问或无法解析，`discover_remote_projects()` 会抛出异常——`gui.py` 和 `main.py` 都已经捕获了这一点，并回退到本地发现的项目列表，而不是显示一次损坏或空白的扫描。相反，单个仓库格式错误的清单会被隔离到该次扫描自己的 `errors` 列表中，绝不会中止对其余项目的发现——一个真实的、基于夹具服务器的测试（`tests/test_github_client.py`）证明了这两条路径。
- **`install`/`update` 始终需要一个明确的项目名称。** 不存在"更新全部"这样的子命令，这是一项设计决策，而非缺失的功能——一支真实的机器人车队不是那种可以放任其无人值守地自动更新的东西。`status` 显示哪些已过期；由人来决定实际要动哪一个。
- **仅使用标准库。** `urllib` 用于 GitHub 抓取（`github_client.py`），`subprocess` 用于 git/构建脚本调用（`install.py`），仅此而已——一个负责维护其他*所有*项目依赖健全性的工具，其自身保持零依赖，这是刻意为之的。
- **已知的简化处理**：HYDRA-UMC 和 URTC 是真正的多组件固件仓库（各自分别有 6 个和 4 个独立版本管理的二进制文件——见各自的 `VERSION_CHECKLIST.txt`/`build_firmware.sh`），并不存在单一的"那个"版本号。`registry.py` 每个仓库只跟踪*一个*代表性组件——足以回答"这个仓库大致是否是最新的"，但不能替代 `build_firmware.sh` 自身的 `firmware_manifest.json` 用于真实的刷写场景。

## 📂 目录结构

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py         # ProjectEntry —— 没有静态目录;在发现时从每个仓库自身的清单构建
│   ├── project_manifest.py # 读取/校验仓库自身的 hydra-umc.project.json
│   ├── ecosystem_catalog.py # JuanenRac 生态系统公开发现目录的解析器
│   ├── version_parse.py   # 单一的正则表达式提取实现，本地+GitHub 通用
│   ├── detect.py          # 扫描工作区根目录，检测已安装的内容
│   ├── github_client.py   # 并发抓取原始内容 + 针对临时性网络错误的真实重试/退避机制
│   ├── install.py         # git clone/pull + 委托给项目自身的构建脚本
│   ├── i18n.py             # 真实、完整的 GUI 翻译（7 种语言）
│   ├── qt_gui.py           # 通向真实发现/更新服务的 Qt Quick 桥接层
│   ├── qml/Main.qml        # 带主题、检查点和 About 的桌面界面
│   ├── gui.py              # PySide6 不可用时的 Tkinter 兼容回退
│   └── main.py             # 分发逻辑：默认 GUI，--cli 用于 status/install/update
├── tests/                  # 真实测试：github_client、i18n、install、project_manifest、registry
├── docs/
│   ├── CLI_REFERENCE.md     # 命令参考
│   └── QML_DESKTOP_GUI.md   # Qt Quick GUI 架构
├── images/                 # 媒体、应用图标与界面截图
├── tools/
│   ├── build_test.py        # 不递增版本号的构建检查
│   ├── ci_validate.py       # CI 使用的清单/CHANGELOG/文档校验
│   ├── generate_app_icon.py # 将公开的 HYDRA-UMC SVG 渲染为 Windows 使用的图标
│   ├── migrate_project_manifests.py  # 一次性清单迁移后对工作区的审计
│   └── validate_project_manifests.py # 校验仓库自身的清单 + 原生构建版本号
├── .env.example            # 环境变量模板
├── build.sh / build.bat    # venv + 可编辑安装 + 编译检查
├── run.sh / run.bat        # 默认 GUI / CLI 入口
├── run-gui.vbs             # 无控制台窗口的 Windows 图形启动器
├── bump_version.py         # 生态系统统一的里程表式版本递增（pyproject.toml + __init__.py）
└── bump_manifest_version.py # 将 hydra-umc.project.json 的版本与原生版本同步(--sync)
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

首选 GUI 需要可选 Qt 运行时（`pip install -e ".[gui]"`；
`build.bat`/`build.sh` 已经安装它）。`--cli` 没有图形依赖，适合无桌面的
CM5。没有 Qt 时，旧 Tkinter 窗口仅作为兼容回退。

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

本项目是同一作者(JuanenRac / Electro Hobby 3D)打造的 HYDRA-UMC 机器人生态系统的一部分。值得了解,因为某个请求实际上可能是关于这些项目之一,而非本仓库本身。

**直接相关**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 机器人手臂的真实主板——CM5 主机 + 双核 STM32H745，通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂 —— 本工具旨在使其在真实 CM5 硬件上保持已安装且最新状态的旗舰级多机器人单元控制器。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 面向多台服务器的桌面(PySide6)集群指挥中心，打包为独立可执行文件 —— 另一个旨在与单元控制器并行运行的独立 Python 工具,是角色上最接近的兄弟项目(专注于 CM5 端的实用工具,并非机器人控制路径本身的一部分)。

**生态系统中的其他项目**

*核心硬件与平台*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — 面向 CM5 的可复现 Raspberry Pi OS 产品层——只读代理、经过验证的配置/配置文件、WiFi 首次配网。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 每个桥接都据此校验自身指令的共享 JSON-Schema 契约与安全门限边界。

*核心后端与客户端*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — 每个控制客户端真正通信的真实无头后端(REST/WebSocket)。
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — 具有实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 具有生物识别登录和配对 Wear OS 伴侣应用的原生 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — 具有实时 WebSocket 同步的 iOS/iPadOS 控制应用(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 面向机载 7 英寸 DSI 触摸屏的原生触控界面，直接嵌入 CM5 本体。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 将完成的模型推送到 STUDIO 自身目录的桌面版图形化 URDF 创建/编辑工具。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 通过真实的 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 具备真实 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 面向足式/人形机器人的协调边界，具备真实的 Boston Dynamics Spot 指令发送器。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 读取 3 项真实钥匙/外壳/联锁 GPIO 安全信号的激光单元安全协调器。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — 面向 OpenPnP 贴片机板级流程的安全高层协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 面向 Moonraker/Klipper 3D 打印机的安全协调边界，具备真实的受控作业指令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 具备真实的惰性导入 rclpy ROS 2 传输层的安全协调器。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 面向搭载摄像头的无人机的协调边界，具备真实的 MAVLink 指令发送器。

*URTC 工具平台*
- **[URTC](https://github.com/JuanenRac/URTC)** — 面向实体 Universal Robot Tool Controller 板卡的固件，通过 CAN 总线支持 25 种以上工具配置。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — 面向 URTC 板卡的桌面图形烧录工具，支持 CAN-OTA 以及全芯片 SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — 面向 URTC 板卡的桌面实时 CAN 总线诊断工具，每种工具配置对应一个面板。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — 通过 Web Serial API 实现的浏览器版 URTC-TESTER 替代方案，无需本地安装。

*视觉 AI 节点(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — 面向 Hailo-8 视觉流水线的集成中枢，具备逐阶段的真实硬件就绪检测。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — 具备 Hailo 架构/校验和安全加载验证的真实编译模型注册表。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 具备真实 HailoRT 集成边界的真实 GStreamer 流水线 + MediaMTX 配置生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 具备真实 Position-Based Visual Servoing 修正律，并依据上游区域状态进行安全门控。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 具备校准新鲜度强制检查的真实区域入侵检测与 E-STOP 请求。

*认知 AI 节点(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — 面向 Hailo-10 认知流水线(LLM/VLA/语音编排)的集成中枢。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — 面向 Vision-Language-Action 模型的真实动作 token 编解码与轨迹生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 具备受限、需确认的 Watch 中继的真实语音前端(VAD + 意图解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — 基于真实规则的任务分解，以及针对 MCU 错误码的语义化错误恢复。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — 面向本生态系统自身 Markdown 文档的真实纯标准库 TF-IDF 文档检索。

*编排与集群*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 具备真实 gRPC/Protobuf 健康报告契约与任务状态机的集成中枢。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 基于真实 HTTP API 的真实优先级任务队列，支持去重。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — 具备重试/退避与身份不匹配检测的真实基于 gRPC 的车队健康看门狗。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 具备真实障碍物/工作空间碰撞校验的真实基于 RRT 的三维路径规划器。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 经过多单元收敛属性测试的真实 CRDT LWW-Element-Map 状态同步。

*数字孪生与仿真*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 面向数字孪生引擎的集成中枢，具备真实的版本兼容性同步契约。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — 在仿真与真实硬件之间路由指令的真实硬件在环安全联锁。
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 具备真实触觉提醒与配对手机语音中继功能的 WearOS 伴侣应用。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 面向板卡安装机架的固件，具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — 面向热成像/RGB 检测工具头的固件及真实 Python 视觉伴侣程序。

---

## 📚 文档与社区

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — 每一个 `--cli` 子命令、从真实安装环境中获取的真实输出，以及退出码契约。
- **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — Qt Quick/QML 桌面客户端的真实结构，以及它为何始终是同一个后端之上的真实控制界面（与 `--cli` 共用后端），而不是第二套实现。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— 提交 Pull Request 所需的技术栈和编码规范。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— 本社区所期望的行为准则。
- **[SECURITY.md](SECURITY.md)** —— 如何报告漏洞，以及本项目真实的安全关注重点。
- **[SUPPORT.md](SUPPORT.md)** —— 在哪里提问和报告缺陷。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 许可证

GPL-3.0（软件）/ CC BY-SA 4.0（文档）—— 详见 [LICENSE.md](LICENSE.md)。
