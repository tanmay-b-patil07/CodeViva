from __future__ import annotations

from .compiled import CompiledLanguageAdapter
from .generic import GenericLanguageAdapter


class CppAdapter(
    GenericLanguageAdapter,
    CompiledLanguageAdapter,
):
    def __init__(self):
        GenericLanguageAdapter.__init__(self)

        self.name = "cpp"
        self.extensions = (".cpp", ".cc", ".cxx")
        self.source_filename = "student.cpp"

        self.compile_command = [
            "g++",
            "student.cpp",
            "-o",
            "student_program.exe",
        ]

        self.run_command_builder = (
            lambda temp_dir: [
                f"{temp_dir}\\student_program.exe"
            ]
        )
