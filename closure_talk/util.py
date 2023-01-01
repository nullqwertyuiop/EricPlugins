import json
from pathlib import Path

import aiofiles
from aiohttp import ClientSession
from creart import it
from graia.ariadne.model import Group, Member
from graia.saya import Channel
from kayaku import create
from loguru import logger

from library.model.config import EricConfig
from library.util.misc import inflate
from library.util.module import Modules
from module.closure_talk.model.character import ClosureCharacter
from module.closure_talk.model.chat import ClosureChatArea

channel = Channel.current()

GITHUB_RAW_LINK = (
    "https://raw.githubusercontent.com/ClosureTalk/closuretalk.github.io/master/{path}"
)


class ClosureStore:
    characters: dict[str, set[ClosureCharacter]] = {}
    session: dict[int, [str, ClosureChatArea]] = {}

    @classmethod
    def start(cls, identifier: str, field: Group):
        if int(field) in cls.session:
            raise ValueError("[ClosureTalk] 会话已经存在")
        cls.session[int(field)] = [identifier, ClosureChatArea()]

    @classmethod
    def end(cls, field: Group):
        if int(field) in cls.session:
            del cls.session[int(field)]

    @staticmethod
    def search(base: list[ClosureCharacter], key: str) -> list[ClosureCharacter]:
        key = key.lower()
        return list(
            filter(
                lambda character: any(
                    [
                        key == character.id.lower(),
                        (lambda x: any(key == y.lower() for y in x.values()))(
                            character.names
                        ),
                        (lambda x: any(key == y.lower() for y in x))(
                            character.searches
                        ),
                        (lambda x: any(key == y.lower() for y in x.values()))(
                            character.short_names
                        ),
                    ]
                ),
                base,
            )
        )

    @classmethod
    def filter_character(cls, field: Group, key: str) -> list[ClosureCharacter]:
        identifier: str | None = cls.session.get(int(field), [None, None])[0]
        if identifier is None:
            base = inflate(list(cls.characters.values()))
        else:
            base = cls.characters.get(identifier, [])
        return cls.search(base, key)


async def _download_char():
    config: EricConfig = create(EricConfig)
    module = it(Modules).get(channel.module)
    path = "resources/ak/char.json"
    write_path = module.data_path / path
    write_path.parent.mkdir(exist_ok=True, parents=True)
    async with (
        ClientSession() as session,
        session.get(GITHUB_RAW_LINK.format(path=path), proxy=config.proxy) as resp,
        aiofiles.open(write_path, "w", encoding="utf-8") as f,
    ):
        await f.write(await resp.text())
        logger.debug("[ClosureTalk] 成功下载 char.json")


async def _parse_all():
    path = it(Modules).get(channel.module).data_path / "resources"
    identifiers = [i.name for i in path.iterdir() if i.is_dir()]
    for identifier in identifiers:
        await _parse_char(identifier)
        logger.debug(f"[ClosureTalk] 已解析 {identifier}")


async def _parse_char(identifier: str):
    ClosureStore.characters[identifier] = set()
    module = it(Modules).get(channel.module)
    path = f"resources/{identifier}/char.json"
    char_path = module.data_path / path
    async with aiofiles.open(char_path, "r", encoding="utf-8") as f:
        data = json.loads(await f.read())
    for char in data:
        character = ClosureCharacter(**char)
        ClosureStore.characters[identifier].add(character)


async def _download_resource(identifier: str):
    config: EricConfig = create(EricConfig)
    module = it(Modules).get(channel.module)
    async with ClientSession() as session:
        path = f"resources/{identifier}/characters/{{image}}.webp"
        Path(module.data_path / f"resources/{identifier}/characters").mkdir(
            exist_ok=True, parents=True
        )
        total = len(ClosureStore.characters[identifier])
        for char_index, character in enumerate(ClosureStore.characters[identifier]):
            for img_index, image in enumerate(character.images):
                image_path = path.format(image=image)
                if (module.data_path / image_path).is_file():
                    continue
                try:
                    async with (
                        session.get(
                            GITHUB_RAW_LINK.format(path=image_path),
                            proxy=config.proxy,
                        ) as resp,
                        aiofiles.open(module.data_path / image_path, "wb") as f,
                    ):
                        await f.write(await resp.read())
                        name = image_path.split("/")[-1]
                        logger.debug(f"[ClosureTalk] [{char_index} / {total}] 成功下载 {name}")
                except Exception as e:
                    logger.error(f"[ClosureTalk] [{char_index} / {total}] 下载 {identifier} {image} 时出现错误：{e}")
        logger.debug(f"[ClosureTalk] 已下载 {identifier} 的资源")


async def _closure_data_initialize():
    await _download_char()
    await _parse_all()
    await _download_resource("ak")


def check_avatar(sender: Member) -> tuple[str, bool]:
    split = sender.name.split("#")
    split = [split[0], split[1] if len(split) >= 2 else "1"]
    if not (characters := ClosureStore.filter_character(sender.group, split[0])):
        return get_avatar_link(sender), False
    character = characters[0]
    if split[1].isdigit() and 0 < int(split[1]) <= len(character.images):
        return character.images[int(split[1]) - 1], True
    return get_avatar_link(sender), False


def get_avatar_link(sender: Member):
    return f"https://q2.qlogo.cn/headimg_dl?dst_uin={int(sender)}&spec=640"
