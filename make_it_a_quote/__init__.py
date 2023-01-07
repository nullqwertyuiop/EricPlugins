import html
import re

from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, MessageEvent
from graia.ariadne.exception import UnknownTarget
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image
from graia.ariadne.message.parser.twilight import (
    Twilight,
    FullMatch,
    ElementMatch,
    RegexResult,
    WildcardMatch, ArgumentMatch, ArgResult,
)
from graia.saya import Channel
from graiax.playwright import PlaywrightBrowser
from graiax.shortcut import listen, dispatch, decorate

from library.decorator.blacklist import Blacklist
from library.decorator.distribute import Distribution
from library.decorator.function_call import FunctionCall
from library.decorator.switch import Switch
from library.ui.element.page import HARMONY_FONT_URL
from library.util.dispatcher import PrefixMatch
from library.util.message import send_message

channel = Channel.current()


@listen(GroupMessage, FriendMessage)
@dispatch(
    Twilight(
        ElementMatch(At, optional=True),
        PrefixMatch(),
        FullMatch("入典"),
        ArgumentMatch("-c", "--color", action="store_true", default=False) @ "color",
        WildcardMatch().flags(re.S) @ "content",
    )
)
@decorate(
    Switch.check(channel.module),
    Distribution.distribute(),
    Blacklist.check(),
    FunctionCall.record(channel.module),
)
async def make_it_a_quote(app: Ariadne, event: MessageEvent, color: ArgResult, content: RegexResult):
    if not content.result.display and not event.quote:
        return await send_message(event, MessageChain("回复消息或手动输入内容时可用"), app.account)
    content: MessageChain = content.result
    if not (text := content.display):
        try:
            event: MessageEvent = await app.get_message_from_id(
                event.quote.id,
                event.sender.group if isinstance(event, GroupMessage) else event.sender,
            )
            text = event.message_chain.display
        except UnknownTarget:
            return await send_message(event, MessageChain("暂未缓存该消息"), app.account)
    text = html.escape(text).replace("\n", "<br>")
    _html = html_string.format(
        url=f"https://q2.qlogo.cn/headimg_dl?dst_uin={event.sender.id}&spec=640",
        filter="" if color.result else "filter: grayscale(100%);",
        text=text,
        subtext=f"-- {event.sender.name}",
        HARMONY_FONT_URL=HARMONY_FONT_URL
    )
    browser = Ariadne.current().launch_manager.get_interface(PlaywrightBrowser)
    async with browser.page(
        viewport={"width": 640, "height": 1}, device_scale_factor=1.0
    ) as page:
        await page.set_content(_html)
        img = await page.screenshot(
            type="jpeg", quality=80, full_page=True, scale="device"
        )
    return await send_message(event, MessageChain(Image(data_bytes=img)), app.account)


html_string = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Title</title>
    <style>
        @font-face {{
            font-family: homo;
            src: url('{HARMONY_FONT_URL}') format('truetype');
        }}

        * {{
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: black;
        }}

        img {{
            width: 640px;
            height: 640px;
            mask: linear-gradient(75deg, black 60%, transparent 75%, transparent 100%);
            {filter}
        }}

        .text-margin {{
            margin: 10px 50px 10px 10px;
        }}

        p {{
            font-family: 'homo';
            max-width: 600px;
            word-wrap: break-word
        }}

        .text {{
            color: white;
            font-size: 50px;
            font-weight: bold;
        }}

        .subtext {{
            color: gray;
            font-size: 30px;
            font-style: italic;
        }}
    </style>
</head>
<body>
<div style="width: 1280px; height: 640px; background-color: black; flex: auto; display: flex">
    <img src="{url}"/>
    <div id="text-area"
         style="
             flex: auto;
             display: flex;
             align-content: center;
             justify-content: center;
             align-items: center;
             flex-direction: column;
    ">
        <p class="text text-margin"> {text} </p>
        <p class="subtext text-margin"> {subtext} </p>
    </div>
</div>
</body>
</html>
"""
