#!/usr/bin/env python3
from war_council_core import WarCouncil


def print_help():
    print("\n可用命令：")
    print("  @代号 内容               与指定军师对话，可一次@多个")
    print("  /c 内容                  全体军师协作讨论（顺序发言）")
    print("  /models                  查看已注册军师")
    print("  /add 代号 传输 命令...    动态添加军师；传输=mock|stdin|arg")
    print("  /history                 查看会话历史")
    print("  /help                    查看帮助")
    print("  /exit                    退出\n")


def show_models(models):
    if not models:
        print("当前没有军师，请先 /add")
        return

    for i, model in enumerate(models, start=1):
        transport = model.get("transport", "mock")
        if transport == "mock":
            command = "(内置mock)"
        else:
            args = " ".join(model.get("args", []))
            command = f"{model.get('cmd', '')} {args}".strip()
        print(f"{i}. {model.get('alias', '未知')} | {transport} | {command}")


def main():
    council = WarCouncil()

    print("军议系统已启动。主公，请下令。")
    print("提示：使用 @代号 进行点名，例如：@诸葛亮 给我一份三步计划")
    print_help()

    while True:
        try:
            line = input("主公> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n军议结束。")
            return

        if not line:
            continue

        if line == "/exit":
            print("军议结束。")
            return

        if line == "/help":
            print_help()
            continue

        if line == "/models":
            show_models(council.get_models())
            continue

        if line == "/history":
            print(council.render_history())
            continue

        if line.startswith("/add "):
            try:
                model = council.add_model_from_string(line[5:].strip())
                print(f"已添加/更新军师：{model['alias']}")
            except ValueError as exc:
                print(str(exc))
            continue

        if line.startswith("/c "):
            try:
                result = council.chat(line[3:].strip(), collaborate=True)
                for reply in result["replies"]:
                    print(f"\n{reply['speaker']}> {reply['text']}\n")
            except ValueError as exc:
                print(str(exc))
            continue

        try:
            result = council.chat(line, collaborate=False)
            for reply in result["replies"]:
                print(f"\n{reply['speaker']}> {reply['text']}\n")
        except ValueError as exc:
            print(str(exc))


if __name__ == "__main__":
    main()
