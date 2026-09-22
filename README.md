# Codex Profiles

**One account profile. Two ways to use it: the official desktop app and Codex CLI.**

macOS 本地账号启动器。为每个账号提供独立数据目录、带编号的 Dock 入口，以及对应的 CLI 命令。无需修改官方应用、复制登录凭据或引入请求代理。

## 解决的问题

额外启动一个官方应用进程后，它的运行图标仍属于官方应用。将这个图标固定到 Dock，再次点击时通常会走默认启动路径，丢失第二账号的数据目录参数。

本项目提供一个独立、常驻的原生启动器。Dock 固定的是启动器；启动器每次都根据账号配置启动或聚焦正确进程。第二账号图标是蓝底白色 **2 / CODEX**。

> 这是第三方本地工具，与 OpenAI 无隶属关系。桌面隔离使用内部环境变量，兼容性需要随官方应用更新验证。

## 安装

需要 macOS、官方 ChatGPT/Codex 桌面应用、Python 3.9+、Xcode Command Line Tools（提供 Swift 编译器）。没有额外 Python 包依赖。

在下载的本仓库目录执行：

```bash
python3 install.py --pin
```

安装程序会在本机编译 Swift 启动器和图标，进行本地 ad-hoc 签名，并创建：

- `~/Applications/Codex 第二账号.app`
- `~/.local/bin/codex-profile`
- `~/.local/bin/codex-account-2`（兼容旧命令）
- `~/Library/Application Support/Codex Profiles/`（配置、运行代码和备份）

`--pin` 会先备份 Dock 偏好，然后固定第二账号启动器，并整理指向同一官方应用的重复固定图标。保留一个原版入口，保留其他应用的图标顺序与 Dock 设置。不希望调整 Dock 时省略 `--pin`，之后可以手动把启动器拖到 Dock。

首次安装自动登记两套账号目录；如果已有第二账号配置与登录信息，会原样沿用。新用户需要在第二账号窗口完成自己的 ChatGPT 登录。

| 账号 | Codex 数据目录 | 桌面数据目录 |
| --- | --- | --- |
| A / `a` | `~/.codex` | `~/Library/Application Support/Codex` |
| B / `b` | `~/.codex-account-2` | `~/Library/Application Support/Codex Account 2` |

普通 `codex` 命令、shell 配置和官方应用包不会被安装程序改动。源码仓库可以移动，已安装的启动器不依赖仓库路径。Python 的安装路径仍需保持可用；更换 Python 后重新安装启动器即可。

## 日常使用

**桌面 B + CLI A：** 点击 Dock 蓝色 **2** 图标，同时在终端使用原来的 `codex` 命令即可。

也可以显式选择账号（如果 `~/.local/bin` 不在 PATH，使用下面的完整形式）：

```bash
~/.local/bin/codex-profile list
~/.local/bin/codex-profile desktop b
~/.local/bin/codex-profile cli a
~/.local/bin/codex-profile cli b
~/.local/bin/codex-profile cli b -C /path/to/project
~/.local/bin/codex-profile status b
~/.local/bin/codex-profile doctor b
```

CLI 保留调用时的工作目录和全部参数。`status` 使用官方 CLI 查询认证状态；`doctor` 只检查路径、启动器、Dock 入口和认证文件是否存在，不读取 token，也不证明登录有效或实际账号身份。

右键蓝色 **2** 图标，可以打开对应桌面版或在 Terminal 打开此账号的 CLI。

### 关闭与重新打开

- 在第二账号的官方应用窗口按 **Cmd+Q**：退出第二账号应用；蓝色 **2** 启动器仍在 Dock。
- 再次点击蓝色 **2**：仍使用 B 的账号目录。
- 账号应用已运行时点击：根据该进程实际打开的数据文件匹配 PID，聚焦正确进程。
- 在启动器自身菜单选择“退出启动器”：只退出启动器。它的固定图标仍可再次启动。
- 原版 ChatGPT/Codex 图标仍是原版入口；不要把第二实例临时出现的官方图标当作蓝色 **2** 入口。

