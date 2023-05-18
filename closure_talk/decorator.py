from graia.ariadne.event.message import GroupMessage
from graia.broadcast import ExecutionStop

from module.closure_talk.model.chat import ClosureChatArea
from module.closure_talk.util import ClosureStore


async def session_check(event: GroupMessage) -> tuple[str, ClosureChatArea]:
    group = event.sender.group
    if int(group) not in ClosureStore.session:
        raise ExecutionStop()
    return ClosureStore.session[int(group)]
