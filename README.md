# Cat Café Tutorials

> 从零搭建 AI 猫猫协作系统 — 一个真实项目的完整复盘

## 这是什么

这是 Cat Café 项目的配套教程，记录三只 AI 猫猫（Claude/Codex/Gemini）如何真正协作起来的故事。

**不是**理想化的"从零开始"路径，**而是**还原我们真实走过的路 —— 包括错误的尝试、关键的转折、以及血泪教训。

## 三只猫猫

| 猫猫 | 模型 | 角色 |
|------|------|------|
| 布偶猫 | Claude Opus | 主架构师，核心开发 |
| 缅因猫 | Codex | Code Review，安全，测试 |
| 暹罗猫 | Gemini | 视觉设计，创意 |

## 教程目录

→ [查看完整教程目录](./docs/lessons/README.md)

### 已完成

- **第一课**：[选型之路 — 从 SDK 到 CLI](./docs/lessons/01-sdk-to-cli.md)
  - 为什么官方 SDK 行不通？
  - 决策逻辑链完整还原
  - [课后作业](./docs/lessons/01-homework.md)：动手写最小可运行示例

### 即将推出

- 第二课：从玩具到生产 — CLI 调用的工程化
- 第三课：MCP 回传机制 — 让猫猫主动说话
- ...更多

## 适合谁

- 想让多个 AI Agent 协作的开发者
- 对 Claude/Codex/Gemini CLI 感兴趣的人
- 想看真实项目演进过程的人
- 想避开我们踩过的坑的人

## 项目状态

- 教程：公开（你正在看的）
- 代码仓库：私有（打磨中）
- 计划开源时间：待定

## 联系我们

如果你有问题或想交流，欢迎：
- 提 Issue
- 关注后续更新

---

*这个教程由三只猫猫和铲屎官共同编写。*

## 军议 AI 聊天工具（CLI）

已提供一个可运行的多模型军议聊天工具：

- 启动：`python3 src/war_council.py`
- 点名对话：`@诸葛亮 给我一个三步执行计划`
- 全体协作：`/c 评估这个需求的风险和排期`
- 动态添加模型：`/add 奉孝 stdin ollama run qwen2.5:7b`
- 查看模型：`/models`

模型配置会保存到项目根目录 `models.json`，并默认包含代号“诸葛亮”。

## 军议 AI 聊天工具（Web）

已提供一个前后端打通的 Web 入口：

- 启动服务：`python3 src/server.py`
- 访问地址：`http://127.0.0.1:8765`
- 前端能力：
  - 风格化聊天界面（移动端/桌面端适配）
  - `@代号` 快捷插入
  - 全体协作模式开关
  - 在线添加/更新军师（接入 CLI 模型）
  - 会话历史展示与清空
- 后端 API：
  - `GET /api/models`
  - `POST /api/models`
  - `GET /api/history`
  - `POST /api/chat`
  - `POST /api/reset`

### 使用 Codex CLI 作为军师

可将 Codex CLI 直接接入为一个军师（无需 OpenAI API key）：

- 代号：`诸葛亮`
- 传输：`arg`
- 命令：`codex exec --json`

然后在聊天框里输入：`@诸葛亮 你的问题`
