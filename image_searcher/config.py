from graia.saya import Channel
from kayaku import config

from library.util.group_config.util import module_config

channel = Channel.current()


@config(f"{channel.module}.main")
class ImageSearchConfig:
    """主配置"""

    image_only: bool = True
    """是否只返回图片"""

    lifespan: int = 60 * 60 * 24
    """缓存生命周期"""


@module_config(channel.module)
class ImageSearchGroupConfig:
    """群组配置"""

    ascii2d: bool = True
    """是否启用 ascii2d"""

    baidu: bool = True
    """是否启用 baidu"""

    ehentai: bool = True
    """是否启用 ehentai"""

    google: bool = True
    """是否启用 google"""

    saucenao: bool = True
    """是否启用 saucenao"""
