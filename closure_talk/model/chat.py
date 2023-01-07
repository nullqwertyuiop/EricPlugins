from pathlib import Path

from creart import it
from graia.ariadne import Ariadne
from graia.saya import Channel
from graiax.playwright import PlaywrightBrowser
from kayaku import create
from loguru import logger
from lxml.html import builder, tostring
from lxml.html.builder import CLASS

from library.model.config import FastAPIConfig
from library.ui.util import wrap_text
from library.util.module import Modules
from module.closure_talk.style import _STYLE

channel = Channel.current()

ASSETS_PATH = Path(__file__).parent / "assets"


def _escape(string: str) -> str:
    return string.replace("#", ":")


class _ChatContent:
    content: str

    def __init__(self, content: str):
        self.content = content

    def to_e(self):
        return builder.DIV(
            builder.DIV(
                *wrap_text(self.content, hyperlink=False), CLASS("akn-content-text")
            ),
            CLASS("akn-content"),
        )


class _ChatAvatar:
    identifier: str
    src: str

    def __init__(self, identifier: str, src: str):
        self.identifier = identifier
        self.src = src

    @classmethod
    def from_src(cls, identifier: str, src: str):
        return cls(identifier, src)

    @classmethod
    def from_name(cls, identifier: str, name: str):
        avatar_path = (
            it(Modules).get(channel.module).data_path
            / "resources"
            / identifier
            / "characters"
        )
        if not list(avatar_path.glob(f"{name}.*")):
            raise ValueError(f"Avatar for {name} not found")
        return cls(
            identifier,
            f"{create(FastAPIConfig).link}/module/closure_talk"
            f"/character?identifier={identifier}&name={_escape(name)}",
        )

    def to_e(self):
        return builder.DIV(
            builder.IMG(src=self.src),
            CLASS("akn-avatar"),
        )


class _ChatItem:
    content: _ChatContent
    avatar: _ChatAvatar

    def __init__(self, identifier: str, content: str, avatar: str, is_name: bool):
        self.content = _ChatContent(content)
        self.avatar = (
            _ChatAvatar.from_name(identifier, avatar)
            if is_name
            else _ChatAvatar.from_src(identifier, avatar)
        )

    def to_e(self):
        return builder.DIV(self.avatar.to_e(), self.content.to_e(), CLASS("akn-item"))


class ClosureChatArea:
    items: list[_ChatItem]

    def __init__(self):
        self.items = []

    @property
    def _head(self):
        return builder.HEAD(builder.STYLE(_STYLE))

    def add(self, identifier: str, content: str, avatar: str, is_name: bool):
        self.items.append(_ChatItem(identifier, content, avatar, is_name))
        logger.debug(
            f"[ClosureTalk] 会话区域添加了一条消息："
            f"{identifier=}, {avatar=}, {is_name=}, {content=}"
        )

    def to_e(self):
        return builder.HTML(
            self._head,
            builder.BODY(
                builder.DIV(
                    *map(lambda item: item.to_e(), self.items),
                    CLASS("akn-area"),
                    style="background-color: rgb(35, 27, 20); "
                    "padding-top: 16px; padding-bottom: 16px;",
                )
            ),
        )

    def to_html(self, *_args, **_kwargs) -> str:
        return tostring(
            self.to_e(),
            encoding="unicode",
            pretty_print=True,
        )

    async def render(self) -> bytes:
        browser = Ariadne.launch_manager.get_interface(PlaywrightBrowser)
        async with browser.page(
            viewport={"width": 500, "height": 1},
            device_scale_factor=1.5,
        ) as page:
            logger.info("[ClosureTalk] Setting content...")
            await page.set_content(self.to_html())
            logger.info("[ClosureTalk] Getting screenshot...")
            img = await page.screenshot(
                type="jpeg", quality=80, full_page=True, scale="device"
            )
            logger.success("[ClosureTalk] Done.")
            return img
