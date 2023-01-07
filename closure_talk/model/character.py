from dataclasses import dataclass


@dataclass
class ClosureCharacter:
    id: str
    images: list[str]
    names: dict[str, str]
    searches: list[str]
    short_names: dict[str, str]

    def __hash__(self):
        return hash(self.id)
