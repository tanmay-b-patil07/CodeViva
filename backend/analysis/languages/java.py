from __future__ import annotations

from .compiled import CompiledLanguageAdapter
from .generic import GenericLanguageAdapter


class JavaAdapter(
    GenericLanguageAdapter,
    CompiledLanguageAdapter,
):
    def __init__(self):
        GenericLanguageAdapter.__init__(self)

        self.name = "java"
        self.extensions = (".java",)
        self.source_filename = "Main.java"

        self.compile_command = [
            "javac",
            "Main.java",
        ]

        self.run_command_builder = (
            lambda temp_dir: [
                "java",
                "-cp",
                temp_dir,
                "Main",
            ]
        )