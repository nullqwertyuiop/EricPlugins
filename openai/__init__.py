import asyncio
import json

# import random
import re
from dataclasses import field as dt_field
from pathlib import Path
from typing import TypedDict, Literal

import openai
from creart import it
from graia.ariadne import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message import Source
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.parser.twilight import (
    FullMatch,
    RegexResult,
    SpacePolicy,
    Twilight,
    UnionMatch,
    WildcardMatch,
    ArgumentMatch,
    ArgResult,
)
from graia.ariadne.model import Group
from graia.broadcast.interrupt import InterruptControl, Waiter
from graia.saya import Channel
from graiax.shortcut import decorate, dispatch, listen, priority
from kayaku import config, create
from loguru import logger

# from revChatGPT.V1 import AsyncChatbot
# from revChatGPT.V1 import Error as revChatGPTError

from library.decorator import Blacklist, Distribution, FunctionCall, Permission, Switch
from library.model.config import EricConfig
from library.model.permission import UserPerm
from library.util.dispatcher import PrefixMatch
from library.util.locksmith import LockSmith
from library.util.message import send_message
from library.util.session_container import SessionContainer

channel = Channel.current()


# <editor-fold desc="OpenAI Config">
@config(channel.module)
class _OpenAIConfig:
    api_key: str = ""
    """ OpenAI API Key """

    gpt3_cache: int = 2
    """ GPT-3 缓存对话数量 """

    gpt3_max_token: int = 2000
    """ GPT-3 最大 Token 数量 """

    accounts: dict[str, str] = dt_field(default_factory=dict)
    """ OpenAI 账号，格式为 {账号名: 密码} """

    dalle_switch: bool = True
    """ DallE 开关"""

    gpt3_switch: bool = True
    """ GPT-3 开关 """

    chatgpt_switch: bool = True
    """ ChatGPT 开关 """


openai.api_key = create(_OpenAIConfig).api_key
# </editor-fold>


# <editor-fold desc="OpenAI API Key Flush">
import contextlib


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("openai api flush"),
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Permission.require(UserPerm.BOT_OWNER),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def flush_openai_api_key(app: Ariadne, event: GroupMessage | FriendMessage):
    openai_config: _OpenAIConfig = create(_OpenAIConfig, flush=True)
    openai.api_key = openai_config.api_key
    await send_message(event, MessageChain("OpenAI API Key 已刷新"), app.account)


# </editor-fold>


# <editor-fold desc="OpenAI DallE">
# <editor-fold desc="OpenAI DallE Impl">
async def call_dalle(prompt: str) -> MessageChain:
    logger.info(f"[OpenAI:DALL-E] Generating image: {prompt}")

    def get_url() -> str:
        response = openai.Image.create(prompt=prompt, n=1, size="256x256")
        return response["data"][0]["url"]

    try:
        url = await asyncio.to_thread(get_url)
    except openai.error.OpenAIError as e:
        return MessageChain(f"运行时出现错误：{str(e)}")
    session = await it(SessionContainer).get(channel.module)
    async with session.get(url, proxy=EricConfig.proxy) as resp:
        return MessageChain(Image(data_bytes=await resp.read()))


# </editor-fold>


# <editor-fold desc="OpenAI DallE Prompt">
@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("dalle").space(SpacePolicy.FORCE),
        WildcardMatch().flags(re.S) @ "prompt",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def openai_dalle(app: Ariadne, event: GroupMessage, prompt: RegexResult):
    cfg: _OpenAIConfig = create(_OpenAIConfig)
    if not cfg.dalle_switch:
        return await send_message(event, MessageChain("DallE 功能未开放"), app.account)
    if prompt := prompt.result.display:
        return await send_message(
            event, await call_dalle(prompt), app.account, quote=event.source
        )
    return await send_message(event, MessageChain("请输入 prompt"), app.account)


# </editor-fold>
# </editor-fold>


# <editor-fold desc="OpenAI GPT-3">
# <editor-fold desc="OpenAI GPT-3 Impl">
_GPT_CACHE: dict[str, list[str]] = {}
_GPT_MEMORY: dict[str, str] = {}


