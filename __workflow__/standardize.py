import logging
from pathlib import Path


def standardize_structure(path: Path) -> Path:
    if path.is_dir():
        return path
    new_path = path.parent / path.stem
    new_path.mkdir(exist_ok=True)
    path.rename(new_path / "__init__.py")
    logging.info(f"Standardized {path} to {new_path}")
    return new_path
