from datetime import datetime, timedelta

from graia.ariadne import Ariadne
from graia.ariadne.message.chain import Quote, MessageChain
from graia.ariadne.message.element import Forward, ForwardNode

from library.util.message import send_message
from library.util.typ import Message
from module.openai.api.chat import ChatCompletion


class ChatSession:
    instance: ChatCompletion
    mapping: dict[int, str]

    def __init__(self):
        self.instance = ChatCompletion()
        self.mapping = {}

    async def remove(self, app: Ariadne, event: Message, quote: Quote):
        if quote.id in self.mapping:
            self.instance.remove(self.mapping[quote.id])
            del self.mapping[quote.id]
            return await send_message(event, MessageChain("已删除该条目"), app.account)
        return await send_message(event, MessageChain("未找到该条目"), app.account)

    async def revoke(self, app: Ariadne, event: Message, quote: Quote, count: int):
        if quote.id in self.mapping:
            self.instance.revoke(count, self.mapping[quote.id])
            return await send_message(event, MessageChain("已撤回该条目"), app.account)
        return await send_message(event, MessageChain("未找到该条目"), app.account)

    async def send(
        self, app: Ariadne, event: Message, content: str, quote: Quote | None = None
    ):
        (user_id, _), (reply_id, reply_content) = await self.instance.send(
            content, self.mapping.get(quote.id) if quote else quote
        )
        active = await send_message(event, MessageChain(reply_content), app.account)
        if user_id and reply_id:
            self.mapping[event.id] = user_id
            self.mapping[active.id] = reply_id

    async def get_chain(self, app: Ariadne, event: Message, quote: Quote):
        if chain := self.instance.get_chain(self.mapping.get(quote.id)):
            return await send_message(
                event,
                MessageChain(
                    Forward(
                        [
                            ForwardNode(
                                target=8000_0000
                                if node["entry"]["role"] == "user"
                                else app.account,
                                time=datetime.now()
                                - timedelta(minutes=len(chain))
                                + timedelta(minutes=index),
                                message=MessageChain(node["entry"]["content"]),
                                name="用户"
                                if node["entry"]["role"] == "user"
                                else "ChatGPT",
                            )
                            for index, node in enumerate(chain)
                        ]
                    )
                ),
                app.account,
            )
        return await send_message(event, MessageChain("未找到该条目"), app.account)

    async def flush(self, app: Ariadne, event: Message, system: bool):
        self.instance.flush(system)
        return await send_message(event, MessageChain("已清空"), app.account)

    async def set_system(self, app: Ariadne, event: Message, system: str):
        self.instance.system = system
        return await send_message(event, MessageChain("已设置 system prompt"), app.account)


class ChatSessionContainer:
    session: dict[int, ChatSession] = {}

    @classmethod
    def get_or_create(cls, field: int) -> ChatSession:
        if field not in cls.session:
            cls.session[field] = ChatSession()
        return cls.session[field]
