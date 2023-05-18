import asyncio
import contextlib
import random
import re

import openai
from creart import it
from graia.ariadne import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from graia.ariadne.message.parser.twilight import (
    ArgResult,
    ArgumentMatch,
    FullMatch,
    RegexResult,
    SpacePolicy,
    Twilight,
    UnionMatch,
    WildcardMatch,
)
from graia.saya import Channel
from graiax.shortcut import decorate, dispatch, listen
from kayaku import create
from loguru import logger

from library.decorator import Blacklist, Distribution, FunctionCall, Permission, Switch
from library.decorator.chain import QuotingOrAtMe
from library.model.config import EricConfig
from library.model.message import RebuiltMessage
from library.model.permission import UserPerm
from library.util.dispatcher import PrefixMatch
from library.util.locksmith import LockSmith
from library.util.message import send_message
from library.util.session_container import SessionContainer
from library.util.typ import Message
from module.openai.config import OpenAIConfig
from module.openai.impl import ChatSessionContainer
from module.openai.help import chat_help

channel = Channel.current()

openai.api_key = random.choice(create(OpenAIConfig).api_keys)


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
    openai_config: OpenAIConfig = create(OpenAIConfig, flush=True)
    openai.api_key = random.choice(openai_config.api_keys)
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
    cfg: OpenAIConfig = create(OpenAIConfig)
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
    cfg: OpenAIConfig = create(OpenAIConfig)
    async with it(LockSmith).get(f"{channel.module}:gpt3.{key}"):
        logger.info(f"[OpenAI:GPT3] Generating text for {key}: {prompt}")
        _GPT_CACHE.setdefault(key, [])
        _GPT_CACHE[key].append(f"[用户 {name}]:{prompt}")

        final = "\n".join(_GPT_CACHE[key][-cfg.gpt3_cache :]) + "\n[你]:"
        if memory := _GPT_MEMORY.get(key):
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
    cfg: OpenAIConfig = create(OpenAIConfig)
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
    cfg: OpenAIConfig = create(OpenAIConfig)
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
    cfg: OpenAIConfig = create(OpenAIConfig)
    if not cfg.gpt3_switch:
        return await send_message(event, MessageChain("GPT-3 功能未开放"), app.account)
    if content := content.result.display:
        key = f"{int(event.sender.group)}-{int(event.sender)}"
        overwrite = bool(_GPT_MEMORY.get(key))
        _GPT_MEMORY[key] = content
        await send_message(
            event,
            MessageChain(f"OpenAI GPT3 已记住该内容{'并覆盖旧有记忆' if overwrite else ''}"),
            app.account,
        )


# </editor-fold>
# </editor-fold>


# <editor-fold desc="OpenAI ChatGPT Prompt (Deprecated)">
@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("chatgpt"),
        WildcardMatch().flags(re.S),
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def chatgpt(app: Ariadne, event: GroupMessage):
    await send_message(event, MessageChain("该使用方法已被弃用，请直接回复或 at 机器人使用"), app.account)


# </editor-fold>


