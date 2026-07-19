---
tags: [VS Code, Agent, UCP, DeepSeek]
---

<!-- article-id: FN-001 -->

# 给 VS Code 搭一套顺手的 Agent 工作流

这份笔记的核心，是在 VS Code 里搭建一套顺手的 Agent 工作流，再通过 UCP 接入 DeepSeek 等第三方模型。

我日常更喜欢用这套工作流，而不是大家常用的 OpenCode、Claude 或 Codex。VS Code 能读取代码和源文件、管理项目文件结构，也能同时打开多个终端：一边看 Agent 在操作什么，一边用独立终端做自己的事。

我还会用插件让 Copilot 接入第三方模型，以及一些方便的 skills 和 MCP。遇到问题时，可以直接在 Output 和日志里查找工作流的 bug 与风险。下面从头开始搭建。

> **Agent 补充｜阅读标记**
>
> 本页主体来自作者的实操草稿。后面由 Agent 添加的验证方法、官方依据和时效提醒，都会继续使用这种引用块，与作者正文分开。

## 第 0 步：准备电脑

你需要有一台电脑。当前安装步骤和截图以 Windows 为例；进入 VS Code 后，UCP、模型设置和 Chat 的操作与系统关系不大，macOS 和 Linux 可以按同样思路适配。

## 第 1 步：安装 VS Code

