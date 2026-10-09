
import shutil

import pytest

from backend.analysis import extract_facts, run_code


def test_c_analysis_and_execution():
    if not shutil.which("gcc"):
        pytest.skip("gcc is not installed")

    code = """
#include <stdio.h>
int add(int a, int b) { return a + b; }
int main() { printf("%d", add(2, 3)); return 0; }
"""
    facts = extract_facts(code, "c")
    assert facts.language == "c"
    assert any(f.name == "add" for f in facts.functions)
    assert "stdio.h" in facts.imports

    result = run_code(code, "c")
    assert result.exception is None
    assert result.exit_code == 0
    assert result.stdout.strip() == "5"


def test_cpp_analysis_and_execution():
    if not shutil.which("g++"):
        pytest.skip("g++ is not installed")

    code = """
#include <iostream>
int main() {
    std::cout << "Hello C++";
    return 0;
}
"""
    facts = extract_facts(code, "cpp")
    assert facts.language == "cpp"

    result = run_code(code, "cpp")
    assert result.exception is None
    assert result.exit_code == 0
    assert "Hello C++" in result.stdout


def test_java_analysis_and_execution():
    if not shutil.which("javac") or not shutil.which("java"):
        pytest.skip("Java compiler/runtime is not installed")

    code = """
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello Java");
    }
}
"""
    facts = extract_facts(code, "java")
    assert facts.language == "java"

    result = run_code(code, "java")
    assert result.exception is None
    assert result.exit_code == 0
    assert "Hello Java" in result.stdout


def test_javascript_analysis_and_execution():
    if not shutil.which("node"):
        pytest.skip("Node.js is not installed")

    code = 'console.log("Hello JavaScript");'
    facts = extract_facts(code, "javascript")
    assert facts.language == "javascript"

    result = run_code(code, "javascript")
    assert result.exception is None
    assert result.exit_code == 0
    assert "Hello JavaScript" in result.stdout


def test_unsupported_language_is_rejected():
    with pytest.raises(ValueError, match="Unsupported language"):
        extract_facts("print('hello')", "rust")

def test_java_detects_add_method():
    code = """
public class Main {
    static int add(int a, int b) {
        return a + b;
    }
    public static void main(String[] args) {
        System.out.println(add(2, 3));
    }
}
"""
    facts = extract_facts(code, "java")

    assert facts.language == "java"
    assert any(f.name == "add" for f in facts.functions)


def test_go_detects_add_function():
    code = """
package main

func add(a int, b int) int {
    return a + b
}

func main() {
    println(add(2, 3))
}
"""
    facts = extract_facts(code, "go")

    assert facts.language == "go"
    assert any(f.name == "add" for f in facts.functions)

