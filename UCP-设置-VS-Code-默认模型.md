# 用 UCP 设置 VS Code 默认模型

> 目标：让 Utility、Explore、Plan 等后台任务也使用你选定的模型，减少每次手动切换。

## 直接照做

1. 按 `Ctrl+Shift+P` 打开命令面板。
2. 运行 **Unify Chat Provider: 更改 VS Code 默认模型**。

> [此处应有：图 01——VS Code 命令面板中搜索“更改 VS Code 默认模型”；框出 UCP 命令名称和扩展来源]

3. 先按下面这组分配：

| 任务 | 默认模型 |
| --- | --- |
| Utility、Utility Small、Explore、Ask | `deepseek-v4-flash` |
| Plan、Implement、Inline Chat | `deepseek-v4-flash` |

4. 遇到复杂规划、跨文件修改或困难排错时，在当前会话手动切换到 `deepseek-v4-pro`。
5. 图片理解另选支持视觉的模型；DeepSeek V4 当前是文本模型。

> [此处应有：图 02——UCP 默认模型分配界面；框出 Utility、Explore、Plan 和 Implement 对应的 deepseek-v4-flash；隐藏账号信息]

## 怎么确认成功

- 重新打开一个 Chat 会话，模型选择器显示预期模型。
- Explore 或 Utility 任务运行时，不再悄悄回到不想使用的默认模型。
- 简单任务使用 V4 Flash，复杂任务仍能在会话中切换到 V4 Pro。

## 什么时候用

模型已经接入、但 Copilot 免费额度仍在减少时，通常是后台 Utility 或 Explore 任务还在使用 Copilot 内置模型。统一设置默认模型后，高频小任务会更可预测，也省去反复点选。

## 相关笔记

- [Windows：从安装到 Agent 验证](Windows-VS-Code-UCP-DeepSeek-Agent-工作流)
- [检查 VS Code Agent 的安全与成本](VS-Code-Agent-安全与成本)

最后核验：**2026-07-19**，使用 **Unify Chat Provider 7.12.4**。