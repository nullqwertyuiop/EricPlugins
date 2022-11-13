from typing import Optional, BinaryIO

from PicImageSearch import Network, EHentai
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image

from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem, ImageBox
from module.image_searcher.utils import get_thumb, error_catcher, check_and_serve


@error_catcher
async def ehentai_search(
    *_,
    proxies: Optional[str] = None,
    cookies: Optional[str] = None,
    ex: bool = False,
    url: Optional[str] = None,
    file: Optional[BinaryIO] = None,
    **__,
) -> MessageChain:
    if not url and not file:
        raise ValueError("You should offer url or file!")
    if ex and not cookies:
        raise ValueError("If you use EXHentai Searcher, you should offer cookies!")
    async with Network(proxies=proxies, cookies=cookies) as client:
        ehentai = EHentai(client=client)
        resp = await ehentai.search(url=url, ex=ex) if url else await ehentai.search(file=file, ex=ex)
        if not resp.raw:

            return MessageChain(
                Image(
                    data_bytes=await Page(
                        Banner(f"E{'x' if ex else '-'}Hentai 搜图"),
                        GenericBox(GenericBoxItem("服务器未返回内容", "无法搜索到该图片")),
                    ).render()
                )
            )

        resp = resp.raw[0]
        thumb = await get_thumb(resp.thumbnail, proxies)

        page = Page(
            Banner(f"E{'x' if ex else '-'}Hentai 搜图"),
            ImageBox(img=thumb),
            GenericBox(
                GenericBoxItem("标题", resp.title),
                GenericBoxItem("类别", resp.type),
                GenericBoxItem("上传日期", resp.date),
                GenericBoxItem("标签", " ".join([f"#{tag}" for tag in resp.tags])),
                GenericBoxItem("链接", resp.url),
            ),
            title="E{'x' if ex else '-'}Hentai 搜图",
        )
        msg = MessageChain(Image(data_bytes=await page.render()))
        msg = await check_and_serve(page, f"E{'x' if ex else '-'}Hentai", str(hash(thumb)), msg)
        return msg
