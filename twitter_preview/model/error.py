import re

from pydantic import BaseModel


class TweetError(BaseModel):
    resource_id: int
    parameter: str
    resource_type: str
    section: str
    title: str
    value: int
    detail: str
    type: str


class GeneralError(BaseModel):
    parameters: dict
    message: str

    def get_id(self) -> int:
        if result := re.findall(r"\[(\d+)]", self.message):
            return int(result[0])
