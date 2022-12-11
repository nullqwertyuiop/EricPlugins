import random
import string
import time
from asyncio import Lock
from contextlib import suppress
from datetime import datetime

import aiohttp
from aiohttp import InvalidURL
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from kayaku import create
from loguru import logger

from library.module.file_server.util import serve_file, get_link
from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem, ImageBox
from library.util.misc import seconds_to_string
from library.util.orm import orm
from module.ai_draw.config import AIDrawConfig
from module.ai_draw.table import StableDiffusionHistory

lock = Lock()


def parse_msg(msg: str) -> tuple[str, str, int, str, float]:
    lines = msg.splitlines()
    positive = None
    negative = None
    steps = None
    method = None
    cfg = None

    for line in lines:
        with suppress(Exception):
            if line.startswith("pos:"):
                positive = line[4:]
            elif line.startswith("neg:"):
                negative = line[4:]
            elif line.startswith("steps:"):
                steps = int(line[6:].strip())
            elif line.startswith("method:"):
                method = line[7:]
            elif line.startswith("cfg:"):
                cfg = float(line[4:].strip())

    if [positive, negative, steps, method, cfg].count(None) == 5:
        positive = msg

    positive = positive or ""
    negative = negative or ""
    steps = steps or 20
    method = method or "Euler a"
    cfg = cfg or 7

    return positive.strip(), negative.strip(), steps, method.strip(), cfg


async def _run_txt2img(
    positive: str,
    negative: str,
    session: str,
    steps: int = 20,
    method: str = "Euler a",
    cfg: float = 7,
) -> Page:
    async with lock:
        logger.info(f"[AI 画图] {session}: 取得锁")
        seed = abs(hash(session))
        start_time = time.perf_counter()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.ws_connect(create(AIDrawConfig).url) as ws:
                    await ws.send_json(
                        {
                            "fn_index": 51,
                            "data": [
                                positive,  # Positive
                                negative,  # Negative
                                "None",  # Style 1
                                "None",  # Style 2
                                steps,  # Sampling steps
                                method,  # Sampling method
                                False,
                                False,
                                1,  # Batch count
                                1,  # Batch size
                                cfg,  # CFG Scale
                                seed,  # Seed
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
                            logger.success(f"[AI 画图] {session}: 生成完成")
                            b64 = msg["output"]["data"][0][0]
                            return _get_page(
                                positive,
                                negative,
                                b64,
                                seed,
                                steps,
                                method,
                                cfg,
                                time.perf_counter() - start_time,
                            )
        except InvalidURL:
            logger.error(f"[AI 画图] {session}: URL 无效")
            raise
        except Exception as e:
            logger.exception(f"[AI 画图] {session}: 发生错误: {e}")
            raise


def _get_page(
    positive: str,
    negative: str,
    img: str,
    seed: int,
    steps: int,
    method: str,
    cfg: float,
    time_cost: float,
) -> Page:
    return Page(
        Banner("AI 画图"),
        ImageBox.from_src(img),
        GenericBox(
            GenericBoxItem(text="Positive Prompt", description=positive or "无"),
            GenericBoxItem(text="Negative Prompt", description=negative or "无"),
            GenericBoxItem(text="Seed", description=str(seed)),
            GenericBoxItem(text="Sampling Steps", description=str(steps)),
            GenericBoxItem(text="Sampling Method", description=method),
            GenericBoxItem(text="CFG Scale", description=str(cfg)),
        ),
        GenericBox(
            GenericBoxItem(
                text="Time Elapsed",
                description=seconds_to_string(_ := int(time_cost))
                + f" {time_cost - _:0.2f} 毫秒",
            )
        ),
        title="AI 画图",
    )


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


async def txt2img(
    field: int,
    supplicant: int,
    positive: str,
    negative: str,
    steps: int = 20,
    method: str = "Euler a",
    cfg: float = 7,
) -> MessageChain:
    session = "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
    ai_cfg: AIDrawConfig = create(AIDrawConfig, flush=True)
    try:
        content = await _run_txt2img(
            positive,
            negative,
            session,
            steps=steps,
            method=method,
            cfg=cfg,
        )
    except Exception as e:  # noqa
        # Already logged, just pass
        return MessageChain('出现错误，可能是 SD 链接失效\n可使用 "[前缀]设置 sd 链接 <链接>" 重新设置')
    uuid = await _serve(content.to_html(), session, ai_cfg.default_lifespan)
    await _insert(field, supplicant, positive, uuid)
    return MessageChain(
        Image(data_bytes=await content.render()),
        f"生成结果：{get_link(uuid)}\n生命周期：{seconds_to_string(ai_cfg.default_lifespan)}",
    )
