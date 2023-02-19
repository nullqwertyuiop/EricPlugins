import asyncio

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, Group, GroupMessage
from graia.ariadne.message.chain import Image, MessageChain
from graia.ariadne.message.parser.twilight import (
    ArgResult,
    ArgumentMatch,
    FullMatch,
    Twilight,
)
from graia.saya import Channel
from graiax.shortcut import decorate, dispatch, listen

from library.decorator import Blacklist, Distribution, FunctionCall, Switch
from library.util.dispatcher import PrefixMatch
from module.the_wandering_earth_counting_down.utils import gen_counting_down, gen_gif

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        [
            PrefixMatch(),
            FullMatch("流浪地球"),
            ArgumentMatch("-t", "--top") @ "top",
            ArgumentMatch("-s", "--start") @ "start",
            ArgumentMatch("-c", "--count") @ "count",
            ArgumentMatch("-e", "--end") @ "end",
            ArgumentMatch("-b", "--bottom") @ "bottom",
            ArgumentMatch("--rgba", optional=True, action="store_true") @ "rgba",
            ArgumentMatch("--gif", optional=True, action="store_true") @ "gif",
        ]
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def wandering_earth_counting_down(
    app: Ariadne,
    group: Group,
    top: ArgResult,
    start: ArgResult,
    count: ArgResult,
    end: ArgResult,
    bottom: ArgResult,
    rgba: ArgResult,
    gif: ArgResult,
):
    top = top.result.display.strip('"').strip("'")
    start = start.result.display.strip('"').strip("'")
    count = count.result.display.strip('"').strip("'")
    end = end.result.display.strip('"').strip("'")
    bottom = bottom.result.display.strip('"').strip("'")
    if gif.matched and not count.isnumeric():
        return await app.send_group_message(
            group, MessageChain("生成 gif 时 count 必须为数字！")
        )
    elif gif.matched and int(count) > 100:
        return await app.send_group_message(
            group, MessageChain("生成 gif 时 count 最大仅支持100！")
        )
    content = await asyncio.to_thread(
        gen_gif if gif.matched else gen_counting_down,
        top,
        start,
        count,
        end,
        bottom,
        rgba.matched,
    )
    await app.send_group_message(group, MessageChain(Image(data_bytes=content)))
