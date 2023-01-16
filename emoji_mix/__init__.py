from datetime import datetime

from creart import it
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Forward, ForwardNode
from graia.ariadne.message.parser.twilight import (
    Twilight,
    UnionMatch,
    FullMatch,
    RegexResult,
    RegexMatch,
)
from graia.saya import Channel
from graiax.shortcut import listen, dispatch, decorate
from graiax.shortcut.saya import every
from kayaku import create

from library.decorator import Switch, Distribution, Blacklist, FunctionCall
from library.model.config import EricConfig, FunctionConfig
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message
from library.util.session_container import SessionContainer
from module.emoji_mix.util import _ALL_EMOJI, get_mix_emoji_url, get_available_pairs, _download

channel = Channel.current()
_cfg: EricConfig = create(EricConfig)
_prefix = create(FunctionConfig).prefix


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        UnionMatch(*_ALL_EMOJI) @ "left",
        FullMatch("+", optional=True),
        UnionMatch(*_ALL_EMOJI) @ "right",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def emoji_mix(
    app: Ariadne, event: MessageEvent, left: RegexResult, right: RegexResult
):
    left: str = left.result.display
    right: str = right.result.display
    try:
        session = await it(SessionContainer).get(channel.module)
        assert (
            url := get_mix_emoji_url(left, right)
        ), f'不存在该 Emoji 组合，可以发送 "{_prefix[0]}查看 emoji 组合：{left}" 查找可用组合'
        async with session.get(url, proxy=_cfg.proxy) as resp:
            assert resp.status == 200, "图片下载失败"
            image: bytes = await resp.read()
            await send_message(
                event, MessageChain(Image(data_bytes=image)), app.account
            )
    except AssertionError as e:
        await send_message(event, MessageChain(e.args[0]), app.account)


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("查看"),
        RegexMatch(r"[eE][mM][oO][jJ][iI]"),
        FullMatch("组合"),
        RegexMatch(r"[:：] *\S+") @ "keyword",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def emoji_mix(app: Ariadne, event: MessageEvent, keyword: RegexResult):
    keyword = keyword.result.display[1:].strip()
    if pairs := get_available_pairs(keyword):
        return send_message(
            event,
            MessageChain(
                Forward(
                    ForwardNode(
                        target=app.account,
                        time=datetime.now(),
                        message=MessageChain(f"可用 Emoji 组合：\n{', '.join(pairs)}"),
                        name=_cfg.name,
                    )
                )
            ),
            app.account,
        )
    return send_message(event, MessageChain("没有可用的 Emoji 组合"), app.account)


@every(24, mode="hour")
async def emoji_mix_update():
    await _download()
