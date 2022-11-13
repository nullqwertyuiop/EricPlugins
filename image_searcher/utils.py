import functools

import aiohttp
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from kayaku import create

from library.module.file_server.util import serve_file, get_link
from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem
from library.util.misc import seconds_to_string
from module.image_searcher.config import ImageSearchConfig


async def get_thumb(url: str, proxy: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy=proxy) as resp:
            return await resp.read()


async def check_and_serve(page: Page, name: str, filename: str, msg: MessageChain) -> MessageChain:
    if not (main_cfg := create(ImageSearchConfig, flush=True)).image_only:
        uuid = await serve_file(
            page.to_html().encode("utf-8"),
            f"{filename}.html",
            lifespan=main_cfg.lifespan,
        )
        msg = msg.append(
            Plain(
                f"{name} 搜图结果：{get_link(uuid)}\n"
                f"生命周期：{seconds_to_string(main_cfg.lifespan)}"
            )
        )
    return msg


def error_catcher(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:

            return MessageChain(
                [
                    Image(
                        data_bytes=await Page(
                            Banner(func.__name__.replace("_", " ").title()),
                            GenericBox(GenericBoxItem("运行搜索时出现异常", f"{e}")),
                            GenericBox(
                                GenericBoxItem(
                                    "可以尝试以下解决方案",
                                    "检查依赖是否为最新版本\n"
                                    "检查服务器 IP 是否被封禁\n"
                                    "检查 API 是否有效\n"
                                    "检查网络连接是否正常"
                                )
                            ),
                        ).render()
                    )
                ]
            )

    return wrapper
