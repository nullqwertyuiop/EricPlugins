import asyncio
import random
import re
from dataclasses import field as dt_field

import openai
from creart import it
from graia.ariadne import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.parser.twilight import (
    FullMatch,
    RegexResult,
    SpacePolicy,
    Twilight,
    UnionMatch,
    WildcardMatch,
)
from graia.saya import Channel
from graiax.shortcut import decorate, dispatch, listen
from kayaku import config, create
from loguru import logger
from revChatGPT.V1 import AsyncChatbot
from revChatGPT.V1 import Error as revChatGPTError

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


openai.api_key = create(_OpenAIConfig).api_key
# </editor-fold>


# <editor-fold desc="OpenAI API Key Flush">
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


# <editor-fold desc="revChatGPT Impl">
_CHAT_GPT_CACHE: dict[int, AsyncChatbot] = {}


def exception_revchatgpt(e: revChatGPTError) -> MessageChain:
    s = str(e)
    if "Too many requests in 1 hour" in s:
        return MessageChain("1 小时内请求次数过多，请稍后再试")
    elif "Only one message at a time" in s:
        return MessageChain("已有请求正在进行，请稍后再试")
    return MessageChain(f"运行时出现错误：{s}")


async def call_revchatgpt(prompt: str, field: int) -> MessageChain:
    if it(LockSmith).get(f"{channel.module}:openai.{field}").locked():
        return MessageChain("你先别急，还没说完")
    async with it(LockSmith).get(f"{channel.module}:openai.{field}"):
        cfg: _OpenAIConfig = create(_OpenAIConfig)
        random.seed(field)
        account = random.choice(list(cfg.accounts.items()))
        random.seed()
        bot = _CHAT_GPT_CACHE.setdefault(
            field,
            AsyncChatbot(
                {
                    "email": account[0],
                    "password": account[1],
                }
            ),
        )
        try:
            async for resp in bot.ask(prompt):
                pass
            return MessageChain(resp["message"])
        except revChatGPTError as e:
            return exception_revchatgpt(e)
        except Exception as e:
            return MessageChain(f"运行时出现意外错误：{str(e)}")


# </editor-fold>


@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("chatgpt"),
        WildcardMatch().flags(re.S) @ "prompt",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def chatgpt(app: Ariadne, event: GroupMessage, prompt: RegexResult):
    if prompt := prompt.result.display:
        await send_message(
            event,
            await call_revchatgpt(prompt, int(event.sender.group)),
            app.account,
            quote=event.source,
        )


@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("openai"),
        FullMatch("chatgpt"),
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
async def flush_chat_gpt_conv(app: Ariadne, event: GroupMessage, scope: RegexResult):
    mapping: dict[str, str] = {"group": "群组", "all": "所有"}
    scope: str = scope.result.display if scope.matched else "group"

    async def del_group(_f: int) -> MessageChain | None:
        try:
            await _CHAT_GPT_CACHE[_f].delete_conversation(
                _CHAT_GPT_CACHE[_f].conversation_id
            )
            del _CHAT_GPT_CACHE[_f]
            logger.info(f"[OpenAI] Deleted conversation {_f}.")
        except Exception as e:
            logger.error(f"[OpenAI] Error while deleting conversation: {e}")
            return MessageChain(f"删除会话时出现错误：{e}")

    async with it(LockSmith).get(channel.module):
        match scope:
            case "all":
                if not Permission.check(event.sender, UserPerm.BOT_OWNER):
                    return await send_message(event, MessageChain("权限不足"), app.account)
                for key in _CHAT_GPT_CACHE.copy():
                    if msg := await del_group(key):
                        return await send_message(event, msg, app.account)
            case "group":
                if not Permission.check(event.sender, UserPerm.ADMINISTRATOR):
                    return await send_message(event, MessageChain("权限不足"), app.account)
                if (key := int(event.sender.group)) in _CHAT_GPT_CACHE:
                    if msg := await del_group(key):
                        return await send_message(event, msg, app.account)
            case _:
                return await send_message(event, MessageChain("未知范围"), app.account)
        await send_message(
            event,
            MessageChain(f"{mapping.get(scope)} OpenAI ChatGPT 会话已清除"),
            app.account,
        )
