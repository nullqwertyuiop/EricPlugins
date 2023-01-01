import contextlib

from graia.ariadne import Ariadne
from graia.saya import Channel
from kayaku import create
from pydantic import ValidationError

from library.model.config import EricConfig
from library.ui import Page
from library.ui.element import Banner, GenericBox, GenericBoxItem
from module.twitter_preview.model.config import TwitterPreviewConfig
from module.twitter_preview.model.response import Response, ErrorResponse
from module.twitter_preview.var import ENDPOINT, STATUS_LINK_PATTERN, SHORT_LINK_PATTERN

channel = Channel.current()


async def query(
    ids: list[int | str], *, banner_text: str = "Twitter 预览", exclude_error: bool = True
) -> Response | ErrorResponse | bytes:
    try:
        config: TwitterPreviewConfig = create(TwitterPreviewConfig, flush=True)
        eric_cfg: EricConfig = create(EricConfig)
        assert config.bearer, "推特 Bearer 未配置"
        headers = {"Authorization": f"Bearer {config.bearer}"}

        ids = list(map(lambda x: str(x), ids))
        _ids: str = ",".join(ids)
        async with Ariadne.service.client_session.get(
            ENDPOINT.format(ids=_ids), proxy=eric_cfg.proxy, headers=headers
        ) as resp:
            try:
                data = await resp.json()
                return Response(**data)
            except ValidationError:
                err_resp = ErrorResponse(**data)
                if not exclude_error:
                    return err_resp
                for _id in err_resp.get_id():
                    _id = str(_id)
                    with contextlib.suppress(ValueError):
                        ids.remove(_id)
                    return await query(
                        ids=ids, banner_text=banner_text, exclude_error=False
                    )
    except AssertionError as err:
        return await compose_error(err.args[0], banner_text)
    except Exception as err:
        return await compose_error(str(err), banner_text)


async def compose_error(err_text: str, banner_text: str) -> bytes:
    page = Page(
        Banner(banner_text),
        GenericBox(GenericBoxItem(text="运行搜索时出现错误", description=err_text)),
    )
    return await page.render()


async def get_status_link(short_link: str) -> str | None:
    config: EricConfig = create(EricConfig)
    if not short_link.startswith("http"):
        short_link = f"https://{short_link}"
    async with Ariadne.service.client_session.get(
        url=short_link, proxy=config.proxy, verify_ssl=False
    ) as res:
        if STATUS_LINK_PATTERN.findall(str(res.url)):
            return str(res.url)


async def get_status_id(message: str) -> list[str]:
    status_links = []
    if short_links := SHORT_LINK_PATTERN.findall(message):
        for short_link in short_links:
            if link := await get_status_link(short_link):
                status_links.append(link)
    if status_ids := STATUS_LINK_PATTERN.findall(message + " ".join(status_links)):
        return status_ids
    return []
