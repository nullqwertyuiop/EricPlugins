import logging
from pathlib import Path
from typing import Generator

from metadata import parse_metadata, update_metadata
from standardize import standardize_structure
from model import ModuleMetadata


def iter_metadata(
    path: Path, *, no_update: bool = False
) -> Generator[ModuleMetadata, None, None]:
    for file in path.iterdir():
        if (
            file.name.startswith("_")
            or file.name.startswith(".")
            or path.suffix == ".py"
            or (file.is_file() and file.suffix != ".py")
        ):
            continue
        try:
            file = standardize_structure(file)
        except ValueError as e:
            logging.error(e)
            continue
        yield parse_metadata(file) if no_update else update_metadata(file)


def list_metadata(path: Path, *, no_update: bool = False) -> list[ModuleMetadata]:
    return list(iter_metadata(path, no_update=no_update))
