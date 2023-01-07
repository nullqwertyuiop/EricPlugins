import re

from creart import it
from fastapi import HTTPException
from graia.ariadne import Ariadne
from graia.ariadne.event.lifecycle import ApplicationLaunched
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    WildcardMatch,
    RegexResult,
    ArgumentMatch,
    ArgResult,
)
from graiax.shortcut import listen, dispatch, decorate
from graia.broadcast.builtin.decorators import Depend
from graia.saya import Channel
from graiax.fastapi.saya import route
from starlette.responses import FileResponse

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.function_call import FunctionCall
from library.decorator.switch import Switch
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message
from library.util.module import Modules
from module.closure_talk.decorator import session_check
from module.closure_talk.model.chat import ClosureChatArea
from module.closure_talk.util import (
    check_avatar,
    ClosureStore,
    _closure_data_initialize,
)

channel = Channel.current()


@route.get("/module/closure_talk/character")
async def closure_talk_get_character(identifier: str, name: str):
    module = it(Modules).get(channel.module)
    if not (identifier_path := module.data_path / "resources" / identifier).is_dir():
        raise HTTPException(status_code=404, detail="Identifier not found")
    name = name.replace(":", "#")
    if not (character := list((identifier_path / "characters").glob(f"{name}.*"))):
        raise HTTPException(status_code=404, detail="Character not found")
    return FileResponse(character[0])


@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("开始对话"),
        ArgumentMatch("-i", "--identifier", type=str, default="ak") @ "identifier",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def closure_talk_start_session(
    app: Ariadne,
    event: GroupMessage,
    identifier: ArgResult,
):
    group = event.sender.group
    identifier: str = identifier.result
    if identifier not in (keys := ClosureStore.characters.keys()):
        return await send_message(
            event, MessageChain(f"未找到该角色组，可用的角色组有：{', '.join(keys)}"), app.account
        )
    if int(group) in ClosureStore.session.keys():
        return await send_message(event, MessageChain("当前群聊已经有对话在进行中"), app.account)
    ClosureStore.start(identifier, group)
    await send_message(
        event,
        MessageChain(
            '已开始记录，可发送 ".结束对话" 结束并渲染\n'
            '发送 "$内容" 以开始加入对话\n'
            "可更改名片为角色名，以便渲染对应头像\n"
            "建议使用英文角色名以获得更高准确度"
        ),
        app.account,
    )


@listen(GroupMessage)
@dispatch(Twilight(FullMatch("$"), WildcardMatch().flags(re.S) @ "content"))
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def closure_talk_in_session(
    event: GroupMessage,
    content: RegexResult,
    session: tuple[str, ClosureChatArea] = Depend(session_check),
):
    content: str = content.result.display
    identifier, chat_area = session
    chat_area.add(identifier, content, *check_avatar(event.sender))


@listen(GroupMessage)
@dispatch(Twilight(PrefixMatch(), FullMatch("结束对话")))
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def closure_talk_end_session(
    app: Ariadne,
    event: GroupMessage,
    session: tuple[str, ClosureChatArea] = Depend(session_check),
):
    try:
        msg = await send_message(event, MessageChain("正在渲染对话内容..."), app.account)
        _, chat_area = session
        data = await chat_area.render()
        await send_message(event, MessageChain(Image(data_bytes=data)), app.account)
        await app.recall_message(msg)
    finally:
        ClosureStore.end(event.sender.group)


@listen(ApplicationLaunched)
async def closure_talk_init():
    await _closure_data_initialize()
