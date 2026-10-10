
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

from ..languages import get_adapter
from ..models import RunResult


MAX_OUTPUT_SIZE = 10_000
DEFAULT_TIMEOUT = 3.0
MAX_TIMEOUT = 10.0


def _safe_json(args: list[Any]) -> str:
    try:
        return json.dumps(args, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Arguments must be JSON serializable."
        ) from exc


def _safe_environment() -> dict[str, str]:
    """Pass only the minimum environment needed by the child."""
    env = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }

    # Windows needs system variables for reliable process startup.
    if os.name == "nt":
        for key in ("SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
            value = os.environ.get(key)
            if value:
                env[key] = value

    return env


def _stop_process_tree(process: subprocess.Popen) -> None:
    """Best-effort termination of the child and its process tree."""
    if process.poll() is not None:
        return

    try:
        if os.name == "nt":
            # Windows: terminate descendants as well as the parent.
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
        else:
            # POSIX: Popen starts a new session/process group.
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill()
        except OSError:
            pass

    # taskkill can report success or failure without ending a process in a
    # restricted Windows execution context. Preserve the process-tree attempt,
    # but always fall back to terminating the direct child if it survived.
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass

    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def _run_limited_process(
    command: list[str],
    *,
    cwd: str,
    timeout: float,
    env: dict[str, str],
) -> dict[str, Any]:
    """Capture bounded output and stop a process that exceeds the cap."""
    creationflags = 0
    popen_options: dict[str, Any] = {}

    if os.name == "nt":
        creationflags = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        popen_options["start_new_session"] = True

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        **popen_options,
    )

    output: dict[str, bytearray] = {
        "stdout": bytearray(),
        "stderr": bytearray(),
    }
    exceeded_output_limit = threading.Event()
    reader_errors: list[BaseException] = []

    def drain(stream, key: str) -> None:
        try:
            while True:
                chunk = stream.read(1024)
                if not chunk:
                    break

                remaining = MAX_OUTPUT_SIZE - len(output[key])
                if remaining > 0:
                    output[key].extend(chunk[:remaining])

                if len(chunk) > remaining:
                    exceeded_output_limit.set()
                    _stop_process_tree(process)
                    break
        except (OSError, ValueError) as exc:
            reader_errors.append(exc)

    threads = [
        threading.Thread(
            target=drain,
            args=(process.stdout, "stdout"),
            daemon=True,
        ),
        threading.Thread(
            target=drain,
            args=(process.stderr, "stderr"),
            daemon=True,
        ),
    ]

    for thread in threads:
        thread.start()

    timed_out = False
    deadline = time.monotonic() + timeout

    try:
        while process.poll() is None:
            if exceeded_output_limit.is_set():
                break

            if time.monotonic() >= deadline:
                timed_out = True
                _stop_process_tree(process)
                break

            time.sleep(0.02)
    finally:
        if process.poll() is None:
            _stop_process_tree(process)

        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _stop_process_tree(process)

        for thread in threads:
            thread.join(timeout=2)

        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    return {
        "stdout": output["stdout"].decode("utf-8", errors="replace"),
        "stderr": output["stderr"].decode("utf-8", errors="replace"),
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "output_limited": exceeded_output_limit.is_set(),
        "reader_error": bool(reader_errors),
    }


def run_code(
    code: str,
    language: str = "python",
    function: str | None = None,
    args: list[Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> RunResult:
    args = args or []
    language = language.strip().lower()
    start_time = time.perf_counter()

    timeout = max(0.1, min(float(timeout), MAX_TIMEOUT))

    try:
        # Validate arguments before starting a process.
        arguments_json = _safe_json(args)

        if language != "python":
            adapter = get_adapter(language)
            return adapter.run(
                code=code,
                function=function,
                args=args,
                timeout=timeout,
            )

        with tempfile.TemporaryDirectory(prefix="codeviva_") as temp_dir:
            return _run_python(
                code=code,
                function=function,
                arguments_json=arguments_json,
                temp_dir=temp_dir,
                timeout=timeout,
                start_time=start_time,
            )

    except ValueError as exc:
        return RunResult(
            language=language,
            exception=str(exc),
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
        )
    except Exception as exc:
        return RunResult(
            language=language,
            exception=f"Runner error: {exc}",
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
        )


def _run_python(
    code: str,
    function: str | None,
    arguments_json: str,
    temp_dir: str,
    timeout: float,
    start_time: float,
) -> RunResult:
    source_file = os.path.join(temp_dir, "student_code.py")
    wrapper_file = os.path.join(temp_dir, "runner.py")

    with open(source_file, "w", encoding="utf-8") as file:
        file.write(code)

    wrapper_code = r'''
import json
import sys
import traceback

source_file = sys.argv[1]
function_name = sys.argv[2]
arguments_json = sys.argv[3]

namespace = {"__name__": "__student_module__"}

try:
    with open(source_file, "r", encoding="utf-8") as file:
        source = file.read()

    compiled = compile(source, source_file, "exec")
    exec(compiled, namespace)

    arguments = json.loads(arguments_json)

    if function_name:
        target = namespace.get(function_name)
        if not callable(target):
            raise RuntimeError(
                f"Function '{function_name}' was not found."
            )
        result = target(*arguments)
        print("__CODEVIVA_RETURN__" + repr(result))

except BaseException as exc:
    print("__CODEVIVA_EXCEPTION__" + repr(exc))
    traceback.print_exc()
    sys.exit(1)
'''

    with open(wrapper_file, "w", encoding="utf-8") as file:
        file.write(wrapper_code)

    command = [
        sys.executable,
        "-I",
        wrapper_file,
        source_file,
        function or "",
        arguments_json,
    ]

    result = _run_limited_process(
        command,
        cwd=temp_dir,
        timeout=timeout,
        env=_safe_environment(),
    )

    stdout = result["stdout"]
    stderr = result["stderr"]
    return_value = None
    exception = None
    clean_lines = []

    for line in stdout.splitlines():
        if line.startswith("__CODEVIVA_RETURN__"):
            return_value = line[len("__CODEVIVA_RETURN__"):]
        elif line.startswith("__CODEVIVA_EXCEPTION__"):
            exception = line[len("__CODEVIVA_EXCEPTION__"):]
        else:
            clean_lines.append(line)

    if result["timed_out"]:
        exception = "Execution timed out."
        stderr = (stderr + "\nExecution timed out.").strip()
    elif result["output_limited"]:
        exception = "Output limit exceeded."
        stderr = (stderr + "\nOutput limit exceeded.").strip()
    elif result["reader_error"]:
        exception = "Failed to capture process output."

    return RunResult(
        language="python",
        stdout="\n".join(clean_lines),
        stderr=stderr,
        return_value=return_value,
        exception=exception,
        exit_code=result["exit_code"],
        timed_out=result["timed_out"],
        execution_time_ms=(time.perf_counter() - start_time) * 1000,
    )
