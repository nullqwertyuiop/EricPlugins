from dataclasses import field

from graia.saya import Channel
from kayaku import config, create

channel = Channel.current()


@config(channel.module)
class SMSForwardConfig:
    registered: dict[str, str] = field(default_factory=dict)


create(SMSForwardConfig)
