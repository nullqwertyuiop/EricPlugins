from sqlalchemy import Column, Integer, DateTime, BIGINT, String

from library.util.orm import Base


class StableDiffusionHistory(Base):
    """功能调用记录"""

    __tablename__ = "stable_diffusion_history"

    id = Column(Integer, primary_key=True)
    """ 记录ID """

    time = Column(DateTime, nullable=False)
    """ 调用时间 """

    field = Column(BIGINT, nullable=False)
    """ 聊天区域"""

    supplicant = Column(BIGINT, nullable=False)
    """ 调用者 """

    positive = Column(String(length=4000), nullable=False)
    """ 正面标签 """

    uuid = Column(String(length=200), nullable=False)
    """ 文件ID """
