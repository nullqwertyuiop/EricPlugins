from contextlib import suppress

from graia.ariadne import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.saya import Channel
from graiax.fastapi.saya import route
from kayaku import create
from pydantic import BaseModel

from library.util.message import send_message
from module.sms_forward.config import SMSForwardConfig
from module.sms_forward.util import resolve_key, gen_msg

channel = Channel.current()


class SMSForwardResponse(BaseModel):
    data: str


@route.post("/module/sms_forward")
async def test(data: SMSForwardResponse, token: str):
    content = data.data.splitlines()
    cfg: SMSForwardConfig = create(SMSForwardConfig, flush=True)
    with suppress(ValueError):
        if token not in cfg.registered.values():
            return
        key = [key for key, value in cfg.registered.items() if value == token][0]
        is_group, target = resolve_key(key)
        msg = gen_msg(content)
        await send_message(
            target, MessageChain(msg), Ariadne.current().account, is_group=is_group
        )
