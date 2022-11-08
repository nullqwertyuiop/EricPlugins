from graia.saya import Channel
from kayaku import config, create

channel = Channel.current()


@config(channel.module)
class TwitterPreviewConfig:
    """ 推特预览配置 """

    bearer: str = ""
    """ Bearer Token，需要 v2 Essentials 权限 """


create(TwitterPreviewConfig)
