from graia.saya import Channel
from kayaku import config

channel = Channel.current()


@config(channel.module)
class EHentaiConfig:
    ipb_member_id: str = ""
    ipb_pass_hash: str = ""
    igneous: str = ""
    lifespan: int = 60 * 60 * 24
    per_day: int = 50
    per_hour: int = 10
    max_size: int = 1024 * 1024 * 1024

    def dict(self):
        return {
            "ipb_member_id": self.ipb_member_id,
            "ipb_pass_hash": self.ipb_pass_hash,
            "igneous": self.igneous,
        }
