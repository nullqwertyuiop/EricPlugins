from pydantic import BaseModel

from module.twitter_preview.model.error import TweetError, GeneralError
from module.twitter_preview.model.include import Includes, Photo, User
from module.twitter_preview.model.tweet import UnparsedTweet, ParsedTweet


class Response(BaseModel):
    data: list[UnparsedTweet]
    includes: Includes
    errors: list[TweetError] = []

    def parse(self) -> list[ParsedTweet]:
        tweets: list[ParsedTweet] = []
        for index, tweet in enumerate(self.data):
            media_keys = tweet.attachments.media_keys
            media: list[Photo] = list(
                filter(lambda x: x.media_key in media_keys, self.includes.media)
            )
            if index >= len(self.includes.users):
                index = 0
            user: User = self.includes.users[index]
            tweets.append(ParsedTweet(**tweet.dict(), media=media, user=user))
        return tweets


class ErrorResponse(BaseModel):
    errors: list[GeneralError]
    title: str
    detail: str
    type: str

    def get_id(self) -> list[int]:
        ids: list[int] = []
        for error in self.errors:
            if tweet_id := error.get_id():
                ids.append(tweet_id)
        return ids
