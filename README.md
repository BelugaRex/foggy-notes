# Foggy Note

一个用来记录容易忘记的小技巧、排错过程和使用心得的 Markdown 笔记库。

当前页面结构兼容 GitHub Wiki：

- `Home.md`：Wiki 首页。
- `_Sidebar.md`：Wiki 侧边导航。
- `笔记模板.md`：新建笔记时可复用的结构。
- `VS-Code-小技巧.md`：第一篇示例笔记。

## 在 VS Code 中编写 GitHub Wiki

GitHub Wiki 是主仓库之外的独立 Git 仓库，远程地址格式为：

`https://github.com/<用户名>/<仓库名>.wiki.git`

推荐流程：

1. 在 GitHub 仓库设置中启用 **Wikis**。
2. 在网页端创建并保存第一个 Wiki 页面。
3. 克隆以 `.wiki.git` 结尾的 Wiki 仓库。
4. 将本目录中的 Wiki 页面复制到克隆目录。
5. 用 VS Code 打开该目录，像普通 Git 仓库一样提交并推送。

如果整个仓库只用于个人笔记，也可以不启用 Wiki，直接将这些 Markdown 文件作为普通仓库内容使用。普通仓库更适合文件夹分类、图片管理、分支和拉取请求。

详细约定见 `.vscode/指北.md`。