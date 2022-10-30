import random
import string
from asyncio import Lock
from datetime import datetime

import aiohttp
from graia.ariadne.message.chain import MessageChain
from loguru import logger

from library.module.file_server.util import serve_file, get_link
from library.util.misc import seconds_to_string
from library.util.orm import orm
from module.ai_draw.table import StableDiffusionHistory

lock = Lock()
SD_URL: str = ""
DEFAULT_LIFESPAN: int = 60 * 60


async def _communicate(positive: str, session: str) -> str:
    async with lock:
        logger.info(f"{session}: 取得锁")
        try:
            async with aiohttp.ClientSession() as s:
                async with s.ws_connect(SD_URL) as ws:
                    await ws.send_json(
                        {
                            "fn_index": 51,
                            "data": [
                                positive,  # Positive
                                "",  # Negative
                                "None",  # Style 1
                                "None",  # Style 2
                                20,  # Sampling steps
                                "Euler a",  # Sampling method
                                False,
                                False,
                                1,  # Batch count
                                1,  # Batch size
                                7,  # CFG Scale
                                -1,  # Seed
                                -1,
                                0,
                                0,
                                0,
                                False,
                                512,  # Width
                                512,  # Height
                                False,
                                0.7,
                                0,
                                0,
                                "None",
                                0.9,
                                5,
                                "0.0001",
                                False,
                                "None",
                                "",
                                0.1,
                                False,
                                False,
                                False,
                                None,
                                "",
                                "Seed",
                                "",
                                "Nothing",
                                "",
                                True,
                                False,
                                False,
                                None,
                                "",
                                "",
                            ],
                            "session_hash": session,
                        }
                    )
                    while True:
                        msg = await ws.receive_json()
                        if msg["msg"] == "process_completed":
                            logger.success(f"{session}: 生成完成")
                            b64 = msg["output"]["data"][0][0]
                            return f"<img src='{b64}'>"
        except Exception as e:
            logger.exception(f"{session}: 发生错误: {e}")
            raise


async def _serve(content: str, session: str, lifespan: int) -> str:
    return await serve_file(
        content.encode("utf-8"), f"{session}.html", lifespan=lifespan
    )


async def _insert(field: int, supplicant: int, positive: str, uuid: str):
    await orm.add(
        StableDiffusionHistory,
        time=datetime.now(),
        field=field,
        supplicant=supplicant,
        positive=positive,
        uuid=uuid,
    )


async def render(field: int, supplicant: int, positive: str) -> MessageChain:
    session = "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
    try:
        content = await _communicate(positive, session)
    except Exception as e:  # noqa
        # Already logged, just pass
        return MessageChain('出现错误，可能是 SD 链接失效\n可使用 "[前缀]设置 sd 链接 <链接>" 重新设置')
    uuid = await _serve(content, session, DEFAULT_LIFESPAN)
    await _insert(field, supplicant, positive, uuid)
    return MessageChain(
        f"生成结果：{get_link(uuid)}\n生命周期：{seconds_to_string(DEFAULT_LIFESPAN)}"
    )
