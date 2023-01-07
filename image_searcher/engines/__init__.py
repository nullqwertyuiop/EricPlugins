from typing import Callable

from .ascii2d import ascii2d_search
from .baidu import baidu_search
from .ehentai import ehentai_search
from .google import google_search
from .saucenao import saucenao_search

__engines__: dict[str, Callable] = {
    "ascii2d": ascii2d_search,
    "baidu": baidu_search,
    "ehentai": ehentai_search,
    "google": google_search,
    "saucenao": saucenao_search,
}
