def resolve_key(key: str) -> tuple[bool, int]:
    if ":" not in key:
        raise ValueError
    scope, target = key.split(":", maxsplit=1)
    if scope not in {"group", "friend"} or not target.isdigit():
        raise ValueError
    return scope == "group", int(target)


def _gen_msg_call(content: list[str]) -> str:
    if len(content) < 5:
        raise ValueError
    _ = content.pop(0)
    device = content.pop().lstrip("device=")
    time = content.pop().lstrip("time=")
    sim = content.pop().lstrip("sim=")
    caller = "\n".join(content).lstrip("caller=")
    return f"收到来自 {caller} 的电话\n时间：{time}\n卡槽：{sim}\n设备：{device}"


def _gen_msg_sms(content: list[str]) -> str:
    if len(content) < 6:
        raise ValueError
    _ = content.pop(0)
    sender = content.pop(0).lstrip("sender=")
    device = content.pop().lstrip("device=")
    time = content.pop().lstrip("time=")
    sim = content.pop().lstrip("sim=")
    body = "\n".join(content).lstrip("body=")
    return (
        f"收到来自 {sender} 的短信\n"
        f"内容：{body}\n"
        f"时间：{time}\n"
        f"卡槽：{sim}\n"
        f"设备：{device}"
    )


def _gen_msg_notification(content: list[str]) -> str:
    if len(content) < 6:
        raise ValueError
    _ = content.pop(0)
    app = content.pop(0).lstrip("app=")
    device = content.pop().lstrip("device=")
    time = content.pop().lstrip("time=")

    is_title = True
    title = []
    body = []
    for part in content:
        print(part)
        if part.startswith("body="):
            is_title = False
        title.append(part) if is_title else body.append(part)
    title = "\n".join(title).lstrip("title=")
    body = "\n".join(body).lstrip("body=")

    return (
        f"收到来自 {app} 的通知\n标题：{title}\n内容：{body}\n时间：{time}\n设备：{device}"
    )


def gen_msg(content: list[str]) -> str:
    match content[0]:
        case "type=sms":
            return _gen_msg_sms(content)
        case "type=call":
            return _gen_msg_call(content)
        case "type=notification":
            return _gen_msg_notification(content)
        case _:
            raise ValueError
