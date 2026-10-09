from __future__ import annotations

import sys
from typing import Any

from .models import TraceStep


def trace_run(
    code: str,
    function: str,
    args: list[Any],
    max_steps: int = 5000,
) -> list[TraceStep]:

    namespace: dict[str, Any] = {}
    trace_steps: list[TraceStep] = []
    step_counter = 0

    def tracer(frame, event, arg):

        nonlocal step_counter

        if event != "line":
            return tracer

        if frame.f_code.co_name != function:
            return tracer

        if step_counter >= max_steps:
            return tracer

        step_counter += 1

        local_values: dict[str, Any] = {}

        for name, value in frame.f_locals.items():
            try:
                representation = repr(value)

                if len(representation) > 500:
                    representation = (
                        representation[:500]
                        + "...<truncated>"
                    )

                local_values[name] = representation

            except Exception:
                local_values[name] = "<unrepresentable>"

        trace_steps.append(
            TraceStep(
                step=step_counter,
                line=frame.f_lineno,
                function=frame.f_code.co_name,
                locals=local_values,
            )
        )

        return tracer

    try:
        compiled = compile(
            code,
            "<student_code>",
            "exec",
        )

        exec(compiled, namespace)

        target = namespace.get(function)

        if not callable(target):
            return []

        sys.settrace(tracer)

        target(*args)

    except Exception:
        pass

    finally:
        sys.settrace(None)

    return trace_steps
