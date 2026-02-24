#!/usr/bin/env python3
import json
import re
import shutil
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import List, Optional

SYSTEM_PROMPT = "\n".join([
    "你正在参加一场军议。",
    "用户是主公，拥有最终决策权。",
    "所有模型都是军师，应该提供可执行、清晰、互补的建议。",
    "请保持尊重，避免空话，输出聚焦结论和下一步。",
])


class WarCouncil:
    def __init__(self, models_file: Optional[Path] = None):
        self.models_file = models_file or (Path.cwd() / "models.json")
        self.lock = Lock()
        self.models = self._bootstrap_models()
        self.history = []

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def safe_read_json(file: Path):
        if not file.exists():
            return None
        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def write_json(file: Path, data):
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _bootstrap_models(self):
        existing = self.safe_read_json(self.models_file)
        if existing and isinstance(existing.get("models"), list):
            return existing["models"]

        models = [{"alias": "诸葛亮", "description": "内置演示模型", "transport": "mock", "cmd": "", "args": []}]
        self.write_json(self.models_file, {"models": models})
        return models

    def render_history(self):
        if not self.history:
            return "(暂无历史)"
        lines = []
        for i, item in enumerate(self.history, start=1):
            lines.append(f"{i}. [{item['time']}] {item['speaker']}({item['role']}): {item['text']}")
        return "\n".join(lines)

    def build_prompt(self, alias: str, content: str):
        return "\n\n".join([
            f"【系统设定】\n{SYSTEM_PROMPT}",
            f"【你的身份】\n你是军师「{alias}」。",
            f"【完整对话历史】\n{self.render_history()}",
            f"【本轮主公问题】\n{content}",
            "请直接给出回答。",
        ])

    def extract_mentions(self, line: str):
        aliases = [m.get("alias") for m in self.models if m.get("alias")]
        found = re.findall(r"@([^\s@]+)", line)
        unique = []
        for alias in found:
            if alias in aliases and alias not in unique:
                unique.append(alias)
        content = re.sub(r"@([^\s@]+)", "", line).strip()
        return unique, content

    def invoke_model(self, model, prompt: str) -> str:
        transport = model.get("transport", "mock")
        alias = model.get("alias", "未知")

        if transport == "mock":
            marker = "【本轮主公问题】\n"
            question = ""
            if marker in prompt:
                question = prompt.split(marker, 1)[1].split("\n\n", 1)[0].strip()
            return f"【{alias}】主公，建议先定目标、再定约束、最后定执行路径。\n你的问题：{question}"

        cmd = model.get("cmd", "")
        args = list(model.get("args", []))
        if not cmd:
            raise RuntimeError(f"模型 {alias} 缺少 cmd")

        run_args = [cmd] + args
        stdin_data = None
        if transport == "arg":
            run_args.append(prompt)
        elif transport == "stdin":
            stdin_data = prompt
        else:
            raise RuntimeError(f"模型 {alias} transport 不支持: {transport}")

        try:
            proc = subprocess.run(
                run_args,
                input=stdin_data,
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            # Fallback: try resolving command through login shell PATH.
            shell_cmd = " ".join(shlex.quote(x) for x in [cmd] + args)
            if transport == "arg":
                shell_cmd = f"{shell_cmd} {shlex.quote(prompt)}"
            proc = subprocess.run(
                ["/bin/zsh", "-lc", shell_cmd],
                input=stdin_data if transport == "stdin" else None,
                text=True,
                capture_output=True,
                check=False,
            )

        if proc.returncode != 0:
            err = proc.stderr.strip() or "无错误信息"
            hint = ""
            if "command not found" in err or "No such file or directory" in err:
                resolved = shutil.which(cmd)
                if resolved:
                    hint = f"；已检测到命令路径 {resolved}，请确认服务进程有权限执行"
                else:
                    hint = f"；未找到命令 {cmd}，请用绝对路径或先在终端确认 `{cmd}` 可执行"
            raise RuntimeError(f"模型 {alias} 返回非0({proc.returncode})：{err}{hint}")

        out = proc.stdout.strip()
        text = self._normalize_cli_output(out)
        return text or f"模型 {alias} 未返回内容"

    def _normalize_cli_output(self, out: str) -> str:
        if not out:
            return ""

        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if not lines:
            return ""

        json_objs = []
        for line in lines:
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    json_objs.append(obj)
            except Exception:
                pass

        if not json_objs:
            return out

        pieces = []
        for obj in json_objs:
            text = self._extract_text_from_json_obj(obj)
            if text:
                pieces.append(text)

        cleaned = "\n".join([p for p in pieces if p.strip()]).strip()
        return cleaned or out

    def _extract_text_from_json_obj(self, obj):
        if not isinstance(obj, dict):
            return ""

        event_type = obj.get("type")
        if isinstance(event_type, str):
            if event_type == "item.completed":
                item = obj.get("item")
                if isinstance(item, dict):
                    item_type = item.get("type")
                    # Ignore internal reasoning traces; only surface assistant-facing text.
                    if item_type in {"reasoning", "tool_call", "tool_result"}:
                        return ""
                    if item_type in {"agent_message", "assistant_message", "message"}:
                        return self._stringify_text_value(item.get("text") or item.get("content"))
            if event_type in {"response.output_text.delta", "response.output_text"}:
                return self._stringify_text_value(obj.get("delta") or obj.get("text") or obj.get("output_text"))
            if event_type in {"thread.started", "turn.started", "turn.completed"}:
                return ""

        candidates = []
        preferred_keys = ["output_text", "text", "message", "content", "delta", "result", "output", "final"]
        for key in preferred_keys:
            if key in obj:
                value = obj.get(key)
                text = self._stringify_text_value(value)
                if text:
                    candidates.append(text)

        if candidates:
            return "\n".join(candidates).strip()

        return ""

    def _stringify_text_value(self, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            parts = []
            for item in value:
                text = self._stringify_text_value(item)
                if text:
                    parts.append(text)
            return "\n".join(parts).strip()
        if isinstance(value, dict):
            for key in ["text", "content", "message", "output_text", "delta"]:
                if key in value:
                    text = self._stringify_text_value(value.get(key))
                    if text:
                        return text
            for nested in value.values():
                text = self._stringify_text_value(nested)
                if text:
                    return text
            return ""
        return ""

    def get_models(self):
        with self.lock:
            return list(self.models)

    def get_history(self):
        with self.lock:
            return list(self.history)

    def reset_history(self):
        with self.lock:
            self.history = []

    def add_model_from_string(self, rest: str):
        try:
            tokens = shlex.split(rest)
        except ValueError as exc:
            raise ValueError(f"参数解析失败: {exc}") from exc

        if len(tokens) < 2:
            raise ValueError("用法: /add 代号 传输 命令...")

        alias = tokens[0]
        transport = tokens[1]
        remaining = tokens[2:]

        return self.add_model(alias, transport, remaining)

    def add_model(self, alias: str, transport: str, command_tokens: List[str]):
        if not alias.strip():
            raise ValueError("代号不能为空")

        if transport not in {"mock", "stdin", "arg"}:
            raise ValueError("传输方式必须是 mock|stdin|arg")

        if transport != "mock" and not command_tokens:
            raise ValueError("非mock模型必须提供命令")

        cmd = "" if transport == "mock" else command_tokens[0]
        args = [] if transport == "mock" else command_tokens[1:]

        new_model = {"alias": alias, "transport": transport, "cmd": cmd, "args": args}
        with self.lock:
            idx = next((i for i, m in enumerate(self.models) if m.get("alias") == alias), -1)
            if idx >= 0:
                self.models[idx] = new_model
            else:
                self.models.append(new_model)
            self.write_json(self.models_file, {"models": self.models})

        return new_model

    def chat(self, text: str, collaborate: bool = False):
        content = text.strip()
        if not content:
            raise ValueError("请输入要咨询的内容")

        with self.lock:
            if collaborate:
                targets = [m.get("alias") for m in self.models if m.get("alias")]
            else:
                targets, content = self.extract_mentions(content)
                if not targets:
                    raise ValueError("请使用 @代号 指定军师，或开启全体协作")
                if not content:
                    raise ValueError("请输入要咨询的内容")

            self.history.append({"role": "user", "speaker": "主公", "text": content, "time": self.now_iso()})

            replies = []
            for alias in targets:
                model = next((m for m in self.models if m.get("alias") == alias), None)
                if not model:
                    continue

                prompt = self.build_prompt(alias, content)
                try:
                    reply_text = self.invoke_model(model, prompt)
                except Exception as exc:
                    reply_text = f"调用失败：{exc}"

                message = {"role": "assistant", "speaker": alias, "text": reply_text, "time": self.now_iso()}
                self.history.append(message)
                replies.append(message)

        return {"input": content, "replies": replies, "history": self.get_history()}