async def call_gpt3(prompt: str, field: int, sender: int, name: str) -> MessageChain:
    key = f"{field}-{sender}"
    cfg: _OpenAIConfig = create(_OpenAIConfig)
    async with it(LockSmith).get(f"{channel.module}:gpt3.{key}"):
        logger.info(f"[OpenAI:GPT3] Generating text for {key}: {prompt}")
        _GPT_CACHE.setdefault(key, [])
        _GPT_CACHE[key].append(f"[用户 {name}]:{prompt}")

        final = "\n".join(_GPT_CACHE[key][-cfg.gpt3_cache :]) + "\n[你]:"
        if memory := _GPT_MEMORY.get(key, None):
            final = f"{memory}\n{final}"

        def get_text() -> str:
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=final,
                temperature=0.5,
                max_tokens=cfg.gpt3_max_token,
                frequency_penalty=0.5,
                presence_penalty=0.0,
                stop=["[用户 "],
            )
            return response["choices"][0]["text"]

        try:
            resp = await asyncio.to_thread(get_text)
            _GPT_CACHE[key].append(f"[你]:{resp}")

            # 防止内存泄漏
            _GPT_CACHE[key] = _GPT_CACHE[key][-100:]

        except openai.error.OpenAIError as e:
            return MessageChain(f"运行时出现错误：{str(e)}")

        return MessageChain(resp)


# </editor-fold>


# <editor-fold desc="OpenAI GPT-3 Prompt">
@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("gpt3").space(SpacePolicy.FORCE),
        WildcardMatch().flags(re.S) @ "prompt",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def openai_gpt3(app: Ariadne, event: GroupMessage, prompt: RegexResult):
    cfg: _OpenAIConfig = create(_OpenAIConfig)
    if not cfg.gpt3_switch:
        return await send_message(event, MessageChain("GPT-3 功能未开放"), app.account)
    if prompt := prompt.result.display:
        await send_message(
            event,
            await call_gpt3(
                prompt, int(event.sender.group), int(event.sender), event.sender.name
            ),
            app.account,
            quote=event.source,
        )
    else:
        return


# </editor-fold>


# <editor-fold desc="OpenAI GPT-3 Cache Flush">
@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("openai"),
        FullMatch("gpt3"),
        FullMatch("flush"),
        UnionMatch("all", "group", optional=True) @ "scope",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def flush_gpt3_cache(app: Ariadne, event: GroupMessage, scope: RegexResult):
    cfg: _OpenAIConfig = create(_OpenAIConfig)
    if not cfg.gpt3_switch:
        return await send_message(event, MessageChain("GPT-3 功能未开放"), app.account)
    mapping: dict[str, str] = {"group": "群组", "all": "所有", "user": "用户"}
    scope: str = scope.result.display if scope.matched else "user"
    async with it(LockSmith).get(channel.module):
        match scope:
            case "all":
                if not Permission.check(event.sender, UserPerm.BOT_OWNER):
                    return await send_message(event, MessageChain("权限不足"), app.account)
                for key in _GPT_CACHE:
                    _GPT_CACHE[key] = []
                for key in _GPT_MEMORY.copy():
                    del _GPT_MEMORY[key]
            case "group":
                if not Permission.check(event.sender, UserPerm.ADMINISTRATOR):
                    return await send_message(event, MessageChain("权限不足"), app.account)
                for key in _GPT_CACHE:
                    if key.startswith(f"{int(event.sender.group)}-"):
                        _GPT_CACHE[key] = []
                for key in _GPT_MEMORY.copy():
                    if key.startswith(f"{int(event.sender.group)}-"):
                        del _GPT_MEMORY[key]
            case "user":
                if (
                    key := f"{int(event.sender.group)}-{int(event.sender)}"
                ) in _GPT_CACHE:
                    _GPT_CACHE[key] = []
                if key in _GPT_MEMORY:
                    del _GPT_MEMORY[key]
            case _:
                return await send_message(event, MessageChain("未知范围"), app.account)
        await send_message(
            event, MessageChain(f"{mapping.get(scope)} OpenAI GPT3 缓存已刷新"), app.account
        )


# </editor-fold>


# <editor-fold desc="OpenAI GPT-3 Memorize">
@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("openai"),
        FullMatch("gpt3"),
        FullMatch("memorize"),
        WildcardMatch() @ "content",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def gpt3_memorize(app: Ariadne, event: GroupMessage, content: RegexResult):
    cfg: _OpenAIConfig = create(_OpenAIConfig)
    if not cfg.gpt3_switch:
        return await send_message(event, MessageChain("GPT-3 功能未开放"), app.account)
    if content := content.result.display:
        key = f"{int(event.sender.group)}-{int(event.sender)}"
        overwrite = bool(_GPT_MEMORY.get(key, None))
        _GPT_MEMORY[key] = content
        await send_message(
            event,
            MessageChain(f"OpenAI GPT3 已记住该内容{'并覆盖旧有记忆' if overwrite else ''}"),
            app.account,
        )


