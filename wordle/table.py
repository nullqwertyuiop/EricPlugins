from sqlalchemy import Column, BIGINT

from library.util.orm import Base


class WordleStatistic(Base):
    """wordle 游戏数据"""

    __tablename__ = "wordle_statistic"

    group_id = Column(BIGINT, primary_key=True)
    member_id = Column(BIGINT, primary_key=True)
    game_count = Column(BIGINT, default=0)
    win_count = Column(BIGINT, default=0)
    lose_count = Column(BIGINT, default=0)
    correct_count = Column(BIGINT, default=0)
    wrong_count = Column(BIGINT, default=0)
    hint_count = Column(BIGINT, default=0)
