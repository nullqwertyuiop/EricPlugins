from typing import Optional, BinaryIO

from PicImageSearch import Network, Ascii2D
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.saya import Channel
from kayaku import config, create

from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem, ImageBox
from module.image_searcher.utils import get_thumb, error_catcher, check_and_serve

channel = Channel.current()


@config(f"{channel.module}.ascii2d")
class Ascii2dConfig:
    """Ascii2d 配置"""

    bovw: bool = True
    """是否使用 BoVW"""


@error_catcher
async def ascii2d_search(
    *_,
    proxies: Optional[str] = None,
    url: Optional[str] = None,
    file: Optional[BinaryIO] = None,
    **__,
) -> MessageChain:
    if not url and not file:
        raise ValueError("You should offer url or file!")
    cfg: Ascii2dConfig = create(Ascii2dConfig, flush=True)
    async with Network(proxies=proxies) as client:
        ascii2d = Ascii2D(client=client, bovw=cfg.bovw)
        resp = await ascii2d.search(url=url) if url else await ascii2d.search(file=file)
        if not resp.raw:

            return MessageChain(
                Image(
                    data_bytes=await Page(
                        Banner("Ascii2D 搜图"),
                        GenericBox(GenericBoxItem("服务器未返回内容", "无法搜索到该图片")),
                    ).render()
                )
            )

        resp = resp.raw[1]
        thumb = await get_thumb(resp.thumbnail, proxies)

        page = Page(
            Banner("Ascii2D 搜图"),
            ImageBox(img=thumb),
            GenericBox(
                GenericBoxItem("标题", resp.title),
                GenericBoxItem("作者", resp.author),
                GenericBoxItem("图像详情", resp.detail),
                GenericBoxItem("图像链接", resp.url),
            ),
            title="Ascii2D 搜图",
        )
        msg = MessageChain(Image(data_bytes=await page.render()))
        msg = await check_and_serve(page, "Ascii2D", str(hash(thumb)), msg)
        return msg
