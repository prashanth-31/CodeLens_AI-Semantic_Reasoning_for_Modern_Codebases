# writer.py
from pathlib import Path
from typing import Dict, List

from .code_parser import FunctionInfo
from .config import DOCS_DIR_NAME


def inject_docstrings_into_file(
    file_path: Path,
    func_docs: Dict[int, str],
) -> None:
    lines = file_path.read_text(encoding="utf-8").splitlines()

    for lineno in sorted(func_docs.keys(), reverse=True):
        def_index = lineno - 1
        raw_doc = func_docs[lineno]

        def_indent = _get_indent(lines[def_index])
        body_indent = def_indent + " " * 4

        doc_lines = raw_doc.strip().splitlines()

        if not doc_lines[0].lstrip().startswith('"""'):
            doc_lines.insert(0, '"""' + doc_lines[0].lstrip())
        if not doc_lines[-1].rstrip().endswith('"""'):
            doc_lines[-1] = doc_lines[-1].rstrip() + '"""'

        indented_doc_lines = [body_indent + line.lstrip() for line in doc_lines]

        insert_pos = def_index + 1
        lines[insert_pos:insert_pos] = indented_doc_lines

    file_path.write_text("\n".join(lines), encoding="utf-8")


def _get_indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def write_module_markdown(
    repo_path: Path,
    file_path: Path,
    module_overview: str,
    functions: List[FunctionInfo],
) -> None:
    docs_root = repo_path / DOCS_DIR_NAME
    docs_root.mkdir(parents=True, exist_ok=True)

    rel = file_path.relative_to(repo_path)
    safe_name = str(rel).replace("/", "_").replace("\\", "_")
    out_path = docs_root / f"{safe_name}.md"

    lines = [
        f"# Documentation for `{rel}`",
        "",
        "## Module Overview",
        "",
        module_overview,
        "",
        "## Functions",
        "",
    ]
    for func in functions:
        lines.append(f"### `{func.name}({', '.join(func.args)})`")
        lines.append("")
        lines.append("*(Docstring will appear in code file; see source.)*")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
