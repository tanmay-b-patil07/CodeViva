from __future__ import annotations

import hashlib
import re

from ..models import CodeFacts, FunctionFact, LoopFact
from .base import LanguageAdapter


class GenericLanguageAdapter(LanguageAdapter):
    """
    Lightweight static analyzer for C, C++, Java and JavaScript.

    This is intentionally conservative:
    - It extracts facts we can identify reliably with regex/patterns.
    - It does not pretend to fully parse the language.
    - Execution remains the source of truth for runtime behavior.
    """

    def analyze(self, code: str) -> CodeFacts:
        source = code.replace("\r\n", "\n").replace("\r", "\n")
        lines = source.splitlines()

        language = self.name
        code_hash = "sha256:" + hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()

        functions = self._extract_functions(source, lines)
        loops = self._extract_loops(source, lines)
        imports = self._extract_imports(source)
        data_structures = self._extract_data_structures(source)

        warnings: list[str] = []

        if not functions:
            warnings.append(
                f"No functions/methods detected for {language}."
            )

        return CodeFacts(
            language=language,
            code_hash=code_hash,
            line_count=len(lines),
            functions=functions,
            loops=loops,
            data_structures=data_structures,
            imports=imports,
            edge_case_inputs=[],
            warnings=warnings,
        )

    def _extract_functions(
        self,
        code: str,
        lines: list[str],
    ) -> list[FunctionFact]:

        results: list[FunctionFact] = []

        patterns = [
            # Java / C / C++:
            # int add(int a, int b) {
            re.compile(
                r"(?:public|private|protected|static|final|\s)*"
                r"(?:[A-Za-z_][\w:<>,\[\]]*\s+)+"
                r"([A-Za-z_]\w*)\s*"
                r"\(([^)]*)\)\s*\{"
            ),

            # JavaScript:
            re.compile(
                r"(?:function\s+([A-Za-z_]\w*)\s*\(([^)]*)\)"
                r"|([A-Za-z_]\w*)\s*=\s*\(([^)]*)\)\s*=>)"
            ),
        ]

        used_names: set[str] = set()

        for pattern in patterns:
            for match in pattern.finditer(code):

                groups = match.groups()

                name = None
                params_text = ""

                for index in range(0, len(groups), 2):
                    if groups[index]:
                        name = groups[index]
                        params_text = groups[index + 1] or ""
                        break

                if not name:
                    continue

                if name in used_names:
                    continue

                used_names.add(name)

                start_position = match.start()
                start_line = code[:start_position].count("\n") + 1

                end_line = self._find_block_end(
                    lines,
                    start_line,
                )

                params = self._parse_params(params_text)

                body = "\n".join(
                    lines[start_line - 1:end_line]
                )

                complexity = 1 + len(
                    re.findall(
                        r"\b(if|else\s+if|for|while|case|catch|&&|\|\|)\b",
                        body,
                    )
                )

                is_recursive = bool(
                    re.search(
                        rf"\b{re.escape(name)}\s*\(",
                        body,
                    )
                )

                # The declaration itself can trigger the regex above,
                # so verify that another call exists.
                declaration_calls = len(
                    re.findall(
                        rf"\b{re.escape(name)}\s*\(",
                        body,
                    )
                )

                is_recursive = declaration_calls > 1

                calls = self._extract_calls(body, name)

                results.append(
                    FunctionFact(
                        name=name,
                        start_line=start_line,
                        end_line=end_line,
                        params=params,
                        is_recursive=is_recursive,
                        cyclomatic_complexity=max(1, complexity),
                        max_loop_depth=self._estimate_loop_depth(body),
                        calls=calls,
                    )
                )

        return results

    def _extract_loops(
        self,
        code: str,
        lines: list[str],
    ) -> list[LoopFact]:

        loops: list[LoopFact] = []

        pattern = re.compile(
            r"\b(for|while|do)\b"
        )

        for match in pattern.finditer(code):

            kind = match.group(1)

            start_line = (
                code[:match.start()].count("\n") + 1
            )

            end_line = self._find_block_end(
                lines,
                start_line,
            )

            function = self._function_for_line(
                start_line,
                self._extract_functions(code, lines),
            )

            loops.append(
                LoopFact(
                    kind=kind,
                    start_line=start_line,
                    end_line=end_line,
                    depth=1,
                    function=function,
                )
            )

        return loops

    def _extract_imports(
        self,
        code: str,
    ) -> list[str]:

        imports: list[str] = []

        patterns = [
            r"^\s*#include\s*[<\"]([^>\"]+)[>\"]",
            r"^\s*import\s+([A-Za-z_][\w.]*)",
            r"^\s*from\s+([A-Za-z_][\w.]*)\s+import",
            r"^\s*import\s+\{?([^}]+)\}?\s+from",
        ]

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                code,
                re.MULTILINE,
            ):
                value = match.group(1).strip()

                if value not in imports:
                    imports.append(value)

        return imports

    def _extract_data_structures(
        self,
        code: str,
    ) -> list[str]:

        structures: list[str] = []

        checks = {
            "array": r"\[[^\]]*\]",
            "list": r"\b(?:ArrayList|List|vector|array|Array)\b",
            "map": r"\b(?:HashMap|Map|unordered_map|Map)\b",
            "set": r"\b(?:HashSet|Set|unordered_set)\b",
            "stack": r"\b(?:Stack|stack)\b",
            "queue": r"\b(?:Queue|queue)\b",
        }

        for name, pattern in checks.items():
            if re.search(pattern, code):
                if name not in structures:
                    structures.append(name)

        return structures

    @staticmethod
    def _parse_params(params_text: str) -> list[str]:

        if not params_text.strip():
            return []

        params: list[str] = []

        for item in params_text.split(","):
            item = item.strip()

            if not item:
                continue

            # Remove Java/C/C++ type declarations.
            item = re.sub(
                r"\b(?:const|final|volatile|static)\b",
                "",
                item,
            ).strip()

            parts = re.split(
                r"\s+",
                item,
            )

            if parts:
                name = parts[-1]
                name = name.replace("*", "")
                name = name.replace("&", "")
                name = name.strip()

                if re.match(
                    r"^[A-Za-z_]\w*$",
                    name,
                ):
                    params.append(name)

        return params
    def _extract_functions(
        self,
        code: str,
        lines: list[str],
    ) -> list[FunctionFact]:
        results: list[FunctionFact] = []
        used_names: set[str] = set()

        # Match function/method declarations line-by-line.
        patterns = [
            # C / C++ / Java
            re.compile(
                r"^\s*"
                r"(?:(?:public|private|protected|static|final|"
                r"virtual|inline|const|async|export)\s+)*"
                r"(?:[A-Za-z_][\w:<>,\[\]*&]*\s+)+"
                r"([A-Za-z_]\w*)"
                r"\s*\(([^)]*)\)\s*\{"
            ),

            # JavaScript function declaration
            re.compile(
                r"^\s*function\s+"
                r"([A-Za-z_]\w*)"
                r"\s*\(([^)]*)\)\s*\{"
            ),

            # JavaScript arrow function
            re.compile(
                r"^\s*(?:const|let|var)\s+"
                r"([A-Za-z_]\w*)"
                r"\s*=\s*"
                r"\(([^)]*)\)\s*=>\s*\{"
            ),
        ]

        for line_number, line in enumerate(lines, start=1):

            match = None

            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    break

            if not match:
                continue

            name = match.group(1)

            if name in used_names:
                continue

            used_names.add(name)

            params_text = match.group(2) or ""

            end_line = self._find_block_end(
                lines,
                line_number,
            )

            body_lines = lines[
                line_number:end_line
            ]

            body = "\n".join(body_lines)

            complexity = 1 + len(
                re.findall(
                    r"\b(if|else\s+if|for|while|case|catch)\b"
                    r"|&&|\|\|",
                    body,
                )
            )

            recursive_calls = re.findall(
                rf"\b{re.escape(name)}\s*\(",
                body,
            )

            is_recursive = len(recursive_calls) > 0

            calls = self._extract_calls(
                body,
                name,
            )

            results.append(
                FunctionFact(
                    name=name,
                    start_line=line_number,
                    end_line=end_line,
                    params=self._parse_params(
                        params_text
                    ),
                    is_recursive=is_recursive,
                    cyclomatic_complexity=max(
                        1,
                        complexity,
                    ),
                    max_loop_depth=self._estimate_loop_depth(
                        body
                    ),
                    calls=calls,
                )
            )

        return results

    @staticmethod
    def _extract_calls(
        body: str,
        function_name: str,
    ) -> list[str]:

        calls = re.findall(
            r"\b([A-Za-z_]\w*)\s*\(",
            body,
        )

        ignored = {
            "if",
            "for",
            "while",
            "switch",
            "catch",
            "sizeof",
        }

        result: list[str] = []

        for call in calls:

            # Don't count the function itself as a call.
            if call == function_name:
                continue

            # Don't count language keywords.
            if call in ignored:
                continue

            if call not in result:
                result.append(call)

        return result
    @staticmethod
    def _find_block_end(
        lines: list[str],
        start_line: int,
    ) -> int:

        depth = 0
        started = False

        for index in range(
            start_line - 1,
            len(lines),
        ):

            line = lines[index]

            opens = line.count("{")
            closes = line.count("}")

            if opens:
                started = True

            if started:
                depth += opens
                depth -= closes

                if depth <= 0:
                    return index + 1

        return min(
            start_line,
            len(lines),
        )

    @staticmethod
    def _estimate_loop_depth(
        body: str,
    ) -> int:

        max_depth = 0
        current_depth = 0

        for line in body.splitlines():

            if re.search(
                r"\b(for|while|do)\b",
                line,
            ):
                current_depth += 1
                max_depth = max(
                    max_depth,
                    current_depth,
                )

            if "}" in line and current_depth:
                current_depth -= line.count("}")

        return max_depth

    @staticmethod
    def _function_for_line(
        line: int,
        functions: list[FunctionFact],
    ) -> str | None:

        for function in functions:
            if (
                function.start_line
                <= line
                <= function.end_line
            ):
                return function.name

        return None
    