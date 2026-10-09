from __future__ import annotations

from .compiled import CompiledLanguageAdapter
from .generic import GenericLanguageAdapter


class GoAdapter(
    GenericLanguageAdapter,
    CompiledLanguageAdapter,
):
    def __init__(self):
        GenericLanguageAdapter.__init__(self)

        self.name = "go"
        self.extensions = (".go",)
        self.source_filename = "student.go"

        self.compile_command = None

        self.run_command_builder = (
            lambda temp_dir: [
                "go",
                "run",
                "student.go",
            ]
        )