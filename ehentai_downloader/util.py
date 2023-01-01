import re

from aiohttp import ClientSession, TCPConnector
from creart import it
from graia.ariadne import Ariadne
from graia.ariadne.event.message import ActiveMessage
from graia.saya import Channel
from kayaku import create
from loguru import logger
from lxml import html

from library.decorator import timer
from library.model.config import EricConfig
from library.module.file_server.util import serve_file, get_link, serve_page
from library.ui.element import Page, Banner, GenericBox, GenericBoxItem, Button
from library.util.session_container import SessionContainer
from module.ehentai_downloader.config import EHentaiConfig
from module.ehentai_downloader.threshold import _EThreshold

channel = Channel.current()
HTTP_LINK_PATTERN = re.compile(r"""https?://[^\s'"]+""")
GALLERY_PATTERN = re.compile(r"(?:https?://)?e[-x]hentai\.org/g/(\d+)/[\da-z]+/?")


class _EGallery:
    def __init__(self, _html: str):
        self.element = html.fromstring(_html)

    @property
    def title(self) -> str:
        return self.element.xpath('//*[@id="gn"]/text()')[0]

    @property
    def archiver(self) -> str:
        onclick = self.element.xpath('//*[@id="gd5"]/p[2]/a/@onclick')[0]
        return HTTP_LINK_PATTERN.findall(onclick)[0]


class _EArchiver:
    def __init__(self, _html: str):
        self.element = html.fromstring(_html)

    @property
    def title(self) -> str:
        return self.element.xpath('//*[@id="db"]/h1/text()')[0]

    @property
    def cost(self) -> int:
        cost = self.element.xpath('//*[@id="db"]/div[1]/div[2]/div/strong/text()')[0]
        return int(cost) if cost.isdigit() else 0

    @property
    def size_repr(self) -> str:
        return self.element.xpath('//*[@id="db"]/div[1]/div[2]/p/strong/text()')[0]

    @property
    def size(self) -> int:
        size, unit = self.size_repr.split()
        size = float(size)
        match unit:
            case "KB":
                return int(size * 1024)
            case "MB":
                return int(size * 1024**2)
            case "GB":
                return int(size * 1024**3)

    @property
    def post_url(self):
        return self.element.xpath('//*[@id="db"]/div[1]/div[1]/form/@action')[0]


class _ESession:
    id: int
    link: str
    gallery: _EGallery | None = None
    archiver: _EArchiver | None = None
    hath_url: str | None = None
    filename: str | None = None
    zip_link: str | None = None
    last_msg: ActiveMessage | None = None

    def __init__(self, link: str):
        self.id = int(GALLERY_PATTERN.findall(link)[0])
        self.link = link

    @staticmethod
    async def _session() -> ClientSession:
        return await it(SessionContainer).get(
            channel.module,
            connector=TCPConnector(verify_ssl=False),
            cookies=create(EHentaiConfig).dict(),
        )

    async def _get_text(self, url: str, headers: dict = None) -> str:
        session = await self._session()
        eric_cfg: EricConfig = create(EricConfig)
        async with session.get(
                url, proxy=eric_cfg.proxy, verify_ssl=False, headers=headers or {}
        ) as resp:
            return await resp.text()

    async def _get_bytes(self, url: str, headers: dict = None) -> bytes:
        session = await self._session()
        eric_cfg: EricConfig = create(EricConfig)
        async with session.get(
                url, proxy=eric_cfg.proxy, verify_ssl=False, headers=headers or {}
        ) as resp:
            return await resp.read()

    async def _post(self, url: str, data: dict) -> str:
        session = await self._session()
        eric_cfg: EricConfig = create(EricConfig)
        async with session.post(
                url, data=data, proxy=eric_cfg.proxy, verify_ssl=False
        ) as resp:
            data = await resp.text()
            return data

    async def init_gallery(self):
        _html = await self._get_text(self.link)
        self.gallery = _EGallery(_html)

    async def init_archiver(self):
        archiver = self.gallery.archiver
        _html = await self._get_text(archiver)
        self.archiver = _EArchiver(_html)

    async def post_resample(self):
        data = await self._post(
            self.archiver.post_url,
            data={"dltype": "res", "dlcheck": "Download Resample Archive"},
        )
        element = html.fromstring(data)
        hath_url = element.xpath('//*[@id="continue"]/a/@href')[0]
        self.hath_url = hath_url

    async def parse_hath(self):
        data = await self._get_text(self.hath_url)
        element = html.fromstring(data)
        filename = element.xpath('//*[@id="db"]/p/strong/text()')[0]
        self.filename = filename

    async def download(self):
        config: EHentaiConfig = create(EHentaiConfig)
        file = await self._get_bytes(f"{self.hath_url}?start=1")
        file_id = await serve_file(file, self.filename, lifespan=config.lifespan)
        self.zip_link = get_link(file_id)

    def log_info(self):
        text = "[E-hentai]\n"
        text += f"{'Gallery ID':15}{self.id}\n"
        text += f"{'Title':15}{self.archiver.title}\n"
        text += f"{'Cost':15}{self.archiver.cost}\n"
        text += f"{'Size':15}{self.archiver.size} ({self.archiver.size_repr})\n"
        text += f"{'Hath Link':15}{self.hath_url}\n"
        text += f"{'Filename':15}{self.filename}\n"
        logger.info(text)

    def page(self) -> Page:
        page = Page(title="E-hentai 下载器")
        page.add(Banner(self.archiver.title))
        page.add(Button("下载", self.zip_link))
        page.add(
            GenericBox(
                GenericBoxItem(
                    text="图库 ID",
                    description=str(self.id),
                ),
                GenericBoxItem(
                    text="标题",
                    description=self.archiver.title,
                ),
                GenericBoxItem(
                    text="消耗点数",
                    description=str(self.archiver.cost or "免费"),
                ),
                GenericBoxItem(
                    text="文件大小",
                    description=f"{self.archiver.size} ({self.archiver.size_repr})",
                ),
                GenericBoxItem(
                    text="文件名",
                    description=self.filename,
                ),
            )
        )
        return page

    async def proceed(self):
        await self.init_gallery()
        await self.init_archiver()
        await self.post_resample()
        await self.parse_hath()
        self.log_info()
        await self.download()

    def add_threshold(self):
        _EThreshold.daily += 1
        _EThreshold.hourly += 1
        _EThreshold.size += self.archiver.size

    @timer(channel.module)
    async def serve(self) -> str:
        await self.proceed()
        self.add_threshold()
        file_id = await serve_page(self.page(), lifespan=create(EHentaiConfig).lifespan)
        return get_link(file_id)
