from typing import Optional, BinaryIO

from PicImageSearch import Network, SauceNAO
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.saya import Channel
from kayaku import config, create

from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem, ImageBox, ProgressBar
from module.image_searcher.utils import get_thumb, error_catcher, check_and_serve

channel = Channel.current()


@config(f"{channel.module}.saucenao")
class SauceNAOConfig:
    """SauceNAO 配置"""

    api_key: str = ""
    """API Key"""


@error_catcher
async def saucenao_search(
    *_,
    proxies: Optional[str] = None,
    api_key: str = None,
    url: Optional[str] = None,
    file: Optional[BinaryIO] = None,
    **__,
) -> MessageChain:
    if not url and not file:
        raise ValueError("You should give url or file!")
    if not api_key:
        if not (api_key := create(SauceNAOConfig, flush=True).api_key):
            raise ValueError("未配置 SauceNAO API Key")
    async with Network(proxies=proxies) as client:
        saucenao = SauceNAO(client=client, api_key=api_key)
        resp = await saucenao.search(url=url) if url else await saucenao.search(file=file)
        if not resp.raw:

            return MessageChain(
                Image(
                    data_bytes=await Page(
                            Banner("SauceNAO 搜图"),
                            GenericBox(GenericBoxItem("服务器未返回内容", "无法搜索到该图片")),
                    ).render()
                )
            )
        resp = resp.raw[0]
        thumb = await get_thumb(resp.thumbnail, proxies)

        page = Page(
            Banner("SauceNAO 搜图"),
            ImageBox(img=thumb),
            ProgressBar(resp.similarity / 100, "相似度", f"{resp.similarity}%"),
            GenericBox(
                GenericBoxItem("标题", resp.title),
                GenericBoxItem("作者", resp.author),
                GenericBoxItem("图像链接", resp.url),
            ),
            title="SauceNAO 搜图",
        )
        msg = MessageChain(Image(data_bytes=await page.render()))
        msg = await check_and_serve(page, "SauceNAO", str(hash(thumb)), msg)
        return msg
