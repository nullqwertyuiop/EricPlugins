from graia.saya import Channel

from library.util.group_config import module_config

channel = Channel.current()


@module_config(channel.module)
class WordleGroupConfig:
    show_keyboard: bool = True
