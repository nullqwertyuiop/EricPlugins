from kayaku import create

from module.ehentai_downloader.config import EHentaiConfig


class _EThresholdError(Exception):
    pass


class _EThreshold:
    daily: int = 0
    hourly: int = 0
    size: int = 0

    @classmethod
    def reset_all(cls):
        cls.daily = 0
        cls.hourly = 0
        cls.size = 0

    @classmethod
    def reset_hour(cls):
        cls.hourly = 0

    @classmethod
    def judge(cls):
        config: EHentaiConfig = create(EHentaiConfig, flush=True)
        if cls.daily >= config.per_day:
            raise _EThresholdError("今日公用下载次数已达上限")
        if cls.hourly >= config.per_hour:
            raise _EThresholdError("本小时公用下载次数已达上限")
        if cls.size >= config.max_size:
            raise _EThresholdError("今日公用下载大小已达上限")
