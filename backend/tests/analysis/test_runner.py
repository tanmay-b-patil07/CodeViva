from backend.analysis import run_code


def test_python_function_execution():

    code = """
def add(a, b):
    return a + b
"""

    result = run_code(
        code=code,
        language="python",
        function="add",
        args=[10, 20],
    )

    assert result.timed_out is False
    assert result.exception is None
    assert result.return_value == "30"


def test_python_timeout():

    code = """
def infinite():
    while True:
        pass
"""

    result = run_code(
        code=code,
        language="python",
        function="infinite",
        args=[],
        timeout=1,
    )

    assert result.timed_out is True


def test_python_output_limit_is_enforced():
    code = """
def noisy():
    print("x" * 11000)
"""

    result = run_code(
        code=code,
        language="python",
        function="noisy",
        timeout=3.0,
    )

    assert result.exception == "Output limit exceeded."
    assert result.timed_out is False