@listen(GroupMessage, FriendMessage)
@dispatch(
    CHAT_TWILIGHT := Twilight(
        PrefixMatch().help(f"{PrefixMatch.get_prefix()[0]}chat"),
        FullMatch("chat"),
        ArgumentMatch("-h", "--help", action="store_true", default=False).help(
            "获取当前的帮助"
        )
        @ "get_help",
        ArgumentMatch("--set-system", type=str, default=None).help(
            "输入并替换系统提示，提示内容会显著影响生成结果"
        )
        @ "system_prompt",
        ArgumentMatch("-f", "--flush", action="store_true", default=False).help(
            "清除当前会话记录"
        )
        @ "flush",
        ArgumentMatch("-s", "--system", action="store_true", default=False).help(
            "清除当前会话记录，包括系统提示"
        )
        @ "flush_system",
        ArgumentMatch("-x", "--export", action="store_true", default=False).help(
            "导出一条会话链条"
        )
        @ "export",
        ArgumentMatch("-T", "--timeout", type=int, default=None).help("设置等待超时时间")
        @ "timeout",
        ArgumentMatch("-c", "--cache", type=int, default=None).help(
            "更改缓存区上下文大小，不建议设置过大或过小"
        )
        @ "cache",
        ArgumentMatch("-t", "--temperature", type=float, default=None).help(
            "更改模型 temperature 值，越低的值会使结果更加贴近上下文，越高的值会使结果更加随机"
        )
        @ "temperature",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def chat_completion_init(
    app: Ariadne,
    event: Message,
    get_help: ArgResult,
    system_prompt: ArgResult,
    flush: ArgResult,
    flush_system: ArgResult,
    export: ArgResult,
    timeout: ArgResult,
    cache: ArgResult,
    temperature: ArgResult,
):
    get_help: bool = get_help.result
    system_prompt: str | None = system_prompt.result
    flush: bool = flush.result
    flush_system: bool = flush_system.result
    export: bool = export.result
    timeout: int | None = timeout.result
    cache: int | None = cache.result
    temperature: float | None = temperature.result
    if get_help:
        return await send_message(
            event,
            MessageChain(Image(data_bytes=await chat_help())),
            app.account,
        )
    if system_prompt is not None and (flush or flush_system or export):
        return await send_message(
            event,
            MessageChain("参数错误，--flush/--system/--export 与其他参数不能同时使用"),
            app.account,
        )
    elif not flush and flush_system:
        return await send_message(
            event,
            MessageChain("参数错误，--system 不能单独使用"),
            app.account,
        )
    elif flush and export:
        return await send_message(
            event, MessageChain("参数错误，--flush 与 --export 不能同时使用"), app.account
        )
    session = ChatSessionContainer.get_or_create(
        -int(event.sender)
        if isinstance(event, FriendMessage)
        else int(event.sender.group)
    )
    if flush:
        return await session.flush(app, event, flush_system)
    if export:
        return (
            await session.get_chain(app, event, event.quote)
            if event.quote
            else await send_message(
                event, MessageChain("--export 仅能在回复 Chat 消息时使用"), app.account
            )
        )
    actions = 0
    try:
        if system_prompt is not None:
            session.instance.system = system_prompt
            actions += 1
        if timeout:
            assert timeout > 15, "超时时间过短"
            session.instance.timeout = timeout
            actions += 1
        if cache:
            assert cache >= 2, "缓存区大小过小"
            session.instance.cache_size = cache
            actions += 1
        if temperature:
            assert 0 <= temperature <= 2, "temperature 超出范围"
            session.instance.temperature = temperature
            actions += 1
        return await send_message(
            event,
            MessageChain(
                f"已完成 {actions} 项操作"
                if actions
                else f'未给定参数，可发送 "{PrefixMatch.get_prefix()[0]}chat --help" 查看帮助'
            ),
            app.account,
        )
    except AssertionError as e:
        return await send_message(
            event, MessageChain(f"进行操作时出现错误：{str(e)}"), app.account
        )


@listen(GroupMessage)
@decorate(
    Switch.check(channel.module, show_log=False),
    QuotingOrAtMe(),
    Distribution.distribute(),
    Blacklist.check(),
)
async def chat_completion_impl_group(
    app: Ariadne, event: GroupMessage, chain: MessageChain
):
    if re.fullmatch(
        rf"^\s*[{re.escape(''.join(PrefixMatch.get_prefix()))}]+.*$",
        (text := "".join(plain.display for plain in chain.get(Plain)).strip()),
    ):  # 包含前缀，可能是其他模块触发词，直接 return 掉
        return

    # if int(event.sender.group) not in ChatSessionContainer.session.keys():
    #     return
    # # 前面的 ChatGPT Impl 删了之后这里就别检查了

    def escape(__text: str) -> str:
        return __text.replace("[", "\\[").replace("]", "\\]")

    session = ChatSessionContainer.get_or_create(int(event.sender.group))
    if event.quote and event.quote.id not in session.mapping:
        # 检查回复消息是不是在 ChatChain 里面，不是的话加入上下文
        quote = None
        with contextlib.suppress(Exception):
            rebuilt = await RebuiltMessage.from_orm(
                event.quote.id, event.quote.group_id
            )
            escaped = escape(rebuilt.message_chain.safe_display)
            text = f"[Context]{escaped}[/Context]" + "\n" + text
    elif event.quote:
        quote = event.quote
    else:
        quote = None
    await session.send(app, event, text, quote)
    await FunctionCall.add_record(
        channel.module, int(event.sender.group), int(event.sender)
    )
