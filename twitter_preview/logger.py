from loguru import logger


class _TwitterPreviewLogger:
    @staticmethod
    def debug(msg):
        logger.debug(msg)

    @staticmethod
    def warning(msg):
        logger.warning(msg)

    @staticmethod
    def error(msg):
        logger.error(msg)
