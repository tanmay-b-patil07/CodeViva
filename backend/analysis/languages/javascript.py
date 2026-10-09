from __future__ import annotations

from .compiled import CompiledLanguageAdapter
from .generic import GenericLanguageAdapter


class JavaScriptAdapter(
    GenericLanguageAdapter,
    CompiledLanguageAdapter,
):
    def __init__(self):
        GenericLanguageAdapter.__init__(self)

        self.name = "javascript"
        self.extensions = (".js", ".mjs")
        self.source_filename = "student.js"

        self.compile_command = None

        self.run_command_builder = (
            lambda temp_dir: [
                "node",
                "student.js",
            ]
        )