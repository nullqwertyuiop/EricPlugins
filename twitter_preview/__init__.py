import re
from datetime import datetime

from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, ForwardNode, Forward
from graia.ariadne.message.parser.twilight import Twilight, WildcardMatch, RegexMatch
from graia.ariadne.util.saya import decorate, dispatch, listen
from graia.saya import Channel
from kayaku import create

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.function_call import FunctionCall
from library.decorator.switch import Switch
from library.model.config.eric import EricConfig
from module.twitter_preview.model.response import ErrorResponse
from module.twitter_preview.util import get_status_id, query

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        [
            WildcardMatch().flags(re.S),
            RegexMatch(
                r"((?:https?://)?(?:www\.)?twitter\.com/[\w\d]+/status/(\d+))|"
                r"((?:https?://)?(?:www\.)?(t\.co/[a-zA-Z\d_.-]{10}))"
            ),
            WildcardMatch(),
        ]
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def twitter_preview(app: Ariadne, event: MessageEvent):
    if not (ids := await get_status_id(event.message_chain.display)):
        return
    response = await query(ids)
    if isinstance(response, bytes):
        return await app.send_message(
            event.sender.group if isinstance(event, GroupMessage) else event.sender,
            MessageChain(Image(data_bytes=response)),
        )
    elif isinstance(response, ErrorResponse):
        msgs = []
    else:
        parsed = response.parse()
        msgs = [await tweet.generate_message() for tweet in parsed]
    if len(msgs) == 1:
        msg_chain = msgs[0]
    else:
        config: EricConfig = create(EricConfig)
        msg_chain = MessageChain(
            Forward(
                [
                    ForwardNode(
                        target=config.account,
                        name=f"{config.name}#{config.num}",
                        time=datetime.now(),
                        message=msg,
                    )
                    for msg in msgs
                ]
            )
        )
    await app.send_message(
        event.sender.group if isinstance(event, GroupMessage) else event.sender,
        msg_chain,
    )
