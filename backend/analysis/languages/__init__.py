from .registry import (
    get_adapter,
    register_adapter,
    supported_languages,
)

from .python import PythonAdapter
from .c import CAdapter
from .cpp import CppAdapter
from .java import JavaAdapter
from .javascript import JavaScriptAdapter
from .go import GoAdapter


register_adapter(PythonAdapter())
register_adapter(CAdapter())
register_adapter(CppAdapter())
register_adapter(JavaAdapter())
register_adapter(JavaScriptAdapter())
register_adapter(GoAdapter())


__all__ = [
    "get_adapter",
    "register_adapter",
    "supported_languages",
]
