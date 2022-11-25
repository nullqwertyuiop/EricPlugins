import re
from contextlib import suppress

import kayaku
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    WildcardMatch,
    RegexResult,
)
from graia.ariadne.util.saya import listen, dispatch, decorate
from graia.saya import Channel
from kayaku import create

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.permission import Permission
from library.decorator.switch import Switch
from library.decorator.timer import timer
from library.model.permission import UserPerm
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message
from module.ai_draw.config import AIDrawConfig
from module.ai_draw.util import txt2img, parse_msg

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(PrefixMatch(), FullMatch("生成图片"), WildcardMatch().flags(re.S) @ "content")
)
@decorate(Switch.check(channel.module), Distribution.distribute(), Blacklist.check())
@timer(channel.module)
async def sd_webui_generate(app: Ariadne, event: MessageEvent, content: RegexResult):
    content: str = content.result.display
    field = int(event.sender.group) if isinstance(event, GroupMessage) else 0
    supplicant = int(event.sender)
    positive, negative, steps, method, cfg = parse_msg(content)

    if steps > 250:
        return await send_message(
            event, MessageChain("步数过多"), app.account, quote=event.source
        )

    if cfg < 0:
        return await send_message(
            event, MessageChain("CFG 配置错误"), app.account, quote=event.source
        )

    if method not in ["Euler a", "Euler b", "Euler c", "RK4"]:
        return await send_message(
            event,
            MessageChain("方法配置错误，可选：Euler a, Euler b, Euler c, RK4"),
            app.account,
            quote=event.source,
        )

    wait_msg = await send_message(
        event,
        MessageChain("已加入等候队列，请坐和放宽"),
        app.account,
        quote=event.source,
    )
    msg = await txt2img(
        field,
        supplicant,
        positive,
        negative,
        steps,
        method,
        cfg,
    )
    with suppress(Exception):
        await app.recall_message(wait_msg)
    await send_message(event, msg, app.account, quote=event.source)


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("设置"),
        FullMatch("sd"),
        FullMatch("链接"),
        WildcardMatch() @ "content",
    )
)
@decorate(
    Switch.check(channel.module, show_log=True),
    Distribution.distribute(),
    Blacklist.check(),
    Permission.require(UserPerm.BOT_ADMIN),
)
async def sd_webui_set_link(app: Ariadne, event: MessageEvent, content: RegexResult):
    url: str = content.result.display
    url = url.lstrip("http://").lstrip("https://").rstrip("/")  # noqa
    url = f"wss://{url}/queue/join"
    cfg: AIDrawConfig = create(AIDrawConfig)
    cfg.url = url
    kayaku.save(AIDrawConfig)
    await send_message(
        event, MessageChain(f"已设置为 {url}"), app.account, quote=event.source
    )
