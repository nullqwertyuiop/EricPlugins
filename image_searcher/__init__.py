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
from graiax.shortcut import dispatch, listen, decorate
from graia.broadcast.interrupt import InterruptControl
from graia.saya import Channel
from kayaku import create

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.function_call import FunctionCall
from library.decorator.switch import Switch
from library.model.config import EricConfig
from library.util.dispatcher import PrefixMatch
from library.util.group_config.util import module_create
from library.util.message import send_message
from library.util.waiter.friend import FriendImageWaiter
from library.util.waiter.group import GroupImageWaiter
from module.image_searcher.config import ImageSearchGroupConfig
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
    if (quote := event.quote) and (
        images := await _get_image_from_quote(app, quote, event)
    ):
        image = images[0].url
    elif not image.matched:
        bot_msg = await send_message(
            event, MessageChain("请在 30s 内发送要处理的图片"), app.account, quote=event.source
        )
        try:
            if not (
                image := await inc.wait(
                    GroupImageWaiter(event.sender.group, event.sender, force=True)
                    if isinstance(event, GroupMessage)
                    else FriendImageWaiter(event.sender, force=True),
                    timeout=30,
                )
            ):
                await app.recall_message(bot_msg)
                return await send_message(
                    event,
                    MessageChain("未检测到图片，请重新发送，进程退出"),
                    app.account,
                    quote=event.source,
                )
            await app.recall_message(bot_msg)
            image = image.url

        except asyncio.TimeoutError:
            await app.recall_message(bot_msg)
            return await send_message(
                event,
                MessageChain("图片等待超时，进程退出"),
                app.account,
                quote=event.source,
            )
    else:
        image = image.result.url  # type: ignore
    bot_msg = await send_message(
        event,
        MessageChain("已收到图片，正在进行搜索..."),
        app.account,
        quote=event.source,
    )

    eric_config: EricConfig = create(EricConfig)
    search_config: ImageSearchGroupConfig = module_create(
        ImageSearchGroupConfig,
        event.sender.group if isinstance(event, GroupMessage) else 0,
        flush=True
    )
    tasks = [
        asyncio.create_task(engine(proxies=eric_config.proxy, url=image))
        for name, engine in __engines__.items()
        if search_config.__getattribute__(name)
    ]
    msgs = await asyncio.gather(*tasks)
    await app.recall_message(bot_msg)

    bot_msg = await send_message(
        event,
        MessageChain("已完成搜索，正在发送结果..."),
        app.account,
    )
    await send_message(
        event,
        MessageChain(
            [
                Forward(
                    [
                        ForwardNode(
                            target=app.account,
                            time=datetime.now(),
                            name=eric_config.name,
                            message=msg,
                        )
                        for msg in msgs
                    ]
                )
            ]
        ),
        app.account,
    )
    await app.recall_message(bot_msg)


async def _get_image_from_quote(app: Ariadne, quote: Quote, event: MessageEvent):
    msg: MessageEvent = await app.get_message_from_id(
        quote.id,
        event.sender.group if isinstance(event, GroupMessage) else event.sender,
    )
    return msg.message_chain.get(Image)
