from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from typing import Any

from ..models import RunResult
from .base import LanguageAdapter


MAX_OUTPUT_SIZE = 10_000


def _safe_environment() -> dict[str, str]:
    """
    Provide runtimes with the minimum useful Windows environment
    without exposing the user's full environment.
    """
    environment: dict[str, str] = {}

    for key in (
        "PATH",
        "SystemRoot",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "SystemDrive",
        "ComSpec",
    ):
        value = os.environ.get(key)
        if value:
            environment[key] = value

    environment["LANG"] = "C.UTF-8"

    return environment


class CompiledLanguageAdapter(LanguageAdapter):

    def __init__(
        self,
        name: str,
        source_filename: str,
        compile_command: list[str] | None,
        run_command_builder,
        extensions: tuple[str, ...],
    ):
        self.name = name
        self.source_filename = source_filename
        self.compile_command = compile_command
        self.run_command_builder = run_command_builder
        self.extensions = extensions

    def analyze(self, code: str):
        raise NotImplementedError(
            f"Static analysis for {self.name} is not implemented yet."
        )

    def run(
        self,
        code: str,
        function: str | None,
        args: list[Any],
        timeout: float,
    ) -> RunResult:

        start_time = time.perf_counter()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:

                source_path = os.path.join(
                    temp_dir,
                    self.source_filename,
                )

                with open(
                    source_path,
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(code)

                environment = _safe_environment()

                # -------------------------
                # Compile
                # -------------------------
                if self.compile_command:

                    compiler = self.compile_command[0]

                    if shutil.which(compiler) is None:
                        return RunResult(
                            language=self.name,
                            exception=(
                                f"Required compiler '{compiler}' "
                                "is not installed or not available on PATH."
                            ),
                            execution_time_ms=(
                                time.perf_counter() - start_time
                            )
                            * 1000,
                        )

                    try:
                        compile_result = subprocess.run(
                            self.compile_command,
                            cwd=temp_dir,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            timeout=timeout,
                            env=environment,
                        )

                    except subprocess.TimeoutExpired:
                        return RunResult(
                            language=self.name,
                            exception="Compilation timed out.",
                            timed_out=True,
                            execution_time_ms=(
                                time.perf_counter() - start_time
                            )
                            * 1000,
                        )

                    if compile_result.returncode != 0:
                        return RunResult(
                            language=self.name,
                            stdout=compile_result.stdout[
                                :MAX_OUTPUT_SIZE
                            ],
                            stderr=compile_result.stderr[
                                :MAX_OUTPUT_SIZE
                            ],
                            exception="Compilation failed.",
                            exit_code=compile_result.returncode,
                            execution_time_ms=(
                                time.perf_counter() - start_time
                            )
                            * 1000,
                        )

                # -------------------------
                # Run
                # -------------------------
                command = self.run_command_builder(temp_dir)

                executable = command[0]

                # For external runtimes, verify availability.
                if not os.path.isabs(executable):
                    if shutil.which(executable) is None:
                        return RunResult(
                            language=self.name,
                            exception=(
                                f"Required runtime '{executable}' "
                                "is not installed or not available on PATH."
                            ),
                            execution_time_ms=(
                                time.perf_counter() - start_time
                            )
                            * 1000,
                        )

                try:
                    result = subprocess.run(
                        command,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=timeout,
                        env=environment,
                    )

                except subprocess.TimeoutExpired:
                    return RunResult(
                        language=self.name,
                        exception="Execution timed out.",
                        timed_out=True,
                        execution_time_ms=(
                            time.perf_counter() - start_time
                        )
                        * 1000,
                    )

                return RunResult(
                    language=self.name,
                    stdout=result.stdout[:MAX_OUTPUT_SIZE],
                    stderr=result.stderr[:MAX_OUTPUT_SIZE],
                    exception=(
                        result.stderr[:2000]
                        if result.returncode != 0
                        else None
                    ),
                    exit_code=result.returncode,
                    timed_out=False,
                    execution_time_ms=(
                        time.perf_counter() - start_time
                    )
                    * 1000,
                )

        except FileNotFoundError as exc:

            return RunResult(
                language=self.name,
                exception=(
                    f"Required compiler/runtime could not be launched: "
                    f"{exc}"
                ),
                execution_time_ms=(
                    time.perf_counter() - start_time
                )
                * 1000,
            )

        except Exception as exc:

            return RunResult(
                language=self.name,
                exception=str(exc),
                execution_time_ms=(
                    time.perf_counter() - start_time
                )
                * 1000,
            )
