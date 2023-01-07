import asyncio
import json
import random

from creart import it
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.message.parser.twilight import (
    ArgResult,
    ArgumentMatch,
    Twilight,
    FullMatch,
)
from graia.ariadne.model import Group, Member
from graia.broadcast.interrupt import InterruptControl
from graia.saya import Channel
from graiax.shortcut import listen, dispatch, decorate
from kayaku import create
from loguru import logger

from library.decorator import Switch, Blacklist, FunctionCall, Distribution
from library.model.config import FunctionConfig
from library.util.dispatcher import PrefixMatch
from library.util.group_config import module_create
from library.util.message import send_message
from module.wordle.config import WordleGroupConfig
from module.wordle.gb import running_group, running_mutex
from module.wordle.utils import get_member_statistic
from module.wordle.waiter import WordleWaiter
from module.wordle.wordle import Wordle, word_dic, word_path

channel = Channel.current()
inc = it(InterruptControl)

DEFAULT_DIC = "CET4"

decorators = [
    Switch.check(channel.module),
    Blacklist.check(),
    FunctionCall.record(channel.module),
    Distribution.distribute()
]

# 你肯定好奇为什么会有一个 @ "_"，因为这涉及到一个bug


@listen(GroupMessage)
@dispatch(
    Twilight(
        [
            PrefixMatch(),
            FullMatch("wordle"),
            ArgumentMatch("-h", "--help", action="store_true", optional=False) @ "_",
        ]
    )
)
@decorate(*decorators)
async def wordle_help(app: Ariadne, event: MessageEvent):
    config: FunctionConfig = create(FunctionConfig)
    await send_message(
        event,
        MessageChain(
            "Wordle文字游戏\n"
            "答案为指定长度单词，发送对应长度单词即可\n"
            "灰色块代表此单词中没有此字母\n"
            "黄色块代表此单词中有此字母，但该字母所处位置不对\n"
            "绿色块代表此单词中有此字母且位置正确\n"
            "猜出单词或用光次数则游戏结束\n"
            f"发起游戏：{config.prefix[0]}wordle -l 5 -d SAT，其中-l/--length为单词长度，-d/--dic为指定词典，默认为5和CET4\n"
            f"中途放弃：{config.prefix[0]}wordle -g 或 {config.prefix[0]}wordle --giveup\n"
            f"查看数据统计：{config.prefix[0]}wordle -s 或 {config.prefix[0]}wordle --statistic\n"
            f"查看提示：{config.prefix[0]}wordle -hint\n"
            f"注：目前包含词典：{'、'.join(word_dic)}"
        ),
        app.account,
    )


@listen(GroupMessage)
@dispatch(
    Twilight(
        [
            PrefixMatch(),
            FullMatch("wordle"),
            ArgumentMatch(
                "-s", "--statistic", action="store_true", optional=False
            )
            @ "_",
        ]
    )
)
@decorate(*decorators)
async def wordle_statistic(app: Ariadne, event: MessageEvent):
    group = event.sender.group
    member = event.sender
    data = await get_member_statistic(group, member)
    await send_message(
        group,
        MessageChain(
            f"用户 {member.name}\n共参与{data[4]}场游戏，"
            f"其中胜利{data[0]}场，失败{data[1]}场\n"
            f"一共猜对{data[2]}次，猜错{data[3]}次，"
            f"共使用过{data[5]}次提示，再接再厉哦~"
        ),
        app.account,
        quote=event.source,
    )


@listen(GroupMessage)
@dispatch(
    Twilight(
        PrefixMatch(),
        FullMatch("wordle"),
        ArgumentMatch("-n", "--no-keyboard", action="store_true") @ "no_keyboard",
        ArgumentMatch("-k", "--keyboard", action="store_true") @ "keyboard",
    )
)
@decorate(*decorators)
async def wordle_keyboard_cfg(app: Ariadne, event: MessageEvent, no_keyboard: ArgResult, keyboard: ArgResult):
    no_keyboard = no_keyboard.result
    keyboard = keyboard.result
    if no_keyboard and keyboard:
        await send_message(
            event,
            MessageChain("参数错误，无法同时开启和关闭键盘"),
            app.account,
        )
        return
    wordle_group_cfg: WordleGroupConfig = module_create(WordleGroupConfig)
    if no_keyboard:
        wordle_group_cfg.show_keyboard = False
    if keyboard:
        wordle_group_cfg.show_keyboard = True
    await send_message(
        event,
        MessageChain(f"Wordle 键盘已{'开启' if wordle_group_cfg.show_keyboard else '关闭'}"),
        app.account,
    )


@listen(GroupMessage)
@dispatch(
    Twilight(
        [
            PrefixMatch(),
            FullMatch("wordle"),
            ArgumentMatch("-d", "--dic") @ "dic",
            ArgumentMatch("--single", action="store_true") @ "single",
            ArgumentMatch("-l", "--length") @ "length",
        ]
    )
)
@decorate(*decorators)
async def wordle(
    app: Ariadne,
    group: Group,
    member: Member,
    source: Source,
    dic: ArgResult,
    single: ArgResult,
    length: ArgResult,
):
    # 判断是否开了
    async with running_mutex:
        if group.id in running_group:
            await send_message(
                group, MessageChain("诶，游戏不是已经开始了吗？等到本局游戏结束再开好不好"), app.account
            )
            return

    # 字典选择
    if dic.matched:
        if (choose_dic := str(dic.result)) not in word_dic:
            await send_message(
                group,
                MessageChain(
                    f"{choose_dic}是什么类型的字典啊，我不造啊\n" f"我只知道{'、'.join(word_dic)}"
                ),
                app.account
            )
            return
    else:
        choose_dic = "CET4"

    dic_data = json.loads(
        (word_path / f"{choose_dic}.json").read_text(encoding="UTF-8")
    )

    # 长度选择
    if length.matched:
        ls = str(length.result)
        if not ls.isnumeric():
            await send_message(group, MessageChain(f"'{ls}'是数字吗？"), app.account)
            return
        word_length = int(ls)
    else:
        word_length = 5

    # 搜寻并决定单词
    choices = [k for k in dic_data if len(k) == word_length]
    if not choices:
        await send_message(group, MessageChain("对不起呢，没有这种长度的单词"), app.account)
        return

    guess_word = random.choice(choices)

    # 是否单人
    single_gamer = single.matched

    async with running_mutex:
        running_group.add(group.id)
    gaming = True

    w = Wordle(guess_word)
    logger.success(f"成功创建 Wordle 实例，单词为：{guess_word}")
    await send_message(group, MessageChain(Image(data_bytes=w.get_img())), app.account)

    try:
        while gaming:
            gaming = await inc.wait(
                WordleWaiter(
                    w,
                    dic_data[guess_word],
                    group,
                    app.account,
                    member if single_gamer else None,
                ),
                timeout=300,
            )
    except asyncio.exceptions.TimeoutError:
        await send_message(group, MessageChain("游戏超时，进程结束"), app.account, quote=source)
        async with running_mutex:
            # 防止多次删除抛出异常
            if group.id in running_group:
                running_group.remove(group.id)