1. 如果使用 Windows 11，可以直接从[微软商店安装 VS Code](https://apps.microsoft.com/detail/XP9KHM4BK9FZ7Q?hl=zh-Hans-CN&gl=HK&ocid=pdpshare)。
2. 安装后打开 VS Code，确认能正常进入主界面。

<!-- image-id: FN-001-01 | path: images/fn-001/fn-001-01.png -->
![VS Code 安装后的主界面](images/fn-001/fn-001-01.png)

*图 01：VS Code 安装后的主界面。*

等待安装时，可以先[注册一个 GitHub 账号](https://github.com/)。

确认 VS Code 能正常打开后，重启一次电脑，避免后续遇到 PATH 没有刷新的问题。

## 第 2 步：安装 Git

1. 打开 [Git for Windows 下载页](https://git-scm.com/install/windows)。
2. 想直接下载 x64 安装包，也可以使用这个[快速下载链接](https://github.com/git-for-windows/git/releases/download/v2.55.0.windows.3/Git-2.55.0.3-64-bit.exe)。
3. 下载完成后，保持默认选项一路点击 **Next** 即可。如果后续遇到问题，再让 Agent 帮忙调整。
4. 安装完成后，再重启一次电脑。

我的做法是先安装 VS Code，再安装 Git，通常不会遇到太多问题。

> **Agent 补充｜确认安装成功**
>
> 重启后打开 PowerShell，分别运行 `code --version` 和 `git --version`。两条命令都能显示版本号，说明 VS Code 与 Git 已经进入 PATH。Git 官方下载页在 **2026-07-20** 列出的 x64 安装包版本是 `2.55.0.3`，与上面的快速下载链接一致。

## 第 3 步：登录 VS Code 并安装 UCP

打开 VS Code，点击左下角的人头图标，把 GitHub 账号登录到 VS Code。登录后也可以打开设置同步。

<!-- image-id: FN-001-02 | path: images/fn-001/fn-001-02.png -->
![VS Code 左下角的 GitHub 登录入口](images/fn-001/fn-001-02.png)

*图 02：VS Code 左下角的登录入口。*

然后点击左侧的扩展图标。

<!-- image-id: FN-001-03 | path: images/fn-001/fn-001-03.png -->
![VS Code 左侧的扩展入口](images/fn-001/fn-001-03.png)

*图 03：VS Code 左侧的扩展入口。*

搜索并安装 **Unify Chat Provider**。安装完成后，重启 VS Code。

<!-- image-id: FN-001-04 | path: images/fn-001/fn-001-04.png -->
![VS Code 扩展市场中的 Unify Chat Provider](images/fn-001/fn-001-04.png)

*图 04：Unify Chat Provider 扩展。*

> **Agent 补充｜核对扩展来源**
>
> VS Code Marketplace 中的扩展发布者是 **SmallMain**，扩展 ID 是 `SmallMain.vscode-unify-chat-provider`。截至 **2026-07-20**，公开版本为 `7.12.3`。可以在[扩展市场页面](https://marketplace.visualstudio.com/items?itemName=SmallMain.vscode-unify-chat-provider)和[项目仓库](https://github.com/smallmain/vscode-unify-chat-provider)交叉确认。

## 第 4 步：申请 DeepSeek API

1. 打开 [DeepSeek 开放平台](https://platform.deepseek.com/usage)。
2. 申请或登录账号。
3. 在页面左侧边栏充值，然后创建并复制 API Key。

DeepSeek API Key 只会在创建时显示一次。如果丢失，就需要重新创建，所以可以先找个安全的地方保存。

我的做法是先充值 10 元，日常使用通常比较耐用。

## 第 5 步：在 UCP 中配置 DeepSeek

点击 VS Code 上方的输入框，输入 `Unify Chat Provider`，选择从内置供应商列表添加供应商。这里是 UCP 预先配置好的一些模型供应商。

<!-- image-id: FN-001-05 | path: images/fn-001/fn-001-05.png -->
![UCP 的内置供应商入口](images/fn-001/fn-001-05.png)

*图 05：UCP 的内置供应商入口。*

输入 `DeepSeek`，选择 DeepSeek 供应商配置。

<!-- image-id: FN-001-06 | path: images/fn-001/fn-001-06.png -->
![UCP 中的 DeepSeek 供应商](images/fn-001/fn-001-06.png)

*图 06：UCP 中的 DeepSeek 供应商。*

接下来按顺序操作：

1. 输入供应商名称；保持默认的 `DeepSeek` 即可，然后按回车。
2. 粘贴刚才复制的 API Key，再按回车。
3. 进入配置界面后点击 **保存**，然后按 `Esc`。

<!-- image-id: FN-001-07 | path: images/fn-001/fn-001-07.png -->
![UCP 的 DeepSeek 供应商配置界面](images/fn-001/fn-001-07.png)

*图 07：DeepSeek 供应商配置界面。*

如果配置正确，右下角会出现一个银行卡图标。把鼠标移上去，可以看到余额情况。

<!-- image-id: FN-001-08 | path: images/fn-001/fn-001-08.png -->
![UCP 显示的 DeepSeek 余额](images/fn-001/fn-001-08.png)

*图 08：UCP 显示的 DeepSeek 余额。*

## 第 6 步：修改两个 VS Code 设置

VS Code 更新后，还需要多改两个设置。

在设置里搜索 `chat.utilityModel`，把两个模型都改成 DeepSeek V4 Pro。

<!-- image-id: FN-001-09 | path: images/fn-001/fn-001-09.png -->
![VS Code 中的 chat.utilityModel 设置](images/fn-001/fn-001-09.png)

*图 09：修改 Utility Model。*

如果想省钱，也可以在设置里搜索 `explore agent`，启用代码研究子代理，再把模型改成 DeepSeek V4 Pro。DeepSeek V4 Flash 也可以，会更便宜、更快。

<!-- image-id: FN-001-10 | path: images/fn-001/fn-001-10.png -->
![VS Code 中的 Explore Agent 设置](images/fn-001/fn-001-10.png)

*图 10：修改 Explore Agent 模型。*

更改浏览子模型后，将来使用比较贵的中转站模型时，仍然可以让 DeepSeek 负责浏览代码，能省下不少费用。

> **Agent 补充｜这两项设置有官方依据**
>
> UCP 项目说明列出了 `chat.utilityModel`、`chat.utilitySmallModel` 和 Explore Agent 的默认模型设置，也说明后台任务可能继续使用 Copilot 内置模型。这里修改 Utility 与 Explore，并不是截图里凭空多出来的两行设置。

## 开始使用

点击 VS Code 上方输入框旁边的 Chat 图标，打开聊天面板。

<!-- image-id: FN-001-11 | path: images/fn-001/fn-001-11.png -->
![VS Code 顶部的 Chat 入口](images/fn-001/fn-001-11.png)

*图 11：打开 Chat 面板。*

聊天面板可以按自己的习惯拖到另一侧。我更喜欢放在左边。

在聊天栏底部打开模型选择器，先选择 DeepSeek V4 Flash，验证是否已经正常连接。

<!-- image-id: FN-001-12 | path: images/fn-001/fn-001-12.png -->
![Copilot Chat 中的 DeepSeek 模型选择器](images/fn-001/fn-001-12.png)

*图 12：切换到 DeepSeek V4 Flash。*

输入一些内容试试看。只要 DeepSeek 正常回复，基本上就没有问题了。

<!-- image-id: FN-001-13 | path: images/fn-001/fn-001-13.png -->
![DeepSeek 在 Copilot Chat 中的连通性测试](images/fn-001/fn-001-13.png)

*图 13：实际测试结果。*

## 按需添加 NVIDIA NIM 免费模型

上面是内置模型供应商的配置。除了 DeepSeek，我个人还推荐 [NVIDIA NIM 模型平台](https://build.nvidia.com/models)：可以免费使用，不过速度比较慢。

NVIDIA NIM 的模型很多，但不是每个都好用。下面是我在 **2026-07-20** 暂时使用的配置。

前面的步骤基本一样：在 UCP 的内置供应商里选择 NVIDIA，输入 API Key，然后按回车。

接着点击 **从官方模型列表添加**。

<!-- image-id: FN-001-14 | path: images/fn-001/fn-001-14.png -->
![NVIDIA 供应商中的官方模型列表入口](images/fn-001/fn-001-14.png)

*图 14：从官方模型列表添加模型。*

在列表中勾选模型，然后点击确认。我暂时只推荐图中这些模型。

<!-- image-id: FN-001-15 | path: images/fn-001/fn-001-15.png -->
![NVIDIA NIM 的官方模型列表](images/fn-001/fn-001-15.png)

*图 15：NVIDIA NIM 模型列表。*

NVIDIA NIM 还需要调整供应商配置。先点击 **供应商配置**。

<!-- image-id: FN-001-16 | path: images/fn-001/fn-001-16.png -->
![UCP 中的 NVIDIA 供应商配置入口](images/fn-001/fn-001-16.png)

*图 16：打开 NVIDIA 供应商配置。*

选择 **网络设置**。

<!-- image-id: FN-001-17 | path: images/fn-001/fn-001-17.png -->
![NVIDIA 供应商配置中的网络设置](images/fn-001/fn-001-17.png)

*图 17：打开网络设置。*

按照下图调整 **连接超时**、**响应超时** 和 **最大重试次数**。完成后返回供应商配置，再返回供应商页面并点击保存，最后按 `Esc`，就可以开始使用 NVIDIA NIM 模型了。

<!-- image-id: FN-001-18 | path: images/fn-001/fn-001-18.png -->
![NVIDIA NIM 的连接超时与重试设置](images/fn-001/fn-001-18.png)

*图 18：调整连接超时、响应超时和最大重试次数。*

> **Agent 补充｜时效提醒**
>
> Git 安装包、UCP 版本、DeepSeek 模型和 NVIDIA NIM 模型列表都可能更新。本页外部入口最后核验于 **2026-07-20**；如果界面名称变化，可以优先按页面中的关键词搜索。