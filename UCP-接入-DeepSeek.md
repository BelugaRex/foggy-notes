# 用 UCP 把 DeepSeek 接入 VS Code

> 目标：让 DeepSeek V4 Flash 和 V4 Pro 出现在 VS Code 的模型选择器中。前置条件是已登录 Copilot Chat，并有 DeepSeek API 余额。

## 直接照做

### 1. 安装 UCP

1. 按 `Ctrl+Shift+X` 打开扩展市场。
2. 搜索 `@id:SmallMain.vscode-unify-chat-provider`。
3. 确认扩展名称是 **Unify Chat Provider**、发布者是 **SmallMain**，然后安装。
4. 执行 **Developer: Reload Window**。
5. 按 `Ctrl+Shift+P`，输入 `ucp:`；能看到 UCP 命令就继续。

### 2. 创建 DeepSeek API Key

1. 登录 [DeepSeek 开放平台](https://platform.deepseek.com/)。
2. 查看余额，打开 [API Keys](https://platform.deepseek.com/api_keys)。
3. 创建一个给 VS Code 使用的 Key，并临时复制它。

### 3. 添加 DeepSeek

1. 打开命令面板，运行 **Unify Chat Provider: 从内置供应商列表添加供应商**。
2. 搜索并选择 **DeepSeek**。
3. 选择 API Key 身份验证，粘贴刚创建的 Key。
4. 在导入页面确认配置并保存。

内置配置应包含：

| 字段 | 值 |
| --- | --- |
| API 格式 | OpenAI Chat Completion |
| Base URL | `https://api.deepseek.com` |
| 身份验证 | API Key |
| 模型 | 自动拉取官方模型，并使用 UCP 内置参数 |

## 怎么确认成功

- **Unify Chat Provider: 管理供应商** 中能看到 DeepSeek。
- Copilot Chat 的模型选择器中能看到 **DeepSeek V4 Flash** 或 **DeepSeek V4 Pro**。
- 设置文件里只有 `$UCPSECRET:...$` 引用，没有实际 Key。

如果没有模型，打开 DeepSeek 的模型列表，启用 **自动拉取官方模型**，再刷新官方模型。

## 模型先这样选

| 模型 | 先用在这里 |
| --- | --- |
| `deepseek-v4-flash` | 日常问答、搜索、轻量修改和高频 Agent 任务 |
| `deepseek-v4-pro` | 复杂规划、跨文件实现和困难排错 |

旧名称 `deepseek-chat` 与 `deepseek-reasoner` 将于 **2026-07-24 15:59 UTC** 弃用，新配置直接使用 V4 Flash 或 V4 Pro。

## Key 放在哪里

UCP 默认把 Key 存入 VS Code Secret Storage，设置文件只保留引用。保持 `unifyChatProvider.storeApiKeyInSettings` 关闭即可；打开它会让 Key 以明文进入 `settings.json`。

用完剪贴板里的 Key 后可以清掉。它不需要在桌面上拥有一个温馨的小家。

## UCP 在这里做什么

UCP 只负责把 VS Code 的模型请求转换并发送给 DeepSeek API。Agent 循环、聊天界面和文件、终端、Git 等工具仍由 Copilot Chat 与 VS Code 提供。

## 相关笔记

- [在 Copilot Chat 运行 DeepSeek Agent](Copilot-Chat-运行-DeepSeek-Agent)
- [处理 UCP 和 DeepSeek 常见问题](UCP-DeepSeek-常见问题)

最后核验：**2026-07-19**，使用 **Unify Chat Provider 7.12.4**。UCP 7.12.4 要求 VS Code 1.104.0 或更新版本。