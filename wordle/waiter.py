import asyncio
from typing import Dict, Optional, Union

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.model import Group, Member
from graia.broadcast.interrupt.waiter import Waiter
from kayaku import create

from library.model.config import FunctionConfig
from library.util.message import send_message
from module.wordle.gb import running_group, running_mutex
from module.wordle.utils import StatisticType, update_member_statistic
from module.wordle.wordle import Wordle, all_word

CE = {"CHS": "中译", "ENG": "英译"}


class WordleWaiter(Waiter.create([GroupMessage])):
    def __init__(
        self,
        wordle: Wordle,
        meaning: Dict[str, str],
        group: Union[Group, int],
        account: int,
        member: Optional[Union[Member, int]] = None,
    ):
        self.account = account
        self.wordle = wordle
        self.group = group if isinstance(group, int) else group.id
        self.meaning = meaning
        self.meaning_str = "\n".join(
            f"{CE[e]}：{self.meaning[e]}" for e in CE if e in self.meaning
        )
        self.member = (
            (member if isinstance(member, int) else member.id) if member else None
        )
        self.member_list = set()
        self.member_list_mutex = asyncio.Lock()

    async def update_statistic(
        self, statistic: StatisticType, member: Union[Member, int]
    ):
        async with self.member_list_mutex:
            await update_member_statistic(self.group, member, statistic)

    async def remove_running(self):
        async with running_mutex:
            if self.group in running_group:
                running_group.remove(self.group)

    async def game_over(self, app: Ariadne, source: Source):
        await send_message(
            self.group,
            MessageChain(
                Image(data_bytes=self.wordle.get_img()),
                "很遗憾，没有人猜出来呢" f"单词：{self.wordle.word}\n{self.meaning_str}",
            ),
            app.account,
            quote=source,
            is_group=True,
        )

        async with self.member_list_mutex:
            for m in self.member_list:
                await update_member_statistic(
                    self.group, m, StatisticType.lose | StatisticType.game
                )
        await self.remove_running()

        return False

    async def detected_event(
        self,
        app: Ariadne,
        group: Group,
        member: Member,
        message: MessageChain,
        source: Source,
    ):
        # 判断是否是服务范围
        if (
            app.account != self.account
            or self.group != group.id
            or (self.member and self.member != member.id)
        ):
            return

        # 什么，放弃了？GiveUp!
        word = str(message).strip()
        config: FunctionConfig = create(FunctionConfig)
        if word in {
            f"{config.prefix[0]}wordle --giveup",
            f"{config.prefix[0]}wordle -g",
        }:
            return await self.game_over(app, source)

        if word == f"{config.prefix[0]}wordle --hint":
            await self.update_statistic(StatisticType.hint, member)
            await send_message(
                group,
                MessageChain(
                    Image(data_bytes=self.wordle.get_hint())
                    if self.wordle.guess_right_chars
                    else "你还没有猜对过一个字母哦~再猜猜吧~"
                ),
                app.account,
                is_group=True,
            )
            return True

        word = word.upper()
        # 应该是聊其他的，直接 return
        legal_chars = "'-./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if len(word) != self.wordle.length or any(c not in legal_chars for c in word):
            return

        async with self.member_list_mutex:
            self.member_list.add(member.id)

        if word not in all_word:
            await send_message(
                group,
                MessageChain(f"你确定 {word} 是一个合法的单词吗？"),
                app.account,
                quote=source,
                is_group=True,
            )
            return True
        elif word in self.wordle.history_words:
            await send_message(
                group,
                MessageChain("你已经猜过这个单词了呢"),
                app.account,
                quote=source,
                is_group=True,
            )
            return True

        game_end, game_win = self.wordle.guess(word)

        if game_win:
            await self.update_statistic(StatisticType.correct, member)
            for m in self.member_list:
                await self.update_statistic(StatisticType.win | StatisticType.game, m)

            await send_message(
                group,
                MessageChain(
                    Image(data_bytes=self.wordle.get_img()),
                    f"\n恭喜你猜出了单词！\n【单词】：{self.wordle.word}\n{self.meaning_str}",
                ),
                app.account,
                quote=source,
                is_group=True,
            )
            await self.remove_running()
            return False
        elif game_end:
            await self.update_statistic(StatisticType.wrong, member)
            return (
                await self.game_over(app, source)
                if group.id in running_group
                else False
            )
        else:
            await send_message(
                group,
                MessageChain(Image(data_bytes=self.wordle.get_img())),
                app.account,
                is_group=True,
            )
            await self.update_statistic(StatisticType.wrong, member)
            return True
