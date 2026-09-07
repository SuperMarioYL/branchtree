[English](README.en.md) | **简体中文**

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/hero-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/hero-dark.svg">
  <img src="assets/presentation/hero-light.svg" width="960" alt="BranchTree — Keep more than one path for your story.">
</picture>

**BranchTree 把章节、分支与角色事实保存在本地故事树中，让你尝试另一条支线、保留旧稿，并检查明显的事实矛盾。**

`Python 3.12+` · [MIT](LICENSE) · [GitHub](https://github.com/SuperMarioYL/branchtree) · [网站](https://branchtree.lei6393.com)

## 为什么需要它

修改连载的某个转折时，新版本不必覆盖后续所有旧稿。故事树把章节之间的父子关系与每个分支的当前结尾分开保存，作者可以比较不同走向，再决定把哪一条提升为主线。事实锁为检查器提供具体参照，并不保证自动消除叙事矛盾。

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/process-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/process-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/process-dark.svg">
  <img src="assets/presentation/process-light.svg" width="960" alt="Try and inspect an alternate continuation">
</picture>

## 架构

tree.py 的 StoryTree 保存 ChapterNode、Branch 和 Lock；add_chapter 用父节点连接正文，并更新 active_tip。state.py 仅记录文本长度和已知人物名称出现情况。consistency.py 检查有限的中文显式否定规则；render_html.py 将树渲染为静态 HTML。模型重写和深层抽取在 llm.py 中仍未实现。

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/architecture-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/architecture-dark.svg">
  <img src="assets/presentation/architecture-light.svg" width="960" alt="Chapters, branches and fact records">
</picture>

## 安装

需要 Python 3.12+。安装依赖可能联网，下面的树操作与检查不调用模型。

```bash
git clone https://github.com/SuperMarioYL/branchtree.git
cd branchtree
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## 快速开始

```bash
python examples/presentation_demo.py
```

例子建立三章，从 ch1 分出 alternate，并在 ch3 写入“林晚左手没有疤”。检查器对锁定事实“左手有疤”报告一条矛盾。合并后 main 指向 ch3，但 ch1、ch2、ch3 均保留；JSON 重新加载有效，静态 HTML 成功写出。临时文件结束后清理。

## 用法

```bash
# 在独立的故事工作目录中
mkdir my-story
cd my-story
branchtree new serial
branchtree lock add character:林晚 --facts "左手有疤"
branchtree add --text "林晚醒来，左手有疤。"
branchtree branch --from ch1 --name alternate
branchtree add --text "林晚左手没有疤。" --branch alternate
branchtree consistency
branchtree view --no-browser
branchtree merge --branch alternate --into main
```

merge 将支线节点重新标为目标分支并移动目标 tip，随后删除支线记录；它不会做逐句文本合并，也不自动拒绝矛盾章节。

## 能力与集成

| 输入/输出 | 当前支持 |
|---|---|
| 章节正文 | --text 或 UTF-8 文件 --file |
| 持久化 | <name>.tree/tree.json |
| 人物事实 | lock add / lock list |
| 阅读视图 | 静态 HTML；可关闭自动打开浏览器 |
| Python | StoryTree、Lock 和检查器 API |

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/integrations-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/integrations-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/integrations-dark.svg">
  <img src="assets/presentation/integrations-light.svg" width="960" alt="Local writing inputs and outputs">
</picture>

## 配置与边界

CLI 在当前目录查找按名称排序的第一个 *.tree 目录，因此建议一个工作目录放一棵故事树。lock 的默认 scope 是 tree，事实使用分号分隔。

一致性规则只检查包含目标人物名的章节，并匹配有限的否定片段。它不理解隐喻、人物动机或完整时间线；无违规输出不能证明全文正确。当前 consistency 即使报告违规也不会设置非零退出码；需要自动化时消费 Python 检查器返回的 Violation 列表。

regenerate 和深层状态抽取仍抛出 NotImplementedError，配置模型端点或 API key 不能激活它们。

## 运行记录

v0.1.0 使用三章构造文本完成真实树操作、持久化与 HTML 导出。规则命中不是对整部小说一致性的证明。

[输入、命令和完整输出](docs/demo-results.json)

[保留的历史终端录屏](assets/demo.gif) · [录制脚本](docs/demo.tape)。本轮示例以以上可重放记录为准。

## 路线图

- [x] 章节树、分叉、支线提升和 JSON 保存。
- [x] 事实锁记录、规则矛盾检查、静态 HTML。
- [ ] 模型辅助重写与深层状态抽取。
- [ ] 云同步与协作工作流。

当前不提供托管套餐或购买入口；未实现功能只列为方向。

## 开发与许可证

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

树格式见 [tree.py](src/branchtree/tree.py)，检查规则见 [consistency.py](src/branchtree/consistency.py)。

[MIT](LICENSE) · [Issues](https://github.com/SuperMarioYL/branchtree/issues)
