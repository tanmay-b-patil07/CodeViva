from backend.analysis import extract_facts


def test_python_analysis():

    code = """
def add(a, b):
    return a + b
"""

    facts = extract_facts(code, "python")

    assert facts.language == "python"
    assert facts.line_count == 3
    assert len(facts.functions) == 1

    function = facts.functions[0]

    assert function.name == "add"
    assert function.params == ["a", "b"]
    assert function.is_recursive is False
