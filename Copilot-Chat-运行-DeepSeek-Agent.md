# 在 Copilot Chat 运行 DeepSeek Agent

> 目标：让 DeepSeek 在 Copilot Chat 中完成一次“读取、修改、运行、修复”的完整工具调用。

## 直接照做

1. 按 `Ctrl+Shift+I` 打开 Chat。
2. 把会话模式切换到 **Agent**。
3. 选择 **DeepSeek V4 Flash (DeepSeek)**。
4. 新建一个空目录，在终端运行：

```powershell
git init
code .
```

5. 在 Agent 会话中发送：

> 请先检查当前工作区并给出简短计划。然后创建一个 `hello-agent.ps1`：接受 `-Name` 参数，输出带当前时间的问候语。运行 `./hello-agent.ps1 -Name Foggy` 验证；如果失败就修复。最后总结修改内容和验证结果。

6. 逐次查看文件修改和终端动作，任务结束后打开源代码管理视图看 diff。

## 怎么确认成功

- Agent 先读取工作区，再给出简短计划。
- 工作区出现 `hello-agent.ps1`。
- 终端实际运行脚本，并输出带时间的问候语。
- 如果第一次运行失败，Agent 会读取错误并继续修复。
- 源代码管理视图能看到完整改动。

只回一句“你好”还不算通关，毕竟聊天和干活是两回事。

## 如果卡住

- 模型选择器里没有 DeepSeek：看 [处理 UCP 和 DeepSeek 常见问题](UCP-DeepSeek-常见问题)。
- 能聊天但不能调用工具：确认当前是 **Agent** 模式，并使用 V4 Flash 或 V4 Pro。
- 请求很慢：先用 V4 Flash 和 `High` 思考强度，减少并行会话后再试。

## 这次验证有什么用

普通聊天只能证明模型能回复。这个小任务同时验证了模型选择、上下文读取、文件编辑、终端执行、错误恢复和 Git diff，跑通后才算接入了可用的 Agent 工作流。

## 相关笔记

- [用 UCP 设置 VS Code 默认模型](UCP-设置-VS-Code-默认模型)
- [给 VS Code Agent 添加项目规则](VS-Code-Agent-项目规则)
- [检查 VS Code Agent 的安全与成本](VS-Code-Agent-安全与成本)

最后核验：**2026-07-19**。