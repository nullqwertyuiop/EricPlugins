import re
import urllib.parse

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    SpacePolicy,
    WildcardMatch,
    MatchResult,
)
from graia.saya import Channel
from graiax.shortcut import listen, dispatch, decorate

from library.decorator import Switch, Blacklist, FunctionCall
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        [
            PrefixMatch(optional=True),
            FullMatch("百度").space(SpacePolicy.FORCE).flags(re.S),
            WildcardMatch() @ "content",
        ]
    )
)
@decorate(
    Switch.check(channel.module),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def search_shortcut(app: Ariadne, event: MessageEvent, content: MatchResult):
    if content := content.result.display:
        await send_message(
            event,
            MessageChain(f"https://www.baidu.com/s?wd={urllib.parse.quote(content)}"),
            app.account,
            quote=event.source,
        )
