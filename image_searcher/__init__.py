import asyncio
from datetime import datetime

from creart import it
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import (
    GroupMessage,
    FriendMessage,
    MessageEvent,
)
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image, Forward, ForwardNode, Quote
from graia.ariadne.message.parser.twilight import Twilight
from graia.ariadne.message.parser.twilight import (
    UnionMatch,
    RegexMatch,
    ElementMatch,
    ElementResult,
)
from graia.ariadne.util.saya import dispatch, listen, decorate
from graia.broadcast.interrupt import InterruptControl
from graia.saya import Channel
from kayaku import create

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.function_call import FunctionCall
from library.decorator.switch import Switch
from library.model.config.eric import EricConfig
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message
from library.util.waiter.friend import FriendImageWaiter
from library.util.waiter.group import GroupImageWaiter
from module.image_searcher.engines import __engines__

channel = Channel.current()
inc = it(InterruptControl)


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        [
            ElementMatch(At, optional=True),
            PrefixMatch(),
            UnionMatch("搜图", "识图", "以图搜图"),
            RegexMatch(r"[\s]+", optional=True),
            ElementMatch(Image, optional=True) @ "image",
        ]
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def image_searcher(
    app: Ariadne,
    event: MessageEvent,
    image: ElementResult,
):
    if (quote := event.quote) and (images := await _get_image_from_quote(app, quote, event)):
        image = images[0].url
    elif not image.matched:
        try:
            await send_message(
                event, MessageChain("请在 30s 内发送要处理的图片"), app.account, quote=event.source
            )
            if not (
                image := await inc.wait(
                    GroupImageWaiter(event.sender.group, event.sender, force=True)
                    if isinstance(event, GroupMessage)
                    else FriendImageWaiter(event.sender, force=True),
                    timeout=30,
                )
            ):
                return await send_message(
                    event,
                    MessageChain("未检测到图片，请重新发送，进程退出"),
                    app.account,
                    quote=event.source,
                )
            image = image.url

        except asyncio.TimeoutError:
            return await send_message(
                event,
                MessageChain("图片等待超时，进程退出"),
                app.account,
                quote=event.source,
            )
    else:
        image = image.result.url  # type: ignore
    await send_message(
        event,
        MessageChain("已收到图片，正在进行搜索..."),
        app.account,
        quote=event.source,
    )

    config: EricConfig = create(EricConfig)
    tasks = [
        asyncio.create_task(engine(proxies=config.proxy, url=image))
        for engine in __engines__.values()
    ]
    msgs = await asyncio.gather(*tasks)
    await send_message(
        event,
        MessageChain(
            [
                Forward(
                    [
                        ForwardNode(
                            target=app.account,
                            time=datetime.now(),
                            name=config.name,
                            message=msg,
                        )
                        for msg in msgs
                    ]
                )
            ]
        ),
        app.account,
    )


async def _get_image_from_quote(app: Ariadne, quote: Quote, event: MessageEvent):
    msg: MessageEvent = await app.get_message_from_id(
        quote.id,
        event.sender.group if isinstance(event, GroupMessage) else event.sender,
    )
    return msg.message_chain.get(Image)
