from graia.saya import Channel
from kayaku import config, create

channel = Channel.current()


@config(channel.module)
class AIDrawConfig:
    """AI 画图配置"""

    default_lifespan: int = 60 * 10
    """ 保存文件默认生命周期（秒） """


create(AIDrawConfig)