# </editor-fold>
# </editor-fold>


# # <editor-fold desc="revChatGPT">
# # <editor-fold desc="revChatGPT Impl">
# _CHAT_GPT_CACHE: dict[int, AsyncChatbot] = {}
#
#
# def exception_revchatgpt(e: Exception) -> MessageChain:
#     s = str(e)
#     if "Too many requests in 1 hour" in s:
#         return MessageChain("1 小时内请求次数过多，请稍后再试")
#     elif "Only one message at a time" in s:
#         return MessageChain("已有请求正在进行，请稍后再试")
#     elif "Hmm...something seems to have gone wrong" in s:
#         return MessageChain("呣...似乎有什么地方出错了，请稍后再试")
#     return MessageChain(f"运行时出现意外错误：{s}")
#
#
# async def call_revchatgpt(prompt: str, field: int) -> MessageChain:
#     if it(LockSmith).get(f"{channel.module}:revchatgpt.{field}").locked():
#         return MessageChain("你先别急，还没说完")
#     async with it(LockSmith).get(f"{channel.module}:openai.{field}"):
#         cfg: _OpenAIConfig = create(_OpenAIConfig)
#         random.seed(field)
#         account = random.choice(list(cfg.accounts.items()))
#         random.seed()
#         bot = _CHAT_GPT_CACHE.setdefault(
#             field,
#             AsyncChatbot(
#                 {
#                     "email": account[0],
#                     "password": account[1],
#                 }
#             ),
#         )
#         try:
#             async for resp in bot.ask(prompt):
#                 pass
#             return MessageChain(resp["message"])
#         except revChatGPTError as e:
#             # 下次再说
#             return exception_revchatgpt(e)
#         except Exception as e:
#             return exception_revchatgpt(e)
#
#
# # </editor-fold>
#
#
# # <editor-fold desc="revChatGPT Prompt">
# @listen(GroupMessage)
# @dispatch(
#     Twilight(
#         PrefixMatch(),
#         FullMatch("chatgpt"),
#         WildcardMatch().flags(re.S) @ "prompt",
#     )
# )
# @decorate(
#     Switch.check(channel.module),
#     Distribution.distribute(),
#     Blacklist.check(),
#     FunctionCall.record(channel.module),
# )
# async def chatgpt(app: Ariadne, event: GroupMessage, prompt: RegexResult):
#     if prompt := prompt.result.display:
#         await send_message(
#             event,
#             await call_revchatgpt(prompt, int(event.sender.group)),
#             app.account,
#             quote=event.source,
#         )
# # </editor-fold>
#
#
# # <editor-fold desc="revChatGPT Cache Flush">
# @listen(GroupMessage)
# @dispatch(
#     Twilight(
#         PrefixMatch(),
#         FullMatch("openai"),
#         FullMatch("chatgpt"),
#         FullMatch("flush"),
#         UnionMatch("all", "group", optional=True) @ "scope",
#     )
# )
# @decorate(
#     Switch.check(channel.module),
#     Distribution.distribute(),
#     Blacklist.check(),
#     FunctionCall.record(channel.module),
# )
# async def flush_chat_gpt_conv(app: Ariadne, event: GroupMessage, scope: RegexResult):
#     mapping: dict[str, str] = {"group": "群组", "all": "所有"}
#     scope: str = scope.result.display if scope.matched else "group"
#
#     async def del_group(_f: int) -> MessageChain | None:
#         try:
#             await _CHAT_GPT_CACHE[_f].delete_conversation(
#                 _CHAT_GPT_CACHE[_f].conversation_id
#             )
#             del _CHAT_GPT_CACHE[_f]
#             logger.info(f"[OpenAI] Deleted conversation {_f}.")
#         except Exception as e:
#             logger.error(f"[OpenAI] Error while deleting conversation: {e}")
#             return MessageChain(f"删除会话时出现错误：{e}")
#
#     async with it(LockSmith).get(channel.module):
#         match scope:
#             case "all":
#                 if not await Permission.check(event.sender, UserPerm.BOT_OWNER):
#                     return await send_message(event, MessageChain("权限不足"), app.account)
#                 for key in _CHAT_GPT_CACHE.copy():
#                     if msg := await del_group(key):
#                         return await send_message(event, msg, app.account)
#             case "group":
#                 if not await Permission.check(event.sender, UserPerm.ADMINISTRATOR):
#                     return await send_message(event, MessageChain("权限不足"), app.account)
#                 if (key := int(event.sender.group)) in _CHAT_GPT_CACHE:
#                     if msg := await del_group(key):
#                         return await send_message(event, msg, app.account)
#             case _:
#                 return await send_message(event, MessageChain("未知范围"), app.account)
#         await send_message(
#             event,
#             MessageChain(f"{mapping.get(scope)} OpenAI ChatGPT 会话已清除"),
#             app.account,
#         )
# # </editor-fold>
# # </editor-fold>


