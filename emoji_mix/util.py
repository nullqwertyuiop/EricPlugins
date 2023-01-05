import asyncio
import json

import aiofiles
from aiohttp import ClientSession
from creart import it
from graia.saya import Channel
from kayaku import create
from loguru import logger

from library.model.config import EricConfig
from library.util.module import Modules

channel = Channel.current()
_DATA_PATH = it(Modules).get(channel.module).data_path
_JSON_LINK = (
    "https://raw.githubusercontent.com/xsalazar/"
    "emoji-kitchen/main/src/Components/emojiData.json"
)
_FILE = _DATA_PATH / _JSON_LINK.split("/")[-1]
_KITCHEN: str = (
    "https://www.gstatic.com/android/keyboard/emojikitchen"
    "/{date}/u{left_emoji}/u{left_emoji}_u{right_emoji}.png"
)


async def _download():
    cfg: EricConfig = create(EricConfig)
    async with ClientSession() as session, session.get(
        _JSON_LINK, proxy=cfg.proxy
    ) as resp:
        data = await resp.json(content_type=None)
        async with aiofiles.open(_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data))
            logger.success("[EmojiMix] emojiData.json 下载完成")


asyncio.get_event_loop().run_until_complete(_download())


def read_data() -> list[tuple[str, str, str]]:
    data: list[tuple[str, str, str]] = []
    with open(_FILE, "r", encoding="utf-8") as f:
        f_dict: dict[str, list[dict[str, str]]] = json.load(f)
        for pairs in f_dict.values():
            data.extend(
                (pair["leftEmoji"], pair["rightEmoji"], pair["date"]) for pair in pairs
            )
    return data


_MIX_DATA: list[tuple[str, str, str]] = read_data()


def get_emoji(code_point: str) -> str:
    if "-" not in code_point:
        return chr(int(code_point, 16))
    emoji = code_point.split("-")
    return "".join(chr(int(i, 16)) for i in emoji)


def get_all_emoji() -> set[str]:
    emoji = set()
    for left_emoji, right_emoji, _ in _MIX_DATA:
        emoji.add(get_emoji(left_emoji))
        emoji.add(get_emoji(right_emoji))
    return emoji


_ALL_EMOJI: set[str] = get_all_emoji()


def emoji_to_codepoint(emoji: str) -> str:
    if len(emoji) == 1:
        return hex(ord(emoji))[2:]
    return "-".join(hex(ord(char))[2:] for char in emoji)


def get_mix_emoji_url(left_emoji: str, right_emoji: str) -> str | None:
    left_emoji = emoji_to_codepoint(left_emoji)
    right_emoji = emoji_to_codepoint(right_emoji)
    for _left_emoji, _right_emoji, date in _MIX_DATA:
        if _left_emoji == left_emoji and _right_emoji == right_emoji:
            return _KITCHEN.format(
                date=date,
                left_emoji=left_emoji.replace("-", "-u"),
                right_emoji=right_emoji.replace("-", "-u"),
            )
        elif _left_emoji == right_emoji and _right_emoji == left_emoji:
            return _KITCHEN.format(
                date=date,
                left_emoji=right_emoji.replace("-", "-u"),
                right_emoji=left_emoji.replace("-", "-u"),
            )


def get_available_pairs(emoji: str) -> set[str]:
    emoji = emoji_to_codepoint(emoji)
    pairs = set()
    for _left_emoji, _right_emoji, _ in _MIX_DATA:
        if _left_emoji == emoji:
            pairs.add(get_emoji(_right_emoji))
        elif _right_emoji == emoji:
            pairs.add(get_emoji(_left_emoji))
    return pairs