这个设计会额外占用一个启动器 Dock 图标。官方应用运行时仍可能显示自己的图标；本项目不修改它的 Bundle ID、名称、签名或 Dock 行为。

### 新增账号

```bash
~/.local/bin/codex-profile add work --name 'Codex Work'
python3 install.py --profile work --pin
~/.local/bin/codex-profile cli work login
```

`add` 支持 `--home`、`--desktop-data` 和 `--app`，用于登记已有账号目录或非默认位置的官方应用。默认会为新账号在管理目录下创建独立路径。不同账号的目录不能相同或相互嵌套。

一个账号目录可以同时供桌面和 CLI 使用。新建目录本身不会产生登录状态；首次使用需完成登录。同一目录中的认证被多个客户端共用，退出登录可能影响其他客户端。

## 原理

```text
蓝色 2 启动器 ─┐
桌面命令 b ────┼─→ 账号 B 配置 → CODEX_HOME(B) + 桌面数据目录(B) → 官方桌面应用
CLI 命令 b ────┘             └→ CODEX_HOME(B) → 官方 Codex CLI

普通 codex ───────────────────→ 默认 CODEX_HOME(A) → 官方 Codex CLI
```

桌面首次启动使用 macOS `open -n` 并显式传递：

- `CODEX_HOME`
- `CODEX_ELECTRON_USER_DATA_PATH`
- `--user-data-dir`

在已验证的官方版本中，应用会自行设置 Electron userData；只传 Chromium 的 `--user-data-dir` 不够可靠。显式桌面隔离路径也能使该版本在载入 shell 环境后保留选定的 CODEX_HOME。

启动前过滤继承的 `CODEX_*` 会话变量、API 身份变量和 `ELECTRON_RUN_AS_NODE`，然后设置选定账号的路径。已有账号配置不改写；新账号配置默认使用文件认证缓存与 ChatGPT 登录。

认证、历史和运行数据保留在仓库外。安装器和管理器不读取、复制或代理认证 token。它不是操作系统沙箱：多个账号仍可访问同一 macOS 用户可访问的项目和文件。

## 升级与卸载

升级前，在蓝色 **2** 启动器菜单选择“退出启动器”，然后重新运行安装命令；官方应用可保持运行。旧启动器、命令、管理配置和 Dock 偏好会保存在管理目录的 `backups/` 下。账号认证和会话目录不会被覆盖。

移除时，退出启动器，将 `~/Applications/Codex 第二账号.app` 移到废纸篓，并从 Dock 移除其图标。需要完全移除管理工具时，可一并移走 `~/.local/bin/codex-profile`、`~/.local/bin/codex-account-2`。保留账号目录，下次安装仍可继续使用。

管理目录也可能包含通过 `add` 创建的新账号数据，因此不要在未检查内容时整目录删除。

## 开发与验证

```bash
python3 -m unittest discover -s tests -v
xcrun swiftc -typecheck -framework AppKit src/AccountLauncher.swift
xcrun swiftc -typecheck -framework AppKit src/FocusApp.swift
xcrun swiftc -typecheck -framework AppKit src/MakeIcon.swift
```

详见 [测试范围与手工验收](docs/TESTING.md)。自动测试不使用真实账号或调用模型。

发布范围只包含源码、文档与测试；生成的 `.app` 包包含本机安装路径，不作为通用二进制直接发布。

## 参考与许可证

- [官方认证文档](https://learn.chatgpt.com/docs/auth)
- [官方配置与状态目录](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [ccheney/chatgpt-multi-account](https://github.com/ccheney/chatgpt-multi-account)
- [edihasaj/codex-account-switcher](https://github.com/edihasaj/codex-account-switcher)

参考了上述项目的目录隔离思路；本项目独立实现原生 Dock 启动器和账号管理。采用 [MIT License](LICENSE)。