# <editor-fold desc="OpenAI ChatGPT w/ preset">
# <editor-fold desc="OpenAI ChatGPT Cache Store">
class _ChatGPTPreset(TypedDict):
    name: str
    description: str
    content: str


class _ChatGPTLine(TypedDict):
    role: str
    content: str


class _ChatGPTStore:
    presets: dict[str, _ChatGPTPreset]
    cache: dict[int, list[_ChatGPTLine]]
    in_session: set[int]

    def __init__(self):
        self.presets = {}
        self.cache = {}
        self.in_session = set()
        self.load_presets()

    def load_presets(self):
        data = (Path(__file__).parent / "assets" / "presets.json").read_text("utf-8")
        self.presets = json.loads(data)

    def fill_preset(self, name: str, field: int):
        if name in self.presets:
            preset: _ChatGPTPreset = self.presets[name]
        else:
            preset = next(filter(lambda x: x["name"] == name, self.presets.values()))
        self.cache.setdefault(field, [])
        self.cache[field].insert(0, {"role": "system", "content": preset["content"]})

    def flush(self, field: int, keep_system: bool = True):
        self.cache.setdefault(field, [])
        has_system: bool = (
            len(self.cache[field]) and self.cache[field][0]["role"] == "system"
        )
        self.cache[field] = self.cache[field][:1] if has_system and keep_system else []

    def flush_all(self, keep_system: bool = True):
        for key in self.cache:
            self.flush(key, keep_system=keep_system)

    def pop_head(self, field: int):
        self.cache.setdefault(field, [])
        has_system: bool = (
            len(self.cache[field]) and self.cache[field][0]["role"] == "system"
        )
        self.cache[field].pop(1 if has_system else 0)

    def get(self, field: int):
        self.cache.setdefault(field, [])
        return self.cache[field]

    def add(self, field: int, role: Literal["user", "assistant"], content: str):
        self.cache.setdefault(field, [])
        self.cache[field].append({"role": role, "content": content})


_chatgpt_store = _ChatGPTStore()
# </editor-fold>


# <editor-fold desc="OpenAI ChatGPT Impl">
async def call_chatgpt(prompt: str, field: int) -> MessageChain:
    if it(LockSmith).get(f"{channel.module}:chatgpt.{field}").locked():
        return MessageChain("你先别急，还没说完")
    async with it(LockSmith).get(f"{channel.module}:chatgpt.{field}"):
        logger.info(f"[OpenAI:ChatGPT] Generating text for {field}: {prompt}")
        _chatgpt_store.add(field, "user", prompt)

        def get_text() -> str:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=_chatgpt_store.get(field)
            )
            return response["choices"][0]["message"]["content"]

        pops = 3
        while (pops := pops - 1) >= 0:
            try:
                resp = await asyncio.to_thread(get_text)
                _chatgpt_store.add(field, "assistant", resp)
                return MessageChain(resp)

            except openai.error.OpenAIError as e:
                if "maximum context length" in (e := str(e)):
                    _chatgpt_store.pop_head(field)
                    continue
                _chatgpt_store.cache[field].pop()
                return MessageChain(f"运行时出现错误：{e}")


# </editor-fold>


# <editor-fold desc="OpenAI ChatGPT Prompt">
class _ChatGPTWaiter(Waiter.create([GroupMessage])):
    def __init__(self, group: Group | int, *sources: Source | int):
        self.group_id = int(group)
        self.sources = {int(source) for source in sources}

    async def detected_event(
        self,
        app: Ariadne,
        group: Group,
        event: GroupMessage,
    ):
        await Distribution.judge(app, event, event.source)
        if int(group) != self.group_id:
            return
        if event.quote and event.quote.id in self.sources:
            return event
        with contextlib.suppress(ValueError):
            if Twilight(
                PrefixMatch(),
                FullMatch("chatgpt"),
                WildcardMatch().flags(re.S) @ "prompt",
            ).generate(event.message_chain):
                return event


