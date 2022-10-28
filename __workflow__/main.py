import json
import logging
import os
from pathlib import Path


def install_deps(*dependencies: str):
    import pip

    pip.main(["install", *dependencies])


def chdir():
    if Path.cwd() != Path(__file__).parent.parent:
        logging.info(f"Change working directory to {Path(__file__).parent.parent}")
        os.chdir(Path(__file__).parent.parent)


def generate() -> list[str]:
    from model import ModuleMetadata
    from get import iter_metadata

    modules: list[ModuleMetadata] = []
    logging.info("Start generating module metadata")

    for module in iter_metadata(Path.cwd()):
        module.calc_size().gen_files()
        modules.append(module)
        print(repr(module))

    dicts: list[dict] = [module.dict() for module in modules]

    with (Path.cwd() / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(dicts, f, ensure_ascii=False, indent=4)

    logging.info("Finished generating module metadata")

    return [module.pack.split(".")[-1] for module in modules]


def push(modules: list[str]):
    logging.info("Start pushing module metadata")

    os.system("git config user.name github-actions[bot]")
    os.system(
        "git config user.email 41898282+github-actions[bot]@users.noreply.github.com"
    )

    os.system("git branch -D modules")
    os.system("git checkout --orphan modules")
    os.system("git reset")

    for module in modules:
        os.system(f"git add {module}")
    os.system("git add metadata.json")

    os.system('git commit -m ":package: Update module metadata"')

    os.system("git push -f origin modules")
    logging.info("Finished pushing module metadata")


if __name__ == "__main__":
    chdir()
    install_deps("pydantic")
    push(generate())
