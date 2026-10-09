
from backend.analysis import extract_facts


def test_edge_case_inputs_include_all_function_arguments():
    code = """
def binary_search(arr, target):
    for item in arr:
        if item == target:
            return True
    return False
"""

    facts = extract_facts(code, "python")

    function = next(
        f for f in facts.functions if f.name == "binary_search"
    )

    edge_cases = [
        case for case in facts.edge_case_inputs
        if case.function == "binary_search"
    ]

    assert edge_cases, "Expected edge cases for binary_search"

    for case in edge_cases:
        assert len(case.args) == len(function.params), (
            f"Incomplete arguments for {case.label}: "
            f"expected {len(function.params)}, got {len(case.args)}"
        )