_CHATGPT_TWILIGHT = Twilight(
    PrefixMatch(),
    FullMatch("chatgpt"),
    ArgumentMatch("-p", "--preset", optional=True, type=str) @ "preset",
    WildcardMatch().flags(re.S) @ "prompt",
)


@listen(GroupMessage)
@dispatch(_CHATGPT_TWILIGHT)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def chatgpt(
    app: Ariadne, event: GroupMessage, preset: ArgResult, prompt: RegexResult
):
    if (gid := int(event.sender.group)) in _chatgpt_store.in_session:
        return
    if preset.matched:
        if (preset.result not in _chatgpt_store.presets) and not next(
            filter(
                lambda x: x.get("name", "") == preset.result,
                _chatgpt_store.presets.values(),
            ),
            None,
        ):
            return await send_message(
                event,
                MessageChain(
                    f"预设 {preset.result} 不存在，当前内置预设：\n"
                    + "\n".join(
                        [
                            f"{i} ({v['name']})：{v['description']}"
                            for i, v in _chatgpt_store.presets.items()
                        ]
                    )
                ),
                app.account,
            )
        _chatgpt_store.fill_preset(preset.result, gid)
    if not (prompt := prompt.result.display) or not (
        msg := await send_message(
            event,
            await call_chatgpt(prompt, gid),
            app.account,
            quote=event.source,
        )
    ):
        return
    try:
        _chatgpt_store.in_session.add(gid)
        sources = {int(msg.source)}
        while gid in _chatgpt_store.in_session:
            if waiter_msg := await it(InterruptControl).wait(
                _ChatGPTWaiter(
                    event.sender.group,
                    *sources,
                ),
                timeout=600,
            ):
                if gid not in _chatgpt_store.in_session:
                    return
                waiter_msg: GroupMessage
                try:
                    prompt = (
                        _CHATGPT_TWILIGHT.generate(waiter_msg.message_chain)
                        .get("prompt")
                        .result.display
                    )
                except (KeyError, ValueError):
                    prompt = waiter_msg.message_chain.display
                if reply := await send_message(
                    waiter_msg,
                    await call_chatgpt(prompt, gid),
                    app.account,
                    quote=waiter_msg.source,
                ):
                    sources.add(int(reply.source))
    except asyncio.exceptions.TimeoutError:
        return
    finally:
        if gid in _chatgpt_store.in_session:
            _chatgpt_store.in_session.remove(gid)


# </editor-fold>


# <editor-fold desc="OpenAI ChatGPT Cache Flush">
@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("openai"),
        FullMatch("chatgpt"),
        FullMatch("flush"),
        UnionMatch("all", "group", optional=True) @ "scope",
        ArgumentMatch("-s", "--system", action="store_true", default=False) @ "system",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
@priority(10)
async def flush_chat_gpt_conv(
    app: Ariadne, event: GroupMessage, scope: RegexResult, system: ArgResult
):
    mapping: dict[str, str] = {"group": "群组", "all": "所有"}
    scope: str = scope.result.display if scope.matched else "group"
    flush_system: bool = system.result
    async with it(LockSmith).get(channel.module):
        match scope:
            case "all":
                if not await Permission.check(event.sender, UserPerm.BOT_OWNER):
                    return await send_message(event, MessageChain("权限不足"), app.account)
                _chatgpt_store.flush_all(keep_system=not flush_system)
                _chatgpt_store.in_session.clear()
            case "group":
                if not await Permission.check(event.sender, UserPerm.ADMINISTRATOR):
                    return await send_message(event, MessageChain("权限不足"), app.account)
                _chatgpt_store.flush(
                    int(event.sender.group), keep_system=not flush_system
                )
                if int(event.sender.group) in _chatgpt_store.in_session:
                    _chatgpt_store.in_session.remove(int(event.sender.group))
            case _:
                return await send_message(event, MessageChain("未知范围"), app.account)
        await send_message(
            event,
            MessageChain(f"{mapping.get(scope)} OpenAI ChatGPT 会话已清除"),
            app.account,
        )


# </editor-fold>
# </editor-fold>
