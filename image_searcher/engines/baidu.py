from pathlib import Path
from typing import Optional, BinaryIO

from PIL import Image as PillowImage
from PicImageSearch import Network, BaiDu
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image

from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem, ImageBox, ProgressBar
from module.image_searcher.utils import get_thumb, error_catcher, check_and_serve

ICON = PillowImage.open(Path(__file__).parent.parent / "icon.png")


@error_catcher
async def baidu_search(
    *_, url: Optional[str] = None, file: Optional[BinaryIO] = None, **__
) -> MessageChain:
    if not url and not file:
        raise ValueError("You should offer url or file!")
    async with Network() as client:
        baidu = BaiDu(client=client)
        resp = await baidu.search(url=url) if url else await baidu.search(file=file)
        if not resp.raw:

            return MessageChain(
                Image(
                    data_bytes=await Page(
                        Banner("百度 搜图", icon=ICON),
                        GenericBox(GenericBoxItem("服务器未返回内容", "无法搜索到该图片")),
                    ).render()
                )
            )

        resp = resp.raw[2]
        thumb = await get_thumb(resp.thumbnail, "")

        page = Page(
            Banner("百度 搜图"),
            ImageBox(img=thumb),
            ProgressBar(resp.similarity / 100, "相似度", f"{resp.similarity}%"),
            GenericBox(
                GenericBoxItem("标题", resp.title),
                GenericBoxItem("链接", resp.url),
            ),
            title="百度 搜图",
        )
        msg = MessageChain(Image(data_bytes=await page.render()))
        msg = await check_and_serve(page, "百度", str(hash(thumb)), msg)
        return msg
