# call_graph.py
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Union


@dataclass
class FunctionNode:
    name: str
    qualified_name: str
    file_path: Path
    lineno: int
    end_lineno: int
    code: str
    calls: Set[str] = field(default_factory=set)
    called_by: Set[str] = field(default_factory=set)


class CallGraphBuilder(ast.NodeVisitor):

    def __init__(self):
        self.functions: Dict[str, FunctionNode] = {}
        self.current_file: Optional[Path] = None
        self.current_module: str = ""
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        self._source_lines: List[str] = []

    def _qualified_name(self, name: str) -> str:
        parts = [self.current_module]
        if self.current_class:
            parts.append(self.current_class)
        parts.append(name)
        return ".".join(parts)

    def _extract_code(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]) -> str:
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        return "\n".join(self._source_lines[start:end])

    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_function(node)

    def _process_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        assert self.current_file is not None

        qualified = self._qualified_name(node.name)
        code = self._extract_code(node)

        fn = FunctionNode(
            name=node.name,
            qualified_name=qualified,
            file_path=self.current_file,
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            code=code,
        )

        old_func = self.current_function
        self.current_function = qualified

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._resolve_call_name(child)
                if call_name:
                    fn.calls.add(call_name)

        self.functions[qualified] = fn
        self.current_function = old_func

    def _resolve_call_name(self, node: ast.Call) -> Optional[str]:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            parts = []
            current = func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            parts.reverse()
            return ".".join(parts)
        return None

    def parse_file(self, file_path: Path, module_name: str):
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return

        self.current_file = file_path
        self.current_module = module_name
        self._source_lines = source.splitlines()
        self.visit(tree)

    def build(self, repo_path: Path) -> Dict[str, FunctionNode]:
        for py_file in repo_path.rglob("*.py"):
            if not py_file.is_file():
                continue
            parts = py_file.relative_to(repo_path).parts
            if any(p.startswith(".") or p in ("venv", ".venv", "node_modules", "__pycache__", "build", "dist") for p in parts):
                continue

            rel = py_file.relative_to(repo_path)
            module_name = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
            self.parse_file(py_file, module_name)

        self._build_reverse_edges()
        return self.functions

    def _build_reverse_edges(self):
        name_to_qualified: Dict[str, List[str]] = {}
        for qn, fn in self.functions.items():
            simple = fn.name
            name_to_qualified.setdefault(simple, []).append(qn)

        for qn, fn in self.functions.items():
            for call_name in fn.calls:
                candidates = []

                if call_name in self.functions:
                    candidates.append(call_name)

                simple = call_name.split(".")[-1]
                if simple in name_to_qualified:
                    candidates.extend(name_to_qualified[simple])

                if "." in call_name:
                    method = call_name.split(".")[-1]
                    if method in name_to_qualified:
                        candidates.extend(name_to_qualified[method])

                for candidate in set(candidates):
                    if candidate in self.functions and candidate != qn:
                        self.functions[candidate].called_by.add(qn)


def build_call_graph(repo_path: Path) -> Dict[str, FunctionNode]:
    builder = CallGraphBuilder()
    return builder.build(repo_path)


def get_downstream_dependents(
    graph: Dict[str, FunctionNode],
    changed_functions: List[str],
    max_depth: int = 3,
) -> List[FunctionNode]:
    visited: Set[str] = set()
    dependents: List[FunctionNode] = []

    def dfs(name: str, depth: int):
        if depth > max_depth or name in visited:
            return
        visited.add(name)

        if name in graph:
            fn = graph[name]
            for caller in fn.called_by:
                if caller not in visited and caller in graph:
                    dependents.append(graph[caller])
                    dfs(caller, depth + 1)

    for fn_name in changed_functions:
        dfs(fn_name, 0)

    return dependents


def get_upstream_dependencies(
    graph: Dict[str, FunctionNode],
    function_name: str,
    max_depth: int = 3,
) -> List[FunctionNode]:
    visited: Set[str] = set()
    dependencies: List[FunctionNode] = []

    def dfs(name: str, depth: int):
        if depth > max_depth or name in visited:
            return
        visited.add(name)

        if name in graph:
            fn = graph[name]
            for callee_name in fn.calls:
                if callee_name in graph and callee_name not in visited:
                    dependencies.append(graph[callee_name])
                    dfs(callee_name, depth + 1)

    dfs(function_name, 0)
    return dependencies
