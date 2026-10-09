from backend.analysis import trace_run


def test_trace_run_records_lines():
    code = """
def add(a, b):
    total = a + b
    return total

add(2, 3)
"""

    trace = trace_run(
        code=code,
        function="add",
        args=[2, 3],
        max_steps=20,
    )

    assert trace
    assert len(trace) <= 20

    lines = [step.line for step in trace]

    assert 3 in lines
    assert 4 in lines


def test_trace_contains_local_variables():
    code = """
def calculate(a, b):
    total = a + b
    result = total * 2
    return result

calculate(3, 4)
"""

    trace = trace_run(
        code=code,
        function="calculate",
        args=[3, 4],
        max_steps=20,
    )

    assert trace

    all_locals = {}

    for step in trace:
        all_locals.update(step.locals)

    assert "a" in all_locals
    assert "b" in all_locals
    assert "total" in all_locals


def test_trace_respects_max_steps():
    code = """
def count():
    i = 0
    while i < 1000:
        i += 1
    return i

count()
"""

    trace = trace_run(
        code=code,
        function="count",
        args=[],
        max_steps=5,
    )

    assert len(trace) <= 5
