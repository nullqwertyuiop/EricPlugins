import asyncio
import re
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image as PillowImage
from creart import it
from dateutil.relativedelta import relativedelta
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.parser.twilight import (
    Twilight,
    UnionMatch,
    FullMatch,
    RegexResult,
)
from graia.saya import Channel
from graiax.shortcut import listen, dispatch, decorate
from jieba.analyse import extract_tags
from loguru import logger
from sqlalchemy import select, func
from wordcloud import WordCloud, ImageColorGenerator

from library.decorator import Switch, Distribution, Blacklist, FunctionCall
from library.module.recorder import MessageRecord
from library.ui import Page, Banner, GenericBox, GenericBoxItem, ImageBox
from library.ui.color import is_dark
from library.util.dispatcher import PrefixMatch
from library.util.locksmith import LockSmith
from library.util.message import send_message
from library.util.module import Modules
from library.util.orm import orm

_DEFAULT_FONT = "HarmonyOSHans.ttf"
_DELTA = {
    "年内": relativedelta(years=1),
    "今年": relativedelta(years=1),
    "年度": relativedelta(years=1),
    "月内": relativedelta(months=1),
    "本月": relativedelta(months=1),
    "月度": relativedelta(months=1),
    "日内": relativedelta(days=1),
    "今日": relativedelta(days=1),
}
_SCOPE_TYPE = Literal["我的", "本群"]

channel = Channel.current()


@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        UnionMatch("我的", "本群", "我的本群") @ "scope",
        UnionMatch("年内", "今年", "年度", "月内", "本月", "月度", "日内", "今日", "全部") @ "typ",
        FullMatch("词云"),
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def get_wc(
    app: Ariadne, event: GroupMessage, scope: RegexResult, typ: RegexResult
):
    lock = it(LockSmith).get(f"{channel.module}:{int(event.sender)}")
    if lock.locked():
        return await send_message(event, MessageChain("已在生成词云，等稍后再试"), app.account)

    async with lock:
        scope: str = scope.result.display
        typ: str = typ.result.display
        await send_message(event, MessageChain("正在生成词云，请稍候..."), app.account)
        start = time.perf_counter()
        conditions = parse_condition(
            int(event.sender),
            int(event.sender.group) if isinstance(event, GroupMessage) else 0,
            scope,  # type: ignore
            typ,  # type: ignore
        )
        tasks = [
            asyncio.create_task(get_count(*conditions)),
            asyncio.create_task(get_frequency(5000, 5000, *conditions)),
        ]
        results = await asyncio.gather(*tasks)
        count = results[0]
        if not count:
            return await send_message(
                event, MessageChain("暂无发言记录"), app.account, quote=event.source
            )
        frequencies = results[1]
        logger.info(
            f"[Wordcloud] {int(event.sender)}: "
            f"获取数据耗时 {time.perf_counter() - start:.2f}s"
        )
        checkpoint = time.perf_counter()
        img = await async_generate_wordcloud(frequencies)
        logger.info(
            f"[Wordcloud] {int(event.sender)}: "
            f"生成词云耗时 {time.perf_counter() - checkpoint:.2f}s"
        )
        avatar = await (
            event.sender if "我的" in scope else event.sender.group
        ).get_avatar()
        page = Page(
            Banner("词云"),
            GenericBox(
                GenericBoxItem(event.sender.name, str(int(event.sender)), image=avatar)
            ),
            ImageBox.from_bytes(img),
            GenericBox(GenericBoxItem("发言次数", f"{count} 次")),
        )
        await send_message(
            event,
            MessageChain(Image(data_bytes=await page.render())),
            app.account,
            quote=event.source,
        )


def parse_condition(
    sender: int,
    field: int,
    scope: Literal["我的", "本群", "我的本群"],
    typ: Literal["年内", "今年", "年度", "月内", "本月", "月度", "日内", "今日", "全部"],
) -> list[...]:
    field = field or -field
    conditions = [
        (MessageRecord.sender == sender)
        if "我的" in scope
        else (MessageRecord.target == field)
    ]
    if scope == "我的本群":
        conditions.append(MessageRecord.target == field)
    if typ == "全部":
        return conditions
    time_condition = datetime.now() - _DELTA[typ]
    conditions.append(MessageRecord.time >= time_condition)
    return conditions


class WCFilter:
    keys: list[str]

    def __init__(self):
        if ((it(Modules).get(channel.module)).data_path / "filter.txt").is_file():
            with open((it(Modules).get(channel.module)).data_path / "filter.txt") as f:
                self.keys = f.read().splitlines()
        else:
            self.keys = []

    def filter(self, content: str) -> str:
        content = self.filter_at(content)
        for word in self.keys:
            content = content.replace(word, "")
        return content

    @staticmethod
    def filter_at(content: str) -> str:
        return re.sub(r"@\d+", "", content)


_filter = WCFilter()


async def get_frequency(
    item_count: int, kw_count: int, *conditions: ...
) -> dict[str, float]:
    cursor = await orm.execute(
        select(MessageRecord.content)
        .where(*conditions)
        .order_by(MessageRecord.time.desc())  # type: ignore
        .limit(item_count)
    )
    result = {}
    for (item,) in cursor.yield_per(1):
        item = _filter.filter(item)
        jieba_analyse = extract_tags(item, topK=None, withWeight=True)
        for word, weight in jieba_analyse:
            result[word] = result.get(word, 0) + weight
    return {
        k: v
        for k, v in sorted(result.items(), key=lambda x: x[1], reverse=True)[:kw_count]
    }


async def get_count(*conditions: ...) -> int:
    count = await orm.execute(
        select(func.count(MessageRecord.msg_id)).where(*conditions)
    )
    return count.scalar_one()


def generate_wordcloud(frequencies: dict[str, float], mask: ... = None) -> bytes:
    dark = is_dark()
    mask = mask or read_mask()
    wc = WordCloud(
        font_path=str(Path() / "library" / "assets" / "fonts" / _DEFAULT_FONT),
        background_color="black" if dark else "white",
        max_font_size=100,
        width=1920,
        height=1080,
        mask=mask,
    )
    wc.generate_from_frequencies(frequencies)
    if mask is not None:
        wc.recolor(
            color_func=ImageColorGenerator(
                mask, default_color=(0, 0, 0) if dark else (255, 255, 255)
            )
        )
    bytes_io = BytesIO()
    img = wc.to_image()
    img.save(bytes_io, format="PNG")
    return bytes_io.getvalue()


async def async_generate_wordcloud(
    frequencies: dict[str, float], mask: ... = None
) -> bytes:
    return await asyncio.to_thread(generate_wordcloud, frequencies, mask)


def read_mask():
    data_path = it(Modules).get(channel.module).data_path
    for file in (
        set(data_path.glob("*.png"))
        | set(data_path.glob("*.jpg"))
        | set(data_path.glob("*.jpeg"))
    ):
        return np.array(PillowImage.open(file))  # type: ignore
    return None
