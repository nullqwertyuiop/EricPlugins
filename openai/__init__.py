import asyncio
import re

import openai
from creart import it
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    SpacePolicy,
    WildcardMatch,
    RegexResult,
)
from graia.saya import Channel
from graiax.shortcut import listen, dispatch, decorate
from kayaku import create, config
from loguru import logger

from library.decorator import Switch, Distribution, Blacklist, FunctionCall, Permission
from library.model.config import EricConfig
from library.model.permission import UserPerm
from library.util.dispatcher import PrefixMatch
from library.util.locksmith import LockSmith
from library.util.message import send_message
from library.util.session_container import SessionContainer

channel = Channel.current()


@config(channel.module)
class _OpenAIConfig:
    api_key: str = ""


openai.api_key = create(_OpenAIConfig).api_key


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
        return await send_message(event, await call_dalle(prompt), app.account, quote=event.source)
    return await send_message(event, MessageChain("请输入 prompt"), app.account)


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


_GPT_CACHE: dict[int, list[str]] = {}


async def call_gpt3(prompt: str, field: int, name: str) -> MessageChain:
    async with it(LockSmith).get(f"{channel.module}:gpt3.{field}"):
        logger.info(f"[OpenAI:GPT3] Generating text for {field}: {prompt}")
        complete_prompt = _GPT_CACHE.setdefault(field, [])
        complete_prompt.append(f"[用户 {name}]:{prompt}")
        complete_prompt = "\n".join(complete_prompt) + "\n[机器人 你]:"

        def get_text() -> str:
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=complete_prompt,
                temperature=0.5,
                max_tokens=100,
                frequency_penalty=0.5,
                presence_penalty=0.0,
                stop=["[用户 "],
            )
            return response["choices"][0]["text"]

        try:
            resp = await asyncio.to_thread(get_text)
            _GPT_CACHE[field] = _GPT_CACHE[field][:20]
            _GPT_CACHE[field].append(f"[机器人 你]:{resp}")
        except openai.error.OpenAIError as e:
            return MessageChain(f"运行时出现错误：{str(e)}")

        return MessageChain(resp)


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
            await call_gpt3(prompt, int(event.sender.group), event.sender.name),
            app.account,
            quote=event.source,
        )
    else:
        return


@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("openai gpt3 flush"),
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def flush_openai_api_key(app: Ariadne, event: GroupMessage):
    _GPT_CACHE[int(event.sender.group)] = []
    await send_message(event, MessageChain("OpenAI GPT3 缓存已刷新"), app.account)
