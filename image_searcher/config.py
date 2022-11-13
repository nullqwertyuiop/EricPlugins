from graia.saya import Channel
from kayaku import config

channel = Channel.current()


@config(f"{channel.module}.main")
class ImageSearchConfig:
    """主配置"""

    image_only: bool = True
    """是否只返回图片"""

    lifespan: int = 60 * 60 * 24
    """缓存生命周期"""
