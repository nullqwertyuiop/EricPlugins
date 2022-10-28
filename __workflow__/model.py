import re
from pathlib import Path

from pydantic import BaseModel, validator
from typing_extensions import Self


class ModuleAdvancedSetting(BaseModel):
    allow_disable: bool = True
    allow_unload: bool = True
    hidden: bool = False


class ModuleMetadata(BaseModel):
    name: str
    version: str = "0.1.0"
    pack: str
    authors: list[str] = []
    required: list[str] = []
    description: str = ""
    category: list[str] = []
    advanced: ModuleAdvancedSetting = ModuleAdvancedSetting()
    size: int = -1
    files: list[str] = []

    def __repr__(self):
        output = ["ModuleMetadata:"]
        max_length = max(len(key) for key in self.dict().keys())
        for key, value in self.dict().items():
            if isinstance(value, list):
                value = f"\n\t{' ' * max_length}  ".join(value)
            output.append(f"\t{key + ' ' * (max_length - len(key))}: {value}")
        return "\n".join(output)

    @validator("version")
    def _module_version_validator(cls, version: str):
        """模块版本验证器"""
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            raise ValueError("版本号不符合规范")
        return version

    @property
    def path(self):
        return Path.cwd() / self.pack.split(".")[-1]

    def walk(self, path: Path = None):
        if path is None:
            path = self.path
        for file in path.iterdir():
            if file.is_file():
                yield file
            else:
                yield from self.walk(file)

    def calc_size(self) -> Self:
        self.size = sum(file.stat().st_size for file in self.walk())
        return self

    def gen_files(self) -> Self:
        self.files = [str(file.relative_to(self.path)) for file in self.walk()]
        return self
