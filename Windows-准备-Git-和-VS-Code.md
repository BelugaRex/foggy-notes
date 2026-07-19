# 在 Windows 准备 Git 和 VS Code

> 目标：让 PowerShell 能调用 Git 和 VS Code，并在编辑器里打开 Copilot Chat。

## 直接照做

### 1. 安装 Git for Windows

1. 打开 [Git for Windows 官方页面](https://git-scm.com/install/windows)，下载 x64 安装包。
2. 没有特殊需求时保留默认选项并完成安装。
3. 关闭旧 PowerShell，重新打开一个窗口。
4. 运行：

```powershell
git --version
```

5. 设置提交身份：

```powershell
git config --global user.name "你的 GitHub 用户名"
git config --global user.email "你的 GitHub noreply 邮箱"
```

### 2. 安装 VS Code

1. 打开 [VS Code 的 Windows 安装说明](https://code.visualstudio.com/docs/setup/windows)，下载 **User Setup**。
2. 完成安装后重新打开 PowerShell。
3. 运行：

```powershell
code --version
```

4. 打开 VS Code，点击状态栏中的 Copilot 图标。
5. 选择 **Use AI Features**，使用 GitHub 账号登录。
6. 按 `Ctrl+Shift+I` 打开 Chat。

## 怎么确认成功

- `git --version` 和 `code --version` 都能输出版本号。
- VS Code 中能打开 Chat，并看到模式和模型选择器。
- 新建空目录后运行 `git init`，不会提示找不到命令。

版本号能出来就够了，今天不用顺手研究安装器里的每一颗螺丝。

## 这一步有什么用

Git 用来保存修改前后的快照，方便查看差异和回退；VS Code 负责把聊天、文件、终端、Git diff 和审批界面放在同一个窗口。这里先把地基铺好，模型下一篇再接。

## 相关笔记

- [用 UCP 把 DeepSeek 接入 VS Code](UCP-接入-DeepSeek)
- [在 Copilot Chat 运行 DeepSeek Agent](Copilot-Chat-运行-DeepSeek-Agent)

最后核验：**2026-07-19**。