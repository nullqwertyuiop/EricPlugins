import pickle
import random
from pathlib import Path

import aiofiles
from creart import it
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, MessageEvent
from graia.ariadne.exception import UnknownTarget
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import ForwardNode, Forward, At, MultimediaElement
from graia.ariadne.message.parser.twilight import (
    Twilight,
    ElementMatch,
    FullMatch,
)
from graia.ariadne.model import Group
from graiax.shortcut import listen, dispatch, decorate
from graia.saya import Channel

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.function_call import FunctionCall
from library.decorator.switch import Switch
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message
from library.util.module import Modules

channel = Channel.current()
module = it(Modules).get(channel.module)


@listen(GroupMessage)
@dispatch(
    Twilight(
        ElementMatch(At, optional=True), PrefixMatch(optional=True), FullMatch("上传圣经")
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def save_bible(app: Ariadne, event: MessageEvent):
    if not (quote := event.quote):
        return await send_message(
            event,
            MessageChain("用法：\n1. 回复某条消息记录单条消息2. \n回复某条转发消息记录整条消息"),
            app.account,
        )
    try:
        msg: MessageEvent = await app.get_message_from_id(
            quote.id,
            event.sender.group if isinstance(event, GroupMessage) else event.sender,
        )
    except UnknownTarget:
        return await send_message(
            event, MessageChain("暂未缓存该消息，可尝试合并转发后再上传"), app.account
        )
    pickle_id = await _pickle(msg, event)
    await send_message(event, MessageChain(f"已上传圣经 #{pickle_id}"), app.account)


@listen(GroupMessage)
@dispatch(Twilight(PrefixMatch(optional=True), FullMatch("随机圣经")))
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def random_bible(app: Ariadne, event: MessageEvent):
    if not (file := _get_random(event.sender.group)):
        return await send_message(event, MessageChain("暂无已保存的圣经"), app.account)
    forward = await _unpickle(file)
    await send_message(event, MessageChain(forward), app.account)


def _get_random(field: Group) -> Path | None:
    data_path = module.data_path
    if not (group_path := (data_path / str(int(field)))).is_dir():
        return
    if not (files := list(group_path.iterdir())):
        return
    return random.choice(files)


async def _pickle(to_upload: MessageEvent, meta: MessageEvent) -> str:
    group_path = module.data_path / str(int(meta.sender.group))
    group_path.mkdir(exist_ok=True)
    pickle_id = len(list(group_path.iterdir())) + 1
    while (file := group_path / f"{pickle_id}.pkl").is_file():
        pickle_id += 1
    meta_msg = ForwardNode(
        target=meta.sender,
        time=to_upload.source.time,
        message=MessageChain(
            f"圣经 #{file.stem}\n"
            f"由 {meta.sender.name} ({meta.sender.id}) "
            f"于 {meta.source.time:%Y-%m-%d %H:%M:%S} 上传"
        ),
    )
    for element in to_upload.message_chain:
        if isinstance(element, MultimediaElement):
            await element.get_bytes()
    forward = Forward(meta_msg, to_upload)
    async with aiofiles.open(file, "wb") as f:
        await f.write(pickle.dumps(forward))
    return file.stem


async def _unpickle(file: Path) -> Forward:
    async with aiofiles.open(file, "rb") as f:
        data = await f.read()
    forward: Forward = pickle.loads(data)
    assert isinstance(forward, Forward)
    return forward
