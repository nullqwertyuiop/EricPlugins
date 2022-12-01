from dataclasses import dataclass, field

from graia.saya import Channel
from kayaku import config, create

channel = Channel.current()


@dataclass
class TwitterPreviewMetricsConfig:
    """ 推特预览数据配置 """

    tags: bool = False
    """ 包含标签 """

    retweet: bool = False
    """ 包含转推 """

    reply: bool = False
    """ 包含回复 """

    like: bool = False
    """ 包含点赞 """

    quote: bool = False
    """ 包含引用 """

    create_time: bool = True
    """ 发布时间 """

    fetch_time: bool = False
    """ 获取时间 """


@config(channel.module)
class TwitterPreviewConfig:
    """ 推特预览配置 """

    bearer: str = ""
    """ Bearer Token，需要 v2 Essentials 权限 """

    lifespan: int = 60 * 60 * 24
    """ 生命周期 """

    metrics: TwitterPreviewMetricsConfig = field(default_factory=TwitterPreviewMetricsConfig)
    """ 推特预览数据配置 """


create(TwitterPreviewConfig)
