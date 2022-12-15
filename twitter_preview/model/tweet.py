import asyncio
from datetime import datetime
from io import BytesIO

import youtube_dl
from PIL import Image as PillowImage
from aiohttp import ClientSession
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from kayaku import create
from loguru import logger
from pydantic import BaseModel

from library.model.config.eric import EricConfig
from library.module.file_server.util import serve_file, get_link
from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem, ImageBox, VideoBox
from library.util.misc import seconds_to_string
from module.twitter_preview.model.config import TwitterPreviewConfig
from module.twitter_preview.model.include import Photo, Video, AnimatedGif, User
from module.twitter_preview.var import STATUS_LINK


class Attachments(BaseModel):
    media_keys: list[str] = []


class EntityAnnotation(BaseModel):
    start: int
    end: int
    probability: float
    type: str
    normalized_text: str


class EntityURLExternalImage(BaseModel):
    url: str
    width: int
    height: int


class EntityURLExternal(BaseModel):
    start: int
    end: int
    url: str
    expanded_url: str
    display_url: str
    images: list[EntityURLExternalImage] = []
    status: int
    title: str
    description: str
    unwound_url: str


class EntityURLMedia(BaseModel):
    start: int
    end: int
    url: str
    expanded_url: str
    display_url: str
    media_key: str = ""


class EntityHashtag(BaseModel):
    start: int
    end: int
    tag: str


class Entities(BaseModel):
    annotations: list[EntityAnnotation] = []
    hashtags: list[EntityHashtag] = []
    urls: list[EntityURLMedia | EntityURLExternal] = []


class PublicMetrics(BaseModel):
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0


class UnparsedTweet(BaseModel):
    author_id: int
    attachments: Attachments = Attachments()
    text: str
    entities: Entities = Entities()
    id: int
    created_at: datetime
    public_metrics: PublicMetrics = PublicMetrics()
    possibly_sensitive: bool


class ParsedTweet(UnparsedTweet):
    media: list[Photo | Video | AnimatedGif] = []
    user: User

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def has_video(self) -> bool:
        return bool(list(filter(lambda x: isinstance(x, Video), self.media)))

    @property
    def has_animation(self) -> bool:
        return bool(list(filter(lambda x: isinstance(x, AnimatedGif), self.media)))

    async def get_images(self) -> list[bytes]:
        images: list[bytes] = []
        async with ClientSession() as session:
            for media in self.media:
                if not isinstance(media, Photo):
                    continue
                url = media.url
                config: EricConfig = create(EricConfig)
                async with session.get(url, proxy=config.proxy) as resp:
                    images.append(await resp.read())
        return images

    async def get_video_bytes(self) -> tuple[bytes, str]:
        def get_video_info() -> dict | None:
            for media in self.media:
                if not isinstance(media, (Video, AnimatedGif)):
                    continue
                with youtube_dl.YoutubeDL() as ydl:
                    return ydl.extract_info(
                        STATUS_LINK.format(username=self.user.username, id=self.id),
                        download=False,
                    )

        info = await asyncio.to_thread(get_video_info)
        config: EricConfig = create(EricConfig)
        async with ClientSession() as session:
            async with session.get(info["url"], proxy=config.proxy) as resp:
                return await resp.read(), f"{info['display_id']}.{info['ext']}"

    async def get_page(self, banner_text: str = "Twitter 预览") -> Page:
        config: TwitterPreviewConfig = create(TwitterPreviewConfig)
        logger.info(f"取得推文 {self.id} 图片中...")
        images: list[bytes] = await self.get_images()
        _avatar: PillowImage.Image = PillowImage.open(
            BytesIO(await self.user.get_avatar())
        )

        page = Page(
            Banner(banner_text),
            GenericBox(
                GenericBoxItem(
                    text=self.user.name,
                    description=self.user.username,
                )
            ),
            title=f"Twitter 预览 - {self.user.name}",
        )

        page.add(*[ImageBox.from_bytes(image) for image in images])
        if self.has_video or self.has_animation:
            video, filename = await self.get_video_bytes()
            url = get_link(await serve_file(video, filename, lifespan=config.lifespan))
            page.add(
                VideoBox(
                    url=url,
                    loop=False,
                    controls=True,
                )
            )

        page.add(
            GenericBox(
                GenericBoxItem(text="正文", description=self.text, highlight=True)
            ),
        )

        if config.metrics.tags and (hashtags := self.entities.hashtags):
            page.add(
                GenericBox(
                    GenericBoxItem(
                        text="标签",
                        description=" ".join(
                            [f"#{hashtag.tag}" for hashtag in hashtags]
                        ),
                    )
                )
            )

        if config.metrics.retweet:
            page.add(
                GenericBox().add(
                    GenericBoxItem(
                        text="转推", description=str(self.public_metrics.retweet_count)
                    )
                )
            )
        if config.metrics.reply:
            page.add(
                GenericBoxItem(
                    text="回复", description=str(self.public_metrics.reply_count)
                )
            )
        if config.metrics.like:
            page.add(
                GenericBoxItem(
                    text="点赞", description=str(self.public_metrics.like_count)
                )
            )
        if config.metrics.quote:
            page.add(
                GenericBoxItem(
                    text="引用", description=str(self.public_metrics.quote_count)
                )
            ),
        time_box = []
        if config.metrics.create_time:
            time_box.append(
                GenericBoxItem(
                    text="发布时间",
                    description=self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
        if config.metrics.fetch_time:
            time_box.append(
                GenericBoxItem(
                    text="制图时间",
                    description=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
        if time_box:
            page.add(GenericBox(*time_box))

        return page

    async def generate_message(self) -> MessageChain:
        config: TwitterPreviewConfig = create(TwitterPreviewConfig)
        page = await self.get_page()
        if self.has_video:
            uuid = await serve_file(
                page.to_html().encode("utf-8"),
                f"{self.id}.html",
                lifespan=config.lifespan,
            )
            url = get_link(uuid)
            return MessageChain(
                f"已解析推文 {self.id}，请点击链接查看：{url}\n"
                f"生命周期：{seconds_to_string(config.lifespan)}"
            )
        return MessageChain(Image(data_bytes=await page.render()))
