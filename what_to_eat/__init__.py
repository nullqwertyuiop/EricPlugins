import random
from pathlib import Path

from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    RegexMatch,
    RegexResult,
)
from graia.ariadne.util.saya import listen, dispatch, decorate
from graia.saya import Channel

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.switch import Switch
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message

channel = Channel.current()

ASSETS_PATH = Path(__file__).parent / "assets"
with (ASSETS_PATH / "foods.txt").open() as f:
    FOODS = f.read().splitlines()


@listen(GroupMessage, FriendMessage)
@dispatch(Twilight(PrefixMatch(), FullMatch("吃什么")))
@decorate(Switch.check(channel.module), Distribution.distribute(), Blacklist.check())
async def what_to_eat_direct(app: Ariadne, event: MessageEvent):
    _food = FOODS.copy()
    random.shuffle(_food)
    await send_message(
        event.sender.group if isinstance(event, GroupMessage) else event.sender,
        MessageChain("今天吃 " + " ".join(_food[:3]) + " 吧！"),
        app.account,
    )


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        PrefixMatch(), FullMatch("吃哪"), RegexMatch(r"(\d+)") @ "amount", FullMatch("样")
    )
)
@decorate(Switch.check(channel.module), Distribution.distribute(), Blacklist.check())
async def what_to_eat_custom(app: Ariadne, event: MessageEvent, amount: RegexResult):
    amount: int = int(amount.result.display)
    if amount > 10:
        return await send_message(
            event.sender.group if isinstance(event, GroupMessage) else event.sender,
            MessageChain("吃这么多？"),
            app.account,
        )
    elif amount == 0:
        return await send_message(
            event.sender.group if isinstance(event, GroupMessage) else event.sender,
            MessageChain("吃啥？"),
            app.account,
        )
    _food = FOODS.copy()
    random.shuffle(_food)
    await send_message(
        event.sender.group if isinstance(event, GroupMessage) else event.sender,
        MessageChain("今天吃 " + " ".join(_food[:amount]) + " 吧！"),
        app.account,
    )
