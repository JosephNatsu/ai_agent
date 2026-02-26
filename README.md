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
  - `GET /api/memory/dates`（按日期查看摘要/话题，支持 `?q=关键词`）
  - `GET /api/memory/date?date=YYYY-MM-DD`（查看某天完整聊天内容）

### 使用 Codex CLI 作为军师

可将 Codex CLI 直接接入为一个军师（无需 OpenAI API key）：

- 代号：`诸葛亮`
- 传输：`arg`
- 命令：`codex exec --json`

然后在聊天框里输入：`@诸葛亮 你的问题`

### 使用 Qwen CLI 作为军师

Qwen 的 `-p` 需要紧跟 prompt，本项目支持 `{prompt}` 占位符：

- 代号：`仲达`
- 传输：`arg`
- 命令：`qwen -p {prompt} --output-format stream-json`

系统会自动从 stream-json 中提取最终回答文本（过滤 `thinking/system` 事件）。

## 本地历史记忆（按日期）

系统会把聊天记录按日期持久化到本地：

- 目录：`data/history/`
- 原始记录：`data/history/YYYY-MM-DD.jsonl`
- 话题索引与每日摘要：`data/history/index.json`

记忆能力：

- 前端左侧可先按日期查看“当天聊了哪些话题”，再查看该天完整聊天。
- 支持按关键词检索日期摘要。
- 后端在构建军师 prompt 时，只注入“最近会话节选 + 相关日期摘要”，减少上下文长度和 token 消耗，同时保留历史可回忆性。
