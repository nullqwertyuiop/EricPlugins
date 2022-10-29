import random

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

import module.ai_draw.util
from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.permission import Permission
from library.decorator.switch import Switch
from library.model.permission import UserPerm
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message
from module.ai_draw.util import render

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(Twilight(PrefixMatch(), FullMatch("生成图片"), WildcardMatch() @ "content"))
@decorate(Switch.check(channel.module), Distribution.distribute(), Blacklist.check())
async def sd_webui_generate(app: Ariadne, event: MessageEvent, content: RegexResult):
    content: str = content.result.display
    field = int(event.sender.group) if isinstance(event, GroupMessage) else 0
    supplicant = int(event.sender)
    msg = await render(field, supplicant, content)
    await send_message(event, msg, app.account)


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
    url = url.lstrip("http://").lstrip("https://").rstrip("/")
    url = f"wss://{url}/queue/join"
    module.ai_draw.util.SD_URL = url
    await send_message(event, MessageChain(f"已设置为 {url}"), app.account)


@listen(GroupMessage, FriendMessage)
@dispatch(Twilight(PrefixMatch(), FullMatch("test"), WildcardMatch() @ "content"))
@decorate(Switch.check(channel.module), Distribution.distribute(), Blacklist.check())
async def sd_webui_generate(app: Ariadne, event: MessageEvent, content: RegexResult):
    await send_message(event, MessageChain("test"), app.account)
