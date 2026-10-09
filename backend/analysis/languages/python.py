
from __future__ import annotations

import ast
import hashlib
from typing import Any

from ..models import (
    CodeFacts,
    EdgeCaseInput,
    FunctionFact,
    LoopFact,
)
from .base import LanguageAdapter


class PythonAdapter(LanguageAdapter):
    name = "python"
    extensions = (".py",)

    @staticmethod
    def _generate_edge_cases(
        function_name: str,
        params: list[str],
    ) -> list[EdgeCaseInput]:
        """Generate complete argument lists for common edge cases."""
        if not params:
            return []

        cases: list[EdgeCaseInput] = []

        def default_value(param: str) -> Any:
            name = param.lower()

            if any(
                word in name
                for word in (
                    "list", "array", "items",
                    "values", "nums", "numbers", "elements", "arr",
                )
            ):
                return [1]

            if any(
                word in name
                for word in (
                    "str", "text", "name", "word",
                )
            ):
                return "example"

            if any(
                word in name
                for word in (
                    "number", "num", "value", "count", "size",
                )
            ) or name in ("n", "target", "key"):
                return 1

            return 1

        defaults = [default_value(param) for param in params]

        # Generate a complete argument list for each case.
        for index, param in enumerate(params):
            name = param.lower()

            if any(
                word in name
                for word in (
                    "list", "array", "items",
                    "values", "nums", "numbers", "elements", "arr",
                )
            ):
                empty_args = list(defaults)
                empty_args[index] = []

                single_args = list(defaults)
                single_args[index] = [1]

                cases.append(
                    EdgeCaseInput(
                        function=function_name,
                        args=empty_args,
                        label=f"empty list for {param}",
                    )
                )
                cases.append(
                    EdgeCaseInput(
                        function=function_name,
                        args=single_args,
                        label=f"single-element list for {param}",
                    )
                )

            elif any(
                word in name
                for word in (
                    "number", "num", "value", "count", "size",
                )
            ) or name in ("n", "target", "key"):
                zero_args = list(defaults)
                zero_args[index] = 0

                negative_args = list(defaults)
                negative_args[index] = -1

                cases.append(
                    EdgeCaseInput(
                        function=function_name,
                        args=zero_args,
                        label=f"zero for {param}",
                    )
                )
                cases.append(
                    EdgeCaseInput(
                        function=function_name,
                        args=negative_args,
                        label=f"negative number for {param}",
                    )
                )

            elif any(
                word in name
                for word in ("str", "text", "name", "word")
            ):
                empty_args = list(defaults)
                empty_args[index] = ""

                cases.append(
                    EdgeCaseInput(
                        function=function_name,
                        args=empty_args,
                        label=f"empty string for {param}",
                    )
                )

        # Avoid duplicate inputs.
        unique_cases: list[EdgeCaseInput] = []
        seen: set[str] = set()

        for case in cases:
            key = repr(case.args)
            if key not in seen:
                seen.add(key)
                unique_cases.append(case)

        return unique_cases


    def analyze(self, code: str) -> CodeFacts:
        normalized = code.replace("\r\n", "\n").strip()
        code_hash = (
            "sha256:"
            + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        )
        line_count = len(code.splitlines())

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return CodeFacts(
                language="python",
                code_hash=code_hash,
                line_count=line_count,
                warnings=[
                    f"Syntax error on line {exc.lineno}: {exc.msg}"
                ],
            )

        functions: list[FunctionFact] = []
        loops: list[LoopFact] = []
        imports: set[str] = set()
        data_structures: set[str] = set()

        class Visitor(ast.NodeVisitor):
            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    imports.add(alias.name)
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module:
                    imports.add(node.module)
                self.generic_visit(node)

            def visit_List(self, node: ast.List) -> None:
                data_structures.add("list")
                self.generic_visit(node)

            def visit_Dict(self, node: ast.Dict) -> None:
                data_structures.add("dict")
                self.generic_visit(node)

            def visit_Set(self, node: ast.Set) -> None:
                data_structures.add("set")
                self.generic_visit(node)

            def visit_Tuple(self, node: ast.Tuple) -> None:
                data_structures.add("tuple")
                self.generic_visit(node)

        Visitor().visit(tree)

        def calculate_complexity(node: ast.AST) -> int:
            complexity = 1

            for child in ast.walk(node):
                if isinstance(
                    child,
                    (
                        ast.If,
                        ast.For,
                        ast.While,
                        ast.ExceptHandler,
                        ast.With,
                        ast.IfExp,
                    ),
                ):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1

            return complexity

        def find_calls(node: ast.AST) -> list[str]:
            calls: list[str] = []

            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.append(child.func.attr)

            return sorted(set(calls))

        def contains_self_call(node: ast.AST, name: str) -> bool:
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == name
                ):
                    return True

            return False

        def max_loop_depth(node: ast.AST) -> int:
            maximum = 0

            def walk(current: ast.AST, depth: int) -> None:
                nonlocal maximum

                if isinstance(
                    current,
                    (ast.For, ast.While, ast.AsyncFor),
                ):
                    depth += 1
                    maximum = max(maximum, depth)

                for child in ast.iter_child_nodes(current):
                    walk(child, depth)

            walk(node, 0)
            return maximum

        def visit_loops(
            node: ast.AST,
            function_name: str,
            depth: int,
        ) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(
                    child,
                    (ast.For, ast.While, ast.AsyncFor),
                ):
                    kind = (
                        "for"
                        if isinstance(child, (ast.For, ast.AsyncFor))
                        else "while"
                    )

                    loops.append(
                        LoopFact(
                            kind=kind,
                            start_line=child.lineno,
                            end_line=getattr(
                                child, "end_lineno", child.lineno
                            ),
                            depth=depth + 1,
                            function=function_name,
                        )
                    )

                    visit_loops(
                        child,
                        function_name,
                        depth + 1,
                    )
                else:
                    visit_loops(child, function_name, depth)

        def visit_functions(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    name = child.name
                    params = [
                        arg.arg for arg in child.args.args
                    ]

                    functions.append(
                        FunctionFact(
                            name=name,
                            start_line=child.lineno,
                            end_line=getattr(
                                child, "end_lineno", child.lineno
                            ),
                            params=params,
                            is_recursive=contains_self_call(child, name),
                            cyclomatic_complexity=calculate_complexity(
                                child
                            ),
                            max_loop_depth=max_loop_depth(child),
                            calls=find_calls(child),
                        )
                    )

                    visit_loops(child, name, 0)
                else:
                    visit_functions(child)

        visit_functions(tree)

        edge_cases: list[EdgeCaseInput] = []
        for function in functions:
            edge_cases.extend(
                self._generate_edge_cases(
                    function.name,
                    function.params,
                )
            )

        warnings: list[str] = []
        if not functions:
            warnings.append(
                "No functions were found in the source."
            )

        return CodeFacts(
            language="python",
            code_hash=code_hash,
            line_count=line_count,
            functions=functions,
            loops=loops,
            data_structures=sorted(data_structures),
            imports=sorted(imports),
            edge_case_inputs=edge_cases,
            warnings=warnings,
        )

    def run(
        self,
        code: str,
        function: str | None,
        args: list[Any],
        timeout: float,
    ):
        from ..runner import run_code

        return run_code(
            code=code,
            language="python",
            function=function,
            args=args,
            timeout=timeout,
        )

