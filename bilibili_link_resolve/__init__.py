import json
import re
import time

import aiohttp
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.parser.twilight import (
    Twilight,
    WildcardMatch,
    RegexMatch,
)
from graia.ariadne.util.saya import listen, dispatch, decorate
from graia.saya import Channel

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.function_call import FunctionCall
from library.decorator.switch import Switch
from library.decorator.timer import timer
from library.ui import Page
from library.ui.element.banner import Banner
from library.ui.element.box.generic import GenericBox, GenericBoxItem
from library.ui.element.box.image import ImageBox
from library.util.message import send_message
from library.util.misc import seconds_to_string

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        WildcardMatch(),
        RegexMatch(
            r"(http:|https:\/\/)?([^.]+\.)?"
            r"(bilibili\.com\/video\/"
            r"((BV|bv)[\w\d]{10}|"
            r"((AV|av)([\d]+))))|"
            r"(b23\.tv\/[\w\d]+)"
        ).flags(re.S),
        WildcardMatch(),
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def bilibili_link_resolve(app: Ariadne, event: MessageEvent):
    if msg := await resolve(event.message_chain.display):
        await send_message(event, msg, app.account)


async def resolve(message: str) -> None | MessageChain:
    if match := re.findall(
        r"(?:https?://)?(?:[^.]+\.)?bilibili\.com/video/(?:BV|bv)(\w{10})",
        message,
    ):
        bv = f"bv{match[0]}"
        av = bv_to_av(bv)
        info = await get_info(av)
        return await generate(info)
    elif match := re.findall(
        r"(?:https?://)?(?:[^.]+\.)?bilibili\.com/video/(?:AV|av)(\d+)",
        message,
    ):
        av = match[0]
        info = await get_info(av)
        return await generate(info)
    elif match := re.findall(r"(https?://\)?(?:[^.]+\.)?b23\.tv/\w+)", message):
        match = match[0]
        if not (match.startswith("http")):
            match = f"https://{match}"
        async with aiohttp.ClientSession() as session:
            async with session.get(match) as res:
                if res.status == 200:
                    link = str(res.url)
                    return await resolve(link)


async def get_info(av: int):
    bilibili_video_api_url = f"https://api.bilibili.com/x/web-interface/view?aid={av}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url=bilibili_video_api_url) as resp:
            result = (await resp.read()).decode("utf-8")
    result = json.loads(result)
    return result


def bv_to_av(bv: str) -> int:
    table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
    tr = {table[i]: i for i in range(58)}
    s = [11, 10, 3, 8, 4, 6]
    xor = 177451812
    add = 8728348608
    r = sum(tr[bv[s[i]]] * 58**i for i in range(6))
    return (r - add) ^ xor


@timer(channel.module)
async def generate(info: dict) -> MessageChain:
    data = info["data"]
    return MessageChain(Image(data_bytes=await get_page(data).render()))


def get_page(data: dict) -> Page:
    return Page(
        Banner("B 站链接解析"),
        ImageBox.from_url(data["pic"]),
        GenericBox(
            GenericBoxItem(text=str(data["title"])),
            GenericBoxItem(
                text="投稿时间",
                description=str(
                    time.strftime("%Y-%m-%d", time.localtime(int(data["pubdate"])))
                ),
            ),
            GenericBoxItem(
                text="视频长度", description=str(seconds_to_string(data["duration"]))
            ),
            GenericBoxItem(text="UP 主", description=str(data["owner"].get("name", ""))),
        ),
        GenericBox(
            GenericBoxItem(text="简介", description=str(data["desc"])),
        ),
        GenericBox(
            GenericBoxItem(text="简介", description=str(data["desc"])),
        ),
        GenericBox(
            GenericBoxItem(text="播放量", description=str(data["stat"].get("view", ""))),
            GenericBoxItem(
                text="弹幕量", description=str(data["stat"].get("danmaku", ""))
            ),
            GenericBoxItem(text="评论量", description=str(data["stat"].get("reply", ""))),
            GenericBoxItem(text="点赞量", description=str(data["stat"].get("like", ""))),
            GenericBoxItem(text="投币量", description=str(data["stat"].get("coin", ""))),
            GenericBoxItem(
                text="收藏量", description=str(data["stat"].get("favorite", ""))
            ),
            GenericBoxItem(text="转发量", description=str(data["stat"].get("share", ""))),
        ),
        GenericBox(
            GenericBoxItem(text="AV 号", description=str("av" + str(data["aid"]))),
            GenericBoxItem(text="BV 号", description=str(data["bvid"])),
        ),
    )
