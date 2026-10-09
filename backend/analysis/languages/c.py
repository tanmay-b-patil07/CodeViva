from __future__ import annotations

from .compiled import CompiledLanguageAdapter
from .generic import GenericLanguageAdapter


class CAdapter(
    GenericLanguageAdapter,
    CompiledLanguageAdapter,
):
    def __init__(self):
        GenericLanguageAdapter.__init__(self)

        self.name = "c"
        self.extensions = (".c",)
        self.source_filename = "student.c"

        self.compile_command = [
            "gcc",
            "student.c",
            "-o",
            "student_program.exe",
        ]

        self.run_command_builder = (
            lambda temp_dir: [
                f"{temp_dir}\\student_program.exe"
            ]
        )