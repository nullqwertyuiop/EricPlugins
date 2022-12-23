from contextlib import suppress

from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    SpacePolicy,
    RegexMatch, RegexResult,
)
from graia.saya import Channel
from graiax.shortcut import listen, dispatch, decorate
from graiax.shortcut.saya import schedule
from kayaku import create

from library.decorator import Switch, Distribution, Blacklist
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message
from library.util.misc import seconds_to_string
from module.ehentai_downloader.config import EHentaiConfig
from module.ehentai_downloader.threshold import _EThresholdError, _EThreshold
from module.ehentai_downloader.util import _ESession

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("eh").space(SpacePolicy.FORCE),
        RegexMatch(r"(https?://)?e[-x]hentai\.org/g/\d+/[\da-z]+/?") @ "url",
    )
)
@decorate(Switch.check(channel.module), Distribution.distribute(), Blacklist.check())
async def eh_test(app: Ariadne, event: MessageEvent, url: RegexResult):
    try:
        _EThreshold.judge()
        active = await send_message(event, MessageChain("已收到链接，正在尝试下载"), app.account)
        session = _ESession(url.result.display)
        cfg: EHentaiConfig = create(EHentaiConfig)
        link = await session.serve()
        msg = (
            f"[E-hentai 下载器] 已下载图库 {session.gallery.title}\n"
            f"下载链接: {link}\n生命周期：{seconds_to_string(cfg.lifespan)}"
        )
        await send_message(event, MessageChain(msg), app.account)
        with suppress(Exception):
            await app.recall_message(active)
    except _EThresholdError as e:
        await send_message(event, MessageChain(e.args[0]), app.account)
    except Exception:  # noqa
        await send_message(
            event, MessageChain("下载失败，请检查链接是否有效，或账号点数是否足够"), app.account
        )


@schedule("0 0 * * * *")
async def eh_clear_hour():
    _EThreshold.reset_hour()


@schedule("0 0 0 * * *")
async def eh_clear_day():
    _EThreshold.reset_all()
