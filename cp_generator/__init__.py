import json
import random
from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.message.parser.twilight import RegexResult
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    SpacePolicy,
    ParamMatch,
)
from graia.saya import Channel
from graiax.shortcut import listen, dispatch, decorate

from library.decorator import Switch, Distribution, Blacklist, FunctionCall
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message

channel = Channel.current()

with (Path(__file__).parent / "assets" / "cp_data.json").open(
    "r", encoding="utf-8"
) as _f:
    _CP_DATA = json.load(_f)


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        [
            PrefixMatch(),
            FullMatch("cp").space(SpacePolicy.FORCE),
            ParamMatch() @ "attack",
            ParamMatch() @ "defence",
        ]
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def cp_generator(
    app: Ariadne,
    event: GroupMessage | FriendMessage,
    source: Source,
    attack: RegexResult,
    defence: RegexResult,
):
    attack = attack.result.display
    defence = defence.result.display
    template = random.choice(_CP_DATA["data"])
    content = template.replace("<攻>", attack).replace("<受>", defence)
    await send_message(event, MessageChain(content), app.account, quote=source)
