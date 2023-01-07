from typing import Optional, BinaryIO

from PicImageSearch import Network, Google
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image

from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem, ImageBox
from module.image_searcher.utils import get_thumb, error_catcher, check_and_serve


@error_catcher
async def google_search(
    *_,
    proxies: Optional[str] = None,
    url: Optional[str] = None,
    file: Optional[BinaryIO] = None,
    **__,
) -> MessageChain:
    if not url and not file:
        raise ValueError("You should offer url or file!")
    async with Network(proxies=proxies) as client:
        google = Google(client=client)
        resp = await google.search(url=url) if url else await google.search(file=file)
        if not resp.raw:

            return MessageChain(
                Image(
                    data_bytes=await Page(
                        Banner("Google 搜图"),
                        GenericBox(GenericBoxItem("服务器未返回内容", "无法搜索到该图片")),
                    ).render()
                )
            )
        resp = resp.raw[2]
        thumb = await get_thumb(resp.thumbnail, proxies)

        page = Page(
            Banner("Google 搜图"),
            ImageBox(img=thumb),
            GenericBox(
                GenericBoxItem("标题", resp.title),
                GenericBoxItem("链接", resp.url),
            ),
            title="Google 搜图",
        )
        msg = MessageChain(Image(data_bytes=await page.render()))
        msg = await check_and_serve(page, "Google", str(hash(thumb)), msg)
        return msg
